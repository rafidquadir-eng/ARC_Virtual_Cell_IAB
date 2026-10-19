# REPORT blocks E044–E049 — Lambda instance, 19 Oct 2026

Plan: `docs/16_PLAN_ROUND4.md` (commit fd8473b); runbook ROUND 4 in `docs/07_RUNBOOK_INSTANCE.md`. Standing rules docs/16 §6 apply.
Repo visibility checked before each push: `private`.

---

## REPORT E044 — validator on the instance, reproduction, strength study, test-day mechanics (CPU)

Wall time **02:58–04:03 UTC (1.08 instance-h**, CPU only; the GPU was still running the tail of the old E038 chain, see Anomalies).

### 1. Retro verdict and rank table (LB-span scaling)
`max |span diff|` between `results/lb_spans.json` and the recomputed spans = **0.0**.

```
scaling: raw metrics with official LB spans {'pds': (0.498, 0.954), 'fid': (0.513, 0.812), 'reach': (0.076, 0.99), 'jac': (0.031, 0.356), 'nmae': (0.992, 0.463), 'mse': (0.99, 0.05)}
per-line local deltas (a - b):
                 pds    mse    fid  reach    jac   nmae  context
holdout                                                         
CD4T_Stim8hr   0.029  0.001 -0.069 -0.036 -0.007  0.020   -0.010
K562_GWPS      0.088  0.183 -0.014 -0.073  0.026 -0.038    0.029
KOLF2.1J       0.058  0.000 -0.462 -0.026 -0.026  0.007   -0.075
Orion_HCT116   0.065  0.287  0.071 -0.124  0.029 -0.075    0.042
Orion_HEK293T  0.079  0.089  0.035 -0.119  0.021 -0.099    0.001

mean local delta: {'pds': 0.064, 'mse': 0.112, 'fid': -0.088, 'reach': -0.075, 'jac': 0.009, 'nmae': -0.037, 'context': -0.003}
LB delta:         {'pds': 0.082, 'mse': 0.144, 'fid': -0.226, 'reach': -0.006, 'jac': -0.007, 'nmae': 0.025, 'context': np.float64(0.002)}
per-line metric-sign agreement with LB (of 6): {'CD4T_Stim8hr': 6, 'K562_GWPS': 4, 'KOLF2.1J': 5, 'Orion_HCT116': 3, 'Orion_HEK293T': 3}
context delta local -0.0026 vs LB +0.0018 (|err| 0.0044, need <= 0.015)
local/LB ratio on metrics with |LB delta| >= 0.05 (need 1/3..3): {'pds': np.float64(0.78), 'mse': np.float64(0.78), 'fid': np.float64(0.39)}
RETRODICTION PASS: context sign ok, metric signs 5/6, magnitudes ok
```
**Retro: PASS** (context Δ −0.0026 vs LB +0.0018; metric signs 5/6). **Rank: E021 0.1147, B5 0.1121**, matching planning's 0.115 / 0.112.

