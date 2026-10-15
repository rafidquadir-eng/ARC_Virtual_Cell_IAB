"""Holdout-ready subset of a Perturb-seq h5ad: raw counts on the challenge gene axis, obs `target`.

Keeps up to --panel-cap cells per panel target, --other-cap per other target and --ctrl-cap
control cells (random, seed 0). Works on backed CSR (row blocks) and backed CSC (gene blocks).

  python scripts/make_subset.py --h5ad in.h5ad --pert-col gene --control non-targeting \
      --gene-axis gene_axis.csv --panel-file pert_counts.csv --out subsets/NAME.h5ad \
      [--symbol-col gene_name] [--layer counts] [--where col=val] [--keep-obs a,b] [--label-map map.csv]
"""
import argparse

import anndata as ad
import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp


def pick(labels, control, panel, caps, rng):
    sel = []
    for lab, idx in pd.Series(np.arange(len(labels))).groupby(labels):
        cap = caps["ctrl"] if lab == control else (caps["panel"] if lab in panel else caps["other"])
        idx = idx.to_numpy()
        sel.append(idx if len(idx) <= cap else rng.choice(idx, cap, replace=False))
    return np.sort(np.concatenate(sel))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--h5ad", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--pert-col", required=True); ap.add_argument("--control", required=True)
    ap.add_argument("--gene-axis", required=True); ap.add_argument("--panel-file", required=True)
    ap.add_argument("--symbol-col", default=None); ap.add_argument("--layer", default=None)
    ap.add_argument("--where", action="append", default=[])
    ap.add_argument("--keep-obs", default="", help="extra obs columns to carry over")
    ap.add_argument("--label-map", default=None, help="CSV key,label mapping a column to target labels")
    ap.add_argument("--map-col", default=None, help="obs column the label map is keyed on")
    ap.add_argument("--panel-cap", type=int, default=400); ap.add_argument("--other-cap", type=int, default=100)
    ap.add_argument("--ctrl-cap", type=int, default=20000); ap.add_argument("--block", type=int, default=50000)
    ap.add_argument("--gene-block", type=int, default=500, help="genes per pass for CSC inputs")
    a = ap.parse_args()

    A = ad.read_h5ad(a.h5ad, backed="r")
    obs = A.obs
    ok = np.ones(A.n_obs, bool)
    for cond in a.where:
        col, val = cond.split("=", 1)
        ok &= obs[col].astype(str).values == val
    if a.label_map:
        m = pd.read_csv(a.label_map, index_col=0).iloc[:, 0].astype(str).to_dict()
        labels = obs[a.map_col].astype(str).map(m).fillna("").values
    else:
        labels = obs[a.pert_col].astype(str).values
    ok &= labels != ""
    panel = set(pd.read_csv(a.panel_file)["target_gene"].astype(str))
    rng = np.random.default_rng(0)
    rows = np.where(ok)[0][pick(labels[ok], a.control, panel, dict(panel=a.panel_cap, other=a.other_cap, ctrl=a.ctrl_cap), rng)]

    axis = pd.read_csv(a.gene_axis, header=None).iloc[:, 0].astype(str).values
    sym = np.asarray(A.var[a.symbol_col] if a.symbol_col else A.var_names, str)
    pos = {g: i for i, g in enumerate(axis)}
    col_of = np.full(len(sym), -1); seen = set()
    for j, g in enumerate(sym):
        if g in pos and g not in seen:
            col_of[j] = pos[g]; seen.add(g)
    M = A.layers[a.layer] if a.layer else A.X
    fmt = getattr(M, "format", "csr")
    keepj = np.where(col_of >= 0)[0]
    # kept source columns (in source order) -> axis columns
    P = sp.csr_matrix((np.ones(len(keepj), np.float32), (np.arange(len(keepj)), col_of[keepj])), shape=(len(keepj), len(axis)))

    def row_blocks():
        """Yield consecutive (in `rows` order) CSR blocks already on the axis."""
        if fmt == "csc":
            # stage 1: one pass over gene blocks, keep only the selected rows (CSR pieces, int32)
            pieces = []
            for g0 in range(0, A.n_vars, a.gene_block):
                g1 = min(A.n_vars, g0 + a.gene_block)
                jj = keepj[(keepj >= g0) & (keepj < g1)]
                if len(jj):
                    pieces.append(sp.csr_matrix(sp.csc_matrix(M[:, g0:g1])[:, jj - g0][rows]))
            # stage 2: row chunks across all pieces
            for s0 in range(0, len(rows), a.block):
                yield sp.hstack([q[s0:s0 + a.block] for q in pieces], format="csr") @ P
        else:
            for s0 in range(0, len(rows), a.block):
                yield sp.csr_matrix(M[rows[s0:s0 + a.block]])[:, keepj] @ P

    extra = [c for c in a.keep_obs.split(",") if c]
    o = pd.DataFrame({"target": labels[rows]}, index=np.asarray(obs.index[rows], str))
    for c in extra:
        o[c] = obs[c].values[rows]
    # stream blocks onto disk: write the first block with obs/var, append the rest to X
    first = True
    for B in row_blocks():
        B = sp.csr_matrix(B, dtype=np.float32)
        B.indices = B.indices.astype(np.int64); B.indptr = B.indptr.astype(np.int64)
        if first:
            n0 = B.shape[0]
            head = ad.AnnData(X=B, obs=o.iloc[:n0], var=pd.DataFrame(index=axis))
            head.uns["source"] = a.h5ad
            head.write_h5ad(a.out)
            first = False
            continue
        with h5py.File(a.out, "a") as f:
            ad.io.sparse_dataset(f["X"]).append(B)
    # rewrite obs for all rows (the head file only carries the first block's obs)
    with h5py.File(a.out, "a") as f:
        del f["obs"]
        ad.io.write_elem(f, "obs", o)
    out = ad.read_h5ad(a.out, backed="r")
    assert out.shape == (len(rows), len(axis)), out.shape
    vc = o.target.value_counts()
    print(f"{a.out}: {out.n_obs} cells, {len(vc) - 1} perts ({len(set(vc.index) & panel)} panel), "
          f"{(o.target == a.control).sum()} controls, {len(seen)}/{len(axis)} axis genes")


if __name__ == "__main__":
    main()
