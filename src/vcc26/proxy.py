"""Fast pseudobulk-space proxies of the vcc2026 metrics, plus an error anatomy. Seconds per spec
instead of ~4 min with cell emission + cell-eval2, so denoising/weighting grids can be swept; the
winners are then confirmed with the real metric (vcc26.vstar).

Definitions follow the cell-eval2 vcc2026 brief:
  space    b_p = ln(1 + 5e4 * P_p / sum P_p)   (pseudobulk counts P, target sum 5e4)
  MSE      sum_p N_p / sum_p D_p,  N_p = ||b^_p - b_p||^2 - C_p,  D_p = ||b_p - b_ctrl||^2 - C_p - C_ctrl
           (C = sampling variance from split halves; our balanced emitter adds no prediction noise)
           baseline = the held-out line's mean perturbed profile; scaled = (u - b) / (0 - b)
  PDS      cosine distance of predicted effect (b^_p - b_ctrl) to every measured effect, panel
           targets excluded from the genes; PDS_p = 1 - (#closer or tied others) / (n - 1)
  DEsign   on each target's top-50 truth genes by |lfc| (control > 5 CPM): fraction with the right sign
  NMAEp    on the same genes: sum |lfc^ - lfc| / sum |lfc| (log2, pseudocount 0.1 CPM)
All targets' own gene excluded.

  python -m vcc26.proxy --config loco.json --holdout CD4T_Stim8hr --holdout-dir $DATA/loco/E020/holdout_CD4T_Stim8hr \
      --specs specs_E025.json --out results/E025 [--anatomy B4_lr] [--sources a,b]
"""
from __future__ import annotations

import argparse
import json
import os

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp

from . import loco, models
from .emit import control_cpm
from .pseudobulk import load as load_summary

TS = 5e4
CTRL = "non-targeting"


def truth_tables(real_path: str, seed: int = 0) -> dict:
    a = ad.read_h5ad(real_path)
    X = a.X.tocsr() if sp.issparse(a.X) else sp.csr_matrix(a.X)
    lab = a.obs["target"].astype(str).values
    rng = np.random.default_rng(seed)
    perts = sorted(set(lab) - {CTRL})
    groups = [CTRL] + perts
    full, ha, hb, ncell = [], [], [], []
    for g in groups:
        idx = np.where(lab == g)[0]
        idx = rng.permutation(idx); h = len(idx) // 2
        for store, ii in ((full, idx), (ha, idx[:h]), (hb, idx[h:2 * h])):
            store.append(np.asarray(X[ii].sum(0)).ravel())
        ncell.append(len(idx))
    F, A, B = (np.vstack(z).astype(np.float64) for z in (full, ha, hb))
    return {"genes": np.asarray(a.var_names, str), "perts": perts, "P": F[1:], "Pc": F[0],
            "A": A[1:], "B": B[1:], "Ac": A[0], "Bc": B[0], "ncell": np.array(ncell[1:])}


def bspace(P):
    P = np.atleast_2d(P)
    return np.log1p(TS * P / np.maximum(P.sum(1, keepdims=True), 1e-12))


def pred_counts(lfc: np.ndarray, ctrl_cpm: np.ndarray) -> np.ndarray:
    """Predicted pseudobulk composition (any scale) from pc = 1 CPM log2FC, as the emitter does."""
    return np.maximum((ctrl_cpm[None, :] + 1.0) * np.power(2.0, lfc) - 1.0, 0.0)