```
mean   worst   d_ref lines_pos  n_lines  n_seeds  seed_sd  CD4T_Stim8hr  K562_GWPS  KOLF2.1J  Orion_HCT116  Orion_HEK293T  lb_pds  lb_mse  lb_fid  lb_reach  lb_jac  lb_nmae
variant              emit                                                                                                                                                                                    
ORACLE               balanced  1.0331  0.9796  0.9932       3/3        3        1      NaN        0.9796     1.0492    1.0707           NaN            NaN  1.1008  1.0000  1.4099    1.0065  0.3005   1.3812
                     random    1.0295  1.0011  0.9895       3/3        3        1      NaN        1.0011     1.0336    1.0537           NaN            NaN  1.1008  1.0000  1.5199    1.0096  0.0200   1.5264
B2_raw_gPL(E021)     balanced  0.1147 -0.0560  0.0026       2/5        5        1      NaN        0.0376     0.1944   -0.0560        0.2144         0.1833  0.3463  0.0000 -0.1015    0.3530 -0.0459   0.1367
B5_z2_a0.5_cis5000   balanced  0.1121 -0.1307  0.0000       0/5        5        1      NaN        0.0273     0.2232   -0.1307        0.2565         0.1843  0.4100  0.1120 -0.1893    0.2776 -0.0373   0.0998
B5x_tl0.05           balanced  0.0703 -0.1946 -0.0418       0/5        5        1      NaN        0.0229     0.1674   -0.1946        0.2040         0.1518  0.4090  0.0465 -0.2967    0.2383 -0.0372   0.0618
M1_b1.3              balanced  0.0694 -0.2443 -0.0427       1/5        5        1      NaN        0.0202     0.1881   -0.2443        0.1523         0.2307  0.4356  0.0360 -0.4059    0.2892  0.0145   0.0470
B5x_ml2              balanced  0.0585 -0.2216 -0.0537       0/5        5        1      NaN        0.0254     0.1548   -0.2216        0.1920         0.1417  0.4234  0.0355 -0.3398    0.2058 -0.0311   0.0569
M1_min0.05           balanced  0.0555 -0.2307 -0.0566       2/5        5        1      NaN        0.0322     0.1571   -0.2307        0.1134         0.2056  0.5040  0.0141 -0.4959    0.2607  0.0127   0.0374
M1                   balanced  0.0542 -0.2535 -0.0579       1/5        5        1      NaN        0.0158     0.1563   -0.2535        0.1268         0.2258  0.4420  0.0230 -0.4749    0.2798  0.0114   0.0441
M1_t1500             balanced  0.0500 -0.2485 -0.0621       1/5        5        1      NaN        0.0196     0.1501   -0.2485        0.1134         0.2156  0.4382  0.0184 -0.4840    0.2766  0.0055   0.0455
B2_transfer          random    0.0482  0.0001  0.0083       1/3        3        1      NaN        0.0066     0.1380    0.0001           NaN            NaN  0.1936  0.0000 -0.0287    0.1608 -0.0571   0.0206
B2_raw_gPL           balanced  0.0435 -0.0337  0.0036       2/3        3        1      NaN        0.0290     0.1351   -0.0337           NaN            NaN  0.2623  0.0000 -0.1048    0.1494 -0.0429  -0.0030
B2_transfer          balanced  0.0401 -0.0267  0.0002       1/3        3        1      NaN        0.0174     0.1297   -0.0267           NaN            NaN  0.2145  0.0000 -0.0901    0.1508 -0.0432   0.0086
M1_b0.7              balanced  0.0276 -0.2619 -0.0845       0/5        5        1      NaN        0.0126     0.1151   -0.2619        0.0883         0.1840  0.4423  0.0094 -0.5744    0.2600 -0.0008   0.0292
B2_raw_gPL_dn_b1.6   balanced  0.0169 -0.0620 -0.0230       1/3        3        1      NaN        0.0038     0.1090   -0.0620           NaN            NaN  0.2209  0.0000 -0.1989    0.1190 -0.0214  -0.0181
B2_raw_gPL_dn_b1.3   balanced  0.0041 -0.0865 -0.0359       1/3        3        1      NaN       -0.0001     0.0988   -0.0865           NaN            NaN  0.2217  0.0000 -0.2725    0.1139 -0.0240  -0.0146
B2_raw_gPL_dn        balanced -0.0156 -0.1265 -0.0555       1/3        3        1      NaN       -0.0073     0.0871   -0.1265           NaN            NaN  0.2217  0.0000 -0.3757    0.1079 -0.0306  -0.0167
B3_raw_gPL_dn_linear balanced -0.0159 -0.1266 -0.0558       1/3        3        1      NaN       -0.0082     0.0871   -0.1266           NaN            NaN  0.2181  0.0000 -0.3757    0.1093 -0.0306  -0.0165
A1_gPL_dn            balanced -0.0505 -0.1846 -0.0904       0/3        3        1      NaN       -0.0158     0.0490   -0.1846           NaN            NaN  0.1879  0.0000 -0.5197    0.0916 -0.0397  -0.0229
B1_generic           balanced -0.1197 -0.2914 -0.1597       0/3        3        1      NaN       -0.0418    -0.0260   -0.2914           NaN            NaN  0.0035  0.0000 -0.6955    0.0750 -0.0586  -0.0428
B0_control           balanced -0.1298 -0.3155 -0.2419       0/5        5        1      NaN       -0.0556    -0.0773   -0.3155       -0.0727        -0.1278  0.0035  0.0000 -0.7593    0.1003 -0.0815  -0.0416
B1_gPL               balanced -0.1394 -0.2856 -0.1793       0/3        3        1      NaN       -0.0524    -0.0800   -0.2856           NaN            NaN  0.0035  0.0000 -0.7736    0.0544 -0.0658  -0.0547
wrote results/E044/rank_E020_E031_E034.csv
```

