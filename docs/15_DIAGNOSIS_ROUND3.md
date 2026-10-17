# Diagnosis, round 3: why we're stuck near 0.1, and the plan

> **Corrections, 17 Oct (full review in `review/FINAL_REPORT.md`):**
> 1. **Problem 2's mechanism was wrong.** V\*'s baseline fid of ~0.02 came from our local baseline being emitted "dispersed", while the official arm has identical cells ("tile"). Truth size and depth were not the cause: a 400-cell, 20k-UMI H1 truth still gave 0.03 (E037). Fixed in `local_eval` (E042).
> 2. **"Transfer is at chance / a biological limit" (§0.4, §6) is not established.** The cited cosine and top-50 numbers are noise-limited even under perfect transfer, and LB reach is above no-skill (review C-03).
> 3. **Null targets (N_conf = 0):** calling nothing gives jac = 1, and the scored fid is NaN, so it is dropped rather than scored as 1 (C-01).
> 4. **Not every source is non-Flex:** CD4T is Flex too.

Written 16 Oct 2026, ~15:00 UTC.

**Sources:**
- `reports/REPORTS_E030_E036.md`
- `results/E020`, `E031`, `E034` (V\* rows)
- `EXPERIMENT_LOG.md` (leaderboard entries E001, E012, E021, E032)
- the scorer's own source code: `cell_eval2` 0.18.0, installed from PyPI. The files are named where cited; its notes record measurements on the official val A/B/C bundles.
- Arc, Illumina and Xaira pages, cited inline (Sources at the end).

**Supersedes** the priorities in `14_DIAGNOSIS_ROUND2.md`.

## 0. The short answer

We are not stuck because the models are weak in general. We are stuck because of five things, listed by how much score they cost.

1. **We call too few DE genes, so `fid` sits below chance.** The scored fid is `k / max(n_pred, N_conf)`, where k counts our called genes whose direction matches the *real log2FC of any sign*, significant or not (`metrics/direction.py`, `_components` / `_direction_frame`).
   - If we call at least as many genes as the truth has (N_conf; about 336 per target on val A), coin-flip directions score about 0.5.
   - That is exactly where the official baseline sits: 0.506 / 0.523 / 0.509 on val A/B/C (`competition.py` notes).
   - B5 calls fewer genes than N_conf, so it scores k/N_conf = 0.42.
   - The fid span is only about 0.30, so this costs **−0.29 scaled, i.e. −0.05 overall**, against simply being at chance.
2. **Our validation (V\*) can't see problem 1, so we optimised the wrong thing.**
   - V\* truths have fewer cells per target and less depth than A/B/C (400 cells, ~20k UMI). Their mean-response baseline therefore calls almost nothing: baseline fid is 0.005–0.035 in V\*, against 0.51 on the leaderboard.
   - So *any* calls look good. Our no-change model B0 scores fid **+0.42 to +0.81 scaled** in V\*. On the leaderboard, calling nothing scores about **−1.7**.
   - V\* forecast +0.029 for B5 over E021; the leaderboard gave +0.002. The whole gap is fid: V\* said −0.04, the leaderboard said −0.23 (§2, F3).
3. **The emitter we've used since E021 creates spurious DE calls.** On a no-change prediction, `--emit balanced` makes the scorer's own DE engine call **~2.7% of tested genes for every target** (synthetic null test, `cell_eval2.de_compute.compute_de`).
   - These are the same genes for every target, mostly "up". The cause: herded cells pinned to the population mean shift every skewed gene up.
   - The new modes `balanced2`/`balanced3` give 0 and 0.3%.
   - In V\*, B0 under `balanced` has raw fid 0.37–0.43, which is this artefact.
   - On the leaderboard it dilutes jac and probably reach.
4. **Target-specific responses barely transfer between cell types.** This is the real biological limit and it caps every metric.
   - E021's called genes have chance-level direction (leaderboard fid 0.49 ≈ chance).
   - Per-target cosine is 0.003–0.11, and top-50 gene overlap is at chance (0.03).
   - pds is the one metric where transfer clearly works (0.58).
