"""Perturbation-effect predictors for an unseen context, all on the pseudobulk log2FC scale.

Every predictor returns a (n_targets, G) matrix of predicted log2 fold changes for the target
context, given only: the target context's control CPM and a list of source-context summaries
(see pseudobulk.py). No predictor sees any perturbed cell from the target context.

  B0 control      : no change (sanity floor; scores below 0 on several metrics)
  B1 generic      : the average CRISPRi response across source contexts, same for every target
  B2 transfer     : B1 + alpha * the target's own specific effect averaged over sources that
                    measured it (falls back to B1, or to kNN/linear, for unmeasured targets)
  B3 linear       : Ahlmann-Eltze-style bilinear model on PCA gene embeddings of the pooled
                    source response matrix; predicts specific effects for unmeasured targets
  KNN(E)          : specific effect = similarity-weighted mean of measured targets' effects, using
                    an arbitrary gene embedding E (this is how iMEMORY gene vectors are tested)
"""
from __future__ import annotations

import numpy as np

EPS_CPM = 0.5   # genes below this control CPM in a source are treated as unmeasured there


def _source_effects(src: dict):
    """generic response g (G,), specific effects D (P, G), validity mask (G,)."""
    lfc = src["lfc"].astype(np.float64)
    valid = src["present"] & (src["ctrl_cpm"] > EPS_CPM)
    g = lfc.mean(0)
    D = lfc - g
    g[~valid] = 0.0; D[:, ~valid] = 0.0
    return g, D, valid


def generic(sources: list[dict], weights=None) -> np.ndarray:
    G = len(sources[0]["genes"])
    num, den = np.zeros(G), np.zeros(G)
    for k, s in enumerate(sources):
        g, _, v = _source_effects(s)
        w = 1.0 if weights is None else weights[k]
        num += w * g * v; den += w * v
    return np.where(den > 0, num / np.maximum(den, 1e-12), 0.0)


def denoise_source(src: dict, floor: float = 1e-4) -> dict:
    """Empirical-Bayes shrinkage of a source's per-target log2FC toward 0, gene by gene.

    Sampling noise of a pseudobulk log2FC scales like c / (n_cells * (ctrl CPM + 1)). c is fitted per
    source from the median squared lfc (most target x gene pairs are null, median chi2_1 = 0.455).
    Signal variance per gene tau2_g = max(mean_t lfc^2 - mean_t noise, floor). Each lfc is multiplied
    by tau2 / (tau2 + noise): weak, noisy targets and genes shrink most, so emitted cells stop
    producing spurious DE calls from another line's sampling noise."""
    lfc = src["lfc"].astype(np.float64)
    n = np.maximum(src["ncells"].astype(np.float64), 1.0)[:, None]
    base = 1.0 / (n * (src["ctrl_cpm"].astype(np.float64)[None, :] + 1.0))
    v = src["present"] & (src["ctrl_cpm"] > EPS_CPM)
    if lfc.shape[0] < 5 or not v.any():
        return src
    c = np.median((lfc[:, v] ** 2) / base[:, v]) / 0.455
    noise = c * base
    tau2 = np.maximum((lfc ** 2).mean(0) - noise.mean(0), floor)
    shr = lfc * tau2 / (tau2 + noise)
    gpos = {g: i for i, g in enumerate(src["genes"])}
    for i, p in enumerate(src["perts"]):          # keep each target's own knockdown unshrunk
        j = gpos.get(p)
        if j is not None:
            shr[i, j] = lfc[i, j]
    out = dict(src); out["lfc"] = shr.astype(np.float32)
    return out


def _prep(sources, denoise):
    return [denoise_source(s) for s in sources] if denoise else sources


def generic_pool(sources: list[dict], generic_from=None, weights=None) -> np.ndarray:
    """Generic response from a named subset of sources (e.g. only genome-wide screens, whose
    average knockdown is mostly non-essential genes like the challenge panel). Falls back to all."""
    if generic_from:
        names = {x for x in generic_from if not x.startswith("@")}
        libs = {x[1:] for x in generic_from if x.startswith("@")}      # e.g. "@genome_wide"
        keep = [k for k, s in enumerate(sources) if s.get("name") in names or s.get("library") in libs]
        if keep:
            return generic([sources[k] for k in keep], None if weights is None else [weights[k] for k in keep])
    return generic(sources, weights)


def pooled_raw(sources: list[dict]):
    """Average measured log2FC per target across sources (no generic recomposition).
    Genes no measuring source covers are nan."""
    G = len(sources[0]["genes"])
    acc, cnt = {}, {}
    for s in sources:
        lfc = s["lfc"].astype(np.float64)
        v = s["present"] & (s["ctrl_cpm"] > EPS_CPM)
        for i, p in enumerate(s["perts"]):
            acc.setdefault(p, np.zeros(G)); cnt.setdefault(p, np.zeros(G))
            acc[p] += np.where(v, lfc[i], 0.0); cnt[p] += v
    targets = np.array(sorted(acc))
    if not len(targets):
        return targets, np.zeros((0, G))
    R = np.vstack([np.where(cnt[p] > 0, acc[p] / np.maximum(cnt[p], 1e-12), np.nan) for p in targets])
    return targets, R


