# Findings A: data and validation splits (Auditor A)

Saved by the orchestrator: the auditor was not allowed to write files. Synthetic checks are in `scratchpad/A/check_axis.py` and `check_corr.py`.

**Notes on the evidence:**
- **Sign tests are anchor-independent.** Within one line, `(u−b)/(r−b)` is monotone, so the per-line *sign* of a scaled Δ doesn't depend on O-01's wrong anchors (mse and nmae flip as expected). Scaled *magnitudes* still carry O-01.
- **"Null share" = the fraction of targets with N_conf = 0**, estimated from the local dispersed-baseline jac. That arm calls ~nothing, so jac ≈ P(N_conf = 0) via J(∅,∅) = 1. On every line, jac × n_targets comes out a whole number (22, 40, 58, 60, 3, 6).

---

- id: A-01
  class: Method
  title: V\* truths are in a sparse, null-heavy regime unlike A/B/C. The null-heavy lines flip the sign of the LB deltas, and they alone produced E032's "+0.029".
  severity: P1
  confidence: VERIFIED 90% (regime and sign analysis); how much of the forecast miss it causes is LIKELY
  impact: >
    Measured: the E031 V\* forecast for E032 vs E021 was +0.029; the LB gave +0.002.
    Per-line Δ(B5 − E021) (`results/E031/bootstrap_vstar.json`):
    - low-null lines: KOLF −0.030 (0 % null), CD4T −0.008 (8 %); mean −0.019;
    - null-heavy lines: K562 +0.037 (19 %), HCT116 +0.144 (23 %), HEK293T +0.003 (24 %); mean +0.061.
    Estimated forward risk: the tile baseline scores fid = jac = 0 on N_conf = 0 targets, while calling nothing there scores 1. That is up to about 0.19–0.24 raw per line, which outweighs spec differences of 0.01–0.04.
  evidence: >
    **Regime** (`results/E037/regime_holdout_*.json`):
    - K562_GWPS: 181 cells/target, 7.8k UMI, N_conf mean/median/p90 13.8/4/41, null share 0.188 (40/213);
    - Orion_HCT116: 163, 12.1k, 15.6/2/18, null 0.228 (58/255);
    - Orion_HEK293T: 208, 15.0k, 27.6/2/35, null 0.240 (60/250);
    - CD4T_Stim8hr: 127, 8.9k, 100/10, null 0.079 (22/278);
    - KOLF2.1J: 236, 3.8k, 103/42 (min 4), null 0;
    - val A: 400 cells, ~20k UMI, N_conf mean 335.9, min 4, null 0;
    - val B/C: 23.7 % and 27.3 % of targets have N_conf < 10.

    **Sign test**, per-line scaled Δ(B5_z2_a0.5_cis5000 − E021) on pds/mse/fid/reach/jac/nmae (`results/E031/vstar_rows_E031_seen.csv`) vs the LB Δ (+.082/+.144/−.226/−.006/−.008/+.025):
    - KOLF +.065/+.019/**−.202**/−.029/−.048/+.012: 6/6 signs match;
    - CD4T +.032/0/−.042/−.054/−.014/+.032: 5/6;
    - K562 +.103/+.241/−.007/−.106/+.029/−.039: 4/6;
    - HCT116 +.173/+.890/**+.036**/−.199/+.035/−.072: 3/6;
    - HEK +.131/+.145/**+.020**/−.200/+.028/−.109: 3/6.
    
    Sign agreement falls monotonically with null share; raw-fid Δ against null share has Spearman ρ = 0.9 (n = 5). KOLF predicted the LB fid collapse (−0.20 vs −0.23).
  mechanism: >
    At 150–240 cells/target and 4–15k UMI, most V\* targets have no detectable DE. Sparse callers such as B5 win fid and jac on N_conf = 0 targets (fid = 1 if n_pred = 0; J(∅,∅) = 1) and lose on A/B/C. The 5-line equal-weight mean let the null-heavy lines decide.
  confirm: >
    Dump per-target N_conf per V\* holdout and reweight Δ(B5 − E021) to the val A N_conf strata. The fid sign should turn negative everywhere.
  fix: >
    (1) Reweight per-target V\* metrics to val A/B/C N_conf strata. A: 0 % null, 9.3 % < 10. B and C: 23.7 % and 27.3 % < 10.
    (2) A retrodiction gate: a validator counts only if it reproduces the six LB Δ signs of E032 − E021.
    (3) Rebuild truths at 400 cells and 20k UMI; drop or down-weight lines with median N_conf < 10.
    Verify: reweighted Δfid < 0 on at least 4 of 5 lines.
  effort: hours (reweighting and gate); days (rebuilt truths)
  depends_on: O-01 (magnitudes only), A-02
  seams: >
    Eval: tile anchors amplify null-heavy lines.
    Biology: targets unexpressed in A/B/C are the LB's null targets.