5. **The test lines are far from all of our data, and the leaders likely have data we don't.**
   - A/B/C were profiled with **10x Flex (probe-based)** [Arc 2026].
   - Among our sources only H1 (Arc 2025) and CD4T (Zhu/Dann; per `DATA_DONE.md`) are Flex. The others are 3′ or 5′ poly-A capture.
   - Our nearest sources are 0.78–0.86 in control-profile similarity, and that similarity is partly platform-driven. A's nearest is CD4T, B's are C and H1, C's are B and HCT116: mostly the other Flex datasets.
   - Illumina (#1) announced a 1-billion-cell, genome-wide CRISPR atlas across 200+ cell lines in January 2026 [Illumina]. Xaira (#2) produced X-Atlas/Orion and holds the unreleased Pisces.
   - **Inference, unverified:** their MSE of 0.79 reflects data in or near these lines, which public data can't match.
   - Realistic aim with public data and a metric-correct output layer: the 0.25–0.35 band where #3–5 sit. 0.46+ would need a data breakthrough (§6).

**Good news.** Problems 1–3 are engineering, not biology. All three now have code (§7), and the scorer's own DE engine confirms the fix: with `de_budget` it calls exactly the number of genes we ask for (50/100/200 → 50/100/200 per target).

## 1. Where the score goes

### Leaderboard anatomy
Overall = the mean of six scaled metrics, each `(u − b)/(r − b)` per context: b = mean-response baseline, r = split-half replicate.

| metric | E032 (ours, LB) | Illumina #1 | gap | LB b (backed out) | LB r (backed out) | official val notes |
|---|---|---|---|---|---|---|
| pds | 0.583 | 0.874 | 0.29 | 0.50 | 0.95 | b 0.530/0.528/0.510 |
| mse | 0.144 | 0.787 | **0.64** | – | – | clipped at 0 (E021 raw 4.66 → 0) |
| nmae | 0.111 | 0.419 | 0.31 | 0.99 | 0.46 | control-mean arm 1.006–1.010 |
| fid | **−0.293** | 0.153 | **0.45** | **0.51** | 0.81 | b **0.506/0.523/0.509** |
| reach | 0.102 | 0.444 | 0.34 | 0.08 | 0.99 | val A b 0.042; r 0.965/0.802/0.943 |
| jac | 0.000 | 0.088 | 0.09 | 0.031 | 0.35 | val A b 0.033; half-data arm 0.38 |
| **overall** | **0.108** | **0.461** | 0.353 | | | |

How the b and r columns were derived:
- We solved E021 and E032's raw and scaled values for b and r. These are approximate, because the leaderboard averages per-context values.
- The last column quotes the scorer's source notes.
- The backed-out fid baseline (0.51) matches the official values, which validates the method.

**Shape of the val truth (scorer notes):**
- 400 cells per target ("138,400 cells × 18,533 genes, 301 groups" = 300 × 400 + 18,400 controls).
- Val A has 100,771 reference-significant pairs, i.e. N_conf ≈ 336 per target. The smallest N_conf is 4.
- 272/229/218 of the 300 targets pass the nmae gate on A/B/C. So B and C have more weak targets than A.

### V\* anchors vs leaderboard anchors
Backed out of the E020/E031/E034 V\* rows; residuals are 0 for every metric except MSE.

| metric | V\* baseline (5 lines) | LB baseline | V\* replicate | LB replicate |
|---|---|---|---|---|
| fid | **0.005–0.035** | **0.51** | 0.52–0.69 | 0.81 |
| jac | 0.08–0.24 (KOLF 0) | 0.031 | 0.18–0.49 | 0.35 |
| reach | 0.06–0.30 | 0.04–0.08 | 0.76–0.88 | 0.80–0.97 |
| pds | 0.48–0.52 | 0.50 | 0.66–0.94 | 0.95 |
| nmae | 0.98–1.12 | 0.99 | 0.45–0.79 | 0.46 |

The fid row is the whole story of problem 2. In V\*, the baseline's dispersed cells (at the truth's own, smaller group sizes) have little Wilcoxon power. Our 400 emitted cells have more power than the truth itself, so any call pattern beats the baseline.

## 2. Findings this round

