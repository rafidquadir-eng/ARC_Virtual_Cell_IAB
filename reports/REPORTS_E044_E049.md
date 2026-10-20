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


---

## REPORT E045 — seed variance, emitter choice, the H1-R400 bracket (GPU)

`scripts/run_E045.sh`: V\* 5 lines (`vstar_par.sh`, 2 holdouts at a time) for `specs_E045ref.json` seeds 0/1/2 and `specs_E045b3.json` seeds 0/1, plus H1-R400 for both spec files.
**Wall 04:05–06:53 UTC = 2.80 instance-h** (GPU; estimate 2.5–3 h, within 1.5×). No FAILED lines, no OOM.

### 1. Rank tables (LB-span scaling, ref = `B5_z2_a0.5_cis5000@@balanced`)
V\* (5 lines):
```
mean   worst   d_ref lines_pos  n_lines  n_seeds  seed_sd  CD4T_Stim8hr  K562_GWPS  KOLF2.1J  Orion_HCT116  Orion_HEK293T  lb_pds  lb_mse  lb_fid  lb_reach  lb_jac  lb_nmae
variant               emit                                                                                                                                                                                     
B2_raw_gPL(E021)@b3   balanced3  0.1156 -0.0568  0.0047       3/5        5        2   0.0023        0.0339     0.1973   -0.0568        0.2191         0.1846  0.3467  0.0005 -0.1069    0.3568 -0.0438   0.1403
B2_raw_gPL(E021)      balanced   0.1150 -0.0515  0.0041       3/5        5        3   0.0004        0.0362     0.1896   -0.0515        0.2167         0.1841  0.3462  0.0000 -0.1006    0.3527 -0.0457   0.1376
B5_z2_a0.5_cis5000@b3 balanced3  0.1121 -0.1379  0.0011       3/5        5        2   0.0042        0.0300     0.2194   -0.1379        0.2655         0.1834  0.4095  0.1119 -0.2050    0.2811 -0.0317   0.1066
B5_z2_a0.5_cis5000    balanced   0.1109 -0.1312  0.0000       0/5        5        3   0.0015        0.0283     0.2142   -0.1312        0.2599         0.1837  0.4103  0.1121 -0.1951    0.2743 -0.0370   0.1010
wrote results/E045/rank_vstar.csv
```
H1-R400:
```
mean   worst   d_ref lines_pos  n_lines  n_seeds  seed_sd  H1_R400  lb_pds  lb_mse  lb_fid  lb_reach  lb_jac  lb_nmae
variant               emit                                                                                                                              
B2_raw_gPL(E021)      balanced   0.1384  0.1384  0.0760       1/1        1        1      NaN   0.1384  0.7524  0.0000 -0.2422    0.1416  0.0749   0.1039
B2_raw_gPL(E021)@b3   balanced3  0.1289  0.1289  0.0664       1/1        1        1      NaN   0.1289  0.7526  0.0000 -0.2937    0.1537  0.0617   0.0989
B5_z2_a0.5_cis5000@b3 balanced3  0.0634  0.0634  0.0010       1/1        1        1      NaN   0.0634  0.6938  0.1418 -0.6070    0.1133 -0.0013   0.0401
B5_z2_a0.5_cis5000    balanced   0.0624  0.0624  0.0000       0/1        1        1      NaN   0.0624  0.7010  0.1221 -0.5605    0.0663  0.0046   0.0412
```

### 2. Retro by seed, and on H1
```
== seed 0
context delta local -0.0026 vs LB +0.0018 (|err| 0.0044, need <= 0.015)
local/LB ratio on metrics with |LB delta| >= 0.05 (need 1/3..3): {'pds': np.float64(0.78), 'mse': np.float64(0.78), 'fid': np.float64(0.39)}
RETRODICTION PASS: context sign ok, metric signs 5/6, magnitudes ok
== seed 1
context delta local -0.0056 vs LB +0.0018 (|err| 0.0074, need <= 0.015)
local/LB ratio on metrics with |LB delta| >= 0.05 (need 1/3..3): {'pds': np.float64(0.79), 'mse': np.float64(0.78), 'fid': np.float64(0.47)}
RETRODICTION PASS: context sign ok, metric signs 5/6, magnitudes ok
== seed 2
context delta local -0.0040 vs LB +0.0018 (|err| 0.0058, need <= 0.015)
local/LB ratio on metrics with |LB delta| >= 0.05 (need 1/3..3): {'pds': np.float64(0.79), 'mse': np.float64(0.78), 'fid': np.float64(0.39)}
RETRODICTION PASS: context sign ok, metric signs 5/6, magnitudes ok
```
H1-R400:
```
scaling: raw metrics with official LB spans {'pds': (0.498, 0.954), 'fid': (0.513, 0.812), 'reach': (0.076, 0.99), 'jac': (0.031, 0.356), 'nmae': (0.992, 0.463), 'mse': (0.99, 0.05)}
per-line local deltas (a - b):
           pds    mse    fid  reach   jac   nmae  context
holdout                                                  
H1_R400 -0.051  0.122 -0.318 -0.075 -0.07 -0.063   -0.076

mean local delta: {'pds': -0.051, 'mse': 0.122, 'fid': -0.318, 'reach': -0.075, 'jac': -0.07, 'nmae': -0.063, 'context': -0.076}
LB delta:         {'pds': 0.082, 'mse': 0.144, 'fid': -0.226, 'reach': -0.006, 'jac': -0.007, 'nmae': 0.025, 'context': np.float64(0.002)}
per-line metric-sign agreement with LB (of 6): {'H1_R400': 4}
context delta local -0.0760 vs LB +0.0018 (|err| 0.0778, need <= 0.015)
local/LB ratio on metrics with |LB delta| >= 0.05 (need 1/3..3): {'pds': np.float64(-0.63), 'mse': np.float64(0.85), 'fid': np.float64(1.41)}
RETRODICTION FAIL: context sign ok, metric signs 4/6, magnitudes OFF
```

