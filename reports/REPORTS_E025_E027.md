# REPORT blocks E025–E027 — Lambda instance, 15–16 Oct 2026

Runbook: `docs/07_RUNBOOK_INSTANCE.md` (E025–E027, commit 0784d5f); diagnosis `docs/12_DIAGNOSIS.md`.

---

## REPORT E025 — proxy sweep of B4 noise-aware consensus (CPU)

```
for h in CD4T_Stim8hr KOLF2.1J K562_GWPS; do
  python -m vcc26.proxy --config loco.json --holdout $h --holdout-dir $DATA/loco/E020/holdout_$h \
    --specs specs_E025.json --out results/E025 --anatomy "B2_raw_gPL(E021),B4_lr1_pc20_t0.02_s0"
done
python scripts/pick_e025.py results/E025 > results/E025/pick.txt   # writes specs_E026.json
```
47 specs × 3 V\* lines (seen mode, E020 holdouts), about 18–35 min per line on CPU, run alongside E020 unseen on the GPU.
`loco.json` and the summaries are the E020 ones (the D7 re-summaries are not swapped in yet, so E025b will use them).

### Ranked table (`pick.txt`; mean over the 3 lines, `worst` = worst line's proxy)

| spec | proxy | pds_sc | mse_sc_credit | mse_raw | de_sign | nmae_p | worst |
|---|---|---|---|---|---|---|---|
| B2_raw_gPL(E021) | 0.454 | 0.301 | 0.994 | 4.404 | 0.533 | 0.980 | 0.423 |
| B1_gPL | 0.394 | 0.000 | 1.000 | 1.131 | 0.592 | 0.991 | 0.344 |
| B4x_lowrankTrue_pc20_tau20.02_shrinkFalse | 0.380 | 0.181 | 1.000 | 1.749 | 0.480 | 0.999 | 0.350 |
| B4_lr1_pc1_t0.005_s0 | 0.380 | 0.150 | 1.000 | 1.529 | 0.495 | 0.993 | 0.347 |
| B2_raw_gPL_dn | 0.365 | 0.253 | 1.000 | 1.439 | 0.421 | 1.000 | 0.316 |
| B4_lr1_pc5_t0.005_s0 | 0.311 | 0.148 | 1.000 | 1.273 | 0.393 | 0.999 | 0.286 |
| B4_lr1_pc1_t0.02_s0 | 0.223 | 0.097 | 1.000 | 1.112 | 0.286 | 0.998 | 0.211 |
| B4_lr1_pc20_t0.005_s0 | 0.219 | 0.123 | 1.000 | 1.113 | 0.267 | 1.000 | 0.165 |
| B4_lr1_pc1_t0.005_s0.1 | 0.207 | 0.066 | 1.000 | 1.242 | 0.277 | 0.996 | 0.135 |
| B4_lr0_pc20_t0.005_s0 | 0.166 | 0.149 | 1.000 | 1.067 | 0.174 | 0.999 | 0.118 |
| B4_lr0_pc5_t0.005_s0 | 0.145 | 0.140 | 1.000 | 1.088 | 0.147 | 0.999 | 0.094 |
| B4_lr0_pc1_t0.005_s0 | 0.138 | 0.134 | 1.000 | 1.110 | 0.140 | 0.999 | 0.084 |
| B4_lr1_pc5_t0.005_s0.1 | 0.132 | 0.051 | 1.000 | 1.119 | 0.172 | 0.999 | 0.053 |
| B4_lr1_pc5_t0.02_s0 | 0.102 | 0.057 | 1.000 | 1.048 | 0.124 | 1.000 | 0.069 |
| B4_lr1_pc20_t0.005_s0.1 | 0.101 | 0.041 | 1.000 | 1.061 | 0.131 | 1.000 | 0.036 |
| B4_lr0_pc1_t0.02_s0 | 0.096 | 0.072 | 1.000 | 1.054 | 0.108 | 1.000 | 0.053 |
| B4_lr0_pc20_t0.02_s0 | 0.095 | 0.053 | 1.000 | 1.040 | 0.117 | 1.000 | 0.048 |
| B4_lr0_pc5_t0.02_s0 | 0.090 | 0.058 | 1.000 | 1.044 | 0.106 | 1.000 | 0.045 |
| B4x_lowrankTrue_pc20_tau20.02_beta1.3 | 0.088 | 0.036 | 1.000 | 1.041 | 0.115 | 1.000 | 0.045 |
| B4x_lowrankTrue_pc20_tau20.02_genericgw | 0.086 | 0.034 | 1.000 | 1.041 | 0.111 | 1.000 | 0.041 |
| B4x_lowrankTrue_pc20_tau20.02_gate_up_cpmNone | 0.085 | 0.033 | 1.000 | 1.041 | 0.111 | 1.000 | 0.040 |
| B4_lr1_pc20_t0.02_s0 | 0.085 | 0.033 | 1.000 | 1.041 | 0.110 | 1.000 | 0.040 |
| B4x_lowrankTrue_pc20_tau20.02_gate_target_cpm5 | 0.083 | 0.032 | 1.000 | 1.041 | 0.108 | 1.000 | 0.038 |
| B4x_lowrankTrue_pc20_tau20.02_beta0.7 | 0.082 | 0.031 | 1.000 | 1.041 | 0.107 | 1.000 | 0.036 |
| B4_lr0_pc20_t0.005_s0.1 | 0.080 | 0.034 | 1.000 | 1.042 | 0.103 | 1.000 | 0.026 |
| B4_lr1_pc1_t0.02_s0.1 | 0.078 | 0.017 | 1.000 | 1.049 | 0.108 | 1.000 | 0.025 |
| B4_lr0_pc5_t0.005_s0.1 | 0.069 | 0.027 | 1.000 | 1.042 | 0.090 | 1.000 | 0.021 |
| B4_lr0_pc20_t0.02_s0.1 | 0.068 | 0.018 | 1.000 | 1.042 | 0.094 | 1.000 | 0.017 |
| B4_lr0_pc20_t0.1_s0 | 0.067 | 0.017 | 1.000 | 1.042 | 0.092 | 1.000 | 0.017 |
| B4_lr1_pc5_t0.02_s0.1 | 0.066 | 0.014 | 1.000 | 1.042 | 0.092 | 1.000 | 0.013 |
| B4_lr0_pc1_t0.005_s0.1 | 0.066 | 0.024 | 1.000 | 1.042 | 0.087 | 1.000 | 0.020 |
| B4_lr1_pc20_t0.02_s0.1 | 0.065 | 0.011 | 1.000 | 1.042 | 0.092 | 1.000 | 0.014 |
| B4_lr0_pc5_t0.1_s0 | 0.065 | 0.018 | 1.000 | 1.042 | 0.088 | 1.000 | 0.015 |
| B4_lr0_pc5_t0.02_s0.1 | 0.064 | 0.015 | 1.000 | 1.042 | 0.088 | 1.000 | 0.013 |
| B4_lr0_pc1_t0.1_s0 | 0.063 | 0.017 | 1.000 | 1.042 | 0.086 | 1.000 | 0.014 |
| B4_lr1_pc20_t0.1_s0 | 0.062 | 0.009 | 1.000 | 1.042 | 0.089 | 1.000 | 0.013 |
| B4_lr1_pc1_t0.1_s0 | 0.062 | 0.008 | 1.000 | 1.043 | 0.089 | 1.000 | 0.017 |
| B4_lr0_pc20_t0.1_s0.1 | 0.062 | 0.008 | 1.000 | 1.042 | 0.088 | 1.000 | 0.012 |
| B4_lr1_pc5_t0.1_s0 | 0.061 | 0.010 | 1.000 | 1.042 | 0.087 | 1.000 | 0.012 |
| B4_lr0_pc1_t0.02_s0.1 | 0.061 | 0.013 | 1.000 | 1.042 | 0.085 | 1.000 | 0.011 |
| B4_lr0_pc5_t0.1_s0.1 | 0.061 | 0.009 | 1.000 | 1.042 | 0.086 | 1.000 | 0.011 |
| B4_lr1_pc20_t0.1_s0.1 | 0.059 | 0.004 | 1.000 | 1.042 | 0.087 | 1.000 | 0.010 |
| B4_lr0_pc1_t0.1_s0.1 | 0.059 | 0.008 | 1.000 | 1.042 | 0.085 | 1.000 | 0.010 |
| B4_lr1_pc5_t0.1_s0.1 | 0.059 | 0.004 | 1.000 | 1.042 | 0.086 | 1.000 | 0.009 |
| B4_lr1_pc1_t0.1_s0.1 | 0.058 | 0.003 | 1.000 | 1.042 | 0.085 | 1.000 | 0.008 |
| B0_control | 0.017 | 0.000 | 1.000 | 1.042 | 0.025 | 1.000 | 0.010 |

