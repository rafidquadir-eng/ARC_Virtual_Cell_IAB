# REPORT blocks E030–E036 — Lambda instance, 16 Oct 2026

Runbook: `docs/07_RUNBOOK_INSTANCE.md` (E030–E036, commit 278bbb5); diagnosis `docs/14_DIAGNOSIS_ROUND2.md`.
`loco.json`: 13 contexts (including Orion HCT116/HEK293T, licence-tagged), with the D7 composition-matched summaries in `pb/`.

---

## REPORT E033 — per-context breakdown of our leaderboard entries (no submission)

```
vcc --json status QJexGFhKagEpbvXkiUku > results/E033_E021_status.json   # works
vcc --json status aZXPOs2QkOuKb5oZQzYu                                     # E012: "No such submission for your account" (not_found)
vcc --json status nurtW5XlQHa9XLcPGbdY                                     # E001: same not_found
```
Only the latest entry (E021) can still be looked up. The server seems to keep one entry per team, the most recent, and `vcc` has no list command.
**The status JSON has no per-context (A/B/C) fields**, only the aggregate. So the per-context breakdown isn't available from `vcc status`.

E021 aggregate, raw and scaled (`results/E033_E021_status.json`):

| metric | raw | scaled |
|---|---|---|
| pds (`pds_cosine`) | 0.7266 | 0.5009 |
| mse (`expr_mse_unbiased_capped_norm`) | 4.6628 | 0 |
| nmae (`de_wilcoxon_lfc_nmae`) | 0.9468 | 0.0862 |
| fid (`de_wilcoxon_direction_fidelity_yield_raw`) | 0.4926 | −0.0667 |
| reach (`de_wilcoxon_direction_reach_raw`) | 0.1748 | 0.1078 |
| jac (`de_wilcoxon_sig_jaccard`) | 0.0333 | 0.0076 |
| overall | | 0.1060 (rank now **690**, down from 684 as others submit) |

The raw MSE of 4.66 is the figure `docs/12` started from (about 5× the true effect size). `de_score`, `pert_score` and `mae_score` are null.


---

## REPORT E030 — B5 sparse consistent consensus + cis effects, proxy on 5 V\* lines (CPU)

```
for h in CD4T_Stim8hr KOLF2.1J K562_GWPS Orion_HCT116 Orion_HEK293T; do
  python -m vcc26.proxy --config loco.json --holdout $h --holdout-dir $DATA/loco/E020/holdout_$h --panel-file $PANEL \
    --tss $DATA/tss.csv --specs specs_E030.local.json --out results/E030 --anatomy "B2_raw_gPL(E021),B5_z3_a0.75_cis5000"
done
python scripts/pick_specs.py --results results/E030 --specs specs_E030.local.json --out specs_E031.json
```
32 specs × 5 lines, 07:14–08:05 UTC. The Orion holdouts were built on the first pass into `$DATA/loco/E020/holdout_Orion_*`. Summaries: D7 (composition-matched) plus Orion.

### ORACLE diagnostics (mean over the 5 lines)

| spec             |   pds_sc |   mse_sc |   mse_raw |   de_sign |   nmae_p |
|:-----------------|---------:|---------:|----------:|----------:|---------:|
| ORACLE           |    1.749 |    7.603 |    -6.417 |     1     |    0     |
| ORACLE_CIS1000   |    0.249 |   -0.077 |     1.05  |     0.058 |    0.999 |
| ORACLE_CIS100000 |    1.153 |   -0.073 |     1.046 |     0.298 |    0.997 |
| ORACLE_CIS20000  |    0.561 |   -0.075 |     1.048 |     0.131 |    0.998 |
| ORACLE_CIS5000   |    0.314 |   -0.076 |     1.049 |     0.072 |    0.998 |
| ORACLE_TOPK10    |    1.747 |    0.148 |     0.83  |     0.396 |    0.902 |
| ORACLE_TOPK1000  |    1.749 |    3.53  |    -2.453 |     0.908 |    0.123 |
| ORACLE_TOPK200   |    1.749 |    1.312 |    -0.299 |     0.635 |    0.505 |
| ORACLE_TOPK50    |    1.749 |    0.511 |     0.478 |     0.48  |    0.739 |