| # | Finding | Evidence | Meaning |
|---|---|---|---|
| F1 | **fid counts direction on any gene.** `match = in_denom & committed & sign(lfc_pred) == sign(lfc_real)`, with `in_denom = lfc_real is non-zero`, *not* significant. | `metrics/direction.py` L186–199, L385–406, L747–776 | Calling n ≥ N_conf genes with coin-flip directions ≈ 0.5 = baseline. Under-calling falls below it; calling nothing scores ~0 raw, about −1.7 scaled. |
| F2 | **Leaderboard fid history fits F1.** E012 (dense, random emission) 0.509 ≈ chance; E021 (dense, balanced) 0.493; E032 (B5 sparse) **0.425**; E001 (generic K562 essential shift) 0.37. | backed-out raw values, `EXPERIMENT_LOG` | Our directional skill on called genes is at chance, and B5 under-calls. |
| F3 | **V\* got fid's sign wrong.** E021 → E032 per metric, V\* vs LB: pds +0.10 / +0.08 ✓; mse +0.26 / +0.14 ✓; **fid −0.04 / −0.23 ✗**; reach −0.12 / −0.01; jac +0.01 / −0.01; nmae −0.04 / +0.03. | E031 vs E032 | pds and MSE transfer from V\*. The DE metrics don't, until V\* matches the test's DE regime (P2). |
| F4 | **Emitter artefact.** No-change prediction, 6,000 structured synthetic controls, 400 cells/target, scorer DE engine: spurious calls per target are random 0, **balanced 40/1,479 (2.7%)**, balanced2 0, balanced2h 0, balanced3 4 (0.3%). | `/scratchpad` test this session; B0 raw fid 0.37–0.43 in V\* (E031) | Pinning herded cells to the population mean moves every skewed gene up. These calls carry no information and repeat for every target. |
| F5 | **ORACLE through the emitter is fine for pds/MSE/fid/reach, weak for jac.** ORACLE balanced: fid raw 0.90–0.98, reach 0.99–1.0, **jac 0.06–0.26**. | E020 rows | Even a perfect pseudobulk emitted as cells recovers only part of the significant *set*. jac depends on per-cell distribution shape. Low priority (small span). |
| F6 | **H1 is the only dataset made like A/B/C.** Arc 2025: 10x Flex, CRISPRi dCas9-KRAB dual guide, ~1,000 cells/target, >50k UMI. Its 299 targets were chosen in H1 to span effects "from dramatic … to nearly imperceptible". | [Arc behind-the-data]; `DATA_DONE.md` | H1 measures only **25 of the 300 challenge targets**, so it never qualified as a V\* line (≥ 100 needed). Held out on **its own** targets, subsampled to 400 cells/target and thinned to 20k UMI, it is our best mimic of the leaderboard's *DE regime*: same lab, assay and construct, different targets. It tests the mechanics (call budget, emitter, direction precision), not panel-specific biology. |
| F7 | **Platform confounds context similarity.** Orion is 10x GEM-X 5′ v3 [Orion preprint]; Replogle is 3′; A/B/C, H1 and CD4T are Flex. A's nearest is CD4T (0.86); B's are C (0.84) and H1 (0.79). | E036 `context_id` | "A is T-ALL-like" rests on markers (CD3, TRBC1, DNTT, LCK), so it holds. The *similarity values* and "nearest = HCT116" are partly platform effects. Identify lines against a platform-neutral reference (CCLE) instead. |
| F8 | **Leaders' data.** Illumina's Billion Cell Atlas: 1B cells, 200+ disease-relevant lines, genome-wide CRISPR, January 2026; access through an alliance (AZ, Merck, Lilly). Xaira: Orion (public) plus Pisces (unreleased). | [Illumina], [Xaira/Orion] | **Inference:** the 0.44–0.46 tier is data-driven. Our path is public data, platform-aware transfer and a metric-correct output layer. |

## 3. Problem register, round 3 (open-ended)

Status: ✅ built this round · 🔬 needs a run · ⏳ later · ✔ closed.