### 3. E031 reproduction (seed 0 vs the E031 rows, raw metrics)
```
model        holdout  d_pds  d_mse  d_fid  d_reach  d_jac  d_nmae
0    B2_raw_gPL(E021)   CD4T_Stim8hr    0.0    0.0    0.0      0.0    0.0     0.0
1  B5_z2_a0.5_cis5000   CD4T_Stim8hr    0.0    0.0    0.0      0.0    0.0     0.0
2    B2_raw_gPL(E021)       KOLF2.1J    0.0    0.0    0.0      0.0    0.0     0.0
3  B5_z2_a0.5_cis5000       KOLF2.1J    0.0    0.0    0.0      0.0    0.0     0.0
4    B2_raw_gPL(E021)      K562_GWPS    0.0    0.0    0.0      0.0    0.0     0.0
5  B5_z2_a0.5_cis5000      K562_GWPS    0.0    0.0    0.0      0.0    0.0     0.0
6    B2_raw_gPL(E021)   Orion_HCT116    0.0    0.0    0.0      0.0    0.0     0.0
7  B5_z2_a0.5_cis5000   Orion_HCT116    0.0    0.0    0.0      0.0    0.0     0.0
8    B2_raw_gPL(E021)  Orion_HEK293T    0.0    0.0    0.0      0.0    0.0     0.0
9  B5_z2_a0.5_cis5000  Orion_HEK293T    0.0    0.0    0.0      0.0    0.0     0.0
```
Exact: all differences are 0.0 for both specs on all 5 lines.

### 4. Bootstraps: balanced3 vs balanced (`compare --anchors-override results/lb_spans.json`, two-level, 1,000)

| comparison | Δ mean | 90 % CI | P(Δ > 0) | per line |
|---|---|---|---|---|
| B5_z2_a0.5_cis5000@b3 − B5_z2_a0.5_cis5000 | -0.0030 | [-0.0111, +0.0058] | 0.270 | KOLF2.1J -0.0155, CD4T_Stim8hr -0.0034, Orion_HCT116 +0.0124, Orion_HEK293T +0.0028, K562_GWPS -0.0114 |
| B2_raw_gPL(E021)@b3 − B2_raw_gPL(E021) | -0.0008 | [-0.0056, +0.0060] | 0.483 | KOLF2.1J -0.0047, CD4T_Stim8hr -0.0092, Orion_HCT116 +0.0053, Orion_HEK293T +0.0013, K562_GWPS +0.0034 |

### 5. Decisions
- **seed SD\* = 0.0015** (the larger of B5 0.0015 and E021 0.0004, over 3 seeds). The §3 rule-1 threshold is therefore max(0.005, 2 × 0.0015) = **0.005**.
- **Emitter: keep `balanced`.** Δ(B5@b3 − B5) on V\* is +0.0012 in the rank table (2 b3 seeds vs 3 balanced seeds) and −0.0030 in the seed-0 bootstrap (P = 0.27). Both are below 2·SD\* = 0.003.
  H1-R400 Δ +0.0010 is OK, and the E021 pair moves the same way (+0.0006), but the V\* rule fails. E046 runs without the b3 spec copies, with `REF="B5_z2_a0.5_cis5000@@balanced"`.
- **Validator stability:** V\* retro **PASSes on all 3 seeds** (|err| 0.0044 / 0.0074 / 0.0058). **H1-R400 retro FAILs.** Context Δ is −0.076 vs LB +0.002, metric signs 4/6, and the pds ratio is −0.63:
  H1 says B5 is far worse than E021 (H1 E021 0.138 vs B5 0.062). B5's DE calls cost a lot more fid on H1 (lb_fid −0.56 vs −0.24) because H1's N_conf is 855, above A/B/C's 336.

### 6. GPU hours
2.80 h (V\* 2 processes plus the H1 job in parallel throughout).

### **STOP (standing rule: "any retro or verify FAIL").** E046 not started.
The runbook expects the H1 retro may FAIL ("report it either way … it is one line"), but Rafid's instruction for this round lists *any* retro FAIL as a stop. **Waiting for Rafid's go-ahead to run E046.**