- **The truth is sparse.** Keeping only each target's top 10 genes gives the full pds (1.75). The top 50 give MSE above the baseline (mse_sc 0.51); the top 200 give 1.31,
  and the top 1,000 get 91 % of DE sign. So nearly all of the score lives in a few dozen to a few hundred genes per target.
- **Cis carries little energy.** ORACLE_CIS (truth kept only on genes within d of the target TSS, the target itself excluded) never beats the baseline on MSE.
  Its high pds at 100 kb (1.15) comes from the neighbour gene sets being unique per target, not from signal (DE sign 0.30).

### Ranked table (`pick.txt` + `genes_kept_median`, `cis_genes_median`, `top50_overlap` averaged over lines)

| spec                |   proxy |   pds_sc |   mse_sc |   mse_raw |   de_sign |   nmae_p |   worst |   p_CD4T_Stim8hr |   p_K562_GWPS |   p_KOLF2.1J |   p_Orion_HCT116 |   p_Orion_HEK293T |   genes_kept_median |   cis_genes_median |   top50_overlap |
|:--------------------|--------:|---------:|---------:|----------:|----------:|---------:|--------:|-----------------:|--------------:|-------------:|-----------------:|------------------:|--------------------:|-------------------:|----------------:|
| B5x_tl0.05          |   0.336 |    0.674 |   -0.362 |     1.326 |     0.497 |    0.993 |   0.106 |            0.161 |         0.387 |        0.106 |            0.646 |             0.377 |               238.1 |                  0 |           0.028 |
| B2_raw_gPL(E021)    |   0.3   |    0.568 |   -3.548 |     4.425 |     0.541 |    0.97  |   0.101 |            0.145 |         0.363 |        0.101 |            0.568 |             0.323 |               nan   |                nan |           0.033 |
| B5x_ml2             |   0.284 |    0.699 |   -0.276 |     1.243 |     0.336 |    0.994 |   0.019 |            0.099 |         0.362 |        0.019 |            0.607 |             0.331 |               163   |                  0 |           0.026 |
| B5_z2_a0.5_cis5000  |   0.278 |    0.673 |   -0.896 |     1.846 |     0.355 |    0.989 |   0.048 |            0.072 |         0.391 |        0.048 |            0.567 |             0.314 |              1002   |                  0 |           0.035 |
| B5_z2_a0.5_cis0     |   0.278 |    0.671 |   -0.896 |     1.846 |     0.355 |    0.989 |   0.048 |            0.069 |         0.391 |        0.048 |            0.566 |             0.314 |              1002   |                  0 |           0.034 |
| B5_z4_a0.5_cis5000  |   0.277 |    0.646 |   -0.295 |     1.261 |     0.386 |    0.996 |   0.067 |            0.129 |         0.292 |        0.067 |            0.578 |             0.319 |               133.4 |                  0 |           0.031 |
| B5_z2_a0.75_cis5000 |   0.276 |    0.674 |   -0.716 |     1.671 |     0.346 |    0.99  |   0.033 |            0.074 |         0.378 |        0.033 |            0.579 |             0.315 |               793.9 |                  0 |           0.032 |
| B5_z2_a0.75_cis0    |   0.274 |    0.672 |   -0.716 |     1.671 |     0.346 |    0.99  |   0.033 |            0.071 |         0.376 |        0.033 |            0.578 |             0.314 |               793.9 |                  0 |           0.032 |
| B5x_b1.5            |   0.273 |    0.643 |   -0.768 |     1.721 |     0.379 |    0.996 |   0.071 |            0.071 |         0.344 |        0.076 |            0.572 |             0.302 |               238.1 |                  0 |           0.027 |
| B5x_pc20            |   0.272 |    0.641 |   -0.39  |     1.354 |     0.379 |    0.998 |   0.071 |            0.111 |         0.323 |        0.071 |            0.571 |             0.286 |               336.3 |                  0 |           0.026 |
| B5_z4_a0.75_cis5000 |   0.272 |    0.649 |   -0.237 |     1.205 |     0.37  |    0.996 |   0.058 |            0.125 |         0.274 |        0.058 |            0.577 |             0.326 |               105.4 |                  0 |           0.03  |
| B5_z4_a0.5_cis0     |   0.269 |    0.629 |   -0.295 |     1.261 |     0.385 |    0.996 |   0.064 |            0.114 |         0.281 |        0.064 |            0.57  |             0.314 |               133.4 |                  0 |           0.031 |
| B5x_sim0.1          |   0.268 |    0.633 |   -0.189 |     1.159 |     0.379 |    0.995 |   0.074 |            0.096 |         0.275 |        0.074 |            0.595 |             0.302 |                57.3 |                  0 |           0.028 |
| B5_z3_a0.5_cis5000  |   0.264 |    0.65  |   -0.462 |     1.424 |     0.348 |    0.994 |   0.057 |            0.068 |         0.352 |        0.057 |            0.559 |             0.286 |               303.5 |                  0 |           0.029 |
| B5x_cis20k          |   0.264 |    0.659 |   -0.366 |     1.33  |     0.336 |    0.994 |   0.04  |            0.069 |         0.338 |        0.04  |            0.574 |             0.3   |               238.1 |                  0 |           0.027 |
| B5x_gt5             |   0.264 |    0.66  |   -0.359 |     1.323 |     0.336 |    0.994 |   0.039 |            0.069 |         0.337 |        0.039 |            0.573 |             0.303 |               238.1 |                  0 |           0.027 |
| B5_z3_a0.75_cis5000 |   0.264 |    0.658 |   -0.366 |     1.33  |     0.337 |    0.994 |   0.04  |            0.068 |         0.337 |        0.04  |            0.574 |             0.3   |               238.1 |                  0 |           0.027 |
| B5_z4_a0.75_cis0    |   0.263 |    0.631 |   -0.238 |     1.205 |     0.37  |    0.996 |   0.056 |            0.112 |         0.263 |        0.056 |            0.567 |             0.32  |               105.4 |                  0 |           0.029 |
| B5_z3_a0.5_cis0     |   0.262 |    0.645 |   -0.462 |     1.424 |     0.348 |    0.994 |   0.056 |            0.061 |         0.35  |        0.056 |            0.559 |             0.283 |               303.5 |                  0 |           0.029 |
| B5_z3_a0.75_cis0    |   0.261 |    0.652 |   -0.366 |     1.33  |     0.337 |    0.994 |   0.039 |            0.06  |         0.334 |        0.039 |            0.573 |             0.297 |               238.1 |                  0 |           0.027 |
| B5x_b0.7            |   0.261 |    0.67  |   -0.205 |     1.174 |     0.314 |    0.995 |   0.03  |            0.067 |         0.333 |        0.03  |            0.574 |             0.299 |               238.1 |                  0 |           0.027 |
| B5x_z5              |   0.228 |    0.548 |   -0.182 |     1.151 |     0.384 |    0.997 |   0.062 |            0.074 |         0.237 |        0.062 |            0.492 |             0.274 |                62.1 |                  0 |           0.027 |
| B0_control          |  -0.189 |    0     |   -0.08  |     1.052 |     0.029 |    1     |  -0.194 |           -0.189 |        -0.194 |       -0.187 |           -0.188 |            -0.185 |               nan   |                nan |           0.003 |