def score(lfc: np.ndarray, T: dict, panel_genes: set, ctrl_cpm: np.ndarray) -> dict:
    genes = T["genes"]; n = len(T["perts"])
    gi = {g: i for i, g in enumerate(genes)}
    b = bspace(T["P"]); bc = bspace(T["Pc"])[0]
    bA, bB = bspace(T["A"]), bspace(T["B"]); bcA, bcB = bspace(T["Ac"])[0], bspace(T["Bc"])[0]
    bh = bspace(pred_counts(lfc, ctrl_cpm))
    own = np.array([gi.get(p, -1) for p in T["perts"]])
    mask = np.ones_like(b, bool)
    mask[np.arange(n)[own >= 0], own[own >= 0]] = False
    C = (((bA - bB) ** 2) / 4 * mask).sum(1)
    Cc = (((bcA - bcB) ** 2) / 4).sum()
    D = (((b - bc) ** 2) * mask).sum(1) - C - Cc
    N = (((bh - b) ** 2) * mask).sum(1) - C
    base = bspace(T["P"].mean(0))[0]
    Nb = (((base[None, :] - b) ** 2) * mask).sum(1) - C
    mse, mse_b = N.sum() / D.sum(), Nb.sum() / D.sum()
    # the official metric also credits the prediction's own jackknife noise (rho * min(C^, C)); our
    # balanced cells have C^ ~ C, so with rho ~ 1 the leaderboard-like value subtracts C once more
    mse_credit = (N - C).sum() / D.sum()
    # PDS on effects, panel targets excluded from the genes
    keep = np.array([g not in panel_genes for g in genes])
    E = (b - bc)[:, keep]; Eh = (bh - bc)[:, keep]
    En = E / np.maximum(np.linalg.norm(E, axis=1, keepdims=True), 1e-12)
    Ehn = Eh / np.maximum(np.linalg.norm(Eh, axis=1, keepdims=True), 1e-12)
    dist = 1 - Ehn @ En.T
    d_own = np.diag(dist)[:, None]
    closer = (dist < d_own).sum(1) + 0.5 * ((dist == d_own).sum(1) - 1)
    pds = float(np.mean(1 - closer / (n - 1)))
    # replicate PDS from halves (A predicts B)
    EA = (bA - bcA)[:, keep]; EB = (bB - bcB)[:, keep]
    EAn = EA / np.maximum(np.linalg.norm(EA, axis=1, keepdims=True), 1e-12)
    EBn = EB / np.maximum(np.linalg.norm(EB, axis=1, keepdims=True), 1e-12)
    dr = 1 - EAn @ EBn.T; dro = np.diag(dr)[:, None]
    pds_r = float(np.mean(1 - ((dr < dro).sum(1) + 0.5 * ((dr == dro).sum(1) - 1)) / (n - 1)))
    # DE-direction and NMAE proxies on each target's top-50 truth genes (control > 5 CPM)
    cpm = T["P"] / T["P"].sum(1, keepdims=True) * 1e6
    ccpm = T["Pc"] / T["Pc"].sum() * 1e6
    tl = np.log2((cpm + 0.1) / (ccpm + 0.1))
    pcpm = pred_counts(lfc, ctrl_cpm); pcpm = pcpm / np.maximum(pcpm.sum(1, keepdims=True), 1e-12) * 1e6
    pl = np.log2((pcpm + 0.1) / (ccpm + 0.1))
    ok = (ccpm > 5)[None, :] & mask
    sgn, nm = [], []
    for i in range(n):
        cand = np.where(ok[i])[0]
        top = cand[np.argsort(-np.abs(tl[i, cand]))[:50]]
        sgn.append(np.mean(np.sign(pl[i, top]) == np.sign(tl[i, top])))
        nm.append(np.abs(pl[i, top] - tl[i, top]).sum() / max(np.abs(tl[i, top]).sum(), 1e-9))
    return {"mse_raw": float(mse), "mse_raw_credit": float(mse_credit), "mse_base_raw": float(mse_b),
            "mse_sc": float(1 - mse / mse_b), "mse_sc_credit": float(min(1.0, max(0.0, 1 - mse_credit / mse_b))),
            "pds_raw": pds, "pds_rep": pds_r, "pds_sc": float((pds - 0.5) / max(pds_r - 0.5, 1e-9)),
            "de_sign": float(np.mean(sgn)), "nmae_p": float(np.mean(nm)),
            "_N": N, "_D": D, "_C": C, "_bh": bh, "_b": b, "_bc": bc, "_mask": mask}


