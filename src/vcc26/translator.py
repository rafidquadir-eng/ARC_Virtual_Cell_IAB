"""M-1: a learned cross-line translator for perturbation responses.

For a target line L (the held-out or challenge context), a knocked-down gene t and a readout gene g,
it predicts L's log2FC from what the OTHER lines measured for t, plus context features. It is
trained only on the source lines handed to it, by rotating each source line into the "target" role
with the remaining lines as evidence, so the held-out line is never seen (no leakage). The training
rows are subsampled: every gene that is notable in the evidence or a cis neighbour, plus a random
background sample.

Features per (t, g, L):
  mu, |z|, agree, k (the B5 cross-line meta-analysis of t's effect on g), max/min/std over lines,
  nearest-line effect (the most control-similar evidence line) and that line's similarity,
  log1p control CPM of g in L, mean in the evidence lines, and their difference,
  log1p control CPM of t in L (can it be knocked down?), cis distance bin of g from t (-1 = none),
  g's responsiveness (mean |lfc| over all perturbations in the evidence), t's mean knockdown in the
  evidence, t's response size (mean |mu|).
Model: sklearn HistGradientBoostingRegressor (CPU), weights 1 / (noise variance in L + 0.01).

Used as models.MODELS["M1_gbm"]; the fitted model is cached per source set, so all specs share it.
"""
from __future__ import annotations

import hashlib
import warnings

import numpy as np

from . import models as M

FEATS = ["mu", "absz", "agree", "k", "emax", "emin", "estd", "near", "near_r", "lcpm_L", "lcpm_E",
         "lcpm_diff", "tcpm_L", "cis_bin", "resp_g", "kd_t", "size_t"]
_CACHE: dict = {}


def _lines(sources):
    out = {}
    for s in sources:
        out.setdefault(s.get("line") or s.get("name"), []).append(s)
    return out


def _prep(s, pc=1.0):
    if "_lfcpc" not in s or s.get("_pc") != pc:
        s["_lfcpc"] = M._lfc_pc(s, pc); s["_varpc"] = M._noise_var(s, s["_lfcpc"], pc); s["_pc"] = pc
    if "_resp" not in s:
        v = s["present"] & (s["ctrl_cpm"] > M.EPS_CPM)
        s["_resp"] = np.where(v, np.abs(s["_lfcpc"]).mean(0), np.nan)
        s["_tpos"] = {p: i for i, p in enumerate(s["perts"])}


def _line_stack(srcs_by_line, t):
    """Per evidence line (merged datasets): effect, variance, ctrl CPM, kd."""
    E, V, C, K, names = [], [], [], [], []
    for L, ss in srcs_by_line.items():
        num = den = None; cc = []; kk = []
        for s in ss:
            i = s["_tpos"].get(t)
            if i is None:
                continue
            v = s["present"] & (s["ctrl_cpm"] > M.EPS_CPM)
            w = np.where(v, 1.0 / np.maximum(s["_varpc"][i], 1e-8), 0.0)
            num = w * s["_lfcpc"][i] if num is None else num + w * s["_lfcpc"][i]
            den = w if den is None else den + w
            cc.append(s["ctrl_cpm"]); kk.append(s["kd"][i])
        if den is None:
            continue
        E.append(np.where(den > 0, num / np.maximum(den, 1e-12), 0.0))
        V.append(np.where(den > 0, 1.0 / np.maximum(den, 1e-12), np.inf))
        C.append(np.mean(cc, 0)); K.append(np.nanmean(kk)); names.append(L)
    return names, E, V, C, K