**`specs_E031.json`:** ['B2_raw_gPL(E021)', 'B5x_tl0.05', 'B5x_ml2', 'B5_z2_a0.5_cis5000', 'B0_control']

- **B5x_tl0.05 is the proxy winner: 0.336 vs 0.300 for the E021 config.** It's better on 4 of 5 lines; HCT116 0.646 vs 0.568. Raw MSE 1.33 vs 4.43, pds_sc 0.674 vs 0.568,
  DE sign 0.497 vs 0.541 (slightly lower). It keeps about 238 genes per target at full size, and the rest at 0.05 × consensus (the `tl` = trans-lambda leak).
- Pure-sparse B5 (no leak) gets better pds and MSE than E021 but loses DE sign (0.34–0.39 vs 0.54), which caps it at 0.26–0.28. The small leak is what recovers DE sign.
- `cis5000` vs `cis0` is almost the same everywhere (±0.003). **`cis_genes_median` = 0 is real, not a bug.** Only 74 of the 300 panel targets have any other axis gene
  within 5 kb (140 within 20 kb, 263 within 100 kb), so the median target gets no cis term.
- `top50_overlap` (the share of the true top-50 genes in the predicted top-50) is 0.026–0.035 for every spec, about chance level. The kept genes are rarely the right ones.