ORACLE is left out of `pick.txt`. Its raw rows are in `proxy_*_seen.csv`: pds_sc 1.15/1.30/1.35 and mse_sc 4.6/4.1/10.1 (CD4T/KOLF/GWPS).

**`specs_E026.json`:** `B2_raw_gPL(E021)`, `B1_gPL`, `B4x_lowrankTrue_pc20_tau20.02_shrinkFalse`, `B4_lr1_pc1_t0.005_s0`.

**`n_lines` / `lowrank_k`:** `vcc26.proxy` doesn't print these (I checked all three logs), so they aren't reported.

### Findings
- **No B4 setting beats the E021 config on the proxy.** E021 scores 0.454 (worst line 0.423). The best B4 is 0.380: `B4x … shrinkFalse` and `B4_lr1_pc1_t0.005`, with low rank, little shrinkage and pc 1.
- **B4 does what it was built for on MSE.** Raw MSE drops from 4.40 (E021) to 1.1–1.7 (B0 = 1.04), which removes the source-noise copy that `docs/12` diagnosed. It loses pds (0.30 → 0.15–0.18) and DE sign (0.53 → 0.48–0.50) at the same time.
- **More shrinkage, larger `tau2` and `sim_tau` 0.1 all push B4 towards B0** (proxy → 0.06, raw MSE → 1.04). The gating, β and generic-source variants of `B4x` change almost nothing; they all sit at 0.08–0.09.
- `mse_sc_credit` is about 1.0 for every spec except E021 (0.994). The proxy only rewards MSE below the baseline, and no non-oracle spec gets there. So MSE isn't moving the proxy ranking: B4's lower MSE is still above the mean-baseline MSE.

