"""How many panel targets are (not) expressed in each challenge context's controls? (review, 17 Oct)

CRISPRi can't knock down a gene that isn't transcribed, and the scorer gives a target with no true DE
genes fid = jac = 1 only if nothing is called. Pair with `regime_check.py --per-target-out`, which
measures, on held-out lines, how often a target at a given control CPM has N_conf = 0.

  python scripts/target_expr.py --controls-dir $DATA/challenge/controls --contexts A,B,C --perts $PANEL \
      --out results/E042/target_expr_ABC.csv
"""
import argparse, os, sys
import anndata as ad, numpy as np, pandas as pd
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from vcc26.predict_challenge import find_ctx  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--controls-dir", required=True); ap.add_argument("--contexts", default="A,B,C")
ap.add_argument("--perts", required=True); ap.add_argument("--out", required=True)
a = ap.parse_args()
targets = sorted(t for t in pd.read_csv(a.perts).iloc[:, 0].astype(str).unique() if t != "non-targeting")
rows = []
for c in a.contexts.split(","):
    x = ad.read_h5ad(find_ctx(a.controls_dir, c))
    X = x.X.tocsc() if hasattr(x.X, "tocsc") else x.X
    tot = np.asarray(X.sum(0)).ravel().astype(float); cpm = tot / tot.sum() * 1e6
    frac = np.asarray((X > 0).sum(0)).ravel() / X.shape[0]
    pos = {g: i for i, g in enumerate(np.asarray(x.var_names, str))}
    for t in targets:
        i = pos.get(t)
        rows.append({"context": c, "target": t, "ctrl_cpm": cpm[i] if i is not None else np.nan,
                     "ctrl_frac": frac[i] if i is not None else np.nan})
df = pd.DataFrame(rows)
os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
df.to_csv(a.out, index=False)
bins = [-1, 0.5, 1, 5, 20, 100, 1e9]
df["bin"] = pd.cut(df["ctrl_cpm"], bins, labels=["<0.5", "0.5-1", "1-5", "5-20", "20-100", ">100"])
print(df.pivot_table(index="bin", columns="context", values="target", aggfunc="count", observed=False).fillna(0).astype(int))
print("not on axis:", df.groupby("context")["ctrl_cpm"].apply(lambda v: int(v.isna().sum())).to_dict())
w = df.pivot(index="target", columns="context", values="ctrl_cpm")
print("targets < 1 CPM in context but > 20 CPM in another:", {c: int(((w[c] < 1) & (w.drop(columns=c).max(1) > 20)).sum()) for c in w.columns})