def pooled_specific(sources: list[dict], weights=None):
    """Average specific effect per measured target across sources -> (targets, D (T,G))."""
    G = len(sources[0]["genes"])
    if sum(len(s["perts"]) for s in sources) == 0:
        return np.array([], dtype=str), np.zeros((0, G))
    acc, cnt = {}, {}
    for k, s in enumerate(sources):
        _, D, v = _source_effects(s)
        w = 1.0 if weights is None else weights[k]
        for i, p in enumerate(s["perts"]):
            acc.setdefault(p, np.zeros(G)); cnt.setdefault(p, np.zeros(G))
            acc[p] += w * D[i]; cnt[p] += w * v
    targets = np.array(sorted(acc))
    Dm = np.vstack([np.where(cnt[p] > 0, acc[p] / np.maximum(cnt[p], 1e-12), 0.0) for p in targets])
    return targets, Dm


def predict_control(targets, sources, **_):
    return np.zeros((len(targets), len(sources[0]["genes"])), np.float32)


def predict_generic(targets, sources, beta=1.0, generic_from=None, denoise=False, **_):
    sources = _prep(sources, denoise)
    g = generic_pool(sources, generic_from)
    return np.tile(beta * g, (len(targets), 1)).astype(np.float32)


def predict_transfer(targets, sources, alpha=1.0, beta=1.0, fallback=None, generic_from=None,
                     raw=False, denoise=False, **_):
    """fallback: callable(unmeasured_targets) -> specific effects (n, G), e.g. kNN or linear.
    generic_from: source names whose average response is the generic shift (default: all sources).
    raw: measured targets get their measured log2FC averaged over sources (shrunk to g by alpha)
         instead of g + specific effect, so another library's average response is not added in.
    denoise: empirical-Bayes shrinkage of every source lfc before use (denoise_source)."""
    sources = _prep(sources, denoise)
    g = generic_pool(sources, generic_from)
    if raw:
        seen, R = pooled_raw(sources)
        Dm = np.where(np.isnan(R), 0.0, R - g) if len(seen) else R
    else:
        seen, Dm = pooled_specific(sources)
    idx = {p: i for i, p in enumerate(seen)}
    out = np.tile(g, (len(targets), 1))
    miss = [t for t in targets if t not in idx]
    fb = dict(zip(miss, fallback(miss))) if (fallback is not None and miss) else {}
    for r, t in enumerate(targets):
        if t in idx:
            out[r] += alpha * Dm[idx[t]]
        elif t in fb:
            out[r] += alpha * fb[t]
    return (beta * out).astype(np.float32)


# ---------------------------------------------------------------------------------------------
# Fallbacks for targets no source measured
# ---------------------------------------------------------------------------------------------

def linear_fallback(sources, k: int = 10, ridge: float = 0.1):
    """Ahlmann-Eltze et al. (2025) linear baseline adapted to specific effects.

    Gene embedding Gemb = top-k left singular vectors of the pooled specific-effect matrix
    (genes x measured targets). Fit Dm^T ~ Gemb W Gemb[targets]^T by ridge; predict a new
    target t as Gemb W Gemb[t]^T.  Needs t on the gene axis (always true here)."""
    seen, Dm = pooled_specific(sources)
    genes = sources[0]["genes"]; gpos = {g: i for i, g in enumerate(genes)}
    Y = Dm.T                                             # (G, T)
    if Y.shape[1] < 3:
        raise ValueError("linear_fallback needs >= 3 measured source targets")
    U, S, _ = np.linalg.svd(Y - Y.mean(1, keepdims=True), full_matrices=False)
    k = min(k, len(S))
    Gemb = U[:, :k] * S[:k] / np.sqrt(Y.shape[1])        # (G, k)
    cols = [i for i, p in enumerate(seen) if p in gpos]
    Pemb = Gemb[[gpos[seen[i]] for i in cols]]           # (T', k)
    Yc = Y[:, cols]
    # W = (G^T G + l I)^-1 G^T Y P (P^T P + l I)^-1
    A = np.linalg.solve(Gemb.T @ Gemb + ridge * np.eye(k), Gemb.T @ Yc @ Pemb)
    W = np.linalg.solve(Pemb.T @ Pemb + ridge * np.eye(k), A.T).T

    def f(miss):
        return np.vstack([(Gemb @ W @ Gemb[gpos[t]]) if t in gpos else np.zeros(len(genes))
                          for t in miss])
    return f


def knn_fallback(sources, emb: dict[str, np.ndarray], k: int = 20, tau: float = 0.1,
                 seed_shuffle: int | None = None):
    """Similarity-weighted average of measured targets' specific effects in embedding space.
    seed_shuffle != None permutes embedding rows across genes: the null control for the probe."""
    seen, Dm = pooled_specific(sources)
    keys = [p for p in seen if p in emb]
    M = np.vstack([emb[p] for p in keys]).astype(np.float64)
    if seed_shuffle is not None:
        pool = list(emb.keys()); rng = np.random.default_rng(seed_shuffle)
        perm = dict(zip(pool, rng.permutation(pool)))
        emb = {g: emb[perm[g]] for g in pool}
        M = np.vstack([emb[p] for p in keys]).astype(np.float64)
    M /= np.linalg.norm(M, axis=1, keepdims=True) + 1e-12
    Dk = Dm[[np.where(seen == p)[0][0] for p in keys]]

    def f(miss):
        out = []
        for t in miss:
            if t not in emb:
                out.append(np.zeros(Dm.shape[1])); continue
            v = emb[t] / (np.linalg.norm(emb[t]) + 1e-12)
            sim = M @ v
            nn = np.argsort(-sim)[:k]
            w = np.exp((sim[nn] - sim[nn].max()) / tau); w /= w.sum()
            out.append(w @ Dk[nn])
        return np.vstack(out)
    return f


