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
   With raw_* columns the rows are scaled with the LB spans (review R-02), which is the default now.

3. spans: write the LB-implied (b, r) as anchors JSON (results/lb_spans.json).
4. rank: LB-span table per variant (spec name + " |renorm" when VCC_RENORM_AXIS=1) x emitter; mean over
   seeds per line, then over lines; seed_sd; --ref adds the delta vs a reference and lines positive.
5. forecast / verify (round 4, R4-01): pre-register an LB entry's per-metric forecast from local deltas,
   commit it, submit, then `verify` the scored status JSON against it.
       python scripts/lb_check.py forecast --status results/E033_E021_status.json results/E033_E032_status.json \
           --rows <rows CSVs> --cand "<spec>@@<emit>" --out results/forecasts/E047a.json
       python scripts/lb_check.py verify --forecast results/forecasts/E047a.json --status results/E047a_status.json
   Caveat (19 Oct): on the one pair we have (E021 vs E032), the overall forecast was within 0.004 but
   per-metric errors were large and cancelled: fid +0.14, reach -0.07, nmae -0.06, mse -0.03. Treat
   per-metric forecasts as rough; V* under-rewards fid changes about 2.5x.
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


def lb_spans(status_a, status_b, mse_b=0.99, mse_r=0.05):  # noqa: E302
    """Official (b, r) per metric backed out of two LB entries. MSE is clamped at 0 for E021, so its
    (b, r) are ASSUMED (b ~ 0.98-0.99 from E032 with r in [0, 0.1]; r ~ split-half noise floor)."""
    (u1, s1), (u2, s2) = _status(status_a), _status(status_b)
    out = {}
    for m in METRICS:
        if m == "mse" or abs(s1[m] - s2[m]) < 1e-9:
            continue
        dd = (u1[m] - u2[m]) / (s1[m] - s2[m]); bb = u1[m] - s1[m] * dd
        out[m] = (bb, bb + dd)
    out["mse"] = (mse_b, mse_r)
    return out


CLAMP = {"mse": (0.0, 1.0), "nmae": (-6.0, None)}


def retro(a):
    df = pd.read_csv(a.rows)
    A = df[df.model == a.a].set_index("holdout"); B = df[df.model == a.b].set_index("holdout")
    if a.holdouts:
        keep = set(a.holdouts.split(",")); A = A[A.index.isin(keep)]; B = B[B.index.isin(keep)]
    lines = sorted(set(A.index) & set(B.index))
    if all(f"raw_{m}" in df.columns for m in METRICS):
        # review R-02: per-line local anchors are degenerate on small truths (tile fid span 0.012-0.18 vs
        # official 0.30), so scale RAW values with the official LB (b, r) and the official clamps.
        sp = lb_spans(a.lb_a, a.lb_b)
        def sc(X, m):
            b_, r_ = sp[m]; v = (X.loc[lines, f"raw_{m}"] - b_) / (r_ - b_)
            lo, hi = CLAMP.get(m, (None, None))
            return v.clip(lower=lo, upper=hi)
        d = pd.DataFrame({m: sc(A, m) - sc(B, m) for m in METRICS})
        print("scaling: raw metrics with official LB spans", {m: tuple(round(x, 3) for x in v) for m, v in sp.items()})
    else:
        pre = "new_" if any(c.startswith("new_") for c in df.columns) else ""
        d = pd.DataFrame({m: A.loc[lines, f"{pre}{m}"] - B.loc[lines, f"{pre}{m}"] for m in METRICS})
        print("scaling: per-line local anchors (WARNING: degenerate on small truths, review R-02)")
    d["context"] = d[list(METRICS)].mean(axis=1)
    _, sa = _status(a.lb_a); _, sb = _status(a.lb_b)
    lbd = {m: sa[m] - sb[m] for m in METRICS if m in sa and m in sb}
    lbd["context"] = np.mean(list(lbd.values())) if len(lbd) == 6 else np.nan
    mean = d.mean()
    ok = {m: (abs(lbd[m]) < 0.01) or (np.sign(mean[m]) == np.sign(lbd[m])) for m in lbd}
    n_ok = sum(ok[m] for m in METRICS if m in ok)
    with pd.option_context("display.width", 250):
        print("per-line local deltas (a - b):"); print(d.round(3).to_string())
        print("\nmean local delta:", mean.round(3).to_dict()); print("LB delta:        ", {k: round(v, 3) for k, v in lbd.items()})
        per_line = (np.sign(d[list(METRICS)]) == np.sign(pd.Series({m: lbd[m] for m in METRICS}))).sum(axis=1)
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


