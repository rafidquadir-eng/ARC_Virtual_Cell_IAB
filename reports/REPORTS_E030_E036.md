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


---

## REPORT E031 — real-metric V\* on 5 lines + V\*-far (GPU)

```
python -m vcc26.vstar --config loco.json --panel-file pert_counts.csv --specs specs_E031.json --out $DATA/loco/E020 --tag E031 --mode seen
# V*-far: Orion_HCT116 without Orion_HEK293T, Orion_HEK293T without Orion_HCT116, KOLF2.1J without H1/HipSci
```
08:07–12:06 UTC. Sources: 13 contexts, with the D7 summaries and Orion. So E021's V\* score here (0.234) isn't comparable with the 3-line, pre-D7 0.167 from E020/E026.

### V\* summary (`vstar_summary_E031_seen.csv`)

| model              | emit     |   pds |   mse |   fid |   reach |    jac |   nmae |   selection |   worst_line |   line_CD4T_Stim8hr |   line_K562_GWPS |   line_KOLF2.1J |   line_Orion_HCT116 |   line_Orion_HEK293T |
|:-------------------|:---------|------:|------:|------:|--------:|-------:|-------:|------------:|-------------:|--------------------:|-----------------:|----------------:|--------------------:|---------------------:|
| B5_z2_a0.5_cis5000 | balanced | 0.664 | 0.261 | 0.752 |   0.21  | -0.516 |  0.205 |       0.263 |        0.141 |               0.184 |            0.262 |           0.141 |               0.483 |                0.242 |
| B2_raw_gPL(E021)   | balanced | 0.563 | 0.002 | 0.791 |   0.328 | -0.522 |  0.24  |       0.234 |        0.172 |               0.192 |            0.225 |           0.172 |               0.339 |                0.24  |
| B5x_tl0.05         | balanced | 0.665 | 0.186 | 0.701 |   0.15  | -0.518 |  0.165 |       0.225 |        0.104 |               0.181 |            0.211 |           0.104 |               0.418 |                0.211 |
| B5x_ml2            | balanced | 0.69  | 0.172 | 0.682 |   0.099 | -0.511 |  0.161 |       0.215 |        0.091 |               0.185 |            0.197 |           0.091 |               0.407 |                0.198 |
| B0_control         | balanced | 0.014 | 0.067 | 0.467 |  -0.066 | -0.577 |  0.056 |      -0.007 |       -0.095 |               0.095 |           -0.039 |           0.015 |              -0.009 |               -0.095 |

### Raw MSE per row (B0 ≈ 1.0–1.1)

| model              |   CD4T_Stim8hr |   K562_GWPS |   KOLF2.1J |   Orion_HCT116 |   Orion_HEK293T |
|:-------------------|---------------:|------------:|-----------:|---------------:|----------------:|
| B0_control         |           1.02 |        1.07 |       1.04 |           1.12 |            1.05 |
| B2_raw_gPL(E021)   |           1.71 |        1.12 |       1.03 |           3.73 |            4.8  |
| B5_z2_a0.5_cis5000 |           0.99 |        0.82 |       1.01 |           0.72 |            0.91 |
| B5x_ml2            |           1    |        0.92 |       1.03 |           0.9  |            0.98 |
| B5x_tl0.05         |           1    |        0.91 |       1.02 |           0.88 |            0.96 |

### V\*-far