# ---------------------------------------------------------------------------------------------
# A1: calibrated transfer (uses the target context's control profile)
# ---------------------------------------------------------------------------------------------

def control_similarity_weights(sources, target_ctrl_cpm, tau: float = 0.2, min_cpm: float = 1.0):
    """Weight each source by how much its control transcriptome resembles the target's.
    Pearson r of log1p CPM over genes expressed in either; w = softmax(r / tau), mean 1."""
    t = np.log1p(np.asarray(target_ctrl_cpm, np.float64))
    rs = []
    for s in sources:
        c = np.asarray(s["ctrl_cpm"], np.float64)
        m = s["present"] & ((c > min_cpm) | (np.expm1(t) > min_cpm))
        rs.append(np.corrcoef(t[m], np.log1p(c[m]))[0, 1] if m.sum() > 10 else 0.0)
    rs = np.nan_to_num(np.array(rs))
    w = np.exp((rs - rs.max()) / tau)
    return w / w.mean(), rs


def per_source_specific(sources, weights=None):
    """{target: [(weight, effect (G,), valid (G,)), ...]} across sources."""
    out = {}
    for k, s in enumerate(sources):
        _, D, v = _source_effects(s)
        w = 1.0 if weights is None else float(weights[k])
        for i, p in enumerate(s["perts"]):
            out.setdefault(p, []).append((w, D[i], v))
    return out


def _agreement(entries, top: int = 200) -> float:
    """Mean pairwise cosine of specific effects over each pair's strongest shared genes."""
    sims = []
    for a in range(len(entries)):
        for b in range(a + 1, len(entries)):
            _, da, va = entries[a]; _, db, vb = entries[b]
            m = va & vb
            if m.sum() < 20:
                continue
            x, y = da[m], db[m]
            sel = np.argsort(-(np.abs(x) + np.abs(y)))[:top]
            x, y = x[sel], y[sel]
            sims.append(float(x @ y / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-12)))
    return float(np.mean(sims)) if sims else float("nan")


def predict_transfer_a1(targets, sources, target_ctrl_cpm=None, alpha_single: float = 0.8,
                        alpha_min: float = 0.6, alpha_max: float = 1.0, beta: float = 1.0,
                        tau: float = 0.2, gate_cpm: float = 5.0, use_weights: bool = True,
                        use_gate: bool = True, use_agreement: bool = True, fallback=None,
                        alpha_fallback: float = 0.5, tss: str | None = None,
                        nb_scope: str = "unmeasured", return_info: bool = False,
                        generic_from=None, denoise=False, **_):
    """A1 = generic + per-target specific effect, with
      * sources weighted by control similarity to the target context (use_weights),
      * per-target alpha: alpha_single if measured in one source, else
        alpha_min + (alpha_max - alpha_min) * clip(cross-source agreement, 0, 1) (use_agreement),
      * target-expression gate: specific effect scaled by clip(target CPM / gate_cpm, 0, 1) in the
        target context, since CRISPRi cannot knock down a gene that is not expressed (use_gate),
      * global effect scale beta,
      * A2 (tss=<path to TSS csv>): CRISPRi neighbour silencing learned from the sources, applied to
        targets in nb_scope ('unmeasured' or 'all'), gated by neighbour expression in the target."""
    sources = _prep(sources, denoise)
    G = len(sources[0]["genes"])
    genes = sources[0]["genes"]; gpos = {g: i for i, g in enumerate(genes)}
    if target_ctrl_cpm is not None and use_weights and len(sources) > 1:
        w, rs = control_similarity_weights(sources, target_ctrl_cpm, tau)
    else:
        w, rs = np.ones(len(sources)), np.full(len(sources), np.nan)
    g = generic_pool(sources, generic_from, w)
    per = per_source_specific(sources, w)
    miss = [t for t in targets if t not in per]
    fb = dict(zip(miss, fallback(miss))) if (fallback is not None and miss) else {}
    out = np.tile(g, (len(targets), 1))
    info = []
    for r, t in enumerate(targets):
        gate = 1.0
        if use_gate and target_ctrl_cpm is not None and t in gpos:
            gate = float(np.clip(target_ctrl_cpm[gpos[t]] / gate_cpm, 0.0, 1.0))
        if t in per:
            ent = per[t]
            num = sum(wk * dk * vk for wk, dk, vk in ent)
            den = sum(wk * vk for wk, dk, vk in ent)
            eff = np.where(den > 0, num / np.maximum(den, 1e-12), 0.0)
            if len(ent) == 1 or not use_agreement:
                a, agr = alpha_single if len(ent) == 1 else alpha_max, float("nan")
            else:
                agr = _agreement(ent)
                a = alpha_min + (alpha_max - alpha_min) * float(np.clip(np.nan_to_num(agr), 0, 1))
            out[r] += a * gate * eff
            info.append((t, len(ent), agr, a, gate))
        elif t in fb:
            out[r] += alpha_fallback * gate * fb[t]
            info.append((t, 0, float("nan"), alpha_fallback, gate))
        else:
            info.append((t, 0, float("nan"), 0.0, gate))
    out = beta * out
    n_nb = 0
    if tss is not None:
        from .neighbors import NeighborPrior, apply_neighbors, load_pairs
        pairs = load_pairs(tss, genes)
        prior = NeighborPrior.learn(sources, pairs)
        rows = [r for r, t in enumerate(targets) if nb_scope == "all" or t not in per]
        eff = prior.predict([targets[r] for r in rows], genes, pairs, target_ctrl_cpm)
        eff = {rows[k]: v for k, v in eff.items()}
        out = apply_neighbors(out, eff)
        n_nb = len(eff)
    out = out.astype(np.float32)
    meta = {"source_r": rs, "source_w": w, "per_target": info, "n_neighbor_targets": n_nb}
    return (out, meta) if return_info else out


