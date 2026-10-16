"""Turn predicted pseudobulk log2FCs into single-cell raw counts the scorer accepts.

For each target we resample real control cells of the target context and push each gene's counts
towards the predicted fold change f = 2**lfc:
  f < 1 : binomial thinning of the observed counts      (keeps the control's own noise)
  f > 1 : add Poisson(lam), lam = mu_g * libsize_c / mean_lib * (f - 1)  (only genes with f > 1+tol)
This keeps realistic per-cell sparsity and depth, which matters because four of the six metrics run
Wilcoxon tests on the emitted cells.

Output: AnnData, raw integer counts (CSR), obs[pert_col] = target, obs['context'] = context id.
"""
from __future__ import annotations

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

PC = 1.0


def control_cpm(ctrl: ad.AnnData) -> np.ndarray:
    """Pseudobulk CPM of a context's control cells, in its own gene order."""
    X = ctrl.X
    tot = np.asarray(X.sum(0)).ravel().astype(np.float64)
    return tot / max(tot.sum(), 1.0) * 1e6


def _choose_base(X: sp.csr_matrix, n: int, rng, n_pc: int = 20, n_genes: int = 2000,
                 keep_order: bool = False) -> np.ndarray:
    """Pick n distinct control cells whose average sits close to the full control population:
    kernel herding on library size + top PCs of log-normalised expression of the top genes."""
    N = X.shape[0]
    if n >= N:
        idx = rng.choice(N, n, replace=True)
        return idx if keep_order else np.sort(idx)
    lib = np.asarray(X.sum(1)).ravel()
    top = np.argsort(-np.asarray(X.sum(0)).ravel())[:n_genes]
    L = np.log1p(X[:, top].toarray() / np.maximum(lib, 1)[:, None] * 1e4)
    L -= L.mean(0)
    _, _, Vt = np.linalg.svd(L[rng.choice(N, min(N, 4000), replace=False)], full_matrices=False)
    Z = L @ Vt[:n_pc].T
    Z = np.hstack([Z, ((lib - lib.mean()) / lib.std())[:, None] * Z.std()])
    Z /= Z.std(0) + 1e-9
    chosen, run = [], np.zeros(Z.shape[1])
    free = np.ones(N, bool)
    for k in range(n):                       # greedy herding: keep the running mean at 0 (= population mean)
        cand = np.where(free)[0]
        cost = np.sum((run + Z[cand]) ** 2, 1)
        j = cand[np.argmin(cost)]
        chosen.append(j); free[j] = False; run += Z[j]
    return np.array(chosen) if keep_order else np.sort(np.array(chosen))


def _exact_round(vals: np.ndarray, totals: np.ndarray, groups: np.ndarray, rng) -> np.ndarray:
    """Integer-round nonnegative vals so each group's sum equals totals[group] (sum-exact stochastic
    rounding: floor, then hand the leftover units to the largest jittered fractional parts)."""
    fl = np.floor(vals); frac = vals - fl
    need = (totals - np.bincount(groups, weights=fl, minlength=len(totals))).round().astype(np.int64)
    order = np.lexsort((-(frac + 1e-6 * rng.random(len(vals))), groups))
    g_sorted = groups[order]
    start = np.searchsorted(g_sorted, np.arange(len(totals)))
    rank = np.arange(len(vals)) - start[g_sorted]
    give = np.zeros(len(vals)); give[order] = (rank < need[g_sorted]).astype(float)
    return fl + give


def _sizes(n_cells, T: int) -> np.ndarray:
    """n_cells as one int for every target, or one int per target (V* --match-cells)."""
    n = np.asarray(n_cells, dtype=np.int64)
    return np.full(T, int(n)) if n.ndim == 0 else n