| holdout       | model              |   n_covered |   context_score |   V* (all sources) |   Δ far − V* |   pds |   mse |    fid |   reach |    jac |   nmae |   raw_mse |
|:--------------|:-------------------|------------:|----------------:|-------------------:|-------------:|------:|------:|-------:|--------:|-------:|-------:|----------:|
| KOLF2.1J      | B2_raw_gPL(E021)   |         258 |           0.163 |              0.172 |       -0.008 | 0.195 | 0.006 |  0.555 |   0.04  |  0.121 |  0.062 |     1.032 |
| KOLF2.1J      | B5x_tl0.05         |         258 |           0.094 |              0.104 |       -0.01  | 0.242 | 0.008 |  0.194 |  -0.003 |  0.047 |  0.074 |     1.03  |
| KOLF2.1J      | B5x_ml2            |         258 |           0.085 |              0.091 |       -0.005 | 0.267 | 0.004 |  0.116 |  -0     |  0.043 |  0.081 |     1.034 |
| KOLF2.1J      | B5_z2_a0.5_cis5000 |         258 |           0.123 |              0.141 |       -0.018 | 0.235 | 0.012 |  0.338 |   0.01  |  0.069 |  0.074 |     1.026 |
| KOLF2.1J      | B0_control         |         258 |           0.015 |              0.015 |        0     | 0.052 | 0     | -0.008 |  -0.016 |  0     |  0.062 |     1.045 |
| Orion_HCT116  | B2_raw_gPL(E021)   |         254 |           0.294 |              0.339 |       -0.046 | 0.979 | 0     |  0.822 |   0.489 | -0.833 |  0.306 |     7.73  |
| Orion_HCT116  | B5x_tl0.05         |         254 |           0.343 |              0.418 |       -0.075 | 1.063 | 0.625 |  0.843 |   0.17  | -0.816 |  0.172 |     0.904 |
| Orion_HCT116  | B5x_ml2            |         254 |           0.327 |              0.407 |       -0.08  | 1.073 | 0.596 |  0.849 |   0.1   | -0.809 |  0.151 |     0.924 |
| Orion_HCT116  | B5_z2_a0.5_cis5000 |         254 |           0.405 |              0.483 |       -0.079 | 1.147 | 0.813 |  0.846 |   0.217 | -0.82  |  0.225 |     0.774 |
| Orion_HCT116  | B0_control         |         254 |          -0.009 |             -0.009 |        0     | 0.038 | 0.312 |  0.58  |  -0.129 | -0.859 |  0.005 |     1.121 |
| Orion_HEK293T | B2_raw_gPL(E021)   |         249 |           0.191 |              0.24  |       -0.049 | 0.445 | 0     |  0.886 |   0.53  | -0.938 |  0.224 |     6.707 |
| Orion_HEK293T | B5x_tl0.05         |         249 |           0.147 |              0.211 |       -0.064 | 0.523 | 0.066 |  0.87  |   0.25  | -0.917 |  0.09  |     0.987 |
| Orion_HEK293T | B5x_ml2            |         249 |           0.13  |              0.198 |       -0.068 | 0.584 | 0.058 |  0.845 |   0.114 | -0.905 |  0.084 |     0.994 |
| Orion_HEK293T | B5_z2_a0.5_cis5000 |         249 |           0.143 |              0.242 |       -0.099 | 0.462 | 0     |  0.897 |   0.286 | -0.926 |  0.142 |     1.201 |
| Orion_HEK293T | B0_control         |         249 |          -0.095 |             -0.095 |        0     | 0.005 | 0.005 |  0.415 |  -0.032 | -0.957 | -0.008 |     1.049 |

### Paired bootstrap, `B5_z2_a0.5_cis5000` − `B2_raw_gPL(E021)` (`vcc26.compare`, 1,000 resamples over targets)

| set | Δ mean | 90 % CI | P(Δ > 0) | per line |
|---|---|---|---|---|
| V\* (5 lines) | +0.029 | [+0.011, +0.039] | 0.995 | CD4T_Stim8hr -0.008, KOLF2.1J -0.030, K562_GWPS +0.037, Orion_HCT116 +0.144, Orion_HEK293T +0.002 |
| V\*-far (3 runs) | +0.007 | [-0.019, +0.026] | 0.665 | Orion_HCT116 +0.111, Orion_HEK293T -0.048, KOLF2.1J -0.041 |

Findings:
- **Top spec: `B5_z2_a0.5_cis5000`, selection 0.263 vs 0.234 for the E021 config.** It's the first real-metric spec with a large MSE score (0.261 scaled; raw MSE below the
  baseline on every line: 0.72–1.01 vs 1.03–4.8 for E021), and it has better pds (0.664 vs 0.563). It loses reach (0.21 vs 0.33) and nmae.
  The gain is concentrated on Orion_HCT116 (+0.144) and K562_GWPS (+0.037); CD4T −0.008, KOLF −0.030.
- The proxy winner `B5x_tl0.05` is 3rd on the real metric (0.225), below E021. The proxy overweights pds/MSE relative to reach/fid,
  which the real metric rewards. The densest B5 (z 2, 1,002 genes kept) wins on the real metric.
- V\*-far: the epithelial gain survives on HCT116 without HEK293T (+0.111). It reverses on HEK293T without HCT116 (−0.048) and on KOLF2.1J without the
  pluripotent lines (−0.041). The aggregate far Δ is +0.007 (CI includes 0).

**E032 decision:** V\* Δ = +0.029 ≥ 0.01 ✓. V\*-far aggregate Δ = +0.007, so not worse ✓ (but worse on 2 of 3 far runs). Submitted as E032 (see below).