MODELS = {"B0_control": predict_control, "B1_generic": predict_generic,
          "B2_transfer": predict_transfer, "A1_transfer": predict_transfer_a1}


# ---------------------------------------------------------------------------------------------
# B4: noise-aware consensus transfer (15 Oct). Fixes found in E020/E021: transferred source noise
# dominates the expression metrics (raw MSE 3-7 vs 0.9 for the mean baseline), datasets of one line
# are counted several times, and noisy low-expression genes create expression the target never had.
# ---------------------------------------------------------------------------------------------

def _lfc_pc(src: dict, pc: float) -> np.ndarray:
    """Source log2FC recomputed with CPM pseudocount pc (the stored lfc uses pc = 1 against the
    possibly composition-matched control, recovered here from cpm and lfc)."""
    if pc == 1.0:
        return src["lfc"].astype(np.float64)
    cpm = src["cpm"].astype(np.float64)
    cref = np.maximum((cpm + 1.0) / np.power(2.0, src["lfc"].astype(np.float64)) - 1.0, 0.0)
    return np.log2((cpm + pc) / (cref + pc))


def _noise_var(src: dict, lfc: np.ndarray, pc: float) -> np.ndarray:
    """Per-entry sampling variance of a pseudobulk log2FC: c / (n_cells * (ctrl CPM + pc)),
    with c fitted per source from the median squared lfc (most target x gene pairs are null)."""
    n = np.maximum(src["ncells"].astype(np.float64), 1.0)[:, None]
    base = 1.0 / (n * (src["ctrl_cpm"].astype(np.float64)[None, :] + pc))
    v = src["present"] & (src["ctrl_cpm"] > EPS_CPM)
    c = np.median((lfc[:, v] ** 2) / base[:, v]) / 0.455 if v.any() and lfc.shape[0] >= 5 else 1.0
    return c * base


def _rsvd(Z: np.ndarray, k: int, seed: int = 0, n_iter: int = 4):
    rng = np.random.default_rng(seed)
    k = min(k, min(Z.shape) - 1)
    Q = Z @ rng.standard_normal((Z.shape[1], k + 10))
    for _ in range(n_iter):
        Q, _ = np.linalg.qr(Z @ (Z.T @ Q))
    Q, _ = np.linalg.qr(Q)
    U, S, Vt = np.linalg.svd(Q.T @ Z, full_matrices=False)
    return (Q @ U)[:, :k], S[:k], Vt[:k]


_LR_CACHE: dict = {}


def lowrank_denoise(src: dict, pc: float = 1.0, kmax: int = 300) -> dict:
    """Gavish-Donoho optimal singular-value shrinkage of the noise-whitened (targets x genes) lfc
    matrix. Pure noise has singular values below the Marchenko-Pastur edge and is removed; shared
    response programs survive. Each target's own (cis) entry is restored unshrunk."""
    key = (src.get("name"), id(src["lfc"]), pc, kmax)
    if key in _LR_CACHE:
        return _LR_CACHE[key]
    lfc = _lfc_pc(src, pc)
    v = src["present"] & (src["ctrl_cpm"] > EPS_CPM)
    out = dict(src)
    if lfc.shape[0] < 20 or v.sum() < 20:
        out["lfc_pc"] = lfc; out["var_pc"] = _noise_var(src, lfc, pc); _LR_CACHE[key] = out
        return out
    var = _noise_var(src, lfc, pc)
    sd = np.sqrt(var[:, v])
    Z = lfc[:, v] / sd
    m, n = Z.shape
    tr = m > n
    if tr:
        Z = Z.T; m, n = n, m
    beta = m / n
    U, S, Vt = _rsvd(Z, kmax)
    y = S / np.sqrt(n)
    edge = 1 + np.sqrt(beta)
    eta = np.where(y > edge, np.sqrt(np.maximum((y ** 2 - beta - 1) ** 2 - 4 * beta, 0.0)) / np.maximum(y, 1e-12), 0.0)
    Zh = (U * (eta * np.sqrt(n))) @ Vt
    if tr:
        Zh = Zh.T
    den = np.zeros_like(lfc)
    den[:, v] = Zh * sd
    gpos = {g: i for i, g in enumerate(src["genes"])}
    for i, p in enumerate(src["perts"]):
        j = gpos.get(p)
        if j is not None:
            den[i, j] = lfc[i, j]
    out["lfc_pc"] = den
    out["var_pc"] = var * 0.0 + np.mean(var[:, v]) * (int((eta > 0).sum()) / max(n, 1))   # residual var proxy
    out["lowrank_k"] = int((eta > 0).sum())
    _LR_CACHE[key] = out
    return out


