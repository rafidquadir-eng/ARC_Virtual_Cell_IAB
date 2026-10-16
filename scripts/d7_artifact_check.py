"""D7 check: donor/batch artefact genes before vs after composition-matched controls.

For each dataset, median |lfc| over all perturbations x (chrY genes | HLA genes) present in the summary,
plus chrY genes expressed in controls (CPM >= 5) against autosomal genes at matched CPM (noise floor),
for the old summary and the re-summarised one. chrY genes come from the GENCODE GTF.

  python scripts/d7_artifact_check.py --gtf gencode.basic.gtf.gz --pairs NAME=old.npz:new.npz ... [--csv out.csv]
"""
import argparse
import gzip
import re

import numpy as np
import pandas as pd


def chry_genes(gtf):
    """male-specific chrY genes: on chrY and not on chrX (drops the pseudoautosomal genes)."""
    y, x = set(), set()
    with gzip.open(gtf, "rt") as f:
        for line in f:
            if (line.startswith("chrY\t") or line.startswith("chrX\t")) and "\tgene\t" in line:
                m = re.search(r'gene_name "([^"]+)"', line)
                if m:
                    (y if line[3] == "Y" else x).add(m.group(1))
    return y - x


def med_abs(z, genes):
    g = np.asarray(z["genes"], str)
    m = np.isin(g, list(genes)) & np.asarray(z["present"], bool)
    if m.sum() == 0 or len(z["perts"]) == 0:
        return np.nan, 0
    return float(np.median(np.abs(z["lfc"][:, m]))), int(m.sum())


def expr_y_vs_floor(z, y, min_cpm=5.0):
    """median |lfc| on chrY genes with control CPM >= min_cpm, and on non-Y genes in the same CPM range
    (the sampling-noise floor at that expression level)."""
    g = np.asarray(z["genes"], str); c = np.asarray(z["ctrl_cpm"], float); pres = np.asarray(z["present"], bool)
    ym = np.isin(g, list(y)) & pres & (c >= min_cpm)
    if ym.sum() == 0:
        return np.nan, np.nan, 0
    lo, hi = c[ym].min(), c[ym].max()
    fm = ~np.isin(g, list(y)) & pres & (c >= lo) & (c <= hi)
    return float(np.median(np.abs(z["lfc"][:, ym]))), float(np.median(np.abs(z["lfc"][:, fm]))), int(ym.sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gtf", required=True); ap.add_argument("--pairs", nargs="+", required=True)
    ap.add_argument("--csv", default=None)
    a = ap.parse_args()
    y = chry_genes(a.gtf)
    rows = []
    for pr in a.pairs:
        name, paths = pr.split("=", 1)
        old_p, new_p = paths.split(":")
        r = {"dataset": name}
        for tag, p in [("old", old_p), ("new", new_p)]:
            z = np.load(p, allow_pickle=True)
            hla = {g for g in np.asarray(z["genes"], str) if g.startswith("HLA-")}
            r[f"Y_{tag}"], r["n_Y"] = med_abs(z, y)
            r[f"HLA_{tag}"], r["n_HLA"] = med_abs(z, hla)
            r[f"Yexpr_{tag}"], r[f"floor_{tag}"], r["n_Yexpr"] = expr_y_vs_floor(z, y)
            r[f"all_{tag}"] = float(np.median(np.abs(z["lfc"][:, np.asarray(z["present"], bool)])))
            r[f"perts_{tag}"] = len(z["perts"])
            r[f"median_kd_{tag}"] = float(np.nanmedian(z["kd"]))
        r["Y_fold_drop"] = r["Y_old"] / r["Y_new"] if r["Y_new"] else np.nan
        r["Yexpr_fold_drop"] = r["Yexpr_old"] / r["Yexpr_new"] if r["Yexpr_new"] else np.nan
        ex_o, ex_n = r["Yexpr_old"] - r["floor_old"], r["Yexpr_new"] - r["floor_new"]
        r["Yexcess_old"], r["Yexcess_new"] = ex_o, ex_n
        r["Yexcess_fold_drop"] = ex_o / ex_n if ex_n > 0 else np.inf
        r["HLA_fold_drop"] = r["HLA_old"] / r["HLA_new"] if r["HLA_new"] else np.nan
        rows.append(r)
        print(r, flush=True)
    df = pd.DataFrame(rows)
    print(df.round(4).to_markdown(index=False))
    if a.csv:
        df.to_csv(a.csv, index=False)


if __name__ == "__main__":
    main()
