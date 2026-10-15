"""REPORT E011 tables + selection score = 0.9 * mean(b-testlike over 4 lines) + 0.1 * (a-unseen context score)."""
import os, pandas as pd
D = os.environ["DATA"] + "/loco/E011"; M = ["pds", "mse", "fid", "reach", "jac", "nmae"]
LINES = ["RPE1", "HepG2", "Jurkat", "H1"]
order = list(pd.read_csv(f"{D}/scores_K562_GWPS_seen_specs_E011.csv")["model"])
md = lambda df: df.round(3).to_markdown()
a = {}
for mode in ["seen", "unseen"]:
    d = pd.read_csv(f"{D}/scores_K562_GWPS_{mode}_specs_E011.csv").set_index("model").reindex(order)
    a[mode] = d["context_score"]
    print(f"\n### (a) K562_GWPS panel holdout, {mode}\n"); print(md(d[["context_score"] + M]))
b = {}
for tag in ["testlike", "all"]:
    t = pd.concat([pd.read_csv(f"{D}/scores_{c}_seen_{tag}.csv").set_index("model")["context_score"].rename(c) for c in LINES], axis=1).reindex(order)
    t["mean"] = t[LINES].mean(axis=1); b[tag] = t
    print(f"\n### (b) held-out lines, sources = {tag}, seen: context score\n"); print(md(t))
sel = (0.9 * b["testlike"]["mean"] + 0.1 * a["unseen"]).rename("selection").to_frame()
sel["b_testlike_mean"] = b["testlike"]["mean"]; sel["a_unseen"] = a["unseen"]
sel = sel.sort_values("selection", ascending=False)
print("\n### Selection score = 0.9 x (b-testlike mean) + 0.1 x (a-unseen)\n"); print(md(sel))
print(f"\nTop spec: {sel.index[0]}")