def _ctrl_corr(a, b, min_cpm=1.0):
    m = (a > min_cpm) | (b > min_cpm)
    return float(np.corrcoef(np.log1p(a[m]), np.log1p(b[m]))[0, 1]) if m.sum() > 50 else 0.0


def predict_consensus(targets, sources, target_ctrl_cpm=None, lowrank: bool = True, pc: float = 1.0,
                      tau2: float = 0.02, sim_tau: float | None = None, gate_up_cpm: float = 1.0,
                      gate_target_cpm: float | None = None, generic: str = "zero",
                      beta: float = 1.0, shrink: bool = True, return_info: bool = False, **_):
    """Random-effects consensus of each target's response across cell LINES.

    1. Each dataset's lfc (pseudocount pc) is optionally low-rank denoised (Gavish-Donoho).
    2. Datasets of the same line are merged by inverse noise variance, so a line counts once
       (CD4T Rest/Stim8hr/Stim48hr = one line).
    3. Lines are combined per gene by inverse (noise + tau2) variance: tau2 is the between-line
       spread of true effects, so adding lines reduces noise but never claims more than the
       context-to-context agreement allows. Optional similarity weighting exp(r/sim_tau) of each
       line's control profile to the target context.
    4. Empirical-Bayes shrinkage of the consensus toward 0 by its predictive variance (shrink).
    5. Gates: genes the target context doesn't express (< gate_up_cpm) cannot be induced from
       nothing (positive lfc clipped); optionally the whole response is scaled by the target
       gene's own expression in the context (gate_target_cpm).
    generic: 'zero' (unmeasured targets get no change) or 'gw' (mean response of genome-wide
    libraries). beta: global effect scale. Returns log2FC with pseudocount pc converted back to
    pc = 1 so the emitter's conversion is unchanged."""
    G = len(sources[0]["genes"])
    genes = sources[0]["genes"]; gpos = {g: i for i, g in enumerate(genes)}
    srcs = [lowrank_denoise(s, pc) if lowrank else dict(s, lfc_pc=_lfc_pc(s, pc)) for s in sources]
    for s in srcs:
        if "var_pc" not in s:
            s["var_pc"] = _noise_var(s, s["lfc_pc"], pc)
    lines: dict[str, list] = {}
    for s in srcs:
        lines.setdefault(s.get("line") or s.get("name"), []).append(s)
    line_w = {}
    for L, ss in lines.items():
        if sim_tau and target_ctrl_cpm is not None:
            r = np.nanmean([_ctrl_corr(s["ctrl_cpm"], np.asarray(target_ctrl_cpm, float)) for s in ss])
            line_w[L] = float(np.exp((0.0 if not np.isfinite(r) else r) / sim_tau))
        else:
            line_w[L] = 1.0
    zmax = max(line_w.values()); line_w = {k: v / zmax for k, v in line_w.items()}
    # (exp(r/tau) is normalised by its max, so the most similar line has weight 1)
    out = np.zeros((len(targets), G))
    n_lines = np.zeros(len(targets), int)
    for r_, t in enumerate(targets):
        num = np.zeros(G); den = np.zeros(G); var_sum = np.zeros(G); nl = 0
        for L, ss in lines.items():
            ln = np.zeros(G); lw = np.zeros(G)
            for s in ss:
                idx = np.where(s["perts"] == t)[0]
                if not len(idx):
                    continue
                i = idx[0]
                vg = s["present"] & (s["ctrl_cpm"] > EPS_CPM)
                w = np.where(vg, 1.0 / np.maximum(s["var_pc"][i] if s["var_pc"].ndim == 2 else s["var_pc"], 1e-6), 0.0)
                ln += w * s["lfc_pc"][i]; lw += w
            if not lw.any():
                continue
            nl += 1
            L_eff = np.where(lw > 0, ln / np.maximum(lw, 1e-12), 0.0)
            L_var = np.where(lw > 0, 1.0 / np.maximum(lw, 1e-12), np.inf)
            wL = np.where(lw > 0, line_w[L] / (L_var + tau2), 0.0)
            num += wL * L_eff; den += wL
        n_lines[r_] = nl
        if nl == 0:
            continue
        mu = np.where(den > 0, num / np.maximum(den, 1e-12), 0.0)
        if shrink:
            pv = np.where(den > 0, 1.0 / np.maximum(den, 1e-12), np.inf)     # variance of the mean
            sig2 = max(float(np.mean(mu ** 2) - np.mean(pv[np.isfinite(pv)])), 1e-6) if np.isfinite(pv).any() else 1e-6
            mu = mu * sig2 / (sig2 + np.where(np.isfinite(pv), pv, 1e9))
            j = gpos.get(t)
            if j is not None:
                mu[j] = num[j] / den[j] if den[j] > 0 else mu[j]              # keep the knockdown itself
        out[r_] = mu
    if generic == "gw":
        gw = [s for s in srcs if s.get("library") == "genome_wide"] or srcs
        g = np.mean([s["lfc_pc"].mean(0) for s in gw], 0)
        out[n_lines == 0] = g
    out *= beta
    if target_ctrl_cpm is not None:
        tc = np.asarray(target_ctrl_cpm, float)
        if gate_up_cpm is not None:
            out = np.where((tc[None, :] < gate_up_cpm) & (out > 0), 0.0, out)
        if gate_target_cpm:
            for r_, t in enumerate(targets):
                j = gpos.get(t)
                if j is not None:
                    out[r_] *= min(1.0, tc[j] / gate_target_cpm)
        # convert pseudocount pc back to the emitter's pc = 1 convention, in the target context
        if pc != 1.0:
            tcpm = np.maximum((tc[None, :] + pc) * np.power(2.0, out) - pc, 0.0)
            out = np.log2((tcpm + 1.0) / (tc[None, :] + 1.0))
    info = {"n_lines": n_lines.tolist(), "line_w": line_w,
            "lowrank_k": {s.get("name"): s.get("lowrank_k") for s in srcs}}
    return (out.astype(np.float32), info) if return_info else out.astype(np.float32)