CSVs: `results/E031/` (summary, rows, far scores, bootstrap JSONs).


---

## REPORT E032 — leaderboard: E031's top spec

Submissions on 16 Oct (UTC) before this entry: 0, so this is **1 of 2** for 16 Oct.

```
python -m vcc26.predict_challenge --controls-dir $DATA/challenge/controls --contexts A,B,C --perts pert_counts.csv --gene-names gene_axis.csv \
  --registry loco.json --summaries <13 loco.json summaries incl. Orion> --spec-file specs_E031.json --spec "B5_z2_a0.5_cis5000" \
  --emit balanced --n-control 0 --out $DATA/preds/E032.h5ad
vcc prep ... -o $DATA/preds/E032.vcc     # passed
vcc submit $DATA/preds/E032.vcc -m "E032 B5_z2_a0.5_cis5000 emit=balanced (E031 V* top), 13 summaries incl. Orion" --wait
```

Entry `n0phFb0FI8GRgERAALGD`, published. **Overall 0.1077, rank 688** (E021: 0.1060, now rank 690). Δ = +0.002.

| metric | raw E032 | raw E021 | scaled E032 | scaled E021 | Δ scaled |
|---|---|---|---|---|---|
| pds | 0.7638 | 0.7266 | 0.5825 | 0.5009 | +0.0817 |
| mse | 0.8512 | 4.6628 | 0.1438 | 0.0000 | +0.1438 |
| nmae | 0.9337 | 0.9468 | 0.1109 | 0.0862 | +0.0247 |
| fid | 0.4248 | 0.4926 | -0.2931 | -0.0667 | -0.2264 |
| reach | 0.1697 | 0.1748 | 0.1022 | 0.1078 | -0.0056 |
| jac | 0.0309 | 0.0333 | 0.0001 | 0.0076 | -0.0075 |

Interpretation:
- **MSE is above zero on the leaderboard for the first time** (0.144; raw 4.66 → 0.85), and pds rises (0.50 → 0.58), as V\* predicted.
- **fid collapses (−0.067 → −0.293)**, which cancels nearly all of it. In V\*, B5's fid was 0.75 vs 0.79 for E021, a small drop. On A/B/C, keeping only the ~1,000
  sign-consistent genes per target and predicting zero elsewhere makes many truly-DE genes "direction wrong/absent". The test contexts likely have broader
  DE sets than the source consensus covers. reach also falls slightly (0.108 → 0.102) and jac goes to 0.
- V\* forecast +0.029; the leaderboard gave +0.002. The gap fits the V\*-far warning (HEK293T and KOLF reverse without a same-lineage source),
  since A/B/C have no same-lineage source except A ~ CD4T.

### E033 addendum: E032 status JSON
`results/E033_E032_status.json`: like E021's, it has no per-context (A/B/C) fields (keys seen: score_avg, pds_cosine, expr_mse_unbiased_capped_norm).


---

## REPORT E034 — learned translator M1 + context-programme projection

**E034a (CPU proxy, 5 lines; run alongside E030, 07:15–08:40 UTC):** `specs_E034.local.json` (10 specs) →
`scripts/pick_specs.py` → `specs_E034b.json`, plus E031's best spec `B5_z2_a0.5_cis5000` added by hand.

