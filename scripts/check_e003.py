"""E003 CHECK: pds baseline 0.500±0.01, replicate pds > 0.85, replicate_sd <= 0.03, replicate beats baseline."""
import json, os, sys
D = os.environ["DATA"]; ok = True
LOWER = {"expr_mse_unbiased_capped_norm", "de_wilcoxon_lfc_nmae"}   # error metrics: lower is better
for c in sys.argv[1:]:
    a = json.load(open(f"{D}/loco/E003/holdout_{c}/anchors.json")); b, r, sd = a["baseline"], a["replicate"], a["replicate_sd"]
    bad = []
    if abs(b["pds_cosine"] - 0.5) > 0.01: bad.append(f"pds b={b['pds_cosine']:.3f}")
    if r["pds_cosine"] <= 0.85: bad.append(f"pds r={r['pds_cosine']:.3f}")
    bad += [f"{m} sd={v:.3f}" for m, v in sd.items() if v > 0.03]
    bad += [f"{m} r not better than b" for m in r if m in b and ((r[m] >= b[m]) if m in LOWER else (r[m] <= b[m]))]
    print(c, "PASS" if not bad else "FAIL: " + "; ".join(bad)); ok &= not bad
sys.exit(0 if ok else 1)