### Anatomy (`anatomy_<line>_seen.json`; D = true effect energy per target, tiers = top 10 % / 10–50 % / bottom 50 % of targets by D)

| line | spec | share of D in top-10 % targets | cos(pred, truth) by tier | best scale by tier | N/D by tier | share of squared error by ctrl-CPM bin [0,1) [1,5) [5,20) [20,100) [100,∞) |
|---|---|---|---|---|---|---|
| CD4T_Stim8hr | B2_raw_gPL (E021) | 0.41 | 0.024, 0.016, 0.008 | 0.041, 0.017, 0.007 | 1.6, 3.2, 10.2 | 0.01, 0.04, 0.16, 0.50, 0.29 |
| CD4T_Stim8hr | B4_lr1_pc20_t0.02_s0 | 0.41 | −0.075, −0.051, −0.052 | −151, −294, −192 | 1.00, 1.02, 1.06 | 0.01, 0.05, 0.18, 0.51, 0.25 |
| KOLF2.1J | B2_raw_gPL (E021) | 0.19 | 0.008, 0.003, 0.017 | 0.020, −0.006, 0.017 | 2.1, 2.5, 4.2 | 0.01, 0.06, 0.24, 0.49, 0.21 |
| KOLF2.1J | B4_lr1_pc20_t0.02_s0 | 0.19 | −0.047, −0.008, −0.056 | −233, −29, −311 | 1.02, 1.03, 1.07 | 0.01, 0.07, 0.26, 0.49, 0.16 |
| K562_GWPS | B2_raw_gPL (E021) | 0.38 | 0.081, 0.030, 0.010 | 0.112, 0.033, 0.010 | 2.9, 5.2, 38.6 | 0.00, 0.00, 0.16, 0.63, 0.20 |
| K562_GWPS | B4_lr1_pc20_t0.02_s0 | 0.38 | 0.011, −0.031, −0.037 | −13, −85, −104 | 1.01, 1.05, 1.48 | 0.00, 0.00, 0.18, 0.66, 0.16 |

