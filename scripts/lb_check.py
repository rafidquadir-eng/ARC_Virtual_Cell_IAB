"""Leaderboard guardrails (review D-01 / A-01 / D-03, 17 Oct). Two checks:

1. calibration: back out the official per-metric baseline b and replicate r from two LB status JSONs
   (scaled = (u - b)/(r - b) per metric; two entries give both), and diff them against local anchors.
       python scripts/lb_check.py calib --status results/E033_E021_status.json results/E033_E032_status.json \
           --anchors $DATA/loco/E037/holdout_H1_R400/anchors.json [--anchors ...]
   A raw gap > 0.05 on any metric prints CALIBRATION ALERT (exit 2).

2. retrodiction: does a local validator reproduce the LB per-metric deltas of two configs that are on
   the LB? Uses rows CSVs from loco/vstar (or rescale_rows.py output with new_* columns).
       python scripts/lb_check.py retro --rows results/E042/rescaled_E020_E031_E034.csv \
           --a "B5_z2_a0.5_cis5000" --b "B2_raw_gPL(E021)" \
           --lb-a results/E033_E032_status.json --lb-b results/E033_E021_status.json
   PASS needs the sign of the mean delta to match the LB on the context score and on at least 5 of 6 metrics
   (metrics with |LB delta| < 0.01 count as matching either way). Per-line sign agreement is printed too.
"""
import argparse
import json
import sys

import numpy as np
import pandas as pd

METRICS = {"pds": "pds_cosine", "mse": "expr_mse_unbiased_capped_norm", "fid": "de_wilcoxon_direction_fidelity_yield_raw",
           "reach": "de_wilcoxon_direction_reach_raw", "jac": "de_wilcoxon_sig_jaccard", "nmae": "de_wilcoxon_lfc_nmae"}


def _status(path):
    """(raw, scaled) dicts by short name from a `vcc --json status` file (flat layout: raw metric
    values under their full names, scaled ones under score_<short>)."""
    d = json.load(open(path))
    raw = {m: float(d[full]) for m, full in METRICS.items() if d.get(full) is not None}
    sc = {m: float(d[f"score_{m}"]) for m in METRICS if d.get(f"score_{m}") is not None}
    return raw, sc


def calib(a):
    (u1, s1), (u2, s2) = _status(a.status[0]), _status(a.status[1])
    rows = []
    for m in METRICS:
        clamped = m == "mse" and any(v in (0.0, 1.0) for v in (s1.get(m), s2.get(m)))
        if clamped or m not in u1 or m not in s1 or m not in u2 or m not in s2 or abs(s1[m] - s2[m]) < 1e-9:
            rows.append({"metric": m, "b_LB": np.nan, "r_LB": np.nan}); continue
        d = (u1[m] - u2[m]) / (s1[m] - s2[m]); b = u1[m] - s1[m] * d
        rows.append({"metric": m, "b_LB": b, "r_LB": b + d})
    lb = pd.DataFrame(rows).set_index("metric")
    alert = False
    for p in a.anchors:
        A = json.load(open(p))
        base = A["baseline"] if "baseline" in A else {METRICS[k]: v for k, v in A.get("anchors_baseline", {}).items() if k in METRICS}
        name = A.get("holdout") or p.split("/")[-2]
        for m, full in METRICS.items():
            lb.loc[m, f"b_local[{name}]"] = base.get(full, np.nan)
        gap = (lb.filter(like="b_local").sub(lb["b_LB"], axis=0)).abs().drop(index="mse", errors="ignore")
        if (gap > 0.05).any().any():
            alert = True
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(lb.round(4).to_string())
    print("note: mse is clamped at 0 on the LB, so an entry scoring 0 there gives no information; fid/jac/reach/pds/nmae are reliable")
    if alert:
        print("CALIBRATION ALERT: a local baseline differs from the LB-implied one by > 0.05 raw (mse excluded if NaN)")
        sys.exit(2)
    print("calibration OK")


def retro(a):
    df = pd.read_csv(a.rows)
    pre = "new_" if any(c.startswith("new_") for c in df.columns) else ""
    cols = {m: f"{pre}{m}" for m in METRICS}
    cs = f"{pre}context_score"
    A = df[df.model == a.a].set_index("holdout"); B = df[df.model == a.b].set_index("holdout")
    lines = sorted(set(A.index) & set(B.index))
    d = pd.DataFrame({m: A.loc[lines, c] - B.loc[lines, c] for m, c in cols.items()})
    d["context"] = A.loc[lines, cs] - B.loc[lines, cs]
    _, sa = _status(a.lb_a); _, sb = _status(a.lb_b)
    lbd = {m: sa[m] - sb[m] for m in METRICS if m in sa and m in sb}
    lbd["context"] = np.mean(list(lbd.values())) if len(lbd) == 6 else np.nan
    mean = d.mean()
    ok = {m: (abs(lbd[m]) < 0.01) or (np.sign(mean[m]) == np.sign(lbd[m])) for m in lbd}
    n_ok = sum(ok[m] for m in METRICS if m in ok)
    with pd.option_context("display.width", 250):
        print("per-line local deltas (a - b):"); print(d.round(3).to_string())
        print("\nmean local delta:", mean.round(3).to_dict()); print("LB delta:        ", {k: round(v, 3) for k, v in lbd.items()})
        per_line = (np.sign(d[list(METRICS)]) == np.sign(pd.Series({m: lbd[m] for m in METRICS}))).sum(1)
        print("per-line metric-sign agreement with LB (of 6):", per_line.to_dict())
    # signs alone are not enough: E031's V* had the context and fid signs right but fid 6x too small
    ctx_err = abs(mean["context"] - lbd["context"])
    big = [m for m in METRICS if m in lbd and abs(lbd[m]) >= 0.05]
    ratio = {m: (mean[m] / lbd[m]) for m in big}
    mag_ok = all(1 / 3 <= r <= 3 for r in ratio.values())
    passed = ok.get("context", False) and n_ok >= 5 and ctx_err <= 0.015 and mag_ok
    print(f"context delta local {mean['context']:+.4f} vs LB {lbd['context']:+.4f} (|err| {ctx_err:.4f}, need <= 0.015)")
    print("local/LB ratio on metrics with |LB delta| >= 0.05 (need 1/3..3):", {m: round(v, 2) for m, v in ratio.items()})
    print(f"RETRODICTION {'PASS' if passed else 'FAIL'}: context sign {'ok' if ok.get('context') else 'WRONG'}, metric signs {n_ok}/6, magnitudes {'ok' if mag_ok else 'OFF'}")
    sys.exit(0 if passed else 3)


ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd", required=True)
c = sub.add_parser("calib"); c.add_argument("--status", nargs=2, required=True); c.add_argument("--anchors", nargs="+", required=True)
r = sub.add_parser("retro"); r.add_argument("--rows", required=True); r.add_argument("--a", required=True); r.add_argument("--b", required=True)
r.add_argument("--lb-a", required=True); r.add_argument("--lb-b", required=True)
a = ap.parse_args()
calib(a) if a.cmd == "calib" else retro(a)
