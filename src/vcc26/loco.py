"""Leave-one-context-out (LOCO) validation that mimics the 2026 zero-shot test.

For each held-out context c:
  1. Build a challenge-shaped reference: up to --panel targets, 400 cells each (or what exists),
     plus c's non-targeting cells, raw counts, on the shared gene axis.
  2. Hand the predictors ONLY c's control cells + the OTHER contexts' summaries.
     --mode seen   : sources keep their measurements of the panel targets (target was screened
                     elsewhere; true for most targets that are in Replogle K562 genome-wide)
     --mode unseen : panel targets are removed from every source (target never screened)
  3. Emit cells, score with the official vcc2026 metric profile, scale with locally built
     baseline/replicate anchors (local_eval.py).

Config (JSON):
{
  "contexts": [
     {"name": "K562", "h5ad": "data/k562_essential.h5ad", "pert_col": "gene",
      "control": "non-targeting", "summary": "pb/K562.npz", "symbol_col": null}, ...
  ],
  "gene_axis": "challenge/gene_names.csv"
}

  python -m vcc26.loco --config loco.json --holdout RPE1 --mode seen --out runs/E001
"""
from __future__ import annotations

import argparse
import json
import os
import time

import anndata as ad
import numpy as np
import pandas as pd
import polars as pl
import scipy.sparse as sp

from . import local_eval, models
from .emit import control_cpm, emit
from .pseudobulk import load as load_summary

CTRL = "non-targeting"


def subset_summary(s: dict, axis: np.ndarray, drop: set[str] | None = None) -> dict:
    pos = {g: i for i, g in enumerate(s["genes"])}
    cols = np.array([pos.get(g, -1) for g in axis])
    def take(M):
        out = np.zeros(M.shape[:-1] + (len(axis),), M.dtype)
        out[..., cols >= 0] = M[..., cols[cols >= 0]]
        return out
    keep = np.ones(len(s["perts"]), bool) if not drop else ~np.isin(s["perts"], list(drop))
    pres = np.zeros(len(axis), bool); pres[cols >= 0] = s["present"][cols[cols >= 0]]
    return dict(genes=axis, perts=s["perts"][keep], lfc=take(s["lfc"][keep]), cpm=take(s["cpm"][keep]),
                ctrl_cpm=take(s["ctrl_cpm"]), present=pres, ncells=s["ncells"][keep], kd=s["kd"][keep])


def read_panel(path: str | None) -> set[str] | None:
    """Target list (CSV with a 'target_gene' column, or one header-less column)."""
    if not path:
        return None
    df = pd.read_csv(path)
    col = "target_gene" if "target_gene" in df.columns else None
    vals = df[col] if col else pd.read_csv(path, header=None).iloc[:, 0]
    return set(vals.astype(str)) - {CTRL}


def thin_umis(X: sp.csr_matrix, umi_target: float | None, rng) -> tuple[sp.csr_matrix, float]:
    """Binomially thin every cell by one global factor so the median UMI/cell drops to umi_target
    (A/B/C have ~20k UMI/cell; Arc's 2025 H1 data has >50k). Returns (X, factor); factor 1 = no-op."""
    if not umi_target:
        return X, 1.0
    lib = np.asarray(X.sum(1)).ravel()
    f = float(umi_target) / float(np.median(lib))
    if f >= 1:
        return X, 1.0
    X = X.copy()
    X.data = rng.binomial(X.data.astype(np.int64), f).astype(np.float32)
    X.eliminate_zeros()
    return X, f