| spec                |   proxy |   pds_sc |   mse_sc |   mse_raw |   de_sign |   nmae_p |   worst |   p_CD4T_Stim8hr |   p_K562_GWPS |   p_KOLF2.1J |   p_Orion_HCT116 |   p_Orion_HEK293T |
|:--------------------|--------:|---------:|---------:|----------:|----------:|---------:|--------:|-----------------:|--------------:|-------------:|-----------------:|------------------:|
| M1_b0.7             |   0.435 |    0.727 |   -0.082 |     1.055 |     0.678 |    0.99  |   0.184 |            0.248 |         0.47  |        0.184 |            0.753 |             0.518 |
| M1                  |   0.434 |    0.724 |   -0.121 |     1.091 |     0.679 |    0.988 |   0.184 |            0.247 |         0.47  |        0.184 |            0.751 |             0.516 |
| M1_t1500            |   0.433 |    0.717 |   -0.13  |     1.101 |     0.687 |    0.987 |   0.24  |            0.258 |         0.45  |        0.24  |            0.741 |             0.477 |
| M1_b1.3             |   0.432 |    0.72  |   -0.178 |     1.147 |     0.681 |    0.986 |   0.184 |            0.246 |         0.469 |        0.184 |            0.75  |             0.514 |
| M1_proj200          |   0.41  |    0.674 |   -0.102 |     1.074 |     0.683 |    0.988 |   0.169 |            0.232 |         0.451 |        0.169 |            0.722 |             0.477 |
| M1_proj50           |   0.407 |    0.668 |   -0.101 |     1.072 |     0.682 |    0.988 |   0.168 |            0.232 |         0.447 |        0.168 |            0.715 |             0.474 |
| M1_min0.05          |   0.338 |    0.821 |   -0.112 |     1.083 |     0.318 |    0.993 |   0.08  |            0.267 |         0.347 |        0.08  |            0.486 |             0.509 |
| B2_raw_gPL(E021)    |   0.3   |    0.568 |   -3.548 |     4.425 |     0.541 |    0.97  |   0.101 |            0.145 |         0.363 |        0.101 |            0.568 |             0.323 |
| B5_z3_a0.75_cis5000 |   0.264 |    0.658 |   -0.366 |     1.33  |     0.337 |    0.994 |   0.04  |            0.068 |         0.337 |        0.04  |            0.574 |             0.3   |
| B5_proj200          |   0.23  |    0.616 |   -0.283 |     1.25  |     0.306 |    0.995 |   0.002 |            0.036 |         0.318 |        0.002 |            0.531 |             0.264 |

**M1 anatomy** (`results/E034/anatomy_*_seen.json`):

| line          |   top-10% D share | cos by tier          | best scale by tier   | N/D by tier                     | sq-err share by ctrl-CPM bin   |
|:--------------|------------------:|:---------------------|:---------------------|:--------------------------------|:-------------------------------|
| CD4T_Stim8hr  |             0.412 | 0.053, 0.035, 0.022  | 0.57, 0.28, 0.18     | 1.00, 1.04, 1.19                | 0.01, 0.05, 0.18, 0.50, 0.25   |
| K562_GWPS     |             0.379 | 0.112, 0.074, 0.027  | 0.53, 0.44, 0.13     | 1.00, 1.09, 2.44                | 0.00, 0.00, 0.18, 0.66, 0.16   |
| KOLF2.1J      |             0.185 | 0.023, -0.006, 0.032 | 0.24, -0.11, 0.39    | 1.03, 1.05, 1.09                | 0.01, 0.07, 0.26, 0.49, 0.16   |
| Orion_HCT116  |             0.621 | 0.060, 0.044, 0.021  | 0.77, 0.41, 0.18     | 0.99, 1.06, -109960986554465.03 | 0.02, 0.06, 0.25, 0.53, 0.14   |
| Orion_HEK293T |             0.493 | 0.029, 0.061, 0.027  | 0.26, 0.36, 0.18     | 1.03, 1.07, ∞                   | 0.02, 0.06, 0.21, 0.53, 0.19   |

**`train_rows`:** `translator.py` records it in the model's info dict, but neither `vcc26.proxy` nor `vcc26.vstar` writes that dict to their CSVs or logs.
So it isn't available. It needs a one-line change in proxy/loco to save `info`, which is planning's code.

**E034b (GPU V\*, 12:09–15:46 UTC):** `vstar_summary_E034_seen.csv`

| model              | emit     |   pds |   mse |   fid |   reach |    jac |   nmae |   selection |   worst_line |   line_CD4T_Stim8hr |   line_K562_GWPS |   line_KOLF2.1J |   line_Orion_HCT116 |   line_Orion_HEK293T |
|:-------------------|:---------|------:|------:|------:|--------:|-------:|-------:|------------:|-------------:|--------------------:|-----------------:|----------------:|--------------------:|---------------------:|
| B5_z2_a0.5_cis5000 | balanced | 0.664 | 0.261 | 0.752 |   0.21  | -0.516 |  0.205 |       0.263 |        0.141 |               0.184 |            0.262 |           0.141 |               0.483 |                0.242 |
| M1_b1.3            | balanced | 0.703 | 0.159 | 0.653 |   0.229 | -0.454 |  0.152 |       0.24  |        0.083 |               0.179 |            0.25  |           0.083 |               0.365 |                0.323 |
| B2_raw_gPL(E021)   | balanced | 0.563 | 0.002 | 0.791 |   0.328 | -0.522 |  0.24  |       0.234 |        0.172 |               0.192 |            0.225 |           0.172 |               0.339 |                0.24  |
| M1_min0.05         | balanced | 0.79  | 0.126 | 0.605 |   0.187 | -0.456 |  0.142 |       0.232 |        0.097 |               0.193 |            0.223 |           0.097 |               0.325 |                0.322 |
| M1                 | balanced | 0.713 | 0.143 | 0.619 |   0.215 | -0.458 |  0.149 |       0.23  |        0.077 |               0.175 |            0.228 |           0.077 |               0.349 |                0.322 |
| M1_t1500           | balanced | 0.698 | 0.141 | 0.614 |   0.21  | -0.465 |  0.151 |       0.225 |        0.085 |               0.18  |            0.22  |           0.085 |               0.33  |                0.309 |
| M1_b0.7            | balanced | 0.715 | 0.124 | 0.568 |   0.184 | -0.474 |  0.133 |       0.209 |        0.071 |               0.171 |            0.196 |           0.071 |               0.313 |                0.291 |