- id: A-02
  class: Data
  title: "`prepare_holdout` picks the truth panel from the holdout's summary (all donors, kd ≤ 0.7 or NaN, target on the source's gene list), not from the truth cells. Truths are a non-random 71–93 % subset of the panel and can be under-powered."
  severity: P2
  confidence: VERIFIED 90% (code, synthetic run, artefacts)
  impact: >
    Bounded: 7–29 % of panel targets per line are left out of local truths; the LB keeps all 300 at 400 cells.
    The poor-knockdown (weak) tail is removed. On H1-R400, N_conf is 2.5× denser than val A.
  evidence: >
    - `loco.py` L102–104: `mc = min(n_cells, 50)` filters on summary `ncells`; `~(kd > max_kd)` keeps NaN; the target must be on the holdout's gene list. `vstar.eligible` counts only ncells (K562: 254 eligible vs 213 in the truth).
    - Attrition: K562 300 → 272 → 263 → 254 → **213** (41 dropped because the target isn't among K562's 7,681 genes); HCT116 → 255; HEK293T → 250; CD4T → 278; KOLF → 258.
    - CD4T summaries pool 4 donors while the truth is donor D4 only. R400 (≥ 400 summary cells) gave a truth with median 167 and minimum 34 cells.
    - Synthetic `check_axis.py`: a kd-NaN target is kept; truth cells/target are 10 where the summary says 80.
  mechanism: LB truths contain every panel target at 400 cells. Local truths drop targets by summary-level rules, so the target mix and power differ from the LB.
  fix: >
    Count cells per label in the truth file and apply `min_cells` there. Take candidates from the raw labels ∩ the panel, so poor-knockdown and unexpressed targets stay in.
    Write the exclusion breakdown to `holdout_*/panel.json`.
  effort: hours
  depends_on: none
  seams: C (expression gating); B (`--match-cells` hides the power mismatch)

- id: A-03
  class: Method
  title: Orion HCT116 and HEK293T are sibling sources from one study and inflate V\*; the `line` field is the wrong unit for leakage, and A–F have no such sibling.
  severity: P2
  confidence: VERIFIED 80% (direction robust; magnitudes carry O-01)
  impact: >
    Measured, V\* → V\*-far: B5 HCT116 0.483 → 0.405, HEK293T 0.242 → 0.143; E021 −0.046 and −0.049.
    On the three far lines, the selection Δ shrinks from +0.039 to +0.007 (CI [−0.019, +0.026]).
  evidence: >
    - `results/E031/bootstrap_far.json`; `loco.py` L156–159 excludes only the same `line`/`lineage`.
    - A/B/C's only same-study source is H1 (Arc, Flex), with 25 panel targets.
  mechanism: Shared guides, filtering, chemistry and processing make the sibling lines co-vary beyond biology.
  fix: >
    Add a `study` field to `loco.json` and exclude same-study sources by default in V\*.
    Verify: V\* Δ(B5 − E021) is about +0.007, with the LB's sign.
  effort: hours
  depends_on: A-01
  seams: D (E032 accepted a V\*-far that was worse on 2 of 3 runs)