### A. Metric and output layer (largest, fastest gains)
| ID | Problem | Fix | Status |
|---|---|---|---|
| P1 | **Under-calling → fid below chance** (F1, F2) | `models.de_budget` (spec `"post": {"de_budget": {"n": 600}}`). Per target, rank genes by model confidence, take the top n, and lift each to 1.25 × the context's **detection threshold** in its predicted direction. Thresholds come from `vcc26.detect`, calibrated through our own emitter plus a Mann-Whitney on CPM. Verified with the scorer's engine: n_pred = n exactly. On synthetic data, 1.25 × threshold is called 100% of the time and 0.4 × threshold 0%. | ✅ 🔬 E038 |
| P2 | **Emitter artefact** (F4) | `--emit balanced3`: random base, exact pseudobulk, natural distributions; 0.3% spurious. `balanced2`: random base, unchanged genes untouched; 0 spurious, but the base's sampling offset stays in the pseudobulk. | ✅ 🔬 E038 |
| P3 | **Magnitude trade-off.** MSE prefers shrunk effects (~0.5×); the DE metrics need detectable ones. Every lifted gene costs MSE (synthetic, 1.5k UMI: raw MSE 0.16 → 4.6). | Partly decoupled: the model's magnitudes drive MSE/pds; `de_budget` only *raises* the n chosen genes to the detectable floor. Options to cut the cost: `rank="snr"` (cheapest calls first: highly expressed genes have small thresholds), per-target `frac` budgets (weak targets call few), and a lower margin. Later: an expected-score layer per gene (C-2) that lifts a gene only if E[Δfid] > E[ΔMSE]. | ✅ partial 🔬 |
| P4 | **reach** needs ≥ 90% direction purity at the head of *our* p-value ranking among truth-significant genes (P0 = 0.9, `direction.py`). Our head is the largest \|lfc\|, not the most certain gene. | `de_budget rank="snr"` (cheapest-to-call first). Next: confidence-ordered lifting (cross-line z, agreement), so the most certain genes get the smallest p-values. | ✅ partial ⏳ |
| P5 | **jac ≈ baseline.** It needs the right gene *sets*, and even ORACLE gets only 0.06–0.26 raw (F5). | Don't trade fid for it. It improves only with gene-identity skill (P13) and the common response (P6). | ⏳ |
| P6 | **Context-mean (common) response not modelled.** The baseline gets it for free, and it matters for MSE and DE sets. | B5 `common="panel"` / `panel_only` (built). Measure how conserved it is (`ORACLE_MEAN` vs `B5_common_only`, E039). | ✅ 🔬 E039 |
| P7 | **Compositional (CPM) artefacts in transferred lfcs.** A knockdown that moves very abundant genes shifts every other gene's CPM in the source line, and that shift doesn't transfer. (Hypothesis.) | Robust size factors (exclude the top 1% expressed genes) when building source lfcs. Test whether direction precision improves. | ⏳ |

### B. Validation
| ID | Problem | Fix | Status |
|---|---|---|---|
| P8 | **V\* DE regime ≠ leaderboard** (F3) | **V\*-R400**: holdouts restricted to targets with ≥ 400 cells, truth thinned to 20k UMI/cell (`--min-target-cells 400 --umi-target 20000 --holdout-tag R400`). `--match-cells` makes the other lines emit as many cells as their truth has. `scripts/regime_check.py` compares each holdout's N_conf, depth and anchors with the official numbers. | ✅ 🔬 E037 |
| P9 | **Calibration of the validator.** We have never checked that V\* reproduces leaderboard *differences*. | E038 checks whether V\*-R400 reproduces E021 → E032 on the leaderboard (fid −0.23, pds +0.08, mse +0.14). This reads two existing entries; it validates the validator and tunes nothing. | 🔬 E038 |
| P10 | **H1 never held out** (F6): only 25 panel targets | Hold H1 out on its own targets with `loco` (no `--panel-file`), at 400 cells and 20k UMI (**H1-R400**), plus a far variant without the pluripotent sources. Any line with ≥ 100 *panel* targets at ≥ 400 cells also joins V\*-R400 (the E037 dry run lists them). | ✅ 🔬 |
| P11 | **Lineage leak.** KOLF keeps H1/HipSci as sources, which is easier than any test line. | `lineage` tags in `loco.json`; `--far` in loco/vstar/proxy. | ✅ |
| P12 | **Proxy mis-calibrated** (M1, B5x_tl over-rated), and its oracles scored truth against itself. | Half-split oracles (`ORACLE_HALF`/`TOPK`/`CIS`/`MEAN` built from half A, scored against half B). `top50_rep` gives the replicate ceiling of top-50 overlap. **`dirprec@k`** estimates fid at k calls. The proxy is now for diagnostics only; selection uses V\*-R400. | ✅ |
| P13a | No per-context leaderboard breakdown (E033) | Accept; use per-line V\*. | ✔ |

