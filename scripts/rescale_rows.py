"""Re-scale stored V*/LOCO rows with the CURRENT anchors (review O-01: tile baseline).

Predictions don't need re-running: rows CSVs keep the raw metric values. After `loco` (or
`local_eval anchors`) has rebuilt `holdout_<h>/anchors.json` with the tile baseline, run

  python scripts/rescale_rows.py --dir $DATA/loco/E020 --rows results/E031/vstar_rows_E031_seen.csv results/E034/vstar_rows_E034_seen.csv \
      --out results/E042/rescaled_E031_E034.csv

It prints per-spec selection (mean context score over held-out lines) under the new anchors, next to
the old one, and the per-metric means.
"""
import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from vcc26.local_eval import SCORED, SHORT, scale  # noqa: E402

INV = {v: k for k, v in SHORT.items()}
ap = argparse.ArgumentParser()
ap.add_argument("--dir", required=True, help="loco output dir holding holdout_<name>/anchors.json")
ap.add_argument("--rows", nargs="+", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()
rows = pd.concat([pd.read_csv(f) for f in a.rows], ignore_index=True)
out = []
for _, r in rows.iterrows():
    anc_p = os.path.join(a.dir, f"holdout_{r['holdout']}", "anchors.json")
    if not os.path.exists(anc_p):
        print(f"skip {r['holdout']}: no {anc_p}"); continue
    anc = json.load(open(anc_p))
    u = {INV[m]: float(r[f"raw_{m}"]) for m in SHORT.values()}
    s = scale(u, anc)
    out.append({"model": r["model"], "emit": r.get("emit", ""), "holdout": r["holdout"],
                "baseline_emit": anc.get("baseline_emit", "dispersed"),
                "old_context_score": r["context_score"], **{f"new_{k}": v for k, v in s.items()}})
df = pd.DataFrame(out)
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
df.to_csv(a.out, index=False)
key = ["model", "emit"]
summ = df.groupby(key)[["old_context_score", "new_context_score"] + [f"new_{SHORT[m]}" for m in SCORED]].mean()
summ = summ.join(df.pivot_table(index=key, columns="holdout", values="new_context_score").add_prefix("line_"))
with pd.option_context("display.width", 250, "display.max_columns", 40):
    print(summ.sort_values("new_context_score", ascending=False).round(3).to_string())
print(f"wrote {a.out}")
