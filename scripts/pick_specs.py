"""Rank proxy results across held-out lines and write the shortlist for a real-metric V* run.

  python scripts/pick_specs.py --results results/E030 --specs specs_E030.json --out specs_E031.json \
      --ref "B2_raw_gPL(E021)" [--n 4]
proxy = 0.5*pds_sc + 0.3*clip(mse_sc,0,1) + 0.2*(2*de_sign-1), averaged over held-out lines (ORACLE* rows
excluded). Shortlist = reference + top n by proxy + best pds_sc + best mse_sc (deduplicated), balanced emitter.
"""
import argparse, glob, json
import pandas as pd
ap = argparse.ArgumentParser()
ap.add_argument("--results", required=True); ap.add_argument("--specs", required=True)
ap.add_argument("--out", required=True); ap.add_argument("--ref", default="B2_raw_gPL(E021)")
ap.add_argument("--n", type=int, default=4)
a = ap.parse_args()
df = pd.concat([pd.read_csv(f) for f in glob.glob(f"{a.results}/proxy_*_seen.csv")], ignore_index=True)
df["proxy"] = 0.5 * df.pds_sc.clip(-1, 1.5) + 0.3 * df.mse_sc.clip(0, 1) + 0.2 * (2 * df.de_sign - 1)
orc = df[df.spec.str.startswith("ORACLE")]
if len(orc):
    print("ORACLE diagnostics (mean over lines):")
    print(orc.groupby("spec")[["pds_sc", "mse_sc", "mse_raw", "de_sign", "nmae_p"]].mean().round(3).to_string(), "\n")
d = df[~df.spec.str.startswith("ORACLE")]
g = d.groupby("spec")[["proxy", "pds_sc", "mse_sc", "mse_raw", "de_sign", "nmae_p"]].mean()
g["worst"] = d.pivot_table(index="spec", columns="holdout", values="proxy").min(axis=1)
per = d.pivot_table(index="spec", columns="holdout", values="proxy")
g = g.join(per.add_prefix("p_")).sort_values("proxy", ascending=False)
with pd.option_context("display.width", 250, "display.max_columns", 30):
    print(g.round(3).to_string())
specs = {s["name"]: s for s in json.load(open(a.specs))}
pick = [a.ref] + list(g.index[: a.n]) + [g.pds_sc.idxmax(), g.mse_sc.idxmax()]
out, seen = [], set()
for n in pick:
    if n in seen or n not in specs or specs[n]["model"].startswith("ORACLE"):
        continue
    seen.add(n); s = dict(specs[n]); s["emit"] = "balanced"; out.append(s)
json.dump(out, open(a.out, "w"), indent=1)
print(f"{a.out}:", [s["name"] for s in out])
