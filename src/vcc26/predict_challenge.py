"""Build a challenge submission h5ad for contexts A/B/C (validation) or D/E/F (final).

  python -m vcc26.predict_challenge --controls-dir data/challenge/controls \
      --contexts A,B,C --perts data/challenge/controls/pert_counts.csv \
      --gene-names data/challenge/controls/gene_names.csv \
      --summaries pb/K562.npz pb/RPE1.npz pb/HepG2.npz pb/Jurkat.npz pb/H1.npz \
      --model B2_transfer --alpha 0.8 --out preds/E005_ABC.h5ad
  vcc prep preds/E005_ABC.h5ad -g gene_names.csv --perts pert_counts.csv --contexts A,B,C -o E005.vcc

Context files are located by glob '*{ctx}*.h5ad' inside --controls-dir; confirm with
inspect_controls.py first. The perturbation list is read from the first column of --perts
(non-targeting rows dropped).
"""
from __future__ import annotations

import argparse
import glob
import os

import anndata as ad
import numpy as np
import pandas as pd

from . import models
from .emit import emit_context
from .loco import CTRL, subset_summary
from .pseudobulk import load as load_summary


def find_ctx(d: str, c: str) -> str:
    hits = [p for p in glob.glob(os.path.join(d, "**", "*.h5ad"), recursive=True)
            if f"_{c}." in os.path.basename(p) or os.path.basename(p).endswith(f"{c}.h5ad")]
    if len(hits) != 1:
        raise SystemExit(f"context {c}: expected one h5ad, found {hits}")
    return hits[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls-dir", required=True); ap.add_argument("--contexts", default="A,B,C")
    ap.add_argument("--perts", required=True); ap.add_argument("--gene-names", required=True)
    ap.add_argument("--summaries", nargs="+", required=True)
    ap.add_argument("--model", default="B2_transfer", choices=list(models.MODELS))
    ap.add_argument("--alpha", type=float, default=1.0); ap.add_argument("--beta", type=float, default=1.0)
    ap.add_argument("--fallback", default="linear", choices=["none", "linear"])
    ap.add_argument("--cells", type=int, default=400); ap.add_argument("--n-control", type=int, default=400)
    ap.add_argument("--pert-col", default="target_gene")
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    axis = pd.read_csv(a.gene_names, header=None).iloc[:, 0].astype(str).values
    pl = pd.read_csv(a.perts).iloc[:, 0].astype(str)
    targets = sorted(t for t in pl.unique() if t != CTRL)
    sources = [subset_summary(load_summary(p), axis) for p in a.summaries]
    kw = {"alpha": a.alpha, "beta": a.beta}
    if a.model == "B2_transfer" and a.fallback == "linear":
        kw["fallback"] = models.linear_fallback(sources)
    lfc = models.MODELS[a.model](targets, sources, **kw)
    parts = []
    for i, c in enumerate(a.contexts.split(",")):
        ctrl = ad.read_h5ad(find_ctx(a.controls_dir, c))
        ctrl = ctrl[:, axis].copy()                     # enforce the official gene order
        parts.append(emit_context(ctrl, targets, lfc, n_cells=a.cells, pert_col=a.pert_col,
                                  context=c, include_control=a.n_control, seed=a.seed + i))
    out = ad.concat(parts, merge="same")
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    out.write_h5ad(a.out)
    print(f"wrote {a.out}: {out.n_obs} cells x {out.n_vars} genes, "
          f"{len(targets)} targets x {len(a.contexts.split(','))} contexts")


if __name__ == "__main__":
    main()