def spans_cmd(a):
    """Write the LB-implied (b, r) as an anchors-format JSON usable by compare.py / rescale_rows.py
    (--anchors-override). Review R-02: with these fixed spans the 5-line V* retrodicts E021 -> E032."""
    sp = lb_spans(a.status[0], a.status[1], a.mse_b, a.mse_r)
    out = {"baseline": {METRICS[m]: v[0] for m, v in sp.items()}, "replicate": {METRICS[m]: v[1] for m, v in sp.items()},
           "baseline_emit": "LB-implied", "source": list(a.status),
           "note": "b, r backed out of two LB entries; mse (b, r) assumed because E021's scaled mse is clamped at 0"}
    json.dump(out, open(a.out, "w"), indent=1); print(json.dumps(out, indent=1))


def _rows(files, sp, label_files=False):
    """Concatenate rows CSVs and add LB-span scaled columns. Rows differ by spec, emitter, line, seed and
    renorm_axis (round 4: seed replicates must not be dropped as duplicates). label_files: append the file
    stem to the variant, for runs that share spec names but differ otherwise (NC on/off, same-line sources)."""
    import os
    fr = []
    for f in files:
        x = pd.read_csv(f)
        x["_file"] = os.path.splitext(os.path.basename(f))[0]
        fr.append(x)
    r = pd.concat(fr, ignore_index=True)
    if "emit" not in r.columns:
        r["emit"] = ""
    r["seed"] = r["seed"].fillna(0).astype(int) if "seed" in r.columns else 0
    r["renorm_axis"] = r["renorm_axis"].fillna(False).astype(bool) if "renorm_axis" in r.columns else False
    r = r.drop_duplicates(["model", "emit", "holdout", "seed", "renorm_axis"] + (["_file"] if label_files else []), keep="last")
    for m in METRICS:
        b_, r_ = sp[m]; v = (r["raw_" + m] - b_) / (r_ - b_); lo, hi = CLAMP.get(m, (None, None)); r["lb_" + m] = v.clip(lower=lo, upper=hi)
    r["lb_ctx"] = r[["lb_" + m for m in METRICS]].mean(axis=1)
    r["variant"] = r["model"] + np.where(r["renorm_axis"], " |renorm", "")
    if label_files:
        r["variant"] = r["variant"] + " [" + r["_file"] + "]"
    return r


def rank_cmd(a):
    """Per variant x emitter: mean over seeds per line, then over lines (LB spans). `seed_sd` is the SD
    over seeds of the all-line mean (needs >= 2 seeds on the same lines). With --ref, adds the delta vs
    that variant on shared lines and how many lines are positive."""
    sp = lb_spans(a.status[0], a.status[1])
    r = _rows(a.rows, sp, a.label_files)
    if a.holdouts:
        r = r[r.holdout.isin(a.holdouts.split(","))]
    key = ["variant", "emit"]
    per = r.groupby(key + ["holdout"])["lb_ctx"].mean().unstack("holdout")
    t = per.copy()
    t.insert(0, "mean", per.mean(axis=1)); t.insert(1, "worst", per.min(axis=1)); t.insert(2, "n_lines", per.notna().sum(axis=1))
    by_seed = r.groupby(key + ["seed"])["lb_ctx"].mean().unstack("seed")
    t.insert(3, "n_seeds", r.groupby(key)["seed"].nunique())
    t.insert(4, "seed_sd", by_seed.std(axis=1, ddof=1) if by_seed.shape[1] > 1 else np.nan)
    t = t.join(r.groupby(key)[["lb_" + m for m in METRICS]].mean())
    if a.ref:
        ref_v, _, ref_e = a.ref.partition("@@")
        refrow = per.loc[(ref_v, ref_e)] if ref_e else per.xs(ref_v, level="variant").iloc[0]
        d = per.sub(refrow, axis=1)
        t.insert(2, "d_ref", d.mean(axis=1)); t.insert(3, "lines_pos", (d > 0).sum(axis=1).astype(str) + "/" + d.notna().sum(axis=1).astype(str))
    with pd.option_context("display.width", 300, "display.max_columns", 50):
        print(t.sort_values("mean", ascending=False).round(4).to_string())
    if a.out:
        t.to_csv(a.out); print(f"wrote {a.out}")


def _variant_lines(r, spec):
    v, _, e = spec.partition("@@")
    x = r[(r.variant == v) & ((r.emit == e) if e else True)]
    if x.empty:
        raise SystemExit(f"no rows for {spec}")
    return x.groupby("holdout")[["lb_" + m for m in METRICS] + ["lb_ctx"]].mean()