### 2. E032 full-matrix reproduction (today's code, including the R-01 random-base emitter)
`results/E044/E032_full_repro.txt`: shape (360000, 18533) both, obs index equal, **rows differing: 0 of 360,000**. So E032 is reproduced bit-for-bit.

### 3. Strength study (R4-05)
Per-target N_conf tables for 7 holdouts: `results/E044/pertarget_nconf_holdout_*.csv` (+ `regime_*.json`).
```
7 held-out lines, 534 distinct targets; computing source features ...
  K562: 55 targets measured
  RPE1: 69 targets measured
  HepG2: 55 targets measured
  Jurkat: 66 targets measured
  H1: 259 targets measured
  K562_GWPS: 474 targets measured
  HipSci_iPSC: 170 targets measured
  KOLF2.1J: 465 targets measured
  CD4T_Rest: 480 targets measured
  CD4T_Stim8hr: 487 targets measured
  CD4T_Stim48hr: 479 targets measured
  Orion_HCT116: 486 targets measured
  Orion_HEK293T: 460 targets measured
  DepMap model for K562_GWPS (K562): ACH-000551
  DepMap model for Orion_HCT116 (HCT116): ACH-000971
  DepMap model for Orion_HEK293T (HEK293T): not screened
Spearman with log1p(N_conf), per held-out line:
                    src_nstrong_mean  src_nstrong_max  src_kd_mean  src_n_lines  target_ctrl_cpm  depmap_mean  depmap_line
CD4T_Stim48hr_R400             0.113            0.060       -0.021       -0.029            0.035       -0.103          NaN
CD4T_Stim8hr                   0.109            0.117        0.018        0.016            0.113       -0.058          NaN
H1_R400                        0.575            0.517        0.119        0.427            0.071       -0.490          NaN
K562_GWPS                      0.391            0.284       -0.004        0.122            0.119       -0.241       -0.253
KOLF2.1J                       0.077            0.073        0.051        0.038            0.123       -0.078          NaN
Orion_HCT116                   0.381            0.282       -0.012        0.105            0.158       -0.225       -0.094
Orion_HEK293T                  0.370            0.326        0.019        0.168            0.128       -0.140          NaN

LOLO linear model on within-line percentiles (Spearman of prediction):
                      all  src_only  depmap_mean_only  src+depmap
CD4T_Stim48hr_R400  0.130     0.113             0.103       0.139
CD4T_Stim8hr        0.112     0.109             0.058       0.111
H1_R400             0.611     0.574             0.486       0.624
K562_GWPS           0.429     0.391             0.241       0.435
KOLF2.1J            0.104     0.077             0.078       0.094
Orion_HCT116        0.411     0.381             0.225       0.416
Orion_HEK293T       0.370     0.370             0.140       0.358
decision: {'all_mean': 0.30962568582405287, 'src_only_mean': 0.28763967379146554, 'best_set': 'src+depmap', 'best_mean': 0.31113360008454155, 'use_per_target_strength': False, 'depmap_adds': False}
wrote results/E044/strength_study.json
```
**Decision block:** best feature set = `src+depmap`, mean LOLO Spearman **0.311** (all features 0.310; source-only 0.288),
`use_per_target_strength = False`, `depmap_adds = False`. Below the 0.45 build bar, so **L7 is not built** (Phase B stays closed for it).
Where it works: H1-R400 0.62, K562_GWPS 0.43, Orion 0.37–0.42. It fails on CD4T (0.11–0.14) and KOLF (0.10), where N_conf is a power effect of thin truths.

