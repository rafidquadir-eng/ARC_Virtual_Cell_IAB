"""Build contexts_meta.json entries (identity + TP53 status) from a CCLE match (review C-05, 18 Oct).

  python scripts/context_meta.py --match reports/E041_ccle_match.json \
      --damaging $DATA/priors/depmap/OmicsSomaticMutationsMatrixDamaging.csv \
      --hotspot $DATA/priors/depmap/OmicsSomaticMutationsMatrixHotspot.csv \
      --out contexts_meta.json [--merge]

Status rule:
- TP53 "deficient" if the top-matched model has a damaging or hotspot TP53 call, or is a known HPV+ line (E6 degrades p53);
- "wt" otherwise.

The match must be clear: top Spearman minus the runner-up ≥ 0.05. If not, the status is null (unknown), and models then don't apply p53 weighting. Identity is an expression-based inference, not a fact.
"""
import argparse
import json
import os

import pandas as pd

HPV_POS = {"HELA", "SIHA", "CASKI", "C4II", "C4I", "MS751", "UPCISCC090", "UPCISCC152", "UMSCC47", "93VU147T", "SCC090", "SCC152", "UPCISCC154"}


def strip(n):
    return "".join(ch for ch in str(n).upper() if ch.isalnum())


def tp53_col(df):
    cols = [c for c in df.columns if c.split(" (")[0] == "TP53"]
    return cols[0] if cols else None


ap = argparse.ArgumentParser()
ap.add_argument("--match", required=True); ap.add_argument("--damaging", required=True)
ap.add_argument("--hotspot", default=None); ap.add_argument("--out", required=True)
ap.add_argument("--merge", action="store_true", help="update an existing contexts_meta.json instead of overwriting")
ap.add_argument("--min-margin", type=float, default=0.05)
a = ap.parse_args()
m = json.load(open(a.match))
dmg = pd.read_csv(a.damaging, index_col=0)
dcol = tp53_col(dmg)
hot = pd.read_csv(a.hotspot, index_col=0) if a.hotspot else None
hcol = tp53_col(hot) if hot is not None else None
meta = json.load(open(a.out)) if (a.merge and os.path.exists(a.out)) else {}
for ctx, d in m["contexts"].items():
    top = d["top"]
    t0, t1 = top[0], top[1] if len(top) > 1 else None
    margin = t0["spearman"] - (t1["spearman"] if t1 else 0)
    mid = t0.get("ModelID") or t0.get("index") or t0.get("Unnamed: 0")  # ccle_match.py writes the ModelID index as "Unnamed: 0"
    name = t0.get("CellLineName", mid)
    entry = {"ccle": f"{name} ({mid})", "spearman": t0["spearman"], "margin": round(margin, 3)}
    if margin < a.min_margin:
        entry.update(tp53=None, tp53_source=f"unclear match (margin {margin:.3f} < {a.min_margin})")
    else:
        d_ = int(dmg.loc[mid, dcol]) if (dcol and mid in dmg.index) else None
        h_ = int(hot.loc[mid, hcol]) if (hot is not None and hcol and mid in hot.index) else None
        hpv = strip(name) in HPV_POS
        defic = bool((d_ or 0) > 0 or (h_ or 0) > 0 or hpv)
        entry.update(tp53="deficient" if defic else "wt",
                     tp53_source=f"DepMap 24Q4 damaging={d_} hotspot={h_}" + (" + HPV+ line (E6)" if hpv else ""))
    meta[ctx] = entry
    print(ctx, entry)
meta.setdefault("_note", "Per-context facts for context-aware models (predict_challenge --context-meta). Identity = CCLE expression match (inference).")
json.dump(meta, open(a.out, "w"), indent=1)
print(f"wrote {a.out}")