Reading:
- For E021, per-target cosine with the truth is close to 0 (0.003–0.08). The best scale is 0.01–0.11, so the transferred effects are mostly noise at the per-gene level. The predicted energy is 1.6–39× the true energy (N/D).
- B4 at τ² 0.02 shrinks the predictions to near zero (N/D ≈ 1), and the little that's left anti-correlates slightly with the truth (cos −0.01 to −0.08). That's why its huge "best scale" is negative.
- About 70 % of the squared error sits in genes with control CPM 20 or more.

Files: `results/E025/pick.txt`, `proxy_*_seen.csv`, `anatomy_*_seen.json`; `specs_E026.json`.


---

## REPORT E025b — proxy on the D7 composition-matched summaries

Same command as E025 into `results/E025b`, with a temporary config pointing the summaries for K562, RPE1, HepG2, Jurkat, K562_GWPS and
CD4T_{Rest,Stim8hr,Stim48hr} at `$DATA/pb/d7/`. HipSci keeps its old summary: only 48 cells carry NonTarget guides, below the
≥ 2,000 cells D7 requires. The live `loco.json` and `pb/` were not changed while E026 ran.

D7 strata: `gem_group` for the Replogle/Nadig files (48–267 groups) and `donor_id` (4 donors) for CD4T.

### Donor artefact (`reports/d7_artifact_check.csv`; male-specific chrY genes with control CPM ≥ 5 vs autosomal genes at matched CPM)

| dataset       |   perts_old |   perts_new |   median_kd_old |   median_kd_new |   n_Yexpr |   Yexpr_old |   Yexpr_new |   floor_old |   floor_new |   Yexcess_fold_drop |
|:--------------|------------:|------------:|----------------:|----------------:|----------:|------------:|------------:|------------:|------------:|--------------------:|
| K562          |        1952 |        1954 |           0.171 |           0.171 |         0 |     nan     |     nan     |     nan     |     nan     |             inf     |
| RPE1          |        2087 |        2086 |           0.091 |           0.091 |         0 |     nan     |     nan     |     nan     |     nan     |             inf     |
| HepG2         |        1970 |        1970 |           0.117 |           0.116 |         6 |       0.236 |       0.239 |       0.25  |       0.251 |             inf     |
| Jurkat        |        2117 |        2117 |           0.122 |           0.122 |         7 |       0.25  |       0.253 |       0.189 |       0.189 |               0.975 |
| K562_GWPS     |        9315 |        9321 |           0.153 |           0.153 |         0 |     nan     |     nan     |     nan     |     nan     |             inf     |
| CD4T_Rest     |       10754 |       10753 |           0.125 |           0.125 |         5 |       0.536 |       0.187 |       0.119 |       0.11  |               5.393 |
| CD4T_Stim8hr  |       10929 |       10929 |           0.117 |           0.117 |         5 |       0.509 |       0.219 |       0.105 |       0.097 |               3.322 |
| CD4T_Stim48hr |       10701 |       10700 |           0.138 |           0.138 |         5 |       0.473 |       0.155 |       0.093 |       0.085 |               5.432 |

`Yexcess_fold_drop` = (Y − floor) before ÷ after. CD4T: 5.4× (Rest), 3.3× (Stim8hr), 5.4× (Stim48hr), so the ≥ 5× target is met for 2 of 3.
K562, RPE1 and K562_GWPS have no expressed male-specific chrY genes. HepG2 and Jurkat are single-donor and unchanged, as expected.
There are no HLA genes on the challenge axis, so the HLA half of the check can't be run.

### Proxy before vs after (top 8 by E025b proxy)