### C. Biology and modelling
| ID | Problem | Fix | Status |
|---|---|---|---|
| P13 | **Weak cross-line transfer** (cos 0.003–0.11; chance directions) | (a) B5 consensus ✅; (b) M1 translator ✅, under-scaled (β 1.3 best); (c) ENS B5+M1 ✅ (B5 wins KOLF/HCT116, M1 wins HEK293T); (d) **platform-aware transfer**: weight the Flex sources (H1, CD4T) and learn per-gene platform offsets ⏳; (e) DepMap context-dependency features ⏳; (f) robust lfcs (P7) ⏳. | partial |
| P14 | **Context identity unknown; similarity is platform-confounded** (F7) | `scripts/ccle_match.py` ✅: rank A/B/C (later D/E/F) against 1,673 DepMap/CCLE lines with platform-neutral, centred scores and a sex-marker check. Uses: the matched line's dependencies (target strength), TP53 status (p53 response), targeted data search. | ✅ 🔬 E041 |
| P15 | **Response strength per target varies** (val A N_conf from 4 to hundreds; B and C have more weak targets) | Per-target budget n_t from H1 N_conf at 400 cells plus cross-line response energy (`de_budget frac/n_max` is the hook). | ⏳ after E038 |
| P16 | Knockdown efficiency per line (remaining 0.25–0.43) is unknown for A/B/C | Magnitude enters only MSE/nmae. Leave β per model and revisit with the expected-score layer. | ⏳ |
| P17 | Cis neighbours are ≤ 0.1% of signal (E030) | Closed; keep `cis_bp` off or harmless. | ✔ |
| P18 | **Platform differences per gene** (Flex probes vs capture) affect gating, expression features and similarity | `platform` tags in `loco.json` (Replogle 3′, Orion GEM-X 5′, H1 and CD4T Flex; HepG2/Jurkat 3′ *unverified*; KOLF/HipSci untagged). Use H1-vs-pluripotent-3′ control differences as a per-gene platform-bias estimate. | ⏳ |

### D. Data
| ID | Problem | Fix | Status |
|---|---|---|---|
| P19 | **Nothing close to B/C**; Pisces unreleased; Illumina's atlas restricted | CUR batch 3 (§4, E043): (i) Flex-platform perturbation datasets (Arc and others); (ii) perturbation data in carcinoma, cervical and squamous lines; (iii) once E041 names candidate lines, any public perturbation data in them; (iv) DepMap 24Q4 `CRISPRGeneEffect` and `OmicsSomaticMutations` (TP53) | ⏳ |
| P20 | NC licence: Orion helps +0.015 on non-NC lines (E035) | R decides before the final, with the E035 numbers. The final pipeline runs NC on and off. | R |

### E. Engineering and operations
| ID | Problem | Fix | Status |
|---|---|---|---|
| P21 | GPU V\* is slow (~10 min per spec per line) | H1-R400 single line first; the proxy for screening; only 5 specs on the 5-line run | plan |
| P22 | M1/B5 info not logged | `loco`/`proxy` now record the info dict (`train_rows`, `genes_kept_median`, `common_genes`) | ✅ |
| P23 | `final_pipeline.sh` output collision | Every output now carries `_nc<on/off>` | ✅ |
| P24 | Fewer than 2 submissions a day used | One confirmation per day once V\*-R400 picks a change (decision rule E040) | plan |

## 4. Plan

These stages are in `07_RUNBOOK_INSTANCE.md`. Dates are UTC.