def forecast_cmd(a):
    """Pre-registration (round 4, R4-01): forecast an LB entry BEFORE submitting it.
    forecast(metric) = LB score of the reference entry + local delta (cand - ref, LB spans, shared lines).
    Commit the JSON before `vcc submit`; afterwards run `verify`."""
    sp = lb_spans(a.status[0], a.status[1])
    r = _rows(a.rows, sp)
    C, R = _variant_lines(r, a.cand), _variant_lines(r, a.ref)
    lines = sorted(set(C.index) & set(R.index))
    d = (C.loc[lines] - R.loc[lines])
    _, sref = _status(a.lb_ref)
    fc = {}
    for m in METRICS:
        lo, hi = CLAMP.get(m, (None, None))
        v = sref[m] + float(d["lb_" + m].mean())
        fc[m] = float(min(hi, v) if hi is not None else v)
        fc[m] = float(max(lo, fc[m]) if lo is not None else fc[m])
    fc["overall"] = float(np.mean([fc[m] for m in METRICS]))
    out = {"cand": a.cand, "ref": a.ref, "lb_ref": a.lb_ref, "lines": lines,
           "local_delta": {m: float(d["lb_" + m].mean()) for m in METRICS} | {"context": float(d["lb_ctx"].mean())},
           "local_delta_per_line": d["lb_ctx"].round(4).to_dict(), "lines_positive": f"{int((d['lb_ctx'] > 0).sum())}/{len(lines)}",
           "lb_ref_scores": sref | {"overall": float(np.mean([sref[m] for m in METRICS]))}, "forecast": fc,
           "note": a.note, "made_utc": pd.Timestamp.now(tz="UTC").isoformat()}
    json.dump(out, open(a.out, "w"), indent=1); print(json.dumps(out, indent=1)); print(f"wrote {a.out} -- commit it before submitting")


def verify_cmd(a):
    """After the entry is scored: forecast vs actual. PASS = |overall error| <= 0.015 and the sign of
    (new - ref) on the overall score matches the forecast's (|delta| < 0.005 counts either way)."""
    f = json.load(open(a.forecast)); _, s = _status(a.status)
    act = s | {"overall": float(np.mean([s[m] for m in METRICS]))}
    ref = f["lb_ref_scores"]
    rows = [{"metric": m, "forecast": f["forecast"][m], "actual": act[m], "err": act[m] - f["forecast"][m],
             "d_forecast": f["forecast"][m] - ref[m], "d_actual": act[m] - ref[m]} for m in list(METRICS) + ["overall"]]
    t = pd.DataFrame(rows).set_index("metric"); print(t.round(4).to_string())
    e = abs(t.loc["overall", "err"]); df_, da = t.loc["overall", "d_forecast"], t.loc["overall", "d_actual"]
    sign_ok = abs(df_) < 0.005 or abs(da) < 0.005 or np.sign(df_) == np.sign(da)
    ok = e <= 0.015 and sign_ok
    print(f"VERIFY {'PASS' if ok else 'FAIL'}: overall error {e:.4f} (need <= 0.015), delta sign {'ok' if sign_ok else 'WRONG'}")
    sys.exit(0 if ok else 4)


ap = argparse.ArgumentParser()
sub = ap.add_subparsers(dest="cmd", required=True)
f_ = sub.add_parser("forecast"); f_.add_argument("--status", nargs=2, required=True); f_.add_argument("--rows", nargs="+", required=True)
f_.add_argument("--cand", required=True); f_.add_argument("--ref", default="B5_z2_a0.5_cis5000@@balanced")
f_.add_argument("--lb-ref", default="results/E033_E032_status.json"); f_.add_argument("--out", required=True); f_.add_argument("--note", default="")
v_ = sub.add_parser("verify"); v_.add_argument("--forecast", required=True); v_.add_argument("--status", required=True)
s_ = sub.add_parser("spans"); s_.add_argument("--status", nargs=2, required=True); s_.add_argument("--out", required=True)
s_.add_argument("--mse-b", type=float, default=0.99); s_.add_argument("--mse-r", type=float, default=0.05)
k_ = sub.add_parser("rank"); k_.add_argument("--status", nargs=2, required=True); k_.add_argument("--rows", nargs="+", required=True)
k_.add_argument("--ref", default=None, help='reference variant, e.g. "B5_z2_a0.5_cis5000" or "B5_z2_a0.5_cis5000@@balanced"')
k_.add_argument("--holdouts", default=None, help="comma-separated subset of held-out lines")
k_.add_argument("--out", default=None, help="also write the table as CSV")
k_.add_argument("--label-files", action="store_true", help="keep rows from different files apart (variant += [file stem])")
c = sub.add_parser("calib"); c.add_argument("--status", nargs=2, required=True); c.add_argument("--anchors", nargs="+", required=True)
r = sub.add_parser("retro"); r.add_argument("--rows", required=True); r.add_argument("--a", required=True); r.add_argument("--b", required=True)
r.add_argument("--lb-a", required=True); r.add_argument("--lb-b", required=True)
r.add_argument("--holdouts", default=None, help="comma-separated subset of held-out lines")
a = ap.parse_args()
{"calib": calib, "retro": retro, "spans": spans_cmd, "rank": rank_cmd, "forecast": forecast_cmd, "verify": verify_cmd}[a.cmd](a)
