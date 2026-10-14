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


def emit_context(ctrl: ad.AnnData, targets, lfc: np.ndarray, *, n_cells: int = 400,
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

    blocks, labels = [], []
    for r, t in enumerate(targets):
        pick = rng.integers(0, X.shape[0], n_cells)
        B = X[pick].tocoo()
        f = fac[r]
        down = np.clip(f[B.col], 0.0, 1.0)
        data = rng.binomial(B.data.astype(np.int64), down).astype(np.float64)
        Bn = sp.csr_matrix((data, (B.row, B.col)), shape=B.shape)
        up = np.where(f > 1.0 + up_tol)[0]
        if len(up):
            lam = np.outer(lib[pick] / lib.mean(), mu[up] * lib.mean() * (f[up] - 1.0))
            add = rng.poisson(lam)
            Bn = Bn + sp.csr_matrix((add.ravel(), (np.repeat(np.arange(n_cells), len(up)),
                                                   np.tile(up, n_cells))), shape=B.shape)
        Bn.eliminate_zeros()
        blocks.append(Bn); labels += [t] * n_cells
    if include_control:
        blocks.append(X[rng.integers(0, X.shape[0], include_control)])
        labels += [control_label] * include_control
    M = sp.vstack(blocks).tocsr()
    M.data = np.rint(M.data)
    M = M.astype(np.float32)
    obs = pd.DataFrame({pert_col: labels, "context": context},
                       index=[f"{context}_{i}" for i in range(len(labels))])
    return ad.AnnData(M, obs=obs, var=pd.DataFrame(index=ctrl.var_names.copy()))