def prepare_holdout(ctx: dict, axis_all: np.ndarray, outdir: str, n_panel: int, n_cells: int,
                    seed: int, max_kd: float = 0.7, panel_set: set[str] | None = None,
                    max_ctrl: int = 18400, min_cells: int | None = None, umi_target: float | None = None):
    """Challenge-shaped truth for one held-out context. Regime matching (round 3): min_cells=400 keeps
    only targets with >= 400 cells (A/B/C have exactly 400 per target), umi_target thins to their depth."""
    os.makedirs(outdir, exist_ok=True)
    real_p, ctrl_p = f"{outdir}/real.h5ad", f"{outdir}/ctrl.h5ad"
    if os.path.exists(real_p) and os.path.exists(ctrl_p):
        r = ad.read_h5ad(real_p, backed="r")
        return real_p, ctrl_p, np.array(r.var_names), \
            sorted(set(r.obs["target"].astype(str)) - {CTRL})
    rng = np.random.default_rng(seed)
    a = ad.read_h5ad(ctx["h5ad"], backed="r")
    sym = np.asarray(a.var[ctx["symbol_col"]] if ctx.get("symbol_col") else a.var_names, str)
    _, first = np.unique(sym, return_index=True)
    in_axis = set(axis_all)
    gcols = np.array(sorted(j for j in first if sym[j] in in_axis))
    axis = sym[gcols]
    lab = a.obs[ctx["pert_col"]].astype(str).values
    summ = load_summary(ctx["summary"])
    mc = min(n_cells, 50) if min_cells is None else min_cells
    ok = set(summ["perts"][(summ["ncells"] >= mc) & ~(summ["kd"] > max_kd)])
    cand = sorted(p for p in ok if p in set(axis) and (panel_set is None or p in panel_set))
    panel = sorted(rng.choice(cand, min(n_panel, len(cand)), replace=False))
    rows = []
    for p in panel:
        idx = np.where(lab == p)[0]
        rows.append(rng.choice(idx, min(n_cells, len(idx)), replace=False))
    cidx = np.where(lab == ctx["control"])[0]
    if len(cidx) > max_ctrl:                      # challenge contexts have 18,400 controls
        cidx = rng.choice(cidx, max_ctrl, replace=False)
    rows.append(cidx)
    rows = np.sort(np.concatenate(rows))
    X = a.X[rows]
    X = sp.csr_matrix((X if sp.issparse(X) else sp.csr_matrix(X))[:, gcols].astype(np.float32))
    X.sum_duplicates()                            # canonical CSR (sorted indices); cell-eval2 requires it
    X, f = thin_umis(X, umi_target, rng)
    if f < 1:
        print(f"thinned UMIs by {f:.3f} to median {umi_target:.0f}/cell")
        X.sum_duplicates()
    t = np.where(lab[rows] == ctx["control"], CTRL, lab[rows])
    real = ad.AnnData(X, obs=pd.DataFrame({"target": t}, index=[f"c{i}" for i in range(len(rows))]),
                      var=pd.DataFrame(index=axis))
    real.write_h5ad(real_p)
    real[real.obs["target"] == CTRL].copy().write_h5ad(ctrl_p)
    return real_p, ctrl_p, axis, panel