### 4. DepMap coverage and contexts_meta
- `results/E044/depmap_ABC.txt`: A (Jurkat, ACH-000995) **screened**; **B (HeLa, ACH-001086) NOT screened** in CRISPRGeneEffect 24Q4; C (CAL-33, ACH-000518) screened.
- `results/E044/contexts_meta_check.json` vs the hand-written `contexts_meta.json`: same cell line and same TP53 status (deficient) for A, B and C: {'A': True, 'B': True, 'C': True}. Only the `tp53_source` wording differs (DepMap damaging/hotspot counts vs literature citations).
  HeLa has no damaging TP53 call in DepMap; it's deficient through HPV18 E6, which the script notes. `contexts_meta.json` was not overwritten.

### 5. Test-day mechanics (`reports/vcc_help_round4.txt`)
- **Nothing about "final" in the CLI.** `vcc submit` has `-m/--model-name` (required), `-d/--description`, `--wait`, `--resume`, `--skip-limit-check`, `--json`, with no final/phase/partition flag.
  `vcc status --json` returns `is_final: false` for E021/E032 and a `partition` field (`val`). So final-entry status seems to be set server-side, or on the website (**unverified**: Rafid should check the challenge page).
- **Test bundle:** there's no top-level `vcc download`. Data comes through `vcc datasets list` / `vcc datasets download <id> [-d DIR]` (resumable, checksum-verified).
  `vcc datasets list` today shows only `controls` (`vcc_2026_controls.zip`, A/B/C). The D/E/F bundle will presumably appear there on 22 Oct (**unverified**).

### 6. Submissions ledger
`results/submissions.csv` (created): E001, E012, E021, E032, with UTC time, spec, emitter, NC, git hash (last commit before submission), `.vcc` md5 (all 4 `.vcc` files still exist), overall, six metrics and rank.
`forecast` = "none (pre-protocol)" for all four.

### Anomalies
- **The old E038 chain (previous round) was still on the GPU** when Round 4 arrived. I let its in-flight H1 far run finish, and armed a watcher to kill the chain after it.
  SKIPPED (superseded by Round 4): the E038 panel run on CD4T_Stim48hr_R400 (≈ 2 h; R400 panel line not used by docs/16), the E042b seed runs (→ E045), E038b (→ E046) and E043 (null gate retired, docs/16 §2).
  E038 itself (H1-R400, 17 specs) completed; its rows are in `$DATA/loco/E037/scores_H1_R400_seen_E038.csv`, unreported, since Round 4 replaces that comparison.
- E039 (proxy diagnostics, previous round) completed on 6 of 7 lines; the Orion_HEK293T proxy was still running at writing time. Not reported: docs/16 doesn't ask for it.
- HEK293T has no DepMap CRISPR model, so the strength study's `depmap_line` feature is missing for Orion_HEK293T (and CD4T/KOLF/H1: not cancer lines).
- The rank table's `seed_sd` is NaN everywhere: one seed per row until E045.
- `results/E042/pertarget_nconf_*.csv` (E042c) were left uncommitted (R4-10). They're superseded by `results/E044/pertarget_nconf_*.csv`, now committed.