| Stage | When | What | Decision / output |
|---|---|---|---|
| **E037** | 16–17 Oct, ~1.5 h | Regime check. Dry-run V\*-R400 eligibility on the panel; build H1-R400 (own targets) and any eligible panel lines; `regime_check.py` on them and on the 5 standard holdouts; `vcc26.detect` thresholds for A/B/C and H1-R400. | Does H1-R400's baseline fid sit near 0.5 and N_conf in the hundreds? If yes, it becomes the primary validator. |
| **E038** | 17 Oct, ~2.5 h GPU | `specs_E038.json` (15 specs) on H1-R400 (and eligible R400 panel lines): emitter null (B0 × balanced/b2/b3), ORACLE × b3, LB references (E021, E032 configs), budget sweep n = 300/600/1,200, B5z2+leak, M1, ENS. Then `specs_E038f.json` on H1-R400-far, plus bootstraps. | (1) Calibration: does it reproduce the leaderboard's E021 → E032 changes (F3), on different targets but in the same regime? (2) Best budget spec vs the LB config (`B5_z2_a0.5_cis5000`, balanced). |
| **E038b** | 17 Oct, ~4 h GPU (after E038) | `specs_E038b.json` on the 5 standard lines with `--match-cells` | A guard: the winner mustn't lose > 0.01 there. |
| **E039** | 17 Oct, CPU, in parallel | Proxy `specs_E039.json` on H1-R400 (+far) and the 5 lines: half-split oracles, `dirprec@k`, common-response conservation (`ORACLE_MEAN` vs `B5_common_only`), B5 common variants, ENS | Direction precision at k → the budget n; whether `common="panel"` is worth a V\* run. |
| **E040** | 17–18 Oct | **Leaderboard:** submit E038's best spec **if** its bootstrap CI lower bound vs the LB config is > 0 on H1-R400 **and** E038b Δ ≥ −0.01. | Expected (estimate): fid −0.29 → about 0 to +0.15; overall about +0.04 to +0.07 (LB ~0.15–0.18). A miss means the validator is wrong; stop and re-diagnose. |
| **E041** | 17 Oct, CPU, 10 min | `scripts/ccle_match.py` on A/B/C | Candidate identities for A/B/C → CUR batch 3 targets, DepMap features |
| E042 | 18–20 Oct | Planning code from E038/E039: per-target budget n_t (P15), confidence-ordered lifting (P4), common response if conserved (P6), platform-aware transfer (P13d), robust lfcs (P7) | H1-R400 sweep, then one LB confirmation per day |
| E043 | 17 Oct → | CUR batch 3 (P19) | `reports/DATA_DONE_batch3.md` |
| Final | 22 Oct → 4 Nov | D/E/F released: `context_id` + `ccle_match` on D/E/F → final pipeline (NC on/off) → first final entry the same day → daily improvements → freeze 4 Nov, deadline 5 Nov 23:59 | `13_EXECUTION_PLAN.md` Phase T |

### Selection rule from now on
1. **Primary:** H1-R400 (and any panel line eligible at R400), plus the far variant. Paired bootstrap; the CI lower bound vs the current LB config must be > 0.
2. **Guard:** the 5-line V\* with `--match-cells` must not lose more than 0.01.
3. **Leaderboard:** confirms only. If the leaderboard and V\*-R400 disagree in sign by more than 0.02, stop and re-diagnose before the next change. The leaderboard is never used to choose parameters.

## 5. Guardrails
- **Information-free gains are out.** The scorer's authors closed two exploits:
  - #348: pinning per-cell sums to farm the MSE noise credit.
  - #351: a leaked gene gate that let a content-free submission gain +0.11.
  
  Our emission only encodes our predictions: which genes change, in which direction, and how much. `de_budget` lifts genes the model predicts to change, in the predicted direction, to a size the test can see. That is a prediction about DE calls, which is what fid scores. If a change ever scores without reading perturbation-specific or context-specific biology, we don't ship it.
- **Considered and not built:** emitting cells whose *distribution shape* triggers the Wilcoxon test with almost no change in mean (e.g. more zeros plus a few high cells). It would decouple DE calls from MSE completely. It still reads our per-target predictions, but it games the test rather than predicting the cells, which is close in spirit to #348. R can overrule; I recommend against.
- No leaderboard tuning (above). iMEMORY is not used in this round. Nothing is uploaded. Box stays read-only.
- Licences: NC data stays tagged; the final is scored with and without it.

## 6. Realistic targets
All of these are estimates, to be replaced by measurements.
- **P1 + P2 alone:** LB about 0.13–0.17.
  - fid rises to about chance: +0.29 scaled, +0.05 overall.
  - Lifting genes to a detectable size costs MSE. The synthetic end-to-end run lost all of B5's MSE gain, but its cells were very shallow (1.5k UMI), so its thresholds were large.
  - At 20k UMI the thresholds are smaller. E038 measures the real trade-off (n 300/600/1,200, cheapest-first `snr` ranking, per-target `frac` budget).