def run(cfg_path: str, holdout: str, mode: str, out: str, n_panel: int, n_cells: int, seed: int,
        model_specs: list[dict], de_backend: str = "auto", device: str = "auto",
        extra_emb: dict | None = None, tag: str = "default", panel_file: str | None = None,
        only_sources: list[str] | None = None, exclude_licence: str | None = None, far: bool = False,
        holdout_tag: str | None = None, min_target_cells: int | None = None, umi_target: float | None = None,
        match_cells: bool = False):
    cfg = json.load(open(cfg_path))
    axis_all = pd.read_csv(cfg["gene_axis"], header=None).iloc[:, 0].astype(str).values
    ctxs = {c["name"]: c for c in cfg["contexts"]}
    hold = ctxs[holdout]
    hdir = f"{out}/holdout_{holdout}" + (f"_{holdout_tag}" if holdout_tag else "")
    real_p, ctrl_p, axis, panel = prepare_holdout(hold, axis_all, hdir, n_panel, n_cells, seed,
                                                  panel_set=read_panel(panel_file),
                                                  min_cells=min_target_cells, umi_target=umi_target)
    ecfg = local_eval.make_config("target", CTRL, device, de_backend)
    anc_p = f"{hdir}/anchors.json"
    if os.path.exists(anc_p) and json.load(open(anc_p)).get("baseline_emit") != local_eval.BASELINE_EMIT:
        # anchors built before 17 Oct used the dispersed baseline (wrong scale, review O-01): keep, rebuild
        os.replace(anc_p, f"{hdir}/anchors_dispersed.json")
        print(f"anchors: moved old dispersed-baseline anchors to {hdir}/anchors_dispersed.json; rebuilding with emit=tile")
    if not os.path.exists(anc_p):
        json.dump(local_eval.build_anchors(real_p, ecfg), open(anc_p, "w"), indent=2)
    anchors = json.load(open(anc_p))
    drop = set(panel) if mode == "unseen" else None
    # never use a source from the same cell line as the held-out context (e.g. K562 essential vs K562 GWPS)
    line = hold.get("line", holdout)
    src_names = [n for n, c in ctxs.items() if n != holdout and c.get("line", n) != line
                 and (not only_sources or n in only_sources)
                 and not (exclude_licence and exclude_licence in str(c.get("licence", "")))
                 and not (far and hold.get("lineage") and c.get("lineage") == hold.get("lineage"))]
    if not src_names:
        raise ValueError("no source contexts left after line/--sources filtering")
    sources = [dict(subset_summary(load_summary(ctxs[n]["summary"]), axis, drop), name=n,
                    library=ctxs[n].get("library"), line=ctxs[n].get("line", n)) for n in src_names]
    cover = sum(any(p in set(s_["perts"]) for s_ in sources) for p in panel)
    print(f"holdout {holdout} (line {line}): {len(panel)} panel targets, sources {src_names}, "
          f"{cover} panel targets measured in >=1 source")
    ctrl = ad.read_h5ad(ctrl_p)
    tgt_cpm = control_cpm(ctrl)            # target context's control profile (all a model may see)
    sizes = n_cells
    if match_cells:   # emit as many cells per target as the truth has, so prediction, truth and the
        # baseline (built at truth group sizes) have the same Wilcoxon power, as on the leaderboard
        vc = ad.read_h5ad(real_p, backed="r").obs["target"].astype(str).value_counts()
        sizes = np.array([int(vc.get(p, n_cells)) for p in panel])
        print(f"match-cells: per-target cells median {int(np.median(sizes))}, min {sizes.min()}, max {sizes.max()}")
    rows, frames = [], []
    for spec in model_specs:
        t0 = time.time()
        name, kw = spec["name"], dict(spec.get("kw", {}))
        fb = spec.get("fallback")
        if fb == "linear":
            kw["fallback"] = models.linear_fallback(sources, **spec.get("fb_kw", {}))
        elif fb and fb.startswith("knn:"):
            emb = (extra_emb or {})[fb[4:]]
            kw["fallback"] = models.knn_fallback(sources, emb, **spec.get("fb_kw", {}))
        kw["target_ctrl_cpm"] = tgt_cpm
        extra = {}
        if spec["model"] == "ORACLE":                # diagnostic ceiling: the held-out line's own lfc
            real_ad = ad.read_h5ad(real_p)
            from .pseudobulk import summarize
            so = summarize(real_ad, "target", CTRL, np.asarray(axis), min_cells=1)
            pos = {p: i for i, p in enumerate(so["perts"])}
            lfc = np.vstack([so["lfc"][pos[p]] for p in panel])
        elif spec["model"] == "A1_transfer":
            lfc, info = models.MODELS["A1_transfer"](panel, sources, return_info=True, **kw)
            pt = info["per_target"]
            extra = {"source_r": [round(float(x), 3) for x in info["source_r"]],
                     "source_w": [round(float(x), 3) for x in info["source_w"]],
                     "mean_gate": round(float(np.mean([x[4] for x in pt])), 3),
                     "n_multi_source": int(sum(x[1] > 1 for x in pt)),
                     "n_unmeasured": int(sum(x[1] == 0 for x in pt)),
                     "n_neighbor_targets": info.get("n_neighbor_targets", 0)}
        elif spec["model"] in ("B5_sparse", "M1_gbm", "ENS"):
            lfc, info = models.MODELS[spec["model"]](panel, sources, return_info=True, **kw)
            extra = {k: v for k, v in info.items() if isinstance(v, (int, float, str))}
        else:
            lfc = models.MODELS[spec["model"]](panel, sources, **kw)
        lfc = models.apply_post(lfc, spec.get("post"), ctrl, n_cells=sizes, targets=panel)
        pred = emit(spec.get("emit", "random"), ctrl, panel, lfc, n_cells=sizes, context=holdout,
                    seed=seed, include_control=n_cells)   # scorer requires the control label
        res, pframe = local_eval.score(pred, real_p, anchors, ecfg, return_frame=True)
        frames.append(pframe.with_columns(pl.lit(name).alias("spec"), pl.lit(spec.get("emit", "random")).alias("emit")))
        row = {"model": name, "emit": spec.get("emit", "random"), "holdout": holdout + (f"_{holdout_tag}" if holdout_tag else ""), "mode": mode,
               "sources": "+".join(src_names),
               "n_panel": len(panel), "n_covered": cover, **{k: v for k, v in res.items() if k != "raw"},
               **{f"raw_{k}": v for k, v in res["raw"].items()}, **{k: json.dumps(v) if isinstance(v, list) else v for k, v in extra.items()},
               "secs": round(time.time() - t0, 1)}
        rows.append(row); print(json.dumps(row))
    df = pd.DataFrame(rows)
    path = f"{out}/scores_{holdout}{'_' + holdout_tag if holdout_tag else ''}_{mode}_{tag}.csv"
    if os.path.exists(path):                       # never overwrite an earlier sweep
        path = path.replace(".csv", f"_{time.strftime('%Y%m%d-%H%M%S')}.csv")
    df.to_csv(path, index=False)
    if frames:   # per-target metrics for paired bootstrap comparisons (vcc26.compare)
        pl.concat(frames, how="diagonal").write_parquet(path.replace("scores_", "pertarget_").replace(".csv", ".parquet"))
    print(f"wrote {path}")
    return df