MODELS["B4_consensus"] = predict_consensus


# ---------------------------------------------------------------------------------------------
# B5: sparse, cross-line-consistent consensus + CRISPRi cis effects (16 Oct). E025/E026 showed that
# per-gene transferred effects barely correlate with the truth (cos 0.003-0.08), that shrinking
# everything (B4) kills the little signal there is, and that the MSE-optimal scale of the dense
# transfer is ~0.01-0.1. So keep only genes whose response is significant AND sign-consistent across
# independent lines, at full size, plus the CRISPRi neighbour (cis) effects, and predict 0 elsewhere.
# ---------------------------------------------------------------------------------------------

def _line_effects(sources, t, pc):
    """{line: (effect (G,), noise var (G,))} for target t, merging datasets of a line by inverse variance.
    If a source carries `_pmean` (its panel-mean response), the effect is taken relative to it."""
    G = len(sources[0]["genes"])
    acc = {}
    for s in sources:
        idx = np.where(s["perts"] == t)[0]
        if not len(idx):
            continue
        i = idx[0]
        if "_lfcpc" not in s or s.get("_pc") != pc:
            s["_lfcpc"] = _lfc_pc(s, pc); s["_varpc"] = _noise_var(s, s["_lfcpc"], pc); s["_pc"] = pc
        v = s["present"] & (s["ctrl_cpm"] > EPS_CPM)
        w = np.where(v, 1.0 / np.maximum(s["_varpc"][i], 1e-8), 0.0) * s.get("_simw", 1.0)
        L = s.get("line") or s.get("name")
        e, ww = acc.get(L, (np.zeros(G), np.zeros(G)))
        eff = s["_lfcpc"][i] - s["_pmean"] if s.get("_pmean") is not None else s["_lfcpc"][i]
        acc[L] = (e + w * eff, ww + w)
    return {L: (np.where(ww > 0, e / np.maximum(ww, 1e-12), 0.0), np.where(ww > 0, 1.0 / np.maximum(ww, 1e-12), np.inf))
            for L, (e, ww) in acc.items()}


