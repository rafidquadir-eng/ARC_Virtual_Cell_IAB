"""Turn any CRISPRi Perturb-seq AnnData (raw counts) into a compact per-context summary.

A context summary (.npz) holds, on a fixed gene axis:
  genes      (G,)    gene symbols
  perts      (P,)    target gene symbols (control excluded)
  ncells     (P,)    cells per perturbation
  cpm        (P, G)  pseudobulk CPM per perturbation  (sum counts / sum library * 1e6)
  ctrl_cpm   (G,)    pseudobulk CPM of the non-targeting control
  lfc        (P, G)  log2((cpm + pc) / (ctrl_cpm + pc)), pc = 1 CPM
  kd         (P,)    on-target knockdown: cpm[p, target] / ctrl_cpm[target]  (nan if absent)

Everything downstream (baselines, transfer models, iMEMORY probe) works on these summaries, so the
multi-GB single-cell files are read once.

  python -m vcc26.pseudobulk --h5ad K562_essential.h5ad --pert-col gene --control non-targeting \
      --gene-axis gene_names.csv --out pb/K562.npz [--min-cells 25] [--max-kd 0.7]
"""
from __future__ import annotations

import argparse

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

PC = 1.0  # CPM pseudocount for log fold changes


def load_gene_axis(path: str | None, adata: ad.AnnData, symbol_col: str | None) -> np.ndarray:
    if path is None:
        return np.asarray(adata.var[symbol_col] if symbol_col else adata.var_names, dtype=str)
    df = pd.read_csv(path, header=None)
    return df.iloc[:, 0].astype(str).values