### Anomalies
- **The E021 config beats the reference on both brackets:** V\* +0.0041 (3/5 lines positive; just below the 0.005 rule-1 threshold) and H1-R400 +0.076. Since E046's reference is still B5, an E021-heavy blend (`ENS_E021B5_w37`/`w55`) has a head start.
- The rank table and the bootstrap disagree in sign for B5@b3 (+0.0012 vs −0.0030), because the rank averages over seeds (2 vs 3) and the bootstrap uses seed 0 only. Both are within noise.
- H1-R400 has 1 seed per spec (as designed), so `seed_sd` is NaN in the H1 table.
- The B5 per-line seed effect is largest on Orion_HCT116 and KOLF2.1J (b3 bootstrap per-line ±0.012–0.015). So a single-seed per-line Δ below about 0.015 shouldn't be read.


---

## REPORT E046 — the lever sweep on both brackets (GPU)

`scripts/run_E046.sh` (no `b3`: E045 kept `balanced`): `specs_E046.json` on V\* (5 lines) and H1-R400; `specs_E046r.json` under `VCC_RENORM_AXIS=1` on both;
`specs_E046same.json` on CD4T_Stim8hr with `--allow-same-line CD4T_Stim48hr,CD4T_Rest`.
**Wall 13:48–16:52 UTC = 3.07 instance-h** (GPU; estimate ~3 h). No FAILED lines, no OOM. Approval to continue after the E045 stop: `docs/APPROVALS.md` (19 Oct, "Continue").
Reference: `B5_z2_a0.5_cis5000@@balanced` (E045s0 rows). Rule-1 threshold: max(0.005, 2 × SD\* 0.0015) = 0.005.

### 1. Per spec (V\* Δ vs ref, lines positive, bootstrap P(Δ > 0) [90 % CI], H1-R400 Δ, LB-span metric deltas on V\*, docs/16 §3 rules 1 / 2 / 3)

| spec | V\* Δ | lines + | P(Δ>0) [CI90] | H1 Δ | Δ pds / mse / fid / reach / jac / nmae (V\*) | rules 1 2 3 | LB slot |
|---|---|---|---|---|---|---|---|
| ENS_E021B5_w55 | +0.0141 | 4/5 | 0.974 [+0.0028, +0.0258] | +0.0253 | -0.028 / +0.019 / +0.004 / +0.062 / -0.002 / +0.029 | ✓ ✓ ✓ | **yes** |
| ENS_E021B5_w37 | +0.0135 | 4/5 | 0.985 [+0.0033, +0.0240] | +0.0261 | -0.011 / +0.033 / -0.012 / +0.052 / +0.001 / +0.019 | ✓ ✓ ✓ | **yes** |
| B5_z2_p53w0.3 | -0.0047 | 2/5 | 0.271 [-0.0161, +0.0074] | -0.0013 | +0.021 / -0.024 / -0.012 / -0.010 / +0.004 / -0.007 | ✗ ✓ ✗ | no |
| B5_z2_vfloor | -0.0073 | 0/5 | 0.033 [-0.0155, -0.0006] | -0.0128 | +0.020 / -0.015 / -0.041 / -0.009 / +0.005 / -0.004 | ✗ ✗ ✗ | no |
| B5_z2_bud600md0.3 | +0.0074 | 4/5 | 0.945 [-0.0001, +0.0161] | +0.0209 | -0.004 / +0.003 / +0.049 / -0.004 / -0.001 / +0.002 | ✓ ✓ ✓ | **yes** |
| B5_z2_bud1500md0.15 | +0.0004 | 2/5 | 0.580 [-0.0018, +0.0027] | +0.0073 | -0.002 / +0.001 / +0.006 / -0.001 / -0.001 / -0.000 | ✗ ✓ ✗ | no |
| B5_z2_ALL | +0.0010 | 3/5 | 0.556 [-0.0169, +0.0171] | +0.0123 | +0.042 / -0.040 / +0.007 / -0.015 / +0.019 / -0.008 | ✗ ✓ ✗ | no |

Full tables: `results/E046/rank_vstar.txt`, `rank_H1.txt`.

### 2. Renorm over the Flex axis (L6, `VCC_RENORM_AXIS=1`)

| spec | V\* mean (off → on) | H1-R400 (off → on) |
|---|---|---|
| B5_z2_a0.5_cis5000 | 0.1121 → 0.1124 (+0.0003) | 0.0624 → 0.0614 (-0.0011) |
| B2_raw_gPL(E021) | 0.1147 → 0.1145 (-0.0003) | 0.1384 → 0.1390 (+0.0006) |
| ENS_E021B5_w55 | 0.1262 → 0.1250 (-0.0012) | 0.0878 → 0.0883 (+0.0005) |

Bootstrap renorm-B5 vs B5 (V\*): Δ +0.0003, CI90 [-0.0019, +0.0025], P = 0.59. **No effect** (all |Δ| ≤ 0.0013, below SD\*).