- id: A-04
  class: Data
  title: The H1-R400 validator is mostly off-panel (at most 20 of its 254 targets are panel targets) and 2.5× denser than val A; its committed per-target files are from the superseded cap100 truth.
  severity: P2
  confidence: VERIFIED 85%
  impact: >
    Estimated: call budgets tuned on N_conf mean 855 / median 135.5 will over-call relative to A (mean 336), and more so on B/C.
  evidence: >
    - `results/E037/regime_holdout_H1_R400.json`: mean 855.2, median 135.5, p90 2993.
    - `pertarget_H1_R400_seen_E037.parquet` and `scores_H1_R400_seen_E037.csv` were last changed in 6d6f462 (cap100). The rerun commit 9ea55c5 did not update them; the parquet returns nmae for 141/254 targets, which fits cap100.
    - The rebuilt `subsets/H1.h5ad` (via `make_subset.py`) dropped the `batch` column, so no batch confound test is possible. `pb/H1.npz` has no D7 composition-matched controls.
  mechanism: The validator's targets (2025 H1 panel, median kd 0.06) and N_conf distribution differ from the 2026 panel.
  fix: >
    Calibrate budgets against val A/B/C N_conf statistics, or reweight. Commit the rerun artefacts. Rebuild with `--keep-obs batch` and run a χ² test of batch vs control.
  effort: hours
  depends_on: O-01
  seams: D (report vs artefacts; H1 subset overwritten in place)

- id: A-05
  class: Data
  title: The case for the LB config and the default final pipeline both rest on NC-licensed Orion data; without the Orion holdouts B5's V\* gain is about 0, and on the LB-like line the NC sources hurt.
  severity: P2
  confidence: VERIFIED 85% (artefacts); the licence exposure is a judgement call
  impact: >
    Measured:
    - without the Orion holdouts, Δ(B5 − E021) = −0.0004;
    - KOLF with vs without NC sources: 0.141 vs 0.172 (−0.031); the +0.015 across 3 lines comes entirely from K562 (+0.060).
  evidence: Orion `licence` is CC BY-NC-SA 4.0; `final_pipeline.sh` L7 `NC=${6:-on}`; `results/E035/*`; `results/E031/bootstrap_vstar.json`.
  mechanism: Orion is both a source and 2 of the 5 holdouts, which are null-heavy (A-01) and sibling-inflated (A-03).
  fix: >
    Settle the licence before 22 Oct. Test NC on vs off with one A/B/C LB pair, or default to `nc=off`.
  effort: hours (decision); 1 day (two submissions)
  depends_on: A-01, A-03
  seams: D; O-03

- id: A-06
  class: Data
  title: The coverage claims hold only under a loose "measured" (kd > 0.7 = unmeasured, but kd NaN = measured); the batch-2/3 numbers can't be reproduced from committed files, and ≥ 2-line coverage depends on NC.
  severity: P3
  confidence: VERIFIED 85%
  impact: >
    Bounded. K562 counts at least 41 targets as "measured" whose knockdown can't be checked.
    Without NC at ≥ 25 cells: 299/290/240 targets in ≥ 1/2/3 lines. At ≥ 50 cells: 299/284/221; EPHB2 is unmeasured.
  evidence: >
    `pseudobulk.py` L120–122; `loco.py` L103. `reports/panel_coverage.csv` reproduces batch 1 only; no committed table backs 300/300/293.
  mechanism: Coverage overstates the evidence B5's consensus has, and it shrinks without NC.
  fix: Regenerate coverage with kd-checked / kd-NaN columns, with and without NC. Treat kd-NaN entries as missing evidence in B5.
  effort: hours
  depends_on: none
  seams: C

- id: A-07
  class: Engineering
  title: Holdout truths are cached by folder name only, and shared inputs were overwritten in place, so which inputs built a truth is ambiguous.
  severity: P3
  confidence: VERIFIED 80%
  impact: Not measured; risk of silently reusing a truth built under different arguments.
  evidence: >
    `loco.py` L89–92 returns the cached truth regardless of arguments. E031 reused E020's truths, built before the D7 swap. `subsets/H1.h5ad` was overwritten; D7 summaries were swapped into `pb/` in place.
  mechanism: Changing how a truth is built doesn't invalidate the cache.
  fix: >
    Write `holdout_*/meta.json` holding the arguments and input hashes; rebuild on mismatch.
  effort: hours
  depends_on: none
  seams: O-03, D