def anatomy(res: dict, T: dict, ctrl_cpm: np.ndarray) -> dict:
    """Where the error lives: target concentration of the truth signal, per-target cosine vs effect
    size, and the expression bins that the squared error comes from."""
    D, N = res["_D"], res["_N"]
    order = np.argsort(-D)
    k10 = max(1, len(D) // 10)
    bh, b, bc, m = res["_bh"], res["_b"], res["_bc"], res["_mask"]
    e = (bh - bc) * m; t = (b - bc) * m
    cos = (e * t).sum(1) / np.maximum(np.linalg.norm(e, axis=1) * np.linalg.norm(t, axis=1), 1e-12)
    scale = (e * t).sum(1) / np.maximum((e * e).sum(1), 1e-12)        # best multiplier for our effect
    ccpm = T["Pc"] / T["Pc"].sum() * 1e6
    bins = [0, 1, 5, 20, 100, 1e9]
    sq = ((bh - b) ** 2 * m).sum(0); sig = ((b - bc) ** 2 * m).sum(0)
    rows = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        g = (ccpm >= lo) & (ccpm < hi)
        rows.append({"ctrl_cpm_bin": f"[{lo},{hi})", "genes": int(g.sum()),
                     "share_sq_error": float(sq[g].sum() / sq.sum()), "share_true_signal": float(sig[g].sum() / sig.sum())})
    q = [order[:k10], order[k10:len(D) // 2], order[len(D) // 2:]]
    return {"share_D_top10pct_targets": float(D[order[:k10]].sum() / D.sum()),
            "cos_by_D_tier(top10%,10-50%,bottom50%)": [float(np.nanmean(cos[ix])) for ix in q],
            "best_scale_by_D_tier": [float(np.nanmedian(scale[ix])) for ix in q],
            "N_over_D_by_tier": [float(N[ix].sum() / max(D[ix].sum(), 1e-12)) for ix in q],
            "error_by_expression_bin": rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True); ap.add_argument("--holdout", required=True)
    ap.add_argument("--holdout-dir", required=True, help="dir with real.h5ad + ctrl.h5ad (from a loco/vstar run)")
    ap.add_argument("--specs", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--mode", default="seen", choices=["seen", "unseen"])
    ap.add_argument("--sources", default=None); ap.add_argument("--anatomy", default=None,
                    help="comma-separated spec names to print an error anatomy for")
    a = ap.parse_args()
    cfg = json.load(open(a.config)); ctxs = {c["name"]: c for c in cfg["contexts"]}
    hold = ctxs[a.holdout]; line = hold.get("line", a.holdout)
    T = truth_tables(f"{a.holdout_dir}/real.h5ad")
    axis = T["genes"]; panel = T["perts"]
    ctrl = ad.read_h5ad(f"{a.holdout_dir}/ctrl.h5ad")
    ccpm = control_cpm(ctrl)
    only = a.sources.split(",") if a.sources else None
    names = [n for n, c in ctxs.items() if n != a.holdout and c.get("line", n) != line and (not only or n in only)]
    drop = set(panel) if a.mode == "unseen" else None
    sources = [dict(loco.subset_summary(load_summary(ctxs[n]["summary"]), axis, drop), name=n,
                    library=ctxs[n].get("library"), line=ctxs[n].get("line", n)) for n in names]
    print(f"holdout {a.holdout}: {len(panel)} targets; sources {names}")
    specs = json.load(open(a.specs))
    pset = set(panel)
    rows, anat = [], {}
    for sp_ in specs:
        name = sp_["name"]; kw = dict(sp_.get("kw", {}))
        if sp_["model"] == "ORACLE":
            cp = T["P"] / T["P"].sum(1, keepdims=True) * 1e6
            lfc = np.log2((cp + 1) / (ccpm[None, :] + 1))
        else:
            if sp_.get("fallback") == "linear":
                kw["fallback"] = models.linear_fallback(sources)
            lfc = models.MODELS[sp_["model"]](panel, sources, target_ctrl_cpm=ccpm, **kw)
        r = score(np.asarray(lfc, float), T, pset, ccpm)
        row = {"spec": name, "holdout": a.holdout, "mode": a.mode, **{k: v for k, v in r.items() if not k.startswith("_")}}
        rows.append(row); print(json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()}))
        if a.anatomy and name in a.anatomy.split(","):
            anat[name] = anatomy(r, T, ccpm)
    os.makedirs(a.out, exist_ok=True)
    df = pd.DataFrame(rows)
    df.to_csv(f"{a.out}/proxy_{a.holdout}_{a.mode}.csv", index=False)
    if anat:
        json.dump(anat, open(f"{a.out}/anatomy_{a.holdout}_{a.mode}.json", "w"), indent=1)
        print(json.dumps(anat, indent=1))
    print(df.drop(columns=["holdout", "mode"]).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