### 3. Same-line proxy (L8): CD4T_Stim8hr with CD4T_Stim48hr/Rest allowed as sources
```
mean   worst   d_ref lines_pos  n_lines  n_seeds  seed_sd  CD4T_Stim8hr  lb_pds  lb_mse  lb_fid  lb_reach  lb_jac  lb_nmae
variant            emit                                                                                                                                  
B5_z2_sameW10      balanced  0.2523  0.2523  0.2249       1/1        1        1      NaN        0.2523  0.7811  0.3127  0.0018    0.2712 -0.0010   0.1478
B5_z2_sameW3       balanced  0.2374  0.2374  0.2100       1/1        1        1      NaN        0.2374  0.7379  0.3473 -0.0144    0.2392 -0.0061   0.1203
B5_z2_sameW1       balanced  0.1961  0.1961  0.1688       1/1        1        1      NaN        0.1961  0.6828  0.2577 -0.0435    0.2055 -0.0141   0.0882
B2_raw_gPL(E021)   balanced  0.0376  0.0376  0.0103       1/1        1        1      NaN        0.0376  0.2923  0.0000 -0.1108    0.1368 -0.0458  -0.0467
B5_z2_a0.5_cis5000 balanced  0.0273  0.0273  0.0000       0/1        1        1      NaN        0.0273  0.3215  0.0007 -0.1801    0.1011 -0.0525  -0.0267
```
- Allowing same-line data lifts CD4T_Stim8hr from **0.027 (B5) to 0.196 / 0.237 / 0.252** at line weight 1 / 3 / 10, i.e. **+0.17 to +0.22**. It's by far the largest effect measured in this project.
  MSE scaled 0.26–0.35, pds 0.68–0.78, fid ≈ 0. Weight 10 is best; it hasn't plateaued between 3 and 10.
- Caveat: these are different *conditions* of the same donors' cells (resting / 8 h / 48 h stimulation), so this is an upper-end proxy for "a D/E/F line is one of our source lines".

### 4. Specs that qualify for an LB slot (docs/16 §3 rules 1–3; rule 4 = forecast pre-registration at submission time)
- **`ENS_E021B5_w55`** (V\* +0.0141, 4/5, P 0.974, H1 +0.025) and **`ENS_E021B5_w37`** (+0.0135, 4/5, P 0.985, H1 +0.026): the E021/B5 blends (L2).
- **`B5_z2_bud600md0.3`** (+0.0074, 4/5, P 0.945, H1 +0.021): cheap DE calls (L3).
- Not qualifying: `B5_z2_bud1500md0.15` (+0.0004), `B5_z2_ALL` (+0.0010, P 0.56), `B5_z2_p53w0.3` (−0.0047), `B5_z2_vfloor` (−0.0073, CI excludes 0 on the negative side).
- Two levers (L2, L3) pass rules 1–2, so **E046c is eligible** (combinations, e.g. blend + bud600md0.3). Not started: it needs Rafid's go-ahead.
- No LB entry was made (E047 not run; stop after E046 as instructed). 0 of 2 entries used for 19 Oct UTC.

### 5. GPU hours
3.07 h. Round-4 total so far: E044 1.08 + E045 2.80 + E046 3.07 = **6.95 instance-h**, plus **≈ 5.9 h idle** (06:53–13:48 UTC) waiting for the go-ahead after the E045 stop.

### Anomalies
- **The blends beat both parents on V\* but not on H1-R400.** On H1, E021 alone (0.138) is far above the blends (0.088) and B5 (0.062). The blends pass rule 2 only because the reference is B5.
  If H1 is trusted as the high-N_conf bracket, plain E021 dominates there. Its V\* Δ (+0.0026 in this table, +0.0041 in E045) is below the 0.005 threshold.
- `B5_z2_ALL` (L3 + L4 + L5 combined) is worse than `bud600md0.3` alone. p53 weighting and vfloor each lose on their own (p53w0.3 −0.005; vfloor −0.007, CI fully negative), and they drag the combination down.
- **The blends raise LB-span MSE on V\*** (+0.019 / +0.033 vs B5) while improving fid. On H1 the w55 blend's scaled MSE is 0.000, but w37's is 0.107.
- E021's per-line pattern in the blends: the gain comes mostly from Orion_HCT116 (+0.03), K562_GWPS (+0.02) and CD4T (+0.01); KOLF2.1J stays the worst line (−0.12 to −0.14) for every spec.
- No non-ORACLE LB-span scaled metric > 1.5. 5 V\* lines in every sweep.


---

## REPORT E047a / E050 / E047b — 20 Oct batch (docs/16 §9; approval logged in `docs/APPROVALS.md`, 20 Oct ~02:00 UTC)

### 1. Leaderboard results

