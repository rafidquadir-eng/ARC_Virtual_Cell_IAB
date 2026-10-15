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
