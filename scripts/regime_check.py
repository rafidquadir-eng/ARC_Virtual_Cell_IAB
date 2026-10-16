"""Does a held-out truth look like A/B/C to the DE metrics? (round 3, docs/15 P2)

  python scripts/regime_check.py --holdout-dir $DATA/loco/E037/holdout_H1_R400 [--anchors-too]

Prints cells per target, median UMI/cell, the truth's per-target count of significant genes (N_conf,
own target excluded, scorer gate and BH), and the local baseline/replicate anchors next to the
official val A/B/C values that cell_eval2 0.18.0 records in its source notes.
"""
import argparse, json, logging, os, sys, warnings
import numpy as np, polars as pl, anndata as ad
warnings.filterwarnings("ignore"); logging.getLogger("cell_eval2").setLevel(logging.ERROR)
from cell_eval2.de_compute import compute_de

OFFICIAL = {  # cell_eval2 0.18.0 source notes (competition.py, metrics/de.py, metrics/direction.py, de.py)
    "cells_per_target": 400, "controls": 18400, "median_umi": "~20k (our E000 inventory)",
    "N_conf_mean_valA": round(100771 / 300, 1), "N_conf_min_valA": 4,
    "baseline_fid": [0.5056, 0.5227, 0.5094], "baseline_jac_valA": 0.0333, "replicate_like_jac_valA": 0.38,
    "baseline_reach_valA": 0.0423, "replicate_reach": [0.965, 0.802, 0.943],
    "baseline_pds": [0.5304, 0.5284, 0.5102],
}

ap = argparse.ArgumentParser(); ap.add_argument("--holdout-dir", required=True)
ap.add_argument("--per-target-out", default=None, help="CSV: target, N_conf, target's own control CPM / fraction of cells")
a = ap.parse_args()
real = ad.read_h5ad(f"{a.holdout_dir}/real.h5ad")
lab = real.obs["target"].astype(str)
vc = lab[lab != "non-targeting"].value_counts()
lib = np.asarray(real.X.sum(1)).ravel()
df = compute_de(real, backend="auto", groupby="target", reference="non-targeting", mean_calc="arithmetic",
                epsilon=1e-9, input_type="counts", target_sum=1e6, filter_gene_min_cpm_cell=5.0, fdr_scope="per_pert")
df = df.filter(pl.col("feature") != pl.col("target"))
nconf = df.filter(pl.col("p_adj") < 0.05).group_by("target").len()
nc = np.array(nconf["len"].to_list() + [0] * (len(vc) - nconf.height))
out = {"holdout": os.path.basename(a.holdout_dir.rstrip("/")), "targets": int(len(vc)),
       "cells_per_target_median": int(vc.median()), "controls": int((lab == "non-targeting").sum()),
       "median_umi": float(np.median(lib)),
       "N_conf": {"mean": float(nc.mean()), "median": float(np.median(nc)), "min": int(nc.min()),
                  "p90": float(np.percentile(nc, 90)), "max": int(nc.max())}}
# Does the target's own expression in the controls predict a null response (N_conf = 0)? (review, 17 Oct)
ctrl = real[(lab == "non-targeting").values]
Xc = ctrl.X.tocsc() if hasattr(ctrl.X, "tocsc") else ctrl.X
tot = np.asarray(Xc.sum(0)).ravel().astype(float); cpm_all = tot / tot.sum() * 1e6
frac_all = np.asarray((Xc > 0).sum(0)).ravel() / Xc.shape[0]
gpos = {g: i for i, g in enumerate(np.asarray(real.var_names, str))}
nc_map = dict(zip(nconf["target"].to_list(), nconf["len"].to_list()))
import pandas as pd
pt = pd.DataFrame({"target": list(vc.index)})
pt["N_conf"] = [int(nc_map.get(t, 0)) for t in pt["target"]]
pt["target_ctrl_cpm"] = [cpm_all[gpos[t]] if t in gpos else np.nan for t in pt["target"]]
pt["target_ctrl_frac"] = [frac_all[gpos[t]] if t in gpos else np.nan for t in pt["target"]]
bins = [-1, 1, 5, 20, 100, 1e9]
pt["cpm_bin"] = pd.cut(pt["target_ctrl_cpm"], bins, labels=["<1", "1-5", "5-20", "20-100", ">100"])
by = pt.groupby("cpm_bin", observed=False).agg(n=("target", "size"), frac_null=("N_conf", lambda v: float(np.mean(np.asarray(v) == 0)) if len(v) else np.nan),
                                                frac_lt10=("N_conf", lambda v: float(np.mean(np.asarray(v) < 10)) if len(v) else np.nan),
                                                median_nconf=("N_conf", "median"))
out["N_conf_by_target_cpm"] = {str(k): {kk: (None if pd.isna(vv) else float(vv)) for kk, vv in r.items()} for k, r in by.iterrows()}
out["targets_not_on_axis"] = int(pt["target_ctrl_cpm"].isna().sum())
if a.per_target_out:
    pt.to_csv(a.per_target_out, index=False)
anc = f"{a.holdout_dir}/anchors.json"
if os.path.exists(anc):
    A = json.load(open(anc))
    from vcc26.local_eval import SHORT
    out["anchors_baseline"] = {SHORT.get(k, k): round(v, 4) for k, v in A["baseline"].items()}
    out["anchors_replicate"] = {SHORT.get(k, k): round(v, 4) for k, v in A["replicate"].items()}
out["official_valABC"] = OFFICIAL
print(json.dumps(out, indent=1))
