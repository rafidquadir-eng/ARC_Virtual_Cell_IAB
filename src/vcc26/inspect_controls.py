"""Describe the challenge controls bundle (controls.zip unpacked) and write a JSON inventory.

  python -m vcc26.inspect_controls --dir data/challenge/controls --out reports/controls_inventory.json
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp


def describe_h5ad(p: str) -> dict:
    a = ad.read_h5ad(p, backed="r")
    n = min(a.n_obs, 5000)
    idx = np.sort(np.random.default_rng(0).choice(a.n_obs, n, replace=False))
    X = a.X[idx]
    X = X if sp.issparse(X) else sp.csr_matrix(X)
    umis = np.asarray(X.sum(1)).ravel()
    vals = X.data[:100000]
    info = {
        "file": os.path.basename(p), "n_cells": int(a.n_obs), "n_genes": int(a.n_vars),
        "obs_columns": list(a.obs.columns), "var_columns": list(a.var.columns),
        "var_names_head": list(map(str, a.var_names[:5])),
        "median_umis_per_cell(sample)": float(np.median(umis)),
        "integer_counts": bool(np.allclose(vals, np.round(vals))),
        "uns_keys": list(a.uns.keys()) if hasattr(a, "uns") else [],
    }
    for c in a.obs.columns:
        s = a.obs[c]
        if s.dtype == object or str(s.dtype) == "category":
            vc = s.astype(str).value_counts()
            info[f"obs[{c}]"] = {"n_unique": int(len(vc)), "top": vc.head(5).to_dict()}
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    inv = {"files": []}
    for p in sorted(glob.glob(os.path.join(a.dir, "**", "*"), recursive=True)):
        if os.path.isdir(p):
            continue
        e = {"path": os.path.relpath(p, a.dir), "bytes": os.path.getsize(p)}
        if p.endswith(".h5ad"):
            e.update(describe_h5ad(p))
        elif p.endswith((".csv", ".tsv")):
            df = pd.read_csv(p, sep="\t" if p.endswith(".tsv") else ",", nrows=5)
            e["head"] = df.to_dict(orient="records"); e["columns"] = list(df.columns)
            e["n_rows"] = sum(1 for _ in open(p)) - 1
        inv["files"].append(e)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(inv, open(a.out, "w"), indent=2, default=str)
    print(json.dumps(inv, indent=2, default=str))


if __name__ == "__main__":
    main()