def predict_sparse(targets, sources, target_ctrl_cpm=None, pc: float = 1.0, z_thr: float = 3.0,
                   agree: float = 0.75, min_lines: int = 1, trans_lambda: float = 0.0, beta: float = 1.0,
                   cis_bp: int | None = 5000, tss: str | None = None, cis_gate_cpm: float = 5.0,
                   gate_target_cpm: float | None = None, sim_tau: float | None = None,
                   common: str = "none", common_z: float = 3.0, common_scale: float = 1.0,
                   return_info: bool = False, **_):
    """Per target: meta-analyse its measured response across LINES (fixed-effect mean with a
    Birge-ratio inflation of the standard error for between-line heterogeneity). Keep genes with
    |z| >= z_thr whose sign agrees in >= `agree` of the lines measuring them; predict their consensus
    at full size (x beta) and trans_lambda x consensus elsewhere (default 0).
    cis: genes whose TSS lies within cis_bp of the target's TSS get their measured consensus
    knockdown if negative, else the neighbour-prior knockdown for that distance; both gated by the
    neighbour's expression in the target context (CPM / cis_gate_cpm, capped at 1).
    gate_target_cpm: scale the trans part by the target gene's own expression in the context.
    common: 'panel' adds the predicted context-wide response (consensus over lines of each line's mean
    response across the requested panel targets, kept where |z| >= common_z and sign-consistent) to
    every target, and builds the target-specific part from deviations from each line's panel mean;
    'panel_only' predicts the common response alone (diagnostic). The metric's baseline IS the
    context's mean response, so DE calls shared across targets come from this component."""
    G = len(sources[0]["genes"]); genes = sources[0]["genes"]; gpos = {g: i for i, g in enumerate(genes)}
    tc = None if target_ctrl_cpm is None else np.asarray(target_ctrl_cpm, float)
    for s in sources:
        s["_simw"] = 1.0
    if sim_tau and tc is not None:
        rs = {}
        for s in sources:
            L = s.get("line") or s.get("name")
            rs.setdefault(L, []).append(_ctrl_corr(s["ctrl_cpm"], tc))
        rL = {L: np.nanmean(v) for L, v in rs.items()}
        mx = max(rL.values())
        for s in sources:
            s["_simw"] = float(np.exp((rL[s.get("line") or s.get("name")] - mx) / sim_tau))
    cvec = np.zeros(G)
    for s in sources:
        s["_pmean"] = None
    if common in ("panel", "panel_only"):
        tset = set(targets)
        acc = {}
        for s in sources:
            if "_lfcpc" not in s or s.get("_pc") != pc:
                s["_lfcpc"] = _lfc_pc(s, pc); s["_varpc"] = _noise_var(s, s["_lfcpc"], pc); s["_pc"] = pc
            rows = [i for i, p in enumerate(s["perts"]) if p in tset]
            if len(rows) < 10:
                continue
            m = s["_lfcpc"][rows].mean(0); vm = s["_varpc"][rows].mean(0) / len(rows)
            v = s["present"] & (s["ctrl_cpm"] > EPS_CPM)
            s["_pmean"] = np.where(v, m, 0.0)
            L = s.get("line") or s.get("name")
            w = np.where(v, 1.0 / np.maximum(vm, 1e-10), 0.0)
            e, ww = acc.get(L, (np.zeros(G), np.zeros(G)))
            acc[L] = (e + w * m, ww + w)
        if acc:
            E = np.vstack([np.where(ww > 0, e / np.maximum(ww, 1e-12), 0.0) for e, ww in acc.values()])
            W = np.vstack([ww for _, ww in acc.values()]); sw = W.sum(0)
            mu = np.where(sw > 0, (W * E).sum(0) / np.maximum(sw, 1e-12), 0.0)
            k = (W > 0).sum(0)
            Q = np.where(sw > 0, (W * (E - mu) ** 2).sum(0), 0.0)
            birge = np.where(k > 1, np.maximum(1.0, Q / np.maximum(k - 1, 1)), 1.0)
            z = mu / np.where(sw > 0, np.sqrt(birge / np.maximum(sw, 1e-12)), np.inf)
            same = ((np.sign(E) == np.sign(mu)[None, :]) & (W > 0)).sum(0) / np.maximum(k, 1)
            cvec = np.where((np.abs(z) >= common_z) & (same >= agree), mu, 0.0) * common_scale
    pairs, prior = {}, None
    if cis_bp and tss:
        from .neighbors import NeighborPrior, load_pairs
        pairs = load_pairs(tss, genes, max_bp=cis_bp)
        prior = NeighborPrior.learn(sources, load_pairs(tss, genes))      # 0-5 kb distance bins
    out = np.zeros((len(targets), G))
    kept, ncis = [], []
    for r, t in enumerate(targets):
        le = _line_effects(sources, t, pc)
        if not le:
            out[r] = cvec
            kept.append(0); ncis.append(0)
            continue
        E = np.vstack([e for e, _ in le.values()]); V = np.vstack([v for _, v in le.values()])
        W = np.where(np.isfinite(V), 1.0 / V, 0.0)
        sw = W.sum(0)
        mu = np.where(sw > 0, (W * E).sum(0) / np.maximum(sw, 1e-12), 0.0)
        k = (W > 0).sum(0)
        Q = np.where(sw > 0, (W * (E - mu) ** 2).sum(0), 0.0)
        birge = np.where(k > 1, np.maximum(1.0, Q / np.maximum(k - 1, 1)), 1.0)
        se = np.where(sw > 0, np.sqrt(birge / np.maximum(sw, 1e-12)), np.inf)
        z = mu / se
        same = ((np.sign(E) == np.sign(mu)[None, :]) & (W > 0)).sum(0) / np.maximum(k, 1)
        keep = (np.abs(z) >= z_thr) & (same >= agree) & (k >= min_lines)
        pred = np.where(keep, mu * beta, trans_lambda * mu)
        if gate_target_cpm and tc is not None and t in gpos:
            pred *= min(1.0, tc[gpos[t]] / gate_target_cpm)
        nc = 0
        for nb, d in pairs.get(t, []):
            j = gpos.get(nb)
            if j is None:
                continue
            g = 1.0 if tc is None else float(np.clip(tc[j] / cis_gate_cpm, 0, 1))
            if k[j] > 0 and mu[j] < 0:
                pred[j] = mu[j] * g
            elif prior is not None:
                from .neighbors import _bin
                b = _bin(d)
                if b >= 0 and prior.bin_lfc[b] < 0:
                    pred[j] = prior.bin_lfc[b] * g
            nc += 1
        out[r] = cvec + (0.0 if common == "panel_only" else pred)
        kept.append(int(keep.sum())); ncis.append(nc)
    if tc is not None:
        if pc != 1.0:
            tcpm = np.maximum((tc[None, :] + pc) * np.power(2.0, out) - pc, 0.0)
            out = np.log2((tcpm + 1.0) / (tc[None, :] + 1.0))
        out = np.where((tc[None, :] < 1.0) & (out > 0), 0.0, out)        # no induction from nothing
    info = {"genes_kept_median": float(np.median(kept)) if kept else 0.0, "cis_genes_median": float(np.median(ncis)) if ncis else 0.0,
            "common_genes": int((cvec != 0).sum())}
    return (out.astype(np.float32), info) if return_info else out.astype(np.float32)


MODELS["B5_sparse"] = predict_sparse


# ---------------------------------------------------------------------------------------------
# Post-processing (WP9 / C1): pull each predicted effect onto the target context's own programs.
# ---------------------------------------------------------------------------------------------

_PC_CACHE: dict = {}