| spec                                      |   proxy_E025 |   proxy_E025b |   Δproxy |   pds_sc_E025 |   pds_sc_E025b |   mse_raw_E025 |   mse_raw_E025b |   de_sign_E025 |   de_sign_E025b |   worst_E025 |   worst_E025b |
|:------------------------------------------|-------------:|--------------:|---------:|--------------:|---------------:|---------------:|----------------:|---------------:|----------------:|-------------:|--------------:|
| B2_raw_gPL(E021)                          |        0.454 |         0.457 |    0.003 |         0.301 |          0.315 |          4.404 |           4.223 |          0.533 |           0.532 |        0.423 |         0.416 |
| B1_gPL                                    |        0.394 |         0.407 |    0.013 |         0     |          0     |          1.131 |           1.123 |          0.592 |           0.611 |        0.344 |         0.375 |
| B4x_lowrankTrue_pc20_tau20.02_shrinkFalse |        0.38  |         0.38  |    0     |         0.181 |          0.195 |          1.749 |           1.678 |          0.48  |           0.473 |        0.35  |         0.357 |
| B4_lr1_pc1_t0.005_s0                      |        0.38  |         0.378 |   -0.002 |         0.15  |          0.162 |          1.529 |           1.453 |          0.495 |           0.486 |        0.347 |         0.348 |
| B2_raw_gPL_dn                             |        0.365 |         0.371 |    0.006 |         0.253 |          0.263 |          1.439 |           1.375 |          0.421 |           0.425 |        0.316 |         0.324 |
| B4_lr1_pc5_t0.005_s0                      |        0.311 |         0.299 |   -0.012 |         0.148 |          0.167 |          1.273 |           1.231 |          0.393 |           0.365 |        0.286 |         0.256 |
| B4_lr1_pc20_t0.005_s0                     |        0.219 |         0.211 |   -0.008 |         0.123 |          0.133 |          1.113 |           1.093 |          0.267 |           0.251 |        0.165 |         0.148 |
| B4_lr1_pc1_t0.005_s0.1                    |        0.207 |         0.204 |   -0.003 |         0.066 |          0.064 |          1.242 |           1.24  |          0.277 |           0.274 |        0.135 |         0.131 |

- The E021 config gains +0.003 (pds_sc +0.014, raw MSE 4.40 → 4.22). B1_gPL gains +0.013 (de_sign +0.019, worst line +0.031).
  The top two B4s are unchanged (±0.002). Over all 46 specs the mean is −0.002, with 3 better: B4 with more shrinkage loses a little.
- Acceptance (E025b ≥ E025 for the same spec) holds for the E021 config and B1_gPL, and is a tie for the top B4s. `pick_e025.py` picks the same 4 specs
  (`results/E025b/specs_E026_from_E025b.json`).
- Decision: swap the D7 summaries into `pb/` after E026 (originals kept as `*_pooled.npz`), as `docs/09` D7 says. The gain is small.


---

## REPORT E026 — real-metric V\* for the E025 picks, plus V\*-far

```
python -m vcc26.vstar --config loco.json --panel-file pert_counts.csv --specs specs_E026.json --out $DATA/loco/E020 --tag E026 --mode seen
python -m vcc26.loco ... --holdout KOLF2.1J --sources K562,RPE1,HepG2,Jurkat,K562_GWPS,CD4T_Rest,CD4T_Stim8hr,CD4T_Stim48hr --tag E026far
python -m vcc26.loco ... --holdout CD4T_Stim8hr --sources K562,RPE1,HepG2,K562_GWPS,H1,HipSci_iPSC,KOLF2.1J --tag E026far
```
GPU (the E020 holdouts and anchors are reused); 01:52–04:38 UTC on 16 Oct, about 10 min per (spec, line), with B4's low-rank step dominating.
Summaries: the E020 ones (the D7 swap and Orion were applied only after E026, so the runs stay comparable with E020/E025).

### V\* summary (`vstar_summary_E026_seen.csv`)

| model                                     | emit     |   pds |   mse |   fid |   reach |    jac |   nmae |   selection |   worst_line |   line_CD4T_Stim8hr |   line_K562_GWPS |   line_KOLF2.1J |
|:------------------------------------------|:---------|------:|------:|------:|--------:|-------:|-------:|------------:|-------------:|--------------------:|-----------------:|----------------:|
| B2_raw_gPL(E021)                          | balanced | 0.303 | 0     | 0.774 |   0.09  | -0.303 |  0.138 |       0.167 |        0.154 |               0.175 |            0.154 |           0.173 |
| B4x_lowrankTrue_pc20_tau20.02_shrinkFalse | balanced | 0.185 | 0.026 | 0.585 |  -0.007 | -0.299 |  0.132 |       0.104 |        0.067 |               0.141 |            0.067 |           0.103 |
| B4_lr1_pc1_t0.005_s0                      | balanced | 0.159 | 0.015 | 0.573 |   0     | -0.309 |  0.119 |       0.093 |        0.055 |               0.128 |            0.055 |           0.096 |
| B1_gPL                                    | balanced | 0.009 | 0     | 0.468 |  -0.044 | -0.341 |  0.091 |       0.031 |       -0.04  |               0.095 |           -0.04  |           0.037 |

