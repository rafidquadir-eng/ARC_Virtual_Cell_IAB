"""Panel coverage by our sources (round 4, E049): for a perturbation list (A/B/C or D/E/F), how many distinct
source LINES measure each target with >= --min-cells cells.

  python scripts/panel_coverage.py --config loco.json --perts $DATA/challenge_test/<...>/pert_counts.csv \
      --out results/E049/panel_coverage_DEF.csv [--exclude-licence NC] [--min-cells 50]

Prints the >=1 / >=2 / >=3-line counts and lists the targets measured in no line. B5 predicts only cis
effects for an unmeasured target, so a low >=2 share changes which model is safe for the final.
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from vcc26.pseudobulk import load as load_summary  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--config", required=True); ap.add_argument("--perts", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--min-cells", type=int, default=50); ap.add_argument("--exclude-licence", default=None)
a = ap.parse_args()
targets = sorted(t for t in pd.read_csv(a.perts).iloc[:, 0].astype(str).unique() if t.lower() not in ("non-targeting", "non_targeting"))
cov = pd.DataFrame(index=targets)
for c in json.load(open(a.config))["contexts"]:
    if a.exclude_licence and a.exclude_licence in str(c.get("licence", "")):
        continue
    if not os.path.exists(c["summary"]):
        print(f"skip {c['name']}: no summary"); continue
    s = load_summary(c["summary"])
    n = dict(zip(np.asarray(s["perts"]).astype(str), np.asarray(s["ncells"]).astype(int)))
    line = c.get("line", c["name"])
    col = pd.Series({t: n.get(t, 0) >= a.min_cells for t in targets})
    cov[line] = (cov[line] | col) if line in cov.columns else col
cov["n_lines"] = cov.sum(axis=1)
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
cov.to_csv(a.out, index_label="target")
print(f"{len(targets)} targets; lines: {[c for c in cov.columns if c != 'n_lines']}")
for k in (1, 2, 3):
    print(f"  measured in >= {k} line(s) with >= {a.min_cells} cells: {(cov.n_lines >= k).sum()}")
print("  per line:", cov.drop(columns="n_lines").sum().astype(int).to_dict())
miss = cov.index[cov.n_lines == 0].tolist()
print(f"  unmeasured ({len(miss)}): {miss[:50]}{' ...' if len(miss) > 50 else ''}")
print(f"wrote {a.out}")