DEFAULT_SPECS = [
    {"name": "B0_control", "model": "B0_control"},
    {"name": "B1_generic", "model": "B1_generic"},
    {"name": "B2_transfer_a1", "model": "B2_transfer", "kw": {"alpha": 1.0}},
    {"name": "B2_transfer_a0.6", "model": "B2_transfer", "kw": {"alpha": 0.6}},
    {"name": "B3_linear", "model": "B2_transfer", "kw": {"alpha": 1.0}, "fallback": "linear"},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--holdout", required=True)
    ap.add_argument("--mode", choices=["seen", "unseen"], default="seen")
    ap.add_argument("--out", required=True); ap.add_argument("--panel", type=int, default=300)
    ap.add_argument("--cells", type=int, default=400); ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--specs", default=None, help="JSON file with model specs (default: baselines)")
    ap.add_argument("--emb", action="append", default=[],
                    help="name=path.npz gene embedding {symbol: vector}, usable as fallback 'knn:name'")
    ap.add_argument("--de-backend", default="auto"); ap.add_argument("--device", default="auto")
    ap.add_argument("--panel-file", default=None,
                    help="restrict the held-out panel to these targets (e.g. the challenge pert_counts.csv)")
    ap.add_argument("--sources", default=None, help="comma-separated source context names to use (default: all)")
    ap.add_argument("--tag", default=None, help="suffix for the scores file (default: specs file name)")
    ap.add_argument("--exclude-licence", default=None, help='drop sources whose licence contains this, e.g. "NC"')
    ap.add_argument("--far", action="store_true", help="also drop sources of the held-out line's lineage (V*-far)")
    add_regime_args(ap)
    a = ap.parse_args()
    specs = json.load(open(a.specs)) if a.specs else DEFAULT_SPECS
    embs = {}
    for e in a.emb:
        n, p = e.split("=", 1); z = np.load(p, allow_pickle=True); embs[n] = {k: z[k] for k in z.files}
    tag = a.tag or (os.path.splitext(os.path.basename(a.specs))[0] if a.specs else "default")
    run(a.config, a.holdout, a.mode, a.out, a.panel, a.cells, a.seed, specs, a.de_backend, a.device, embs, tag,
        a.panel_file, a.sources.split(",") if a.sources else None, a.exclude_licence, a.far,
        a.holdout_tag, a.min_target_cells, a.umi_target, a.match_cells)


def add_regime_args(ap):
    """Round-3 options that make a held-out line look like A/B/C to the DE metrics (docs/15 P2)."""
    ap.add_argument("--holdout-tag", default=None, help="separate holdout dir/name, e.g. R400 for a regime-matched truth")
    ap.add_argument("--min-target-cells", type=int, default=None, help="keep only targets with >= this many truth cells (A/B/C: 400)")
    ap.add_argument("--umi-target", type=float, default=None, help="thin the truth (and its controls) to this median UMI/cell (A/B/C: ~20000)")
    ap.add_argument("--match-cells", action="store_true", help="emit as many cells per target as the truth has")


if __name__ == "__main__":
    main()
