"""REPORT E004/E005 tables from $DATA/loco/E004/scores_*.csv (specs_baselines file per holdout/mode)."""
import glob, os, pandas as pd
D = os.environ["DATA"]; M = ["pds", "mse", "fid", "reach", "jac", "nmae"]
files = sorted(f for f in glob.glob(f"{D}/loco/E004/scores_*_specs_baselines.csv"))
df = pd.concat([pd.read_csv(f) for f in files])
order = ["B0_control", "B1_generic", "B2_transfer", "B2_transfer_a0.6", "B3_linear"]
ctxs = [c for c in ["K562", "RPE1", "HepG2", "Jurkat", "H1"] if c in set(df.holdout)]
for mode, title in [("seen", "E004 (seen)"), ("unseen", "E005 (unseen)")]:
    d = df[df["mode"] == mode]
    if d.empty: continue
    t = d.pivot(index="model", columns="holdout", values="context_score").reindex(order)[ctxs]
    t["mean"] = t.mean(axis=1)
    pm = d.groupby("model")[M].mean().reindex(order)
    print(f"\n### {title}: context score\n"); print(t.round(3).to_markdown())
    print(f"\nper-metric scaled means across contexts\n"); print(pm.round(3).to_markdown())
    b = d.pivot(index="holdout", columns="model", values="context_score")
    bad = [c for c in b.index if not b.loc[c, "B0_control"] < b.loc[c, "B1_generic"]]
    print(f"\nCHECK B0 < B1: {'PASS in all contexts' if not bad else 'FAIL in ' + ', '.join(bad)}")
