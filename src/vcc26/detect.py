"""Per-gene detection thresholds of the scorer's Wilcoxon test, for one context (round 3, 16 Oct).

Why: `de_wilcoxon_direction_fidelity_yield_raw` = k / max(n_pred, n_conf), where k counts called genes
whose direction matches the real log2FC of ANY non-zero sign (not only significant genes). Calling
>= n_conf genes with coin-flip directions therefore scores ~0.5, which is where the official baseline
sits (0.506 / 0.523 / 0.509 on val A/B/C, cell_eval2 0.18.0 `competition.py` notes), and calling too
few scores k / n_conf, below chance (our E032: 0.42). To control how many genes the scorer calls for
a target we need, per gene, the smallest emitted shift that the test detects with 400 emitted cells
against the context's 18,400 real controls. This module measures that by emitting calibration blocks
through our own emitter and running a Mann-Whitney test on CPM, as cell_eval2 does.

  thresholds(ctrl, n_cells=400) -> (delta_up, delta_dn): |log2FC| needed per gene (inf = never called,
  e.g. genes below the scorer's 5-CPM control gate)

Approximation: each calibration block shifts EVERY gene by the same log2FC and CPM is computed with the
base cells' unshifted library sizes (a real target shifts a few hundred genes, so its library barely
moves). The control reference is subsampled to n_ref cells and z is rescaled to the full control size.
"""
from __future__ import annotations

import hashlib

import numpy as np
import scipy.sparse as sp
from scipy.stats import norm, rankdata

LEVELS = (0.05, 0.1, 0.15, 0.25, 0.4, 0.6, 1.0, 1.5, 2.5)
_CACHE: dict = {}


def gate_cpm(X: sp.csr_matrix) -> np.ndarray:
    """Mean per-cell CPM of each gene: the scorer keeps a gene only if this exceeds 5 (#351)."""
    lib = np.asarray(X.sum(1)).ravel()
    W = sp.diags(1e6 / np.maximum(lib, 1)) @ X
    return np.asarray(W.mean(0)).ravel()


def _mw_z(pred: np.ndarray, ref: np.ndarray, n_ref_full: int) -> np.ndarray:
    """Per-column Mann-Whitney z of pred vs ref (dense, cells x genes), rescaled to a reference of
    n_ref_full cells; zero ties dominate, so the tie term uses the pooled zero fraction."""
    n1, n2 = pred.shape[0], ref.shape[0]
    R = rankdata(np.vstack([pred, ref]), axis=0)
    U = R[:n1].sum(0) - n1 * (n1 + 1) / 2.0
    auc = U / (n1 * n2)
    pi0 = (np.count_nonzero(pred == 0, 0) + np.count_nonzero(ref == 0, 0)) / (n1 + n2)
    sd = np.sqrt(np.maximum(1 - pi0 ** 3, 1e-6) * (n1 + n_ref_full + 1) / (12.0 * n1 * n_ref_full))
    return (auc - 0.5) / sd


def thresholds(ctrl, n_cells: int = 400, levels=LEVELS, p_thr: float = 1e-3, n_ref: int = 4000,
               seed: int = 0, min_cpm: float = 5.0, chunk: int = 2000, emit_mode: str = "balanced2"):
    """(delta_up, delta_dn): per gene, the smallest |log2FC| in `levels` whose emitted block is called
    in the right direction at two-sided p < p_thr (BH at 0.05 over ~10k gated genes calls a few hundred
    genes per target at about this raw p). Cached per (control matrix, n_cells, settings)."""
    from .emit import emit
    X = ctrl.X.tocsr() if sp.issparse(ctrl.X) else sp.csr_matrix(ctrl.X)
    key = (hashlib.md5(np.asarray(X.sum(0)).ravel().tobytes()).hexdigest(), X.shape, int(n_cells),
           tuple(levels), p_thr, n_ref, seed, min_cpm, emit_mode)
    if key in _CACHE:
        return _CACHE[key]
    X = X.astype(np.float64)
    N, G = X.shape
    rng = np.random.default_rng(seed)
    gate = gate_cpm(X) > min_cpm
    L = np.asarray(levels, float)
    names = ["L0"] + [f"u{i}" for i in range(len(L))] + [f"d{i}" for i in range(len(L))]
    lfc = np.vstack([np.zeros(G)] + [np.full(G, x) for x in L] + [np.full(G, -x) for x in L])
    # level 0 must leave the base untouched (adjust_eps), so its rows give the base libraries
    pred = emit(emit_mode, ctrl, names, lfc, n_cells=n_cells, seed=seed)
    P = pred.X.tocsr().astype(np.float64)
    base_lib = np.asarray(P[:n_cells].sum(1)).ravel()
    ref_rows = rng.choice(N, min(n_ref, N), replace=False)
    Rf = X[ref_rows]
    ref_lib = np.asarray(Rf.sum(1)).ravel()
    Rcpm = sp.diags(1e6 / np.maximum(ref_lib, 1)) @ Rf
    up = np.full(G, np.inf); dn = np.full(G, np.inf)
    z_thr = norm.isf(p_thr / 2)
    cols = np.where(gate)[0]
    for k in range(len(L)):
        for block, sign, outv in ((1 + k, 1.0, up), (1 + len(L) + k, -1.0, dn)):
            B = P[block * n_cells:(block + 1) * n_cells]
            Bcpm = sp.diags(1e6 / np.maximum(base_lib, 1)) @ B
            for c0 in range(0, len(cols), chunk):
                cc = cols[c0:c0 + chunk]
                z = _mw_z(Bcpm[:, cc].toarray(), Rcpm[:, cc].toarray(), N)
                hit = (sign * z >= z_thr) & ~np.isfinite(outv[cc])
                outv[cc[hit]] = L[k]
    _CACHE[key] = (up, dn)
    return up, dn


def summary(up: np.ndarray, dn: np.ndarray) -> dict:
    f = lambda v: {"callable": int(np.isfinite(v).sum()),
                   "median": float(np.median(v[np.isfinite(v)])) if np.isfinite(v).any() else None}
    return {"up": f(up), "down": f(dn)}


def main():
    import argparse, json
    import anndata as ad
    ap = argparse.ArgumentParser(description="per-gene detection thresholds for one context's controls")
    ap.add_argument("--ctrl", required=True, help="h5ad of the context's control cells (raw counts)")
    ap.add_argument("--cells", type=int, default=400); ap.add_argument("--out", required=True)
    ap.add_argument("--p-thr", type=float, default=1e-3)
    a = ap.parse_args()
    c = ad.read_h5ad(a.ctrl)
    up, dn = thresholds(c, a.cells, p_thr=a.p_thr)
    np.savez_compressed(a.out, genes=np.asarray(c.var_names, str), up=up, dn=dn)
    print(json.dumps(summary(up, dn)))


if __name__ == "__main__":
    main()
