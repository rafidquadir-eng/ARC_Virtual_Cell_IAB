"""Local re-implementation of the official VCC 2026 scaled score, built on Arc's cell-eval2.

Official definition (cell-eval2 docs/vcc2026_metrics/vcc2026-metrics-brief.md, section 0):
    s = (u - b) / (r - b)
      u = panel aggregate of the submission
      b = generic mean-response baseline (oracle: mean of the context's own perturbed constructs)
      r = replicate: reference split into two disjoint halves per perturbation and per control,
          one half scored against the other with its OWN control cells, mean of 5 seeded splits
    context score = equal-weight mean of the six scaled metrics
    clamps: expr_mse_unbiased_capped_norm -> [0, 1]; de_wilcoxon_lfc_nmae floored at -6
    overall leaderboard score = mean over contexts

Differences from the official bundle (documented, small):
  * The official baseline also filters constructs by cell count / knockdown efficiency; we use
    cell-eval2's build_generic_baseline defaults, which apply its own filter.
  * Our split-halves are seeded by numpy, not the official base_seed stream, so r differs at
    the seed-noise level reported in the brief (0.2-4.8 % of the span).

Usage:
  python -m vcc26.local_eval anchors --real held_out.h5ad --out anchors.json
  python -m vcc26.local_eval score   --pred pred.h5ad --real held_out.h5ad --anchors anchors.json
"""
from __future__ import annotations

import argparse
import json
import logging
import warnings
from dataclasses import replace

import anndata as ad
import numpy as np
import polars as pl

from cell_eval2 import EvalConfig, aggregate_metrics, build_generic_baseline, compute_metrics

warnings.filterwarnings("ignore")
logging.getLogger("cell_eval2").setLevel(logging.ERROR)

SCORED = [
    "pds_cosine",
    "expr_mse_unbiased_capped_norm",
    "de_wilcoxon_direction_fidelity_yield_raw",
    "de_wilcoxon_direction_reach_raw",
    "de_wilcoxon_sig_jaccard",
    "de_wilcoxon_lfc_nmae",
]
SHORT = {"pds_cosine": "pds", "expr_mse_unbiased_capped_norm": "mse",
         "de_wilcoxon_direction_fidelity_yield_raw": "fid",
         "de_wilcoxon_direction_reach_raw": "reach",
         "de_wilcoxon_sig_jaccard": "jac", "de_wilcoxon_lfc_nmae": "nmae"}
CLAMP = {"expr_mse_unbiased_capped_norm": (0.0, 1.0), "de_wilcoxon_lfc_nmae": (-6.0, None)}


def make_config(pert_col: str = "target", control: str = "non-targeting",
                device: str = "auto", de_backend: str = "auto") -> EvalConfig:
    cfg = EvalConfig.from_preset("vcc2026")
    cfg = replace(cfg, pert_col=pert_col, control=control, device=device)
    if de_backend != "auto":
        cfg = replace(cfg, de=replace(cfg.de, backend=de_backend))
    return cfg


def _agg(df: pl.DataFrame) -> dict[str, float]:
    a = aggregate_metrics(df)
    return {m: float(v) for m, v in zip(a["metric"], a["mean"]) if m in SCORED}


def raw_metrics(pred, real, cfg: EvalConfig) -> dict[str, float]:
    return _agg(compute_metrics(pred, real, config=cfg))


def _split_halves(real: ad.AnnData, pert_col: str, seed: int):
    rng = np.random.default_rng(seed)
    a_idx, b_idx = [], []
    for _, idx in real.obs.groupby(pert_col, observed=True).indices.items():
        idx = rng.permutation(idx)
        h = len(idx) // 2
        a_idx.extend(idx[:h]); b_idx.extend(idx[h:2 * h])
    return real[np.sort(a_idx)].copy(), real[np.sort(b_idx)].copy()


# The OFFICIAL baseline arm has identical cells (emit="tile"): cell_eval2 0.18.0 competition.py
# L304-305 "the baseline arm's cells are identical so its jk_pred is exactly 0". The library default
# is emit="dispersed", which calls almost no DE genes and put our local fid/jac/reach anchors on the
# wrong scale (local baseline fid 0.03 vs official 0.51). Review O-01, 17 Oct.
BASELINE_EMIT = "tile"