Raw MSE per row:

| model              |   CD4T_Stim8hr |   K562_GWPS |   KOLF2.1J |   Orion_HCT116 |   Orion_HEK293T |
|:-------------------|---------------:|------------:|-----------:|---------------:|----------------:|
| B2_raw_gPL(E021)   |           1.71 |        1.12 |       1.03 |           3.73 |            4.8  |
| B5_z2_a0.5_cis5000 |           0.99 |        0.82 |       1.01 |           0.72 |            0.91 |
| M1                 |           0.99 |        0.9  |       1.03 |           1.02 |            0.97 |
| M1_b0.7            |           1    |        0.95 |       1.03 |           1.04 |            0.99 |
| M1_b1.3            |           0.98 |        0.87 |       1.02 |           1    |            0.95 |
| M1_min0.05         |           1    |        0.93 |       1.03 |           1.05 |            0.98 |
| M1_t1500           |           0.99 |        0.91 |       1.02 |           1.02 |            0.98 |

**Paired bootstrap** (`vcc26.compare`, 1,000 resamples):

| comparison | Δ mean | 90 % CI | P(Δ > 0) | per line |
|---|---|---|---|---|
| B5_z2_a0.5_cis5000 − E021 (runbook: best E034b spec vs E021) | +0.0291 | [+0.0113, +0.0388] | 0.995 | CD4T_Stim8hr -0.008, KOLF2.1J -0.030, K562_GWPS +0.037, Orion_HCT116 +0.144, Orion_HEK293T +0.002 |
| M1_b1.3 − E021 | +0.0066 | [-0.0088, +0.0161] | 0.715 | CD4T_Stim8hr -0.013, KOLF2.1J -0.088, K562_GWPS +0.025, Orion_HCT116 +0.026, Orion_HEK293T +0.083 |
| M1_b1.3 − B5_z2_a0.5_cis5000 (current LB config) | -0.0225 | [-0.0362, -0.0049] | 0.017 | CD4T_Stim8hr -0.005, KOLF2.1J -0.058, K562_GWPS -0.012, Orion_HCT116 -0.118, Orion_HEK293T +0.081 |

Findings:
- **The proxy and the real metric disagree on M1.** M1 is the proxy winner by a wide margin (0.435 vs B5 0.264 and E021 0.300; DE sign 0.68). On V\* the best M1 variant (β 1.3) is
  0.240: above E021 (+0.007, CI includes 0) but **significantly below B5** (−0.023, CI [−0.036, −0.005]). M1 has the best pds (0.70–0.79), but less MSE than B5 (0.13–0.16 vs 0.26) and lower fid (0.57–0.65 vs 0.75).
- M1 wins clearly on Orion_HEK293T (0.323 vs 0.242 for B5) and loses on KOLF2.1J (0.083 vs 0.141) and Orion_HCT116 (0.365 vs 0.483). Larger β helps M1 (0.7 → 1.0 → 1.3: 0.209 → 0.230 → 0.240), so it's under-scaled.
- The projection variants (`M1_proj200/50`, `B5_proj200`) were below the bare models on the proxy and were not picked for V\*.
- **Top spec for E035/E036: `B5_z2_a0.5_cis5000`** (V\* 0.263). **Leaderboard rule** (CI lower bound vs the current LB config > 0): the LB config is now B5 itself (E032), and no E034 spec beats it, so there's no submission.
- The proxy overrates M1 for the same reason it overrated B5x_tl0.05 in E030: it weights pds/DE sign and under-weights fid/reach/MSE as the real scorer does. Worth recalibrating before using it to pick.

Files: `results/E034/` (proxy CSVs, anatomy, pick.txt, V\* summary/rows, bootstrap JSONs); `specs_E034b.json`.
