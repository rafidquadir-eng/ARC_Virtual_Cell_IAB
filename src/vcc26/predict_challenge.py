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

import json

from . import models
from .emit import control_cpm, emit
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
    ap.add_argument("--kw", default="{}", help='extra model kwargs as JSON, e.g. {"alpha_single": 0.7}')
    ap.add_argument("--seed", type=int, default=0); ap.add_argument("--out", required=True)
    ap.add_argument("--registry", default=None, help="loco.json, to tag sources with name/library/line")
    ap.add_argument("--exclude-licence", default=None, help='with --registry: skip summaries whose licence contains this, e.g. "NC"')
    ap.add_argument("--spec-file", default=None, help="take model/kw/fallback/emit/post from this specs JSON ...")
    ap.add_argument("--spec", default=None, help="... the spec with this name")
    ap.add_argument("--post", default=None, help='post-processing JSON, e.g. {"project": {"k": 200, "lam": 0.5}}')
    ap.add_argument("--emit", default="random", choices=["random", "balanced", "balanced2", "balanced2h", "balanced3"],
                    help="balanced = shared herded base cells + exact per-gene totals (no sampling noise)")
    a = ap.parse_args()
    post = json.loads(a.post) if a.post else None
    if a.spec_file:
        sp_ = {x["name"]: x for x in json.load(open(a.spec_file))}[a.spec]
        a.model = sp_["model"]; a.kw = json.dumps(sp_.get("kw", {})); a.fallback = sp_.get("fallback") or "none"
        a.emit = sp_.get("emit", a.emit); post = sp_.get("post", post)
        print(f"spec {a.spec}: model {a.model} kw {a.kw} fallback {a.fallback} emit {a.emit} post {post}")
    axis = pd.read_csv(a.gene_names, header=None).iloc[:, 0].astype(str).values
    pl = pd.read_csv(a.perts).iloc[:, 0].astype(str)
    targets = sorted(t for t in pl.unique() if t != CTRL)
    # name = file stem (e.g. pb/K562_GWPS.npz -> "K562_GWPS"), used by --kw '{"generic_from": [...]}'
    reg = {}
    if a.registry:                                   # loco.json: summary path -> name / library / line
        for c in json.load(open(a.registry))["contexts"]:
            reg[os.path.abspath(c["summary"])] = c
    sources = []
    for p in a.summaries:
        c = reg.get(os.path.abspath(p), {})
        if a.exclude_licence and a.exclude_licence in str(c.get("licence", "")):
            print(f"skip {p} (licence {c.get('licence')})"); continue
        sources.append(dict(subset_summary(load_summary(p), axis),
                            name=c.get("name", os.path.splitext(os.path.basename(p))[0]),
                            library=c.get("library"), line=c.get("line")))
    kw = {"alpha": a.alpha, "beta": a.beta, **json.loads(a.kw)}
    if a.model in ("B2_transfer", "A1_transfer") and a.fallback == "linear":
        kw["fallback"] = models.linear_fallback(sources)
    parts = []
    for i, c in enumerate(a.contexts.split(",")):
        ctrl = ad.read_h5ad(find_ctx(a.controls_dir, c))
        ctrl = ctrl[:, axis].copy()                     # enforce the official gene order
        # context-specific prediction: A1 uses this context's own control profile
        lfc = models.MODELS[a.model](targets, sources, target_ctrl_cpm=control_cpm(ctrl), **kw)
        lfc = models.apply_post(lfc, post, ctrl, n_cells=a.cells, targets=targets)
        parts.append(emit(a.emit, ctrl, targets, lfc, n_cells=a.cells, pert_col=a.pert_col,
                                  context=c, include_control=a.n_control, seed=a.seed + i))
    out = ad.concat(parts, merge="same")
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    out.write_h5ad(a.out)
    print(f"wrote {a.out}: {out.n_obs} cells x {out.n_vars} genes, "
          f"{len(targets)} targets x {len(a.contexts.split(','))} contexts")


if __name__ == "__main__":
    main()