def ctrl_programs(ctrl, k: int = 200, n_top: int = 3000, seed: int = 0):
    """Top-k principal axes of the context's control cells (log1p CPM over the n_top most expressed
    genes). Returns (gene indices, loadings V (n_top, k)). Cached per AnnData object."""
    import scipy.sparse as sp
    key = (id(ctrl), k, n_top)
    if key in _PC_CACHE:
        return _PC_CACHE[key]
    X = ctrl.X.tocsr() if sp.issparse(ctrl.X) else sp.csr_matrix(ctrl.X)
    lib = np.asarray(X.sum(1)).ravel()
    top = np.argsort(-np.asarray(X.sum(0)).ravel())[:n_top]
    L = np.log1p(X[:, top].toarray() / np.maximum(lib, 1)[:, None] * 1e4)
    rng = np.random.default_rng(seed)
    if L.shape[0] > 8000:
        L = L[rng.choice(L.shape[0], 8000, replace=False)]
    L -= L.mean(0)
    _, _, Vt = np.linalg.svd(L, full_matrices=False)
    out = (top, Vt[: min(k, Vt.shape[0])].T)
    _PC_CACHE[key] = out
    return out


def project_ctrl(lfc: np.ndarray, ctrl, k: int = 200, lam: float = 0.5, n_top: int = 3000) -> np.ndarray:
    """lam * (projection of each target's effect on the context's top-k control programs) +
    (1 - lam) * effect, on the n_top expressed genes; other genes unchanged."""
    top, V = ctrl_programs(ctrl, k, n_top)
    out = np.array(lfc, dtype=np.float64, copy=True)
    E = out[:, top]
    out[:, top] = lam * (E @ V) @ V.T + (1 - lam) * E
    return out.astype(np.float32)


def de_budget(lfc: np.ndarray, ctrl, n: int = 400, margin: float = 1.25, n_cells: int = 400,
              frac: float | None = None, n_max: int | None = None, rank: str = "abs",
              cap_others: bool = False, p_thr: float = 1e-3) -> np.ndarray:
    """Make the scorer CALL about n genes per target (round 3, docs/15 P1).
    fid = k / max(n_pred, n_conf): under-calling scores below chance (E032: 0.42 vs the baseline's
    0.51), over-calling decays only towards ~0.5. Per target, rank genes by the model's confidence
    (rank='abs': |lfc|; 'snr': |lfc| / detection threshold, i.e. cheapest calls first), take the top
    n (or max(n, frac x #genes with |lfc| > 0.05), capped at n_max), and lift each one's |lfc| to at
    least margin x the context's detection threshold in its predicted direction (vcc26.detect).
    cap_others: also hold every other gene below half its threshold, so n_pred ~= n."""
    from . import detect
    up, dn = detect.thresholds(ctrl, n_cells, p_thr=p_thr)
    out = np.array(lfc, dtype=np.float64, copy=True)
    for r in range(out.shape[0]):
        x = out[r]
        d = np.where(x >= 0, up, dn)
        cand = np.isfinite(d) & (x != 0)
        if not cand.any():
            continue
        k = n if frac is None else max(n, int(frac * np.count_nonzero(np.abs(x) > 0.05)))
        if n_max:
            k = min(k, n_max)
        score = np.abs(x) if rank == "abs" else np.abs(x) / np.where(np.isfinite(d), d, np.inf)
        idx = np.where(cand)[0]
        top = idx[np.argsort(-score[idx])[:k]]
        x[top] = np.sign(x[top]) * np.maximum(np.abs(x[top]), margin * d[top])
        if cap_others:
            rest = np.setdiff1d(idx, top)
            x[rest] = np.sign(x[rest]) * np.minimum(np.abs(x[rest]), 0.5 * d[rest])
    return out.astype(np.float32)


def apply_post(lfc: np.ndarray, post: dict | None, ctrl=None, n_cells: int = 400) -> np.ndarray:
    """Spec-level post-processing, applied in this order:
    {"project": {"k": 200, "lam": 0.5}, "scale": 1.2, "de_budget": {"n": 400, "margin": 1.25}}"""
    if not post:
        return lfc
    if "project" in post and ctrl is not None:
        lfc = project_ctrl(lfc, ctrl, **post["project"])
    if "scale" in post:
        lfc = lfc * float(post["scale"])
    if "de_budget" in post and ctrl is not None:
        lfc = de_budget(lfc, ctrl, n_cells=int(np.median(n_cells)), **post["de_budget"])
    return lfc


# ---------------------------------------------------------------------------------------------
# ENS: weighted average of member models' log2FC (M-3, round 3). B5 wins on KOLF/HCT116 and M1 on
# HEK293T (E034b), so an average may beat both.
#   {"model": "ENS", "kw": {"members": [{"model": "B5_sparse", "kw": {...}, "w": 0.5},
#                                       {"model": "M1_gbm", "kw": {"beta": 1.3}, "w": 0.5}]}}
# ---------------------------------------------------------------------------------------------

def predict_ensemble(targets, sources, members=(), return_info: bool = False, **kw):
    acc, wsum, info = None, 0.0, {}
    for i, m in enumerate(members):
        mkw = {**kw, **m.get("kw", {})}
        out = MODELS[m["model"]](targets, sources, **mkw)
        w = float(m.get("w", 1.0))
        acc = w * np.asarray(out, np.float64) if acc is None else acc + w * np.asarray(out, np.float64)
        wsum += w
        info[f"m{i}"] = m["model"]
    out = (acc / max(wsum, 1e-12)).astype(np.float32)
    return (out, info) if return_info else out


MODELS["ENS"] = predict_ensemble


try:                                # M1_gbm registers itself in MODELS
    from . import translator  # noqa: F401
except Exception as _e:             # sklearn missing etc.
    pass
