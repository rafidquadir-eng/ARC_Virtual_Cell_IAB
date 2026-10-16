"""Which DepMap/CCLE cell line does each challenge context most resemble? (round 3, docs/15 P13)

  python scripts/ccle_match.py --controls-dir $DATA/challenge/controls --contexts A,B,C \
      --expr $DATA/priors/depmap/OmicsExpressionProteinCodingGenesTPMLogp1.csv \
      --models $DATA/priors/depmap/Model.csv --out reports/E042_ccle_match.json

Query = pseudobulk log2(CPM+1) of the context's control cells (10x Flex counts are per transcript, so
CPM is TPM-like). Reference = DepMap log2(TPM+1), default entry per model. Two scores over the 3,000
most variable expressed CCLE genes on the challenge axis: Spearman of raw profiles, and Pearson of
profiles centred by the CCLE gene means (removes the 'average cell line' shape). Platform bias (Flex
probes vs bulk poly-A) is common to every comparison of one query, so the RANKING is what to read;
an exact identity is an inference, not a fact. Sex markers are printed as a consistency check.
Only public data are read; nothing is uploaded.
"""
import argparse
import json
import re
import sys

import anndata as ad
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, "src")
from vcc26.predict_challenge import find_ctx  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--controls-dir", required=True); ap.add_argument("--contexts", default="A,B,C")
ap.add_argument("--expr", required=True); ap.add_argument("--models", default=None)
ap.add_argument("--n-genes", type=int, default=3000); ap.add_argument("--top", type=int, default=15)
ap.add_argument("--out", required=True)
a = ap.parse_args()

hdr = pd.read_csv(a.expr, nrows=0).columns.tolist()
gene_cols = [c for c in hdr if re.match(r"^.+ \(\d+\)$", c)]
E = pd.read_csv(a.expr, low_memory=False)
if "IsDefaultEntryForModel" in E.columns:
    E = E[E["IsDefaultEntryForModel"].astype(str).isin(["Yes", "True", "true", "1"])]
idcol = "ModelID" if "ModelID" in E.columns else E.columns[0]
E = E.set_index(idcol)[gene_cols]
E.columns = [c.split(" (")[0] for c in gene_cols]
E = E.loc[:, ~E.columns.duplicated()].astype(np.float32)
meta = pd.read_csv(a.models).set_index("ModelID") if a.models else None
print(f"DepMap: {E.shape[0]} models x {E.shape[1]} genes")

queries = {}
for c in a.contexts.split(","):
    x = ad.read_h5ad(find_ctx(a.controls_dir, c))
    tot = np.asarray(x.X.sum(0)).ravel().astype(np.float64)
    queries[c] = pd.Series(np.log2(tot / tot.sum() * 1e6 + 1), index=np.asarray(x.var_names, str))

common = sorted(set(E.columns) & set.intersection(*[set(q.index) for q in queries.values()]))
Ec = E[common]
expressed = Ec.mean(0) > 1.0
var = Ec.loc[:, expressed].var(0).sort_values(ascending=False)
genes = var.index[: a.n_genes]
R = Ec[genes].values
mu = R.mean(0)
Rc = R - mu
out = {"n_models": int(E.shape[0]), "n_genes_used": int(len(genes)), "contexts": {}}
for c, q in queries.items():
    v = q[genes].values
    sp = np.array([spearmanr(v, r).statistic for r in R])
    vc = v - mu
    pc = (Rc @ vc) / (np.linalg.norm(Rc, axis=1) * np.linalg.norm(vc) + 1e-12)
    df = pd.DataFrame({"spearman": sp, "centred_pearson": pc}, index=Ec.index)
    df["rank_sum"] = df["spearman"].rank(ascending=False) + df["centred_pearson"].rank(ascending=False)
    df = df.sort_values("rank_sum").head(a.top)
    if meta is not None:
        cols = [k for k in ("CellLineName", "OncotreeLineage", "OncotreePrimaryDisease", "OncotreeSubtype", "Sex")
                if k in meta.columns]
        df = df.join(meta[cols], how="left")
    sexq = {g: round(float(q.get(g, np.nan)), 2) for g in ("XIST", "RPS4Y1", "DDX3Y", "UTY")}
    out["contexts"][c] = {"sex_markers_log2cpm": sexq, "top": df.round(3).reset_index().to_dict("records")}
    print(f"\n== context {c}  sex markers {sexq}")
    print(df.round(3).to_string())
json.dump(out, open(a.out, "w"), indent=1, default=str)
print(f"\nwrote {a.out}")