**E047a: `ENS_E021B5_w55`** (`specs_E046.json`; qualifies under §3: V\* +0.0141, 4/5, P 0.974, H1 +0.025).
- Day count before submitting: **0 of 2 for 20 Oct UTC, so this was 1 of 2.**
- Forecast pre-registered and pushed before `vcc submit`: `results/forecasts/E047a.json` (commit 3f4001e), **overall 0.1218**.
- `.vcc` md5 `1303ac58ee444a02483a53d3efe7e4f9`; submitted 02:28 UTC; entry `JMIobPjEqBX1GVuokmrb`; **LB overall 0.1076, rank 730**.
- `lb_check verify`:
```
forecast  actual     err  d_forecast  d_actual
metric                                                 
pds        0.5545  0.6204  0.0658     -0.0280    0.0378
mse        0.1630  0.0000 -0.1630      0.0192   -0.1438
fid       -0.2894 -0.2643  0.0251      0.0037    0.0288
reach      0.1643  0.1388 -0.0254      0.0620    0.0366
jac       -0.0018  0.0071  0.0088     -0.0019    0.0070
nmae       0.1402  0.1434  0.0032      0.0293    0.0325
overall    0.1218  0.1076 -0.0143      0.0141   -0.0002
VERIFY PASS: overall error 0.0143 (need <= 0.015), delta sign ok
```
- **verify PASS** (|err| 0.0143 ≤ 0.015, Δ sign ok). **Outcome: unconfirmed** (LB Δ vs E032 = −0.0002, inside ±0.005). L2 (blend) is **not confirmed** by the LB.
- The miss is almost entirely **MSE**: forecast scaled 0.163, actual **0** (raw 1.139, above the 0.99 baseline span, so clamped). pds (+0.066), fid (+0.025) and jac (+0.009) came in *above* forecast; reach came in below (−0.025).
  The scaled MSE is not strictly between 0 and 1, so the MSE-span report clause doesn't apply; raw and scaled are given here anyway.
- Ledger: `results/submissions.csv`. I added `verify` and `outcome` columns (n/a for the four pre-protocol entries).

**E047b: NOT SUBMITTED. STOP on the like-for-like retro FAIL (§3 below).**
- Its candidate under the runbook rule would have been **`B5_z2_bud600md0.3`** (rule 3: E047a unconfirmed).
- Its prediction was built before the retro result was known (`$DATA/preds/E047b.*`, started 04:34 UTC). No forecast was committed and nothing was submitted. 1 of 2 entries used on 20 Oct UTC.

### 2. E050 rank tables and bootstraps vs `ENS_E021B5_w55`
`scripts/run_E050.sh`, **02:28–04:33 UTC = 2.10 instance-h** (GPU). No FAILED lines, no OOM.