def summarize(adata: ad.AnnData, pert_col: str, control: str, genes_axis: np.ndarray,
              symbol_col: str | None = None, min_cells: int = 25, max_kd: float | None = None,
              chunk: int = 100000, weight_col: str | None = None, strata_col: str | None = None) -> dict:
    """weight_col: obs column giving cells per row, for inputs that are already pseudobulks.
    strata_col: e.g. donor. Each target's control is then composition-matched: the control CPM is the
    per-stratum control CPM averaged with that target's own cell fractions per stratum, so donor/batch
    differences between the control pool and a guide's cells don't show up as fold changes."""
    sym = np.asarray(adata.var[symbol_col] if symbol_col else adata.var_names, dtype=str)
    # map source genes onto the target axis (first occurrence wins for duplicated symbols)
    pos = {g: i for i, g in enumerate(genes_axis)}
    src_idx, dst_idx, seen = [], [], set()
    for j, g in enumerate(sym):
        if g in pos and g not in seen:
            src_idx.append(j); dst_idx.append(pos[g]); seen.add(g)
    src_idx, dst_idx = np.array(src_idx), np.array(dst_idx)
    G = len(genes_axis)

    labels = adata.obs[pert_col].astype(str).values
    cat = pd.Categorical(labels)
    names, codes0 = np.asarray(cat.categories, str), cat.codes.astype(np.int64)
    K0, N = len(names), len(labels)
    if control not in set(names):
        raise ValueError(f"control label {control!r} not in {pert_col}")
    if strata_col:
        scat = pd.Categorical(adata.obs[strata_col].astype(str).values)
        D, scode = len(scat.categories), scat.codes.astype(np.int64)
    else:
        D, scode = 1, np.zeros(N, np.int64)
    codes = codes0 * D + scode                     # group = (label, stratum)
    K = K0 * D
    # one sequential pass over contiguous row blocks (fast on backed files, bounded memory):
    # per-group gene totals = indicator(groups x cells) @ X, restricted to genes on the axis
    tot = np.zeros((K, len(src_idx))); lib = np.zeros(K)
    if adata.isbacked and getattr(adata.X, "format", None) == "csc":
        # column-major file: pass over contiguous gene blocks instead (all cells at once)
        S = sp.csr_matrix((np.ones(N), (codes, np.arange(N))), shape=(K, N))
        col_of = np.full(adata.n_vars, -1); col_of[src_idx] = np.arange(len(src_idx))
        gchunk = max(1, int(chunk * 2e4 // max(N, 1)))
        for g0 in range(0, adata.n_vars, gchunk):
            g1 = min(adata.n_vars, g0 + gchunk)
            X = sp.csc_matrix(adata.X[:, g0:g1])
            T = (S @ X).toarray()
            lib += T.sum(1)
            m = col_of[g0:g1] >= 0
            tot[:, col_of[g0:g1][m]] += T[:, m]
    else:
        for s0 in range(0, N, chunk):
            s1 = min(N, s0 + chunk)
            X = adata.X[s0:s1]
            X = sp.csr_matrix(X) if not sp.issparse(X) else X.tocsr()
            S = sp.csr_matrix((np.ones(s1 - s0), (codes[s0:s1], np.arange(s1 - s0))), shape=(K, s1 - s0))
            lib += np.asarray(S @ np.asarray(X.sum(1)).ravel()).ravel()
            tot += (S @ X[:, src_idx]).toarray()
    w = None if weight_col is None else adata.obs[weight_col].to_numpy(float)
    cnt_kd = np.bincount(codes, weights=w, minlength=K).reshape(K0, D)        # cells per (label, stratum)
    tot = tot.reshape(K0, D, -1); lib = lib.reshape(K0, D)
    counts = cnt_kd.sum(1).round().astype(np.int64)

    def cpm_of(t, l):
        v = np.full(G, 0.0); v[dst_idx] = t / max(l, 1.0) * 1e6
        return v

    kc = int(np.where(names == control)[0][0])
    ctrl = cpm_of(tot[kc].sum(0), lib[kc].sum())                              # pooled control (reported)
    ctrl_d = np.vstack([cpm_of(tot[kc, d], lib[kc, d]) for d in range(D)])    # per-stratum control
    perts, cpm, n, cref, plib = [], [], [], [], []
    for k, p in enumerate(names):
        if p == control or counts[k] < min_cells:
            continue
        perts.append(p); cpm.append(cpm_of(tot[k].sum(0), lib[k].sum())); n.append(int(counts[k]))
        plib.append(float(lib[k].sum()))
        if D > 1:
            f = cnt_kd[k] / max(cnt_kd[k].sum(), 1e-9)
            f = np.where(cnt_kd[kc] > 0, f, 0.0); f = f / max(f.sum(), 1e-9)   # only strata with controls
            cref.append(f @ ctrl_d)
        else:
            cref.append(ctrl)
    cpm = np.vstack(cpm).astype(np.float32)
    cref = np.vstack(cref)
    perts = np.array(perts)
    kd = np.array([cpm[i, pos[p]] / cref[i, pos[p]] if p in pos and cref[i, pos[p]] > 0 else np.nan
                   for i, p in enumerate(perts)])
    keep = np.ones(len(perts), bool) if max_kd is None else ~(kd > max_kd)   # nan kd kept
    lfc = np.log2((cpm + PC) / (cref + PC)).astype(np.float32)
    present = np.zeros(G, bool); present[dst_idx] = True
    return dict(genes=genes_axis, perts=perts[keep], ncells=np.array(n)[keep], cpm=cpm[keep],
                ctrl_cpm=ctrl.astype(np.float32), lfc=lfc[keep], kd=kd[keep], present=present,
                lib=np.array(plib)[keep], ctrl_lib=np.array(float(lib[kc].sum())),
                ctrl_ncells=np.array(int(counts[kc])))


def load(path: str) -> dict:
    z = np.load(path, allow_pickle=True)
    return {k: z[k] for k in z.files}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h5ad", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--pert-col", required=True); ap.add_argument("--control", default="non-targeting")
    ap.add_argument("--gene-axis", default=None, help="one-column CSV of target gene symbols (challenge axis)")
    ap.add_argument("--symbol-col", default=None, help="var column holding gene symbols, if not var_names")
    ap.add_argument("--min-cells", type=int, default=25)
    ap.add_argument("--max-kd", type=float, default=None,
                    help="drop constructs whose on-target remaining fraction exceeds this (e.g. 0.7)")
    ap.add_argument("--weight-col", default=None,
                    help="obs column with cells per row, when the input rows are already pseudobulks")
    ap.add_argument("--strata-col", default=None,
                    help="obs column (e.g. donor) for composition-matched controls per target")
    ap.add_argument("--where", action="append", default=[],
                    help="keep only rows with obs COL == VALUE (COL=VALUE, repeatable); loads the subset")
    a = ap.parse_args()
    adata = ad.read_h5ad(a.h5ad, backed="r")
    if a.where:
        keep = np.ones(adata.n_obs, bool)
        for cond in a.where:
            col, val = cond.split("=", 1)
            keep &= adata.obs[col].astype(str).values == val
        adata = adata[keep].to_memory()
    genes = load_gene_axis(a.gene_axis, adata, a.symbol_col)
    s = summarize(adata, a.pert_col, a.control, genes, a.symbol_col, a.min_cells, a.max_kd,
                  weight_col=a.weight_col, strata_col=a.strata_col)
    np.savez_compressed(a.out, **s)
    print(f"{a.out}: {len(s['perts'])} perts, {s['present'].sum()}/{len(genes)} genes on axis, "
          f"median kd={np.nanmedian(s['kd']):.2f}")


if __name__ == "__main__":
    main()