def features(t, genes_idx, ev_lines, L_ctrl, gpos, cis, line_r):
    """Feature matrix (len(genes_idx), len(FEATS)) for target t from evidence lines."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return _features(t, genes_idx, ev_lines, L_ctrl, gpos, cis, line_r)


def _features(t, genes_idx, ev_lines, L_ctrl, gpos, cis, line_r):
    names, E, V, C, K = _line_stack(ev_lines, t)
    n = len(genes_idx)
    if not names:
        return None
    E = np.vstack(E)[:, genes_idx]; V = np.vstack(V)[:, genes_idx]; C = np.vstack(C)[:, genes_idx]
    W = np.where(np.isfinite(V), 1.0 / V, 0.0); sw = W.sum(0)
    mu = np.where(sw > 0, (W * E).sum(0) / np.maximum(sw, 1e-12), 0.0)
    k = (W > 0).sum(0)
    Q = np.where(sw > 0, (W * (E - mu) ** 2).sum(0), 0.0)
    birge = np.where(k > 1, np.maximum(1.0, Q / np.maximum(k - 1, 1)), 1.0)
    z = mu / np.where(sw > 0, np.sqrt(birge / np.maximum(sw, 1e-12)), np.inf)
    agree = ((np.sign(E) == np.sign(mu)) & (W > 0)).sum(0) / np.maximum(k, 1)
    Em = np.where(W > 0, E, np.nan)
    rs = np.array([line_r.get(nm, 0.0) for nm in names])
    j = int(np.argmax(rs))
    resp = np.nanmean(np.vstack([np.nanmean(np.vstack([s["_resp"] for s in ev_lines[nm]]), 0) for nm in names]), 0)[genes_idx]
    tcpm = L_ctrl[gpos[t]] if t in gpos else 0.0
    lE = np.log1p(np.nanmean(C, 0)); lL = np.log1p(L_ctrl[genes_idx])
    cisb = np.array([cis.get(t, {}).get(int(g), -1) for g in genes_idx], float)
    X = np.column_stack([mu, np.abs(np.nan_to_num(z)), agree, k, np.nanmax(Em, 0), np.nanmin(Em, 0),
                         np.nan_to_num(np.nanstd(Em, 0)), E[j], np.full(n, rs[j]), lL, lE, lL - lE,
                         np.full(n, np.log1p(tcpm)), cisb, np.nan_to_num(resp),
                         np.full(n, np.nanmean(K)), np.full(n, np.nanmean(np.abs(mu)))])
    return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)


def _cis_map(tss, genes, max_bp=5000):
    if not tss:
        return {}
    from .neighbors import _bin, load_pairs
    gpos = {g: i for i, g in enumerate(genes)}
    out = {}
    for t, lst in load_pairs(tss, genes, max_bp=max_bp).items():
        out[t] = {gpos[n]: _bin(d) for n, d in lst if n in gpos}
    return out


def _sim(a, b):
    return M._ctrl_corr(np.asarray(a, float), np.asarray(b, float))


def fit(sources, tss=None, max_targets_per_line=800, bg_genes=300, seed=0, max_iter=300, max_notable=600):
    from sklearn.ensemble import HistGradientBoostingRegressor
    key = hashlib.md5(("|".join(sorted(s.get("name", "") for s in sources)) + f"{tss}{max_targets_per_line}{bg_genes}{seed}{max_iter}").encode()).hexdigest()
    if key in _CACHE:
        return _CACHE[key]
    rng = np.random.default_rng(seed)
    for s in sources:
        _prep(s)
    genes = sources[0]["genes"]; gpos = {g: i for i, g in enumerate(genes)}
    cis = _cis_map(tss, genes)
    by_line = _lines(sources)
    Xs, ys, ws = [], [], []
    for L, Ls in by_line.items():
        ev = {k: v for k, v in by_line.items() if k != L}
        if not ev:
            continue
        L_ctrl = np.mean([s["ctrl_cpm"] for s in Ls], 0)
        line_r = {k: np.mean([_sim(s["ctrl_cpm"], L_ctrl) for s in v]) for k, v in ev.items()}
        tg = sorted(set().union(*[set(s["perts"]) for s in Ls]))
        tg = [t for t in tg if any(t in s["_tpos"] for v in ev.values() for s in v)]
        if len(tg) > max_targets_per_line:
            tg = list(rng.choice(tg, max_targets_per_line, replace=False))
        names, El, Vl, _, _ = None, None, None, None, None
        for t in tg:
            nm, E, V, C, K = _line_stack({L: Ls}, t)
            if not nm:
                continue
            yL, vL = E[0], V[0]
            valid = np.isfinite(vL)
            names, Ee, Ve, Ce, Ke = _line_stack(ev, t)
            if not names:
                continue
            Ee = np.vstack(Ee); Ve = np.vstack(Ve)
            W = np.where(np.isfinite(Ve), 1 / Ve, 0); sw = W.sum(0)
            mu = np.where(sw > 0, (W * Ee).sum(0) / np.maximum(sw, 1e-12), 0)
            z = np.abs(mu) * np.sqrt(sw)
            cand = np.where(valid & (z > 2))[0]
            notable = cand[np.argsort(-z[cand])][:max_notable]
            cisg = np.array([g for g in cis.get(t, {}) if valid[g]], int)
            bg = rng.choice(np.where(valid)[0], min(bg_genes, int(valid.sum())), replace=False)
            gi = np.unique(np.concatenate([notable, cisg, bg]).astype(int))
            X = features(t, gi, ev, L_ctrl, gpos, cis, line_r)
            if X is None:
                continue
            Xs.append(X); ys.append(yL[gi]); ws.append(1.0 / (vL[gi] + 0.01))
    X = np.vstack(Xs); y = np.concatenate(ys); w = np.concatenate(ws)
    w = w / w.mean()
    mdl = HistGradientBoostingRegressor(max_iter=max_iter, learning_rate=0.08, max_leaf_nodes=63,
                                        min_samples_leaf=200, l2_regularization=1.0, random_state=seed)
    mdl.fit(X, y, sample_weight=w)
    _CACHE[key] = (mdl, cis, len(y))
    return _CACHE[key]


def predict_m1(targets, sources, target_ctrl_cpm=None, tss=None, beta: float = 1.0, min_abs: float = 0.0,
               max_targets_per_line: int = 800, bg_genes: int = 300, max_iter: int = 300, return_info=False, **_):
    """M1_gbm: fit (cached) on the sources, predict the target context. min_abs zeroes tiny outputs."""
    mdl, cis, nrows = fit(sources, tss, max_targets_per_line, bg_genes, 0, max_iter)
    genes = sources[0]["genes"]; gpos = {g: i for i, g in enumerate(genes)}
    G = len(genes)
    tc = np.asarray(target_ctrl_cpm, float) if target_ctrl_cpm is not None else np.mean([s["ctrl_cpm"] for s in sources], 0)
    by_line = _lines(sources)
    line_r = {k: np.mean([_sim(s["ctrl_cpm"], tc) for s in v]) for k, v in by_line.items()}
    allg = np.arange(G)
    out = np.zeros((len(targets), G), np.float32)
    for r, t in enumerate(targets):
        X = features(t, allg, by_line, tc, gpos, cis, line_r)
        if X is None:
            continue
        p = mdl.predict(X) * beta
        if min_abs:
            p = np.where(np.abs(p) < min_abs, 0.0, p)
        out[r] = p
    out = np.where((tc[None, :] < 1.0) & (out > 0), 0.0, out)
    info = {"train_rows": nrows}
    return (out, info) if return_info else out


M.MODELS["M1_gbm"] = predict_m1