def build_anchors(real_path: str, cfg: EvalConfig, n_splits: int = 5, emit: str = BASELINE_EMIT) -> dict:
    real = ad.read_h5ad(real_path)
    base = build_generic_baseline(real, config=cfg, emit=emit)
    agg = base.agg
    b = {m: float(agg.filter(pl.col("statistic") == "mean")[m][0]) for m in SCORED if m in agg.columns}
    # replicate end: the scorer's own anchor leg (derived seeds, FULL_GATE_RAW estimator for lfc_nmae);
    # the hand-rolled split-half loop differed on both (review B-05). Falls back to it on failure.
    try:
        from cell_eval2.anchor import compute_replicate_anchor
        _, anc = compute_replicate_anchor(real, config=cfg, base_seed=0, n_splits=n_splits)
        rv = dict(zip(anc["metric"].to_list(), anc["replicate"].to_list()))
        rs = dict(zip(anc["metric"].to_list(), anc["replicate_sd"].to_list()))
        r = {m: float(rv[m]) for m in SCORED}; r_sd = {m: float(rs[m]) for m in SCORED}
        rep_src = "cell_eval2.anchor.compute_replicate_anchor"
    except Exception as e:                                # pragma: no cover
        logging.getLogger(__name__).warning("official replicate anchor failed (%s); split-half fallback", e)
        reps = []
        rep_cfg = replace(cfg, control_source="pred")   # each half uses its own control cells
        for s in range(n_splits):
            ha, hb = _split_halves(real, cfg.pert_col, s)
            reps.append(raw_metrics(hb, ha, rep_cfg))
        r = {m: float(np.mean([x[m] for x in reps])) for m in SCORED}
        r_sd = {m: float(np.std([x[m] for x in reps])) for m in SCORED}
        rep_src = "local split-half fallback"
    return {"baseline": b, "replicate": r, "replicate_sd": r_sd, "n_splits": n_splits, "baseline_emit": emit,
            "replicate_source": rep_src,
            "n_perts": int(real.obs[cfg.pert_col].nunique() - 1)}


def scale(u: dict, anchors: dict) -> dict:
    out = {}
    for m in SCORED:
        b, r = anchors["baseline"][m], anchors["replicate"][m]
        s = (u[m] - b) / (r - b) if r != b else float("nan")
        lo, hi = CLAMP.get(m, (None, None))
        if lo is not None: s = max(lo, s)
        if hi is not None: s = min(hi, s)
        out[SHORT[m]] = s
    out["context_score"] = float(np.nanmean([out[SHORT[m]] for m in SCORED]))
    return out


def score(pred, real_path: str, anchors: dict, cfg: EvalConfig, return_frame: bool = False):
    """Scaled + raw panel metrics. return_frame=True also returns cell-eval2's per-perturbation
    frame (perturbation, metric, value), which vcc26.compare bootstraps."""
    df = compute_metrics(pred, real_path, config=cfg)
    u = _agg(df)
    res = scale(u, anchors)
    res["raw"] = {SHORT[m]: u[m] for m in SCORED}
    return (res, df) if return_frame else res


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("anchors"); a.add_argument("--real", required=True); a.add_argument("--out", required=True)
    a.add_argument("--emit", default=BASELINE_EMIT, choices=["tile", "dispersed"])
    a.add_argument("--n-splits", type=int, default=5)
    s = sub.add_parser("score"); s.add_argument("--pred", required=True); s.add_argument("--real", required=True)
    s.add_argument("--anchors", required=True)
    for p in (a, s):
        p.add_argument("--pert-col", default="target"); p.add_argument("--control", default="non-targeting")
        p.add_argument("--device", default="auto"); p.add_argument("--de-backend", default="auto")
    args = ap.parse_args()
    cfg = make_config(args.pert_col, args.control, args.device, args.de_backend)
    if args.cmd == "anchors":
        anc = build_anchors(args.real, cfg, args.n_splits, emit=args.emit)
        json.dump(anc, open(args.out, "w"), indent=2); print(json.dumps(anc, indent=2))
    else:
        print(json.dumps(score(args.pred, args.real, json.load(open(args.anchors)), cfg), indent=2))


if __name__ == "__main__":
    main()