- id: A-08
  class: Method
  title: No direct holdout leak found; three latent channels remain - `common='panel'`, reuse of the truth's control cells, and the `_PC_CACHE` id key.
  severity: P3
  confidence: VERIFIED 80% (code)
  impact: Estimated ~0 for the LB config.
  evidence: >
    Checked, no leak:
    - same-`line` exclusion (`loco.py` L156);
    - `generic_pool`, `NeighborPrior.learn`, `_line_effects` and `translator.fit` see only the sources (M1's cache is keyed by source names);
    - `detect` and `de_budget` read only the controls;
    - `vstar` applies `exclude_licence` to holdouts and sources alike.

    Latent:
    1. `common='panel'` averages over targets chosen using the holdout's own knockdown and cell counts.
    2. The truth's control cells serve as the emitter base, the detection reference and the scorer's control. That matches the LB only if the official controls are the released ones.
    3. `models._PC_CACHE` is keyed by `id(ctrl)`; it has had no effect so far.
  mechanism: Selection information or stale state could leak into future specs.
  fix: Take the `common` panel from `pert_counts.csv`; key `_PC_CACHE` on a content hash.
  effort: hours
  depends_on: none
  seams: B

- id: A-09
  class: Data
  title: Gene-axis checks pass; a missing gene never enters the LB path as a measured zero.
  severity: P3
  confidence: VERIFIED 80%
  impact: Estimated < 0.005.
  evidence: >
    - `models.py` L26/L93/L536 use only genes with `present & ctrl_cpm > 0.5`.
    - Holdouts built from subset files carry all-zero columns for unmeasured genes, which the scorer's control-CPM gate removes.
    - Duplicate symbols take the first occurrence consistently.
    - Remaining: the K562 truth has 7,681 genes; `_ctrl_corr` counts absent genes as 0 (r 0.799 vs 0.768 on shared genes only); summaries normalise over all source genes.
  mechanism: n/a
  fix: Optionally restrict `_ctrl_corr` to shared genes.
  effort: hours
  depends_on: none
  seams: none

- id: A-10
  class: Data
  title: HipSci "controls" are 99.99 % guide-unassigned cells, so its lfc is relative to an average perturbed cell.
  severity: P3
  confidence: LIKELY 70%
  impact: Estimated small (85 targets, 19 with ≥ 50 cells).
  evidence: DATA_DONE_batch2: 48 NonTarget vs 499,950 unassigned; `convert_feng.py` L66–67.
  mechanism: Subtracting a mix of perturbed cells removes the shared response and pulls target-specific effects toward 0.
  confirm: Re-summarise with NonTarget-only controls and compare.
  fix: Down-weight HipSci in B5.
  effort: hours
  depends_on: none
  seams: C

- id: A-11
  class: Data
  title: The A549 CRISPR-knockout candidate has no modality guard.
  severity: P3
  confidence: VERIFIED 80% (code); impact SUSPECTED
  impact: Estimated ≤ 0.005 (21 targets), but it would bias the cis prior for every target.
  evidence: The `loco_candidates.json` note; no `perturbation` field in `loco.json`; `NeighborPrior.learn` uses all sources; A549 has no `--max-kd`; agreement with HCT116 r 0.12.
  mechanism: Modality-specific responses would enter the consensus, the cis prior and the votes.
  fix: Add a `perturbation` field; keep knockout out of the cis prior and the consensus.
  effort: hours
  depends_on: none
  seams: C

## Out-of-scope observations (seams)
- **B:** `B0_control` with the balanced emitter scores raw fid 0.25–0.43 and reach 0.13–0.28, but jac only 0.0005–0.01 despite 19–24 % null targets. So "no change" emitted that way produces DE calls (KOLF is the exception).
- **B:** `_PC_CACHE` keyed by `id(ctrl)`; `--match-cells` hides power differences.
- **O-01 follow-up:** tile anchors give null-heavy lines more weight, so reweight before ranking.
- **C:** K562 counts at least 41 unexpressed panel targets as "measured".
- **D:** the committed E037 per-target files are stale; shared inputs were overwritten; E032 accepted a far run that was worse on 2 of 3 lines.

## Open questions
1. Are the official A/B/C truth controls exactly the released 18,400 cells?
2. How many val B/C targets have N_conf = 0 (only the count below 10 is known)?
3. Are the D/E/F targets the same 300 as A/B/C?
4. Was the 2026 panel chosen so every target yields 400 cells per context?
5. The batch structure across the 2025 H1 splits.
6. Do the competition rules restrict external-data licences?
