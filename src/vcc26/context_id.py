"""Which cell types are the challenge contexts? Compare their control cells with every public line.

  python -m vcc26.context_id --controls-dir $DATA/challenge/controls --contexts A,B,C \
      --gene-axis gene_axis.csv --summaries $DATA/pb/*.npz --out reports/context_id.json

Prints, per context: Pearson r of log1p control CPM against each source line's control CPM (on genes
both measure), a marker-gene panel, sex genes, and the 30 genes most specific to that context versus
the other contexts. Nothing here is used for training; it tells us how far A/B/C are from our sources.
"""
from __future__ import annotations

import argparse
import json
import os

import anndata as ad
import numpy as np
import pandas as pd

from .emit import control_cpm
from .predict_challenge import find_ctx
from .pseudobulk import load as load_summary

MARKERS = {
    "erythroid/K562": ["HBG1", "HBG2", "HBE1", "GATA1", "TAL1", "GYPA"],
    "hepatocyte/HepG2": ["ALB", "APOA1", "APOB", "AFP", "TTR", "SERPINA1"],
    "T cell/Jurkat": ["CD3E", "CD2", "LCK", "CD1A", "TRBC1", "PTPRC"],
    "pluripotent/H1": ["POU5F1", "NANOG", "LIN28A", "DPPA4", "TDGF1", "SOX2"],
    "epithelial": ["EPCAM", "KRT8", "KRT18", "KRT19", "CDH1", "CLDN4"],
    "mesenchymal/RPE1": ["VIM", "COL1A1", "FN1", "TAGLN", "ACTA2", "SPARC"],
    "myeloid": ["LYZ", "CD14", "CSF1R", "SPI1", "ITGAM", "CD68"],
    "B cell": ["CD19", "MS4A1", "CD79A", "PAX5", "IGHM", "CD74"],
    "neural": ["SOX11", "STMN2", "DCX", "TUBB3", "NES", "PAX6"],
    "kidney/HEK293": ["LIN28B", "PAX2", "PAX8", "LHX1", "CRYAB", "ID2"],
    "colon/HCT116": ["CDX2", "CDX1", "LGALS4", "CEACAM5", "VIL1", "OLFM4"],
    "lung/A549": ["SFTPB", "NKX2-1", "NAPSA", "SFTPC", "AKR1C1", "AKR1B10"],
    "proliferation": ["MKI67", "TOP2A", "CCNB1", "PCNA", "MCM2", "TYMS"],
    "sex": ["XIST", "RPS4Y1", "DDX3Y", "UTY", "KDM5D", "EIF1AY"],
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--controls-dir", required=True); ap.add_argument("--contexts", default="A,B,C")
    ap.add_argument("--gene-axis", required=True); ap.add_argument("--summaries", nargs="+", required=True)
    ap.add_argument("--out", default="reports/context_id.json")
    a = ap.parse_args()
    axis = pd.read_csv(a.gene_axis, header=None).iloc[:, 0].astype(str).values
    ctxs = a.contexts.split(",")
    cpm = {}
    for c in ctxs:
        x = ad.read_h5ad(find_ctx(a.controls_dir, c))
        x = x[:, [g for g in axis if g in set(x.var_names)]]
        v = pd.Series(control_cpm(x), index=x.var_names)
        cpm[c] = v.reindex(axis).fillna(0.0).values
    srcs = {}
    for p in a.summaries:
        s = load_summary(p)
        pos = {g: i for i, g in enumerate(s["genes"])}
        v = np.full(len(axis), np.nan)
        for j, g in enumerate(axis):
            i = pos.get(g)
            if i is not None and s["present"][i]:
                v[j] = s["ctrl_cpm"][i]
        srcs[os.path.splitext(os.path.basename(p))[0]] = v
    out = {}
    gi = {g: i for i, g in enumerate(axis)}
    for c in ctxs:
        lc = np.log1p(cpm[c])
        corr = {}
        for n, v in srcs.items():
            m = ~np.isnan(v)
            corr[n] = round(float(np.corrcoef(lc[m], np.log1p(v[m]))[0, 1]), 3)
        for d in ctxs:
            if d != c:
                corr[f"context_{d}"] = round(float(np.corrcoef(lc, np.log1p(cpm[d]))[0, 1]), 3)
        markers = {k: {g: round(float(cpm[c][gi[g]]), 1) for g in gs if g in gi} for k, gs in MARKERS.items()}
        others = np.mean([cpm[d] for d in ctxs if d != c], 0) if len(ctxs) > 1 else np.zeros(len(axis))
        spec = np.log2((cpm[c] + 5) / (others + 5))
        top = [(axis[j], round(float(cpm[c][j]), 1), round(float(spec[j]), 2)) for j in np.argsort(-spec)[:30]]
        out[c] = {"pearson_log1p_ctrl_cpm": dict(sorted(corr.items(), key=lambda kv: -kv[1])),
                  "markers_cpm": markers, "top_specific_genes(gene,cpm,log2_vs_other_contexts)": top}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)
    for c in ctxs:
        print(f"== context {c}")
        print("  similarity:", out[c]["pearson_log1p_ctrl_cpm"])
        for k, v in out[c]["markers_cpm"].items():
            print(f"  {k:18s}", v)
        print("  most specific:", ", ".join(f"{g}({x})" for g, x, _ in out[c]["top_specific_genes(gene,cpm,log2_vs_other_contexts)"]))
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