V\* (ref = B5@balanced):
```
mean   worst   d_ref lines_pos  n_lines  n_seeds  seed_sd  CD4T_Stim8hr  K562_GWPS  KOLF2.1J  Orion_HCT116  Orion_HEK293T  lb_pds  lb_mse  lb_fid  lb_reach  lb_jac  lb_nmae
variant                    emit                                                                                                                                                                                    
ENS_E021B5_w55_bud600md0.3 balanced  0.1333 -0.0346  0.0212       3/5        5        1      NaN        0.0413     0.2214   -0.0346        0.2571         0.1814  0.3523  0.0996 -0.1009    0.3354 -0.0258   0.1393
ENS_E021B5_w37_bud600md0.3 balanced  0.1283 -0.0365  0.0162       2/5        5        1      NaN        0.0384     0.2127   -0.0365        0.2479         0.1790  0.3607  0.0849 -0.1074    0.3263 -0.0241   0.1292
ENS_E021B5_w73             balanced  0.1271 -0.0943  0.0150       5/5        5        1      NaN        0.0379     0.2426   -0.0943        0.2646         0.1850  0.3669  0.1058 -0.1496    0.3452 -0.0421   0.1365
ENS_E021B5_w55             balanced  0.1262 -0.1238  0.0141       4/5        5        1      NaN        0.0399     0.2431   -0.1238        0.2881         0.1837  0.3820  0.1312 -0.1855    0.3396 -0.0391   0.1291
ENS_E021B5_w37             balanced  0.1256 -0.1389  0.0135       4/5        5        1      NaN        0.0371     0.2386   -0.1389        0.2828         0.2086  0.3990  0.1446 -0.2011    0.3292 -0.0363   0.1184
ENS_E021B5_w73_bud600md0.3 balanced  0.1249 -0.0283  0.0128       3/5        5        1      NaN        0.0388     0.2220   -0.0283        0.2076         0.1845  0.3447  0.0410 -0.0909    0.3388 -0.0286   0.1444
B5_z2_bud600md0.3          balanced  0.1195 -0.1026  0.0074       4/5        5        1      NaN        0.0283     0.2310   -0.1026        0.2586         0.1823  0.4057  0.1152 -0.1403    0.2735 -0.0388   0.1017
B2_raw_gPL(E021)           balanced  0.1147 -0.0560  0.0026       2/5        5        1      NaN        0.0376     0.1944   -0.0560        0.2144         0.1833  0.3463  0.0000 -0.1015    0.3530 -0.0459   0.1367
B5_z2_ALL                  balanced  0.1131 -0.1088  0.0010       3/5        5        1      NaN        0.0292     0.2121   -0.1088        0.2252         0.2078  0.4516  0.0724 -0.1821    0.2627 -0.0180   0.0919
B5_z2_bud1500md0.15        balanced  0.1125 -0.1257  0.0004       2/5        5        1      NaN        0.0268     0.2224   -0.1257        0.2574         0.1816  0.4076  0.1131 -0.1832    0.2763 -0.0383   0.0995
B5_z2_a0.5_cis5000         balanced  0.1121 -0.1307  0.0000       0/5        5        1      NaN        0.0273     0.2232   -0.1307        0.2565         0.1843  0.4100  0.1120 -0.1893    0.2776 -0.0373   0.0998
B5_z2_p53w0.3              balanced  0.1074 -0.1303 -0.0047       2/5        5        1      NaN        0.0262     0.2109   -0.1303        0.2309         0.1995  0.4305  0.0879 -0.2010    0.2672 -0.0330   0.0929
B5_z2_vfloor               balanced  0.1048 -0.1533 -0.0073       0/5        5        1      NaN        0.0262     0.2165   -0.1533        0.2524         0.1823  0.4298  0.0972 -0.2298    0.2687 -0.0327   0.0957
wrote results/E050/rank_vstar.csv
```
H1-R400:
```
mean   worst   d_ref lines_pos  n_lines  n_seeds  seed_sd  H1_R400  lb_pds  lb_mse  lb_fid  lb_reach  lb_jac  lb_nmae
variant                    emit                                                                                                                             
ENS_E021B5_w73_bud600md0.3 balanced  0.1485  0.1485  0.0860       1/1        1        1      NaN   0.1485  0.7453  0.0000 -0.1922    0.1415  0.0895   0.1067
ENS_E021B5_w55_bud600md0.3 balanced  0.1403  0.1403  0.0779       1/1        1        1      NaN   0.1403  0.7425  0.0000 -0.2159    0.1353  0.0822   0.0980
B2_raw_gPL(E021)           balanced  0.1384  0.1384  0.0760       1/1        1        1      NaN   0.1384  0.7524  0.0000 -0.2422    0.1416  0.0749   0.1039
ENS_E021B5_w37_bud600md0.3 balanced  0.1326  0.1326  0.0702       1/1        1        1      NaN   0.1326  0.7326  0.0000 -0.2270    0.1322  0.0766   0.0812
ENS_E021B5_w73             balanced  0.1107  0.1107  0.0482       1/1        1        1      NaN   0.1107  0.7576  0.0000 -0.3955    0.1472  0.0477   0.1069
ENS_E021B5_w37             balanced  0.0885  0.0885  0.0261       1/1        1        1      NaN   0.0885  0.7505  0.1068 -0.5447    0.1268  0.0140   0.0776
ENS_E021B5_w55             balanced  0.0878  0.0878  0.0253       1/1        1        1      NaN   0.0878  0.7572  0.0000 -0.4947    0.1397  0.0283   0.0962
B5_z2_bud600md0.3          balanced  0.0833  0.0833  0.0209       1/1        1        1      NaN   0.0833  0.6942  0.0945 -0.4173    0.0680  0.0192   0.0414
B5_z2_ALL                  balanced  0.0747  0.0747  0.0123       1/1        1        1      NaN   0.0747  0.6865  0.1464 -0.4883    0.0619  0.0072   0.0346
B5_z2_bud1500md0.15        balanced  0.0698  0.0698  0.0073       1/1        1        1      NaN   0.0698  0.7002  0.1186 -0.5173    0.0671  0.0089   0.0410
B5_z2_a0.5_cis5000         balanced  0.0624  0.0624  0.0000       0/1        1        1      NaN   0.0624  0.7010  0.1221 -0.5605    0.0663  0.0046   0.0412
B5_z2_p53w0.3              balanced  0.0611  0.0611 -0.0013       0/1        1        1      NaN   0.0611  0.6736  0.0985 -0.5199    0.0678  0.0100   0.0367
B5_z2_vfloor               balanced  0.0497  0.0497 -0.0128       0/1        1        1      NaN   0.0497  0.7079  0.1440 -0.6445    0.0587 -0.0076   0.0393
```
Bootstraps (`compare --tag E050 … --tag-b E046 --b ENS_E021B5_w55`, LB spans, 1,000):

| spec | Δ vs w55 | 90 % CI | P(Δ > 0) |
|---|---|---|---|
| ENS_E021B5_w55_bud600md0.3 | +0.0071 | [-0.0202, +0.0401] | 0.638 |
| ENS_E021B5_w37_bud600md0.3 | +0.0021 | [-0.0288, +0.0372] | 0.517 |
| ENS_E021B5_w73 | +0.0009 | [-0.0125, +0.0148] | 0.547 |
| ENS_E021B5_w73_bud600md0.3 | -0.0013 | [-0.0432, +0.0394] | 0.463 |

