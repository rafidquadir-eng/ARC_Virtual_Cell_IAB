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
              chunk: int = 20000) -> dict:
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
    groups = pd.Series(np.arange(len(labels))).groupby(labels).apply(lambda s: s.values).to_dict()

    def group_sum(idx):
        tot = np.zeros(len(sym)); lib = 0.0
        for k in range(0, len(idx), chunk):
            X = adata.X[np.sort(idx[k:k + chunk])]
            X = X.toarray() if sp.issparse(X) else np.asarray(X)
            tot += X.sum(0); lib += X.sum()
        return tot, lib

    def to_axis(tot, lib):
        v = np.full(G, 0.0); v[dst_idx] = tot[src_idx] / max(lib, 1.0) * 1e6
        return v

    if control not in groups:
        raise ValueError(f"control label {control!r} not in {pert_col}")
    ctot, clib = group_sum(groups[control])
    ctrl = to_axis(ctot, clib)
    perts, cpm, n = [], [], []
    for p, idx in groups.items():
        if p == control or len(idx) < min_cells:
            continue
        t, l = group_sum(idx)
        perts.append(p); cpm.append(to_axis(t, l)); n.append(len(idx))
    cpm = np.vstack(cpm).astype(np.float32)
    perts = np.array(perts)
    kd = np.array([cpm[i, pos[p]] / ctrl[pos[p]] if p in pos and ctrl[pos[p]] > 0 else np.nan
                   for i, p in enumerate(perts)])
    keep = np.ones(len(perts), bool) if max_kd is None else ~(kd > max_kd)   # nan kd kept
    lfc = np.log2((cpm + PC) / (ctrl + PC)).astype(np.float32)
    present = np.zeros(G, bool); present[dst_idx] = True
    return dict(genes=genes_axis, perts=perts[keep], ncells=np.array(n)[keep], cpm=cpm[keep],
                ctrl_cpm=ctrl.astype(np.float32), lfc=lfc[keep], kd=kd[keep], present=present)


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
    a = ap.parse_args()
    adata = ad.read_h5ad(a.h5ad, backed="r")
    genes = load_gene_axis(a.gene_axis, adata, a.symbol_col)
    s = summarize(adata, a.pert_col, a.control, genes, a.symbol_col, a.min_cells, a.max_kd)
    np.savez_compressed(a.out, **s)
    print(f"{a.out}: {len(s['perts'])} perts, {s['present'].sum()}/{len(genes)} genes on axis, "
          f"median kd={np.nanmedian(s['kd']):.2f}")


if __name__ == "__main__":
    main()