def emit_balanced(ctrl: ad.AnnData, targets, lfc: np.ndarray, *, n_cells=400,
                  pert_col: str = "target", context: str = "X", control_label: str = "non-targeting",
                  include_control: int = 0, seed: int = 0, base_mode: str = "herd",
                  adjust_eps: float = 0.0, **_) -> ad.AnnData:
    """Low-noise emission. ONE base set of real control cells (herded to resemble the whole control
    population, or random) is shared by all targets; each gene's total count over the base cells is
    set EXACTLY to (full-control pseudobulk proportion x predicted fold change), by scaling existing
    counts down (or up, with the extra spread over cells in proportion to library size) and sum-exact
    rounding. So every emitted pseudobulk equals the prediction with no sampling noise, and
    differences between targets are only the predicted effects; cells keep realistic depth and
    sparsity for the Wilcoxon tests.
    n_cells: int, or one int per target (a target with n cells uses the first n base cells)."""
    rng = np.random.default_rng(seed)
    X = ctrl.X.tocsr() if sp.issparse(ctrl.X) else sp.csr_matrix(ctrl.X)
    X = X.astype(np.float64)
    G = X.shape[1]
    sizes = _sizes(n_cells, len(targets))
    nmax = int(sizes.max()) if len(sizes) else 0
    lib_all = np.asarray(X.sum(1)).ravel()
    ctrl_cpm = np.asarray(X.sum(0)).ravel() / lib_all.sum() * 1e6
    # base_mode 'herd' picks cells near the population mean, which narrows each gene's distribution
    # (fewer zeros / higher medians than the controls) and makes Wilcoxon call genes with NO predicted
    # change; 'random' keeps the controls' own distribution shape. adjust_eps > 0 leaves every gene
    # whose |predicted lfc| <= adjust_eps exactly as the base cells have it (no thinning/adding).
    # The base is kept in selection order, so any prefix is itself herded / random.
    if base_mode == "herd":
        base_all = _choose_base(X, nmax, rng, keep_order=True)
    else:
        base_all = rng.permutation(X.shape[0])[:nmax] if nmax <= X.shape[0] else rng.choice(X.shape[0], nmax)
    target_cpm = np.maximum((ctrl_cpm + PC) * np.power(2.0, lfc) - PC, 0.0)     # (T, G)
    cache = {}
    blocks, labels = [], []
    for r, t in enumerate(targets):
        n = int(sizes[r])
        if n not in cache:
            B = X[np.sort(base_all[:n])].tocsc()
            blib = np.asarray(B.sum(1)).ravel()
            bsum = np.asarray(B.sum(0)).ravel()
            Bc = B.tocoo()
            cache[n] = (blib, bsum, Bc.col, Bc.row, Bc.data)
        blib, bsum, col, row, dat = cache[n]
        if not np.any(lfc[r]):
            # predicted "no response" (e.g. target not expressed in this context): emit the base cells
            # untouched. Pinning them to the population mean (balanced/balanced3) creates spurious DE
            # calls, and a target with N_conf = 0 scores fid = jac = 1 only if NOTHING is called.
            blocks.append(sp.csr_matrix((dat, (row, col)), shape=(n, G))); labels += [t] * n
            continue
        tot_lib = blib.sum()
        want = target_cpm[r] / 1e6 * tot_lib                  # desired total count per gene over base cells
        if adjust_eps > 0:
            want = np.where(np.abs(lfc[r]) <= adjust_eps, bsum, want)
        down = np.minimum(want, bsum)                         # part made by scaling existing counts
        s = np.where(bsum > 0, down / np.maximum(bsum, 1e-12), 0.0)
        v = _exact_round(dat * s[col], np.round(down), col, rng)
        M = sp.csr_matrix((v, (row, col)), shape=(n, G))
        extra = np.round(want - down)                         # still missing (upregulation / absent genes)
        up = np.where(extra >= 1)[0]
        if len(up):
            share = blib / blib.sum()
            vals = (share[:, None] * extra[up][None, :]).ravel(order="F")
            grp = np.repeat(np.arange(len(up)), n)
            add = _exact_round(vals, extra[up], grp, rng).reshape(len(up), n).T
            M = M + sp.csr_matrix(add, shape=(n, len(up))) @ sp.csr_matrix(
                (np.ones(len(up)), (np.arange(len(up)), up)), shape=(len(up), G))
        M = sp.csr_matrix(M); M.eliminate_zeros()
        blocks.append(M); labels += [t] * n
    if include_control:
        blocks.append(X[rng.integers(0, X.shape[0], include_control)])
        labels += [control_label] * include_control
    M = sp.vstack(blocks).tocsr()
    M.data = np.rint(M.data)
    M = M.astype(np.float32)
    obs = pd.DataFrame({pert_col: labels, "context": context},
                       index=[f"{context}_{i}" for i in range(len(labels))])
    return ad.AnnData(M, obs=obs, var=pd.DataFrame(index=ctrl.var_names.copy()))


