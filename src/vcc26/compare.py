"""Paired bootstrap comparison of two specs on the real vcc2026 metric (A3 / R13).

loco.run writes per-target metrics next to each scores CSV (pertarget_<holdout>_<mode>_<tag>.parquet).
For each held-out line, targets are resampled with replacement (the same draw for both specs), the
panel aggregates are recomputed with cell-eval2's own aggregate_metrics (so MSE stays a ratio of
sums), scaled with that line's anchors, and the context-score difference is averaged over lines.

  python -m vcc26.compare --dir $DATA/loco/E020 --tag E031 --a "B5_z3_a0.75_cis5000" --b "B2_raw_gPL(E021)" \
      [--emit-a balanced --emit-b balanced] [--n 1000] [--holdouts CD4T_Stim8hr,KOLF2.1J]
Prints mean delta (a - b), the 90% CI, P(delta > 0), and per-line deltas.
"""
from __future__ import annotations

import argparse
import glob
import json
import os

import numpy as np
import polars as pl

from cell_eval2 import aggregate_metrics

from .local_eval import SCORED, scale


def _agg(df: pl.DataFrame) -> dict:
    a = aggregate_metrics(df)
    return {m: float(v) for m, v in zip(a["metric"], a["mean"]) if m in SCORED}


def load(dirpath: str, tag: str, holdouts: list[str] | None):
    out = {}
    for f in glob.glob(f"{dirpath}/pertarget_*_{tag}.parquet"):
        h = os.path.basename(f)[len("pertarget_"):].rsplit(f"_{tag}", 1)[0].rsplit("_", 1)[0]
        if holdouts and h not in holdouts:
            continue
        anc = f"{dirpath}/holdout_{h}/anchors.json"
        if os.path.exists(anc):
            out[h] = (pl.read_parquet(f), json.load(open(anc)))
    return out


def boot(dirpath, tag, a, b, emit_a=None, emit_b=None, n=1000, holdouts=None, seed=0):
    data = load(dirpath, tag, holdouts)
    if not data:
        raise SystemExit(f"no pertarget_*_{tag}.parquet with anchors under {dirpath}")
    rng = np.random.default_rng(seed)
    per_line, draws = {}, []
    sel = lambda df, s, e: df.filter((pl.col("spec") == s) & ((pl.col("emit") == e) if e else pl.lit(True)))
    prepared = {}
    for h, (df, anc) in data.items():
        A, B = sel(df, a, emit_a), sel(df, b, emit_b)
        perts = sorted(set(A["perturbation"].to_list()) & set(B["perturbation"].to_list()))
        if not perts:
            continue
        sa = scale(_agg(A.filter(pl.col("perturbation").is_in(perts))), anc)["context_score"]
        sb = scale(_agg(B.filter(pl.col("perturbation").is_in(perts))), anc)["context_score"]
        per_line[h] = sa - sb
        prepared[h] = (A, B, perts, anc)
    for _ in range(n):
        ds = []
        for h, (A, B, perts, anc) in prepared.items():
            pick = rng.choice(len(perts), len(perts), replace=True)
            m = pl.DataFrame({"perturbation": [perts[i] for i in pick], "_k": np.arange(len(pick))})
            def res(X):
                Y = m.join(X, on="perturbation", how="left")
                Y = Y.with_columns((pl.col("perturbation") + "_" + pl.col("_k").cast(pl.Utf8)).alias("perturbation"))
                return scale(_agg(Y.drop("_k")), anc)["context_score"]
            ds.append(res(A) - res(B))
        draws.append(float(np.mean(ds)))
    d = np.array(draws)
    return {"a": a, "b": b, "tag": tag, "lines": list(prepared), "delta_mean": float(np.mean(list(per_line.values()))),
            "ci90": [float(np.quantile(d, 0.05)), float(np.quantile(d, 0.95))], "p_gt0": float((d > 0).mean()),
            "per_line": per_line, "n_boot": n}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True); ap.add_argument("--tag", required=True)
    ap.add_argument("--a", required=True); ap.add_argument("--b", required=True)
    ap.add_argument("--emit-a", default=None); ap.add_argument("--emit-b", default=None)
    ap.add_argument("--n", type=int, default=1000); ap.add_argument("--holdouts", default=None)
    x = ap.parse_args()
    r = boot(x.dir, x.tag, x.a, x.b, x.emit_a, x.emit_b, x.n, x.holdouts.split(",") if x.holdouts else None)
    print(json.dumps(r, indent=1))


if __name__ == "__main__":
    main()