### Anatomy

| line          | spec                |   within_1000bp |   within_5000bp |   within_20000bp |   within_100000bp | cos by tier          | N/D by tier       |   top-10% D share |
|:--------------|:--------------------|----------------:|----------------:|-----------------:|------------------:|:---------------------|:------------------|------------------:|
| CD4T_Stim8hr  | B2_raw_gPL(E021)    |          0.0004 |          0.0005 |           0.0006 |            0.0008 | 0.034, 0.018, 0.010  | 1.26, 2.07, 5.10  |             0.412 |
| CD4T_Stim8hr  | B5_z3_a0.75_cis5000 |          0.0004 |          0.0005 |           0.0006 |            0.0008 | 0.028, 0.016, 0.009  | 1.01, 1.07, 1.19  |             0.412 |
| K562_GWPS     | B2_raw_gPL(E021)    |          0.0005 |          0.0008 |           0.001  |            0.0013 | 0.097, 0.046, 0.016  | 2.17, 3.11, 20.52 |             0.379 |
| K562_GWPS     | B5_z3_a0.75_cis5000 |          0.0005 |          0.0008 |           0.001  |            0.0013 | 0.084, 0.044, 0.016  | 1.13, 1.21, 3.45  |             0.379 |
| KOLF2.1J      | B2_raw_gPL(E021)    |          0.0001 |          0.0001 |           0.0002 |            0.0004 | 0.012, -0.002, 0.021 | 1.76, 1.96, 3.25  |             0.185 |
| KOLF2.1J      | B5_z3_a0.75_cis5000 |          0.0001 |          0.0001 |           0.0002 |            0.0004 | 0.006, 0.008, 0.014  | 1.09, 1.12, 1.29  |             0.185 |
| Orion_HCT116  | B2_raw_gPL(E021)    |          0.0003 |          0.0004 |           0.0005 |            0.0007 | 0.078, 0.035, 0.016  | 1.95, 5.65, ∞     |             0.621 |
| Orion_HCT116  | B5_z3_a0.75_cis5000 |          0.0003 |          0.0004 |           0.0005 |            0.0007 | 0.057, 0.036, 0.015  | 1.07, 1.37, ∞     |             0.621 |
| Orion_HEK293T | B2_raw_gPL(E021)    |          0.0002 |          0.0002 |           0.0004 |            0.0006 | 0.017, 0.042, 0.014  | 2.30, 5.34, ∞     |             0.493 |
| Orion_HEK293T | B5_z3_a0.75_cis5000 |          0.0002 |          0.0002 |           0.0004 |            0.0006 | 0.014, 0.034, 0.013  | 1.11, 1.41, ∞     |             0.493 |

- The share of true signal within 1–100 kb of the target is ≤ 0.1 % on every line. CRISPRi neighbour silencing is a negligible part of the score here.
- B5 cuts predicted energy to about the true energy on the top tiers (N/D 1.0–1.4, vs 1.3–5.7 for E021) with similar cosine. That's the MSE gain. The bottom-50 % N/D is ∞ on Orion
  because those targets have about zero true energy there.

Files: `results/E030/*`; `specs_E031.json`.
