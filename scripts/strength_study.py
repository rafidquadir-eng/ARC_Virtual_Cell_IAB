"""Can we predict how strongly each target responds in an unseen line? (round 4: R4-05 / C-02 / C-08; CPU)

N_conf, the truth's number of significant genes per target, is heavy-tailed: on val A it runs from 4 to
about 7,000, with a mean of 336. Yet every config treats all 300 targets the same.

This script tests which zero-shot features rank the held-out N_conf: Spearman per held-out line, and a
leave-one-line-out (LOLO) linear model on within-line percentiles.

A feature may only use what a model could see at test time:
  src_nstrong_mean / src_nstrong_max  log1p number of axis genes with |lfc| / (sd_g * sqrt(med_n / n_t)) >= z
                                      in a source (gene SD over all of that source's perts; genes with source
                                      control CPM >= --cpm-min; target gene excluded). Datasets of a line are
                                      averaged, then mean / max over lines. The held-out line's own datasets
                                      are excluded, as in loco.
  src_kd_mean                         mean remaining target expression in the sources (lower = stronger knockdown)
  src_n_lines                         number of source lines measuring the target
  target_ctrl_cpm                     log1p CPM of the target in the held-out controls (from the per-target table)
  depmap_mean                         mean Chronos gene effect over all DepMap models (pan-line fitness; negative = essential)
  depmap_line                         Chronos effect in the held-out line's own DepMap model (--line-names; NaN if not screened)

  python scripts/strength_study.py --config loco.json --pertarget results/E044/pertarget_nconf_holdout_*.csv \
      --depmap $DATA/priors/depmap/CRISPRGeneEffect.csv --models $DATA/priors/depmap/Model.csv \
      --line-names K562_GWPS=K562,Orion_HCT116=HCT116,Orion_HEK293T=HEK293T \
      --out results/E044/strength_study.json

Decision rule (docs/16 §4, lever L6):
- per-target strength (budgets / magnitudes scaled per target) is worth building only if the best feature set's LOLO Spearman, averaged over lines, is >= 0.45;
- DepMap is worth wiring in only if "all" beats src_nstrong_mean alone by >= 0.10.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from vcc26.pseudobulk import load as load_summary  # noqa: E402

FEATS = ["src_nstrong_mean", "src_nstrong_max", "src_kd_mean", "src_n_lines", "target_ctrl_cpm", "depmap_mean", "depmap_line"]


def strip(n):
    return "".join(ch for ch in str(n).upper() if ch.isalnum())


def source_features(path, targets, z, cpm_min):
    """{target: (log1p n_strong, kd)} for one source summary."""
    s = load_summary(path)
    perts = np.asarray(s["perts"]).astype(str)
    genes = np.asarray(s["genes"]).astype(str)
    lfc = s["lfc"].astype(np.float32)
    keep = (np.asarray(s["ctrl_cpm"]).ravel() >= cpm_min)
    if "present" in s:
        keep &= np.asarray(s["present"]).astype(bool).ravel()
    pert_mask = perts != "non-targeting"
    sd = lfc[pert_mask][:, keep].std(axis=0) + 1e-6
    ncells = np.asarray(s["ncells"]).astype(float)
    med = float(np.median(ncells[pert_mask])) if pert_mask.any() else 1.0
    gidx = {g: i for i, g in enumerate(genes)}
    kept_genes = genes[keep]
    out = {}
    pos = {p: i for i, p in enumerate(perts)}
    for t in targets:
        if t not in pos:
            continue
        i = pos[t]
        zz = np.abs(lfc[i, keep]) / (sd * np.sqrt(med / max(ncells[i], 1.0)))
        if t in gidx and keep[gidx[t]]:
            zz = zz[kept_genes != t]
        out[t] = (float(np.log1p((zz >= z).sum())), float(s["kd"][i]) if "kd" in s else np.nan)
    del lfc
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--pertarget", nargs="+", required=True)
    ap.add_argument("--depmap", default=None); ap.add_argument("--models", default=None)
    ap.add_argument("--line-names", default="", help="holdout=DepMap cell line name, comma-separated")
    ap.add_argument("--z", type=float, default=4.0); ap.add_argument("--cpm-min", type=float, default=10.0)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    ctxs = {c["name"]: c for c in cfg["contexts"]}
    files = sorted({f for p in a.pertarget for f in glob.glob(p)})
    truth = {}
    for f in files:
        h = os.path.basename(f).replace("pertarget_nconf_", "").replace("holdout_", "").replace(".csv", "")
        truth[h] = pd.read_csv(f)
    if not truth:
        raise SystemExit("no per-target tables found")
    def reg_name(h):
        return h if h in ctxs else (h.rsplit("_", 1)[0] if h.rsplit("_", 1)[0] in ctxs else None)
    all_targets = sorted({t for df in truth.values() for t in df["target"].astype(str)})
    print(f"{len(truth)} held-out lines, {len(all_targets)} distinct targets; computing source features ...")
    feats = {}
    for n, c in ctxs.items():
        if not os.path.exists(c["summary"]):
            print(f"  skip {n}: no summary"); continue
        feats[n] = source_features(c["summary"], all_targets, a.z, a.cpm_min)
        print(f"  {n}: {len(feats[n])} targets measured")
    dm_mean, dm_line = {}, {}
    if a.depmap:
        D = pd.read_csv(a.depmap, index_col=0)
        D.columns = [c.split(" (")[0] for c in D.columns]
        dm_mean = D.mean(axis=0, skipna=True).to_dict()
        names = dict(kv.split("=", 1) for kv in a.line_names.split(",") if "=" in kv)
        if names and a.models:
            M = pd.read_csv(a.models)
            M["_k"] = M["CellLineName"].map(strip)
            for h, nm in names.items():
                hit = M.loc[M["_k"] == strip(nm), "ModelID"].tolist()
                mid = next((m for m in hit if m in D.index), None)
                dm_line[h] = D.loc[mid].to_dict() if mid else {}
                print(f"  DepMap model for {h} ({nm}): {mid or 'not screened'}")
    rows = []
    for h, df in truth.items():
        rn = reg_name(h)
        line = ctxs[rn].get("line", rn) if rn else h
        src = [n for n in feats if ctxs[n].get("line", n) != line]
        for _, r in df.iterrows():
            t = str(r["target"])
            per_line = {}
            for n in src:
                if t in feats[n]:
                    per_line.setdefault(ctxs[n].get("line", n), []).append(feats[n][t])
            ns = [np.mean([v[0] for v in vs]) for vs in per_line.values()]
            kd = [v[1] for vs in per_line.values() for v in vs if np.isfinite(v[1])]
            rows.append({"holdout": h, "target": t, "N_conf": int(r["N_conf"]), "y": np.log1p(r["N_conf"]),
                         "src_nstrong_mean": np.mean(ns) if ns else np.nan, "src_nstrong_max": np.max(ns) if ns else np.nan,
                         "src_kd_mean": np.mean(kd) if kd else np.nan, "src_n_lines": len(per_line),
                         "target_ctrl_cpm": np.log1p(r.get("target_ctrl_cpm", np.nan)),
                         "depmap_mean": dm_mean.get(t, np.nan), "depmap_line": dm_line.get(h, {}).get(t, np.nan)})
    T = pd.DataFrame(rows)
    res = {"per_line_spearman": {}, "lolo": {}, "n_targets": T.groupby("holdout").size().to_dict()}
    for h, g in T.groupby("holdout"):
        res["per_line_spearman"][h] = {f: (float(spearmanr(g[f], g["y"], nan_policy="omit")[0])
                                           if g[f].notna().sum() >= 10 and g[f].nunique() > 1 else None) for f in FEATS}
    # LOLO on within-line percentiles; NaN -> 0.5 (the median)
    P = T.copy()
    for f in FEATS + ["y"]:
        P[f] = P.groupby("holdout")[f].rank(pct=True).fillna(0.5)
    sets = {"all": [f for f in FEATS if T[f].notna().mean() > 0.3], "src_only": ["src_nstrong_mean"],
            "depmap_mean_only": ["depmap_mean"], "src+depmap": ["src_nstrong_mean", "src_nstrong_max", "depmap_mean"]}
    for name, fs in sets.items():
        per = {}
        for h in P["holdout"].unique():
            tr, te = P[P.holdout != h], P[P.holdout == h]
            X = np.c_[np.ones(len(tr)), tr[fs].values]; w = np.linalg.lstsq(X, tr["y"].values, rcond=None)[0]
            pred = np.c_[np.ones(len(te)), te[fs].values] @ w
            per[h] = float(spearmanr(pred, te["y"])[0])
        res["lolo"][name] = {"features": fs, "per_line": per, "mean": float(np.mean(list(per.values())))}
    full, src = res["lolo"]["all"]["mean"], res["lolo"]["src_only"]["mean"]
    best = max(res["lolo"], key=lambda k: res["lolo"][k]["mean"])
    res["decision"] = {"all_mean": full, "src_only_mean": src, "best_set": best, "best_mean": res["lolo"][best]["mean"],
                       "use_per_target_strength": bool(res["lolo"][best]["mean"] >= 0.45),
                       "depmap_adds": bool(full - src >= 0.10)}
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1)
    T.to_csv(a.out.replace(".json", "_table.csv"), index=False)
    with pd.option_context("display.width", 200):
        print("Spearman with log1p(N_conf), per held-out line:")
        print(pd.DataFrame(res["per_line_spearman"]).T.round(3).to_string())
        print("\nLOLO linear model on within-line percentiles (Spearman of prediction):")
        print(pd.DataFrame({k: v["per_line"] for k, v in res["lolo"].items()}).round(3).to_string())
    print("decision:", res["decision"])
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