- The best combination, `ENS_E021B5_w55_bud600md0.3` (V\* +0.0212 vs ref), is **+0.0071 vs w55 but P = 0.64 (< 0.8)**, so it wouldn't have qualified under E047b rule 1.
- On H1-R400 the budget combinations are the best specs overall (w73+bud 0.149 > E021 0.138 > w55+bud 0.140), unlike the plain blends (0.088).

### 3. Like-for-like retro (E021 **without** NC, as submitted, vs B5 **with** NC, as submitted): **FAIL → STOP**
```
scaling: raw metrics with official LB spans {'pds': (0.498, 0.954), 'fid': (0.513, 0.812), 'reach': (0.076, 0.99), 'jac': (0.031, 0.356), 'nmae': (0.992, 0.463), 'mse': (0.99, 0.05)}
per-line local deltas (a - b):
                 pds    mse    fid  reach    jac   nmae  context
holdout                                                         
CD4T_Stim8hr   0.077  0.001 -0.107 -0.015  0.005  0.034   -0.001
K562_GWPS      0.227  0.183  0.001  0.028  0.050 -0.007    0.080
KOLF2.1J       0.037  0.000 -0.614 -0.024 -0.025  0.019   -0.101
Orion_HCT116   0.117  0.287  0.076 -0.082  0.040 -0.021    0.070
Orion_HEK293T  0.147  0.089  0.052 -0.074  0.026 -0.019    0.037

mean local delta: {'pds': 0.121, 'mse': 0.112, 'fid': -0.119, 'reach': -0.033, 'jac': 0.019, 'nmae': 0.001, 'context': 0.017}
LB delta:         {'pds': 0.082, 'mse': 0.144, 'fid': -0.226, 'reach': -0.006, 'jac': -0.007, 'nmae': 0.025, 'context': np.float64(0.002)}
per-line metric-sign agreement with LB (of 6): {'CD4T_Stim8hr': 5, 'K562_GWPS': 2, 'KOLF2.1J': 5, 'Orion_HCT116': 3, 'Orion_HEK293T': 3}
context delta local +0.0169 vs LB +0.0018 (|err| 0.0151, need <= 0.015)
local/LB ratio on metrics with |LB delta| >= 0.05 (need 1/3..3): {'pds': np.float64(1.48), 'mse': np.float64(0.78), 'fid': np.float64(0.52)}
RETRODICTION FAIL: context sign ok, metric signs 6/6, magnitudes ok
```
- **FAIL by 0.0001**: context Δ local +0.0169 vs LB +0.0018 (|err| 0.0151 > 0.015). Metric signs 6/6 and magnitudes within 1/3–3×.
- The like-for-like pair over-forecasts B5's advantage. Without Orion, E021 loses about 0.020 on V\* (§4), which inflates B5 − E021.
- Per the runbook ("If the like-for-like retro FAILs, that is a stop") and Rafid's batch approval, **E047b was not run and I stopped here.**