### Raw MSE per row (baseline B0 ≈ 1.0)

| model                                     |   CD4T_Stim8hr |   K562_GWPS |   KOLF2.1J |
|:------------------------------------------|---------------:|------------:|-----------:|
| B1_gPL                                    |           1.07 |        1.22 |       1.1  |
| B2_raw_gPL(E021)                          |           3.22 |        3.73 |       1.37 |
| B4_lr1_pc1_t0.005_s0                      |           1.02 |        1.05 |       1.02 |
| B4x_lowrankTrue_pc20_tau20.02_shrinkFalse |           1.01 |        1.02 |       1.02 |

### V\*-far (same lineage removed from the sources)

| holdout      | model                                     |   n_covered |   context_score |   V* (all sources) |   Δ far − V* |    pds |   mse |   fid |   reach |    jac |   nmae |   raw_mse |
|:-------------|:------------------------------------------|------------:|----------------:|-------------------:|-------------:|-------:|------:|------:|--------:|-------:|-------:|----------:|
| CD4T_Stim8hr | B2_raw_gPL(E021)                          |         272 |           0.175 |              0.175 |       -0     |  0.225 | 0     | 0.936 |   0.053 | -0.444 |  0.279 |     3.216 |
| CD4T_Stim8hr | B1_gPL                                    |         272 |           0.095 |              0.095 |        0     | -0.039 | 0     | 0.831 |  -0.053 | -0.453 |  0.283 |     1.074 |
| CD4T_Stim8hr | B4x_lowrankTrue_pc20_tau20.02_shrinkFalse |         272 |           0.141 |              0.141 |        0     |  0.16  | 0     | 0.854 |  -0.03  | -0.445 |  0.306 |     1.009 |
| CD4T_Stim8hr | B4_lr1_pc1_t0.005_s0                      |         272 |           0.128 |              0.128 |        0     |  0.104 | 0     | 0.841 |  -0.03  | -0.444 |  0.294 |     1.024 |
| KOLF2.1J     | B2_raw_gPL(E021)                          |         257 |           0.167 |              0.173 |       -0.006 |  0.218 | 0     | 0.604 |   0.034 |  0.128 |  0.017 |     1.216 |
| KOLF2.1J     | B1_gPL                                    |         257 |           0.038 |              0.037 |        0.002 |  0.052 | 0     | 0.088 |  -0.021 |  0.051 |  0.06  |     1.093 |
| KOLF2.1J     | B4x_lowrankTrue_pc20_tau20.02_shrinkFalse |         257 |           0.084 |              0.103 |       -0.019 |  0.149 | 0.002 | 0.166 |   0.02  |  0.104 |  0.061 |     1.037 |
| KOLF2.1J     | B4_lr1_pc1_t0.005_s0                      |         257 |           0.084 |              0.096 |       -0.012 |  0.155 | 0     | 0.202 |   0.022 |  0.073 |  0.053 |     1.039 |

Findings:
- **Top spec = `B2_raw_gPL(E021)`, emit balanced, 0.167 (worst line 0.154)**. That's the same config, and the same score, as E020/E021.
  The two B4s reach 0.104/0.093: they are the first specs with scaled MSE > 0 (0.026/0.015, raw MSE 1.01–1.06 against 1.4–3.7 for E021),
  but they lose pds (0.30 → 0.16–0.19), fid (0.77 → 0.57–0.59) and reach. B1_gPL is 0.031.
- The proxy ranking (E025) matches the real metric for the top spec. It overrates B1_gPL (proxy #2, real #4).
- **V\*-far:** removing Jurkat from the CD4T sources changes nothing (Jurkat measures no panel targets). Removing the pluripotent lines (H1, HipSci)
  from KOLF2.1J costs the E021 config 0.006 (0.173 → 0.167) and the B4s 0.012–0.019. The E021 config doesn't depend on a same-lineage source.

### E027 (leaderboard): not submitted
E026's top spec is exactly the E021 configuration, which is already on the leaderboard (0.106). Resubmitting it on the same
11 summaries would add no information, and it would be a step towards tuning on the leaderboard. A new entry would only differ through the data
(D7 summaries + Orion HCT116/HEK293T, registered after E026), and that hasn't been validated in V\* yet. Left for the planning session.

CSVs: `results/E026/`.
