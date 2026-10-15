"""V*: leave-one-line-out validation on the challenge panel — the primary selection metric.

For every cell line that measured >= --min-panel challenge targets (with >= --min-cells cells each),
hold that line out, restrict its panel to the challenge targets it measured, use every OTHER line as a
source (datasets of the same line are excluded automatically by loco.run), and score each spec with
the official vcc2026 metrics against locally built anchors. When several datasets share a line, the
one with the most panel targets is the held-out representative.

  python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_E020.json \
      --out $DATA/loco/E020 --tag E020 [--mode seen|unseen] [--min-panel 100] [--lines K562_GWPS,H1]

Writes <out>/vstar_rows_<tag>.csv (one row per holdout x spec) and <out>/vstar_summary_<tag>.csv
(per spec: mean context score over held-out lines = selection score, per-metric means, per-line
scores, and the worst line). Equal weight per held-out line.
"""
from __future__ import annotations

import argparse
import json
import os

import numpy as np
import pandas as pd

from . import loco
from .pseudobulk import load as load_summary

METRICS = ["pds", "mse", "fid", "reach", "jac", "nmae"]


def eligible(cfg: dict, panel: set[str], min_panel: int, min_cells: int) -> list[tuple[str, int]]:
    best: dict[str, tuple[str, int]] = {}
    for c in cfg["contexts"]:
        s = load_summary(c["summary"])
        n = int(sum(1 for p, k in zip(s["perts"], s["ncells"]) if p in panel and k >= min_cells))
        line = c.get("line", c["name"])
        if n >= min_panel and (line not in best or n > best[line][1]):
            best[line] = (c["name"], n)
    return sorted(best.values(), key=lambda x: -x[1])


def summarize(rows: pd.DataFrame) -> pd.DataFrame:
    key = ["model", "emit"] if "emit" in rows.columns else ["model"]
    per_line = rows.pivot_table(index=key, columns="holdout", values="context_score")
    agg = rows.groupby(key)[METRICS + ["context_score"]].mean()
    out = agg.rename(columns={"context_score": "selection"})
    out["worst_line"] = per_line.min(1)
    out = out.join(per_line.add_prefix("line_"))
    return out.sort_values("selection", ascending=False).reset_index()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--panel-file", required=True)
    ap.add_argument("--specs", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--tag", default="vstar"); ap.add_argument("--mode", choices=["seen", "unseen"], default="seen")
    ap.add_argument("--min-panel", type=int, default=100); ap.add_argument("--min-cells", type=int, default=50)
    ap.add_argument("--lines", default=None, help="comma-separated context names to hold out (default: all eligible)")
    ap.add_argument("--cells", type=int, default=400); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--de-backend", default="auto"); ap.add_argument("--device", default="auto")
    ap.add_argument("--dry-run", action="store_true", help="only list the eligible held-out lines")
    a = ap.parse_args()
    cfg = json.load(open(a.config))
    panel = loco.read_panel(a.panel_file)
    elig = eligible(cfg, panel, a.min_panel, a.min_cells)
    if a.lines:
        want = set(a.lines.split(","))
        elig = [e for e in elig if e[0] in want]
    print("held-out lines (context, panel targets measured):", elig)
    if a.dry_run or not elig:
        return
    specs = json.load(open(a.specs))
    os.makedirs(a.out, exist_ok=True)
    frames = []
    for name, _ in elig:
        df = loco.run(a.config, name, a.mode, a.out, 300, a.cells, a.seed, specs, a.de_backend, a.device,
                      None, a.tag, a.panel_file, None)
        frames.append(df)
        rows = pd.concat(frames, ignore_index=True)
        rows.to_csv(f"{a.out}/vstar_rows_{a.tag}_{a.mode}.csv", index=False)   # checkpoint after each line
    summ = summarize(rows)
    summ.to_csv(f"{a.out}/vstar_summary_{a.tag}_{a.mode}.csv", index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 30):
        print(summ.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
