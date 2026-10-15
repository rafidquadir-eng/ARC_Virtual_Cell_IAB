"""Rank E025 proxy results across held-out lines and write specs_E026.json for the real-metric V* run.

  python scripts/pick_e025.py results/E025   ->  prints the table, writes specs_E026.json
Proxy score per holdout = mean(pds_sc, mse_sc_credit, 2*(de_sign-0.5)); ranked by the mean over holdouts.
specs_E026 = E021 reference + top 4 by proxy score + best by mse alone + best by pds alone (deduplicated),
all with the balanced emitter.
"""
import glob, json, sys
import pandas as pd
d = sys.argv[1]
df = pd.concat([pd.read_csv(f) for f in glob.glob(f"{d}/proxy_*_seen.csv")], ignore_index=True)
df["proxy"] = (df.pds_sc.clip(-1, 1.5) + df.mse_sc_credit + 2 * (df.de_sign - 0.5)) / 3
g = df[df.spec != "ORACLE"].groupby("spec")[["proxy", "pds_sc", "mse_sc_credit", "mse_raw", "de_sign", "nmae_p"]].mean()
g["worst"] = df[df.spec != "ORACLE"].pivot_table(index="spec", columns="holdout", values="proxy").min(axis=1)
g = g.sort_values("proxy", ascending=False)
print(g.round(3).to_string())
specs = {s["name"]: s for s in json.load(open("specs_E025.json"))}
pick = ["B2_raw_gPL(E021)"] + list(g.index[:4]) + [g.mse_sc_credit.idxmax(), g.pds_sc.idxmax()]
out, seen = [], set()
for n in pick:
    if n in seen or n not in specs:
        continue
    seen.add(n); s = dict(specs[n]); s["emit"] = "balanced"; out.append(s)
json.dump(out, open("specs_E026.json", "w"), indent=1)
print("specs_E026.json:", [s["name"] for s in out])