### 4. NC on/off on V\* (5 lines, E045s0 = NC on, E050nc0 = NC off)
```
mean   worst  n_lines  n_seeds  seed_sd  CD4T_Stim8hr  K562_GWPS  KOLF2.1J  Orion_HCT116  Orion_HEK293T  lb_pds  lb_mse  lb_fid  lb_reach  lb_jac  lb_nmae
variant                                 emit                                                                                                                                                                  
B2_raw_gPL(E021) [vstar_rows_E045s0]    balanced  0.1147 -0.0560        5        1      NaN        0.0376     0.1944   -0.0560        0.2144         0.1833  0.3463   0.000 -0.1015    0.3530 -0.0459   0.1367
B5_z2_a0.5_cis5000 [vstar_rows_E045s0]  balanced  0.1121 -0.1307        5        1      NaN        0.0273     0.2232   -0.1307        0.2565         0.1843  0.4100   0.112 -0.1893    0.2776 -0.0373   0.0998
B2_raw_gPL(E021) [vstar_rows_E050nc0]   balanced  0.0952 -0.0297        5        1      NaN        0.0283     0.1428   -0.0297        0.1870         0.1476  0.2891   0.000 -0.0707    0.3109 -0.0565   0.0985
B5_z2_a0.5_cis5000 [vstar_rows_E050nc0] balanced  0.0907 -0.0678        5        1      NaN        0.0195     0.1758   -0.0678        0.2034         0.1224  0.3262   0.078 -0.1088    0.2302 -0.0480   0.0664
```
- NC sources are worth **+0.020 for E021 (0.0952 → 0.1147)** and **+0.021 for B5 (0.0907 → 0.1121)** on the 5-line V\*. The loss without NC is spread over all lines, largest on K562_GWPS (−0.05) and Orion_HEK293T (−0.06 for B5).
  (On the 2 Orion lines, NC off means the other Orion line can't be a source.)

### 5. Same-line proxies
K562_GWPS held out with the K562 essential screen allowed:
```
mean   worst   d_ref lines_pos  n_lines  n_seeds  seed_sd  K562_GWPS  lb_pds  lb_mse  lb_fid  lb_reach  lb_jac  lb_nmae
variant            emit                                                                                                                               
B5_z2_a0.5_cis5000 balanced  0.2232  0.2232  0.0000       0/1        1        1      NaN     0.2232  0.6456  0.1834  0.0274    0.3501  0.0010   0.1317
B5_z2_sameK562W1   balanced  0.2232  0.2232  0.0000       0/1        1        1      NaN     0.2232  0.6456  0.1834  0.0274    0.3501  0.0010   0.1317
B5_z2_sameK562W3   balanced  0.2232  0.2232  0.0000       0/1        1        1      NaN     0.2232  0.6456  0.1834  0.0274    0.3501  0.0010   0.1317
B5_z2_sameK562W10  balanced  0.2232  0.2232  0.0000       0/1        1        1      NaN     0.2232  0.6456  0.1834  0.0274    0.3501  0.0010   0.1317
B5_z2_sameK562W30  balanced  0.2232  0.2232  0.0000       0/1        1        1      NaN     0.2232  0.6456  0.1834  0.0274    0.3501  0.0010   0.1317
B2_raw_gPL(E021)   balanced  0.1944  0.1944 -0.0288       0/1        1        1      NaN     0.1944  0.5573  0.0000  0.0415    0.4231 -0.0251   0.1698
```
**Target overlap: the K562 essential summary measures 0 of the 213 K562_GWPS held-out targets.** So same-line weighting has nothing to act on: all 4 weights equal B5 exactly. This proxy is **uninformative** (not evidence against L8).

CD4T_Stim8hr with CD4T_Stim48hr/Rest allowed (weights 1/3/10 from E046, 30/100 new):
```
mean   worst   d_ref lines_pos  n_lines  n_seeds  seed_sd  CD4T_Stim8hr  lb_pds  lb_mse  lb_fid  lb_reach  lb_jac  lb_nmae
variant            emit                                                                                                                                  
B5_z2_sameW10      balanced  0.2523  0.2523  0.2249       1/1        1        1      NaN        0.2523  0.7811  0.3127  0.0018    0.2712 -0.0010   0.1478
B5_z2_sameCD4TW30  balanced  0.2491  0.2491  0.2218       1/1        1        1      NaN        0.2491  0.7948  0.2372  0.0151    0.2884  0.0013   0.1577
B5_z2_sameCD4TW100 balanced  0.2465  0.2465  0.2191       1/1        1        1      NaN        0.2465  0.8016  0.1828  0.0237    0.3030  0.0027   0.1650
B5_z2_sameW3       balanced  0.2374  0.2374  0.2100       1/1        1        1      NaN        0.2374  0.7379  0.3473 -0.0144    0.2392 -0.0061   0.1203
B5_z2_sameW1       balanced  0.1961  0.1961  0.1688       1/1        1        1      NaN        0.1961  0.6828  0.2577 -0.0435    0.2055 -0.0141   0.0882
B2_raw_gPL(E021)   balanced  0.0376  0.0376  0.0103       1/1        1        1      NaN        0.0376  0.2923  0.0000 -0.1108    0.1368 -0.0458  -0.0467
B5_z2_a0.5_cis5000 balanced  0.0273  0.0273  0.0000       0/1        1        1      NaN        0.0273  0.3215  0.0007 -0.1801    0.1011 -0.0525  -0.0267
```
- **Plateau at weight 10** (0.252); 30 → 0.249, 100 → 0.247. Higher weight trades MSE (0.31 → 0.18) for pds/reach.

### 6. Instance hours
E047a build 02:01–02:27 (0.43 h) · E050 02:28–04:33 (2.10 h, overlapping the E047a upload/scoring) · E047b build from 04:34 (CPU, not used).
**Batch total ≈ 2.7 instance-h.** Round-4 cumulative ≈ 9.6 instance-h plus ≈ 5.9 h idle on 19 Oct.

### Anomalies
- **The forecast overshot by 0.0143, nearly the whole tolerance, and all of it is MSE.** On V\* the blend raises scaled MSE (+0.019 vs B5). On A/B/C its raw MSE is 1.14, above baseline, while E032 scored 0.144 scaled.
  V\*'s MSE seems to under-penalise blending a dense (E021) with a sparse (B5) prediction. That fits the unconfirmed result, and suggests MSE is where the validator is weakest (R4-01).
- **The like-for-like retro misses by 0.0001.** The old pair (E021 with NC on V\*) passes with err 0.0044. The NC mismatch planning identified (§9.2 item 1) moves the forecast by +0.019.
- The K562 same-line proxy is degenerate (0 overlapping targets). A useful realistic proxy needs a same-line source that measures the held-out targets: e.g. Orion_HEK293T held out with a HEK293 screen, which we don't have.
- The E050 combinations raise H1-R400 well above the plain blends, which makes H1's ranking flip between E046 and E050. That's consistent with planning's decision to use H1 only as a veto.
- `vcc submit` printed rank 729; the status JSON says 730 (others submitting in between).

**STOPPED.** E047b not submitted; E048 not started (it also needs Rafid's NC decision).