- **Plus direction skill above chance** (dirprec@600 of 0.55–0.6 on held-out lines), the common response and platform-aware transfer: about 0.22–0.30.
- **0.46+ (Illumina):** needs target-specific accuracy (MSE 0.79) that, by inference, comes from perturbation data in or near the test lines. Public data won't give that, unless E041/CUR find close lines with public perturbation data.
- The prize-relevant ranking is on D/E/F, not A/B/C. Fixes to the metric mechanics carry over to new lines; tuning to A/B/C wouldn't.

## 7. Implementation status (16 Oct ~15:00 UTC)

| Item | Code | Test | Runbook |
|---|---|---|---|
| `de_budget` call budget (P1) + `vcc26.detect` thresholds | ✅ `models.de_budget`, `detect.py` | ✅ synthetic: n_pred = n exactly via the scorer's DE; thresholds 100% / 0% at 1.25× / 0.4× | E038 |
| `balanced3` / `balanced2` emitters (P2) | ✅ `emit.py`; `predict_challenge --emit` | ✅ null test (F4) | E038 |
| Per-target emitted cell counts (`--match-cells`) | ✅ `emit.py`, `loco`, `vstar` | ✅ | E038b |
| V\*-R400: `--min-target-cells`, `--umi-target`, `--holdout-tag` (P8/P10) | ✅ `loco`, `vstar`, `proxy` | ✅ synthetic end-to-end | E037 |
| `scripts/regime_check.py` | ✅ | syntax | E037 |
| Lineage/platform tags, `--far` (P11) | ✅ `loco.json`, loco/vstar/proxy | ✅ | E038f |
| Proxy: half-split oracles, `ORACLE_MEAN`, `top50_rep`, `dirprec@k` (P12) | ✅ | ✅ synthetic | E039 |
| B5 `common` response (P6) | ✅ `models.predict_sparse` | ✅ synthetic | E039 |
| ENS model (P13c) | ✅ `models.predict_ensemble` | ✅ | E038 |
| Info logging (P22), pipeline naming (P23) | ✅ | ✅ | – |
| `scripts/ccle_match.py` (P14) | ✅ | ✅ synthetic | E041 |
| Per-target budget n_t (P15), confidence-ordered lifting (P4), robust lfcs (P7), platform-aware transfer (P13d), DepMap features (P13e), platform bias (P18) | ⏳ | | E042 |
| DE-count calibration (C-1) | superseded by `de_budget` | | |
| Expected-score layer (C-2) | ⏳ after E038 | | |

## Sources
- Arc Institute, "The 2026 Virtual Cell Challenge": six lines from different tissues; CRISPRi; 10x Flex on Ultima UG100; zero-shot; perturbations "chosen to provide a strong set of perturbations and responses"; timeline. https://arcinstitute.org/news/virtual-cell-challenge-2026
- Arc Institute, "Behind the Data of the Virtual Cell Challenge" (2025 H1): Flex; dCas9-KRAB dual guide; 300 targets spanning effect sizes; ~1,000 cells/target; >50k UMI. https://arcinstitute.org/news/behind-the-data-virtual-cell-challenge
- Illumina press release, 13 Jan 2026, Billion Cell Atlas. https://www.illumina.com/company/news-center/press-releases/2026/fda84c92-b4b3-4691-a402-35555abe8605.html
- X-Atlas/Orion preprint (Xaira): GEM-X 5′ v3; CRISPRi dCas9-KRAB-ZIM3; HCT116, HEK293T; ~8M cells. https://www.biorxiv.org/content/10.1101/2025.06.11.659105
- `cell_eval2` 0.18.0 (PyPI) source notes:
  - `competition.py`: fid baselines and the #351/#348 measurements;
  - `metrics/direction.py`: fid/reach definitions, P0 = 0.9, reach anchors;
  - `metrics/de.py`: jac val A, nmae returned targets;
  - `de.py`: val A reference-significant pairs;
  - `prep.py`: 138,400 cells, 301 groups;
  - `metrics/discrimination.py`: pds baselines;
  - `configs/vcc2026.yaml`.