def emit(mode: str, *args, **kw) -> ad.AnnData:
    """random | balanced (herded base, every gene set exactly) | balanced2 (random base, only genes
    with a predicted change are set exactly; no Wilcoxon artefacts on unchanged genes) | balanced2h
    (herded base, changed genes only) | balanced3 (random base, every gene set exactly: exact
    pseudobulk like 'balanced' without the herded base's narrowed distributions)."""
    if mode == "balanced":
        return emit_balanced(*args, **kw)
    if mode == "balanced2":
        return emit_balanced(*args, base_mode="random", adjust_eps=1e-3, **kw)
    if mode == "balanced2h":
        return emit_balanced(*args, base_mode="herd", adjust_eps=1e-3, **kw)
    if mode == "balanced3":
        return emit_balanced(*args, base_mode="random", adjust_eps=0.0, **kw)
    return emit_context(*args, **kw)


def emit_context(ctrl: ad.AnnData, targets, lfc: np.ndarray, *, n_cells=400,
                 pert_col: str = "target", context: str = "X", control_label: str = "non-targeting",
                 include_control: int = 0, seed: int = 0, up_tol: float = 0.02) -> ad.AnnData:
    """ctrl: control cells of the target context, genes in the SAME order as lfc's columns."""
    rng = np.random.default_rng(seed)
    X = ctrl.X.tocsr() if sp.issparse(ctrl.X) else sp.csr_matrix(ctrl.X)
    X = X.astype(np.float64)
    lib = np.asarray(X.sum(1)).ravel()
    ctrl_cpm = np.asarray(X.sum(0)).ravel() / lib.sum() * 1e6
    mu = ctrl_cpm / 1e6                                   # per-UMI gene probability
    # Convert pseudobulk-scale lfc (with CPM pseudocount) back to a multiplicative factor on counts
    target_cpm = np.maximum((ctrl_cpm + PC) * np.power(2.0, lfc) - PC, 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        fac = np.where(ctrl_cpm > 0, target_cpm / ctrl_cpm, 1.0)

    sizes = _sizes(n_cells, len(targets))
    blocks, labels = [], []
    for r, t in enumerate(targets):
        n_r = int(sizes[r])
        pick = rng.integers(0, X.shape[0], n_r)
        B = X[pick].tocoo()
        f = fac[r]
        down = np.clip(f[B.col], 0.0, 1.0)
        data = rng.binomial(B.data.astype(np.int64), down).astype(np.float64)
        Bn = sp.csr_matrix((data, (B.row, B.col)), shape=B.shape)
        up = np.where(f > 1.0 + up_tol)[0]
        if len(up):
            lam = np.outer(lib[pick] / lib.mean(), mu[up] * lib.mean() * (f[up] - 1.0))
            add = rng.poisson(lam)
            Bn = Bn + sp.csr_matrix((add.ravel(), (np.repeat(np.arange(n_r), len(up)),
                                                   np.tile(up, n_r))), shape=B.shape)
        Bn.eliminate_zeros()
        blocks.append(Bn); labels += [t] * n_r
    if include_control:
        blocks.append(X[rng.integers(0, X.shape[0], include_control)])
        labels += [control_label] * include_control
    M = sp.vstack(blocks).tocsr()
    M.data = np.rint(M.data)
    M = M.astype(np.float32)
    obs = pd.DataFrame({pert_col: labels, "context": context},
                       index=[f"{context}_{i}" for i in range(len(labels))])
    return ad.AnnData(M, obs=obs, var=pd.DataFrame(index=ctrl.var_names.copy()))
