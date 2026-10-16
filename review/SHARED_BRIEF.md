# SHARED BRIEF: full review of the VCC 2026 effort (16–17 Oct 2026)

Orchestrator: planning session.

Every auditor reads this first. Treat agent reports as **claims to verify**, not conclusions.

## 1. Project context
- **Team.** Immunome AI (Rafid Quadir) is competing in the Arc Institute **Virtual Cell Challenge 2026**.
- **Task.** Zero-shot prediction of CRISPRi knockdown responses for 300 targets in unseen cell lines. The validation contexts are A/B/C, with a live leaderboard (LB). The final test is D/E/F: released 22 Oct, due 5 Nov 23:59 UTC.
- **What we're given per context.** 18,400 non-targeting control cells (raw counts, 18,533 genes on the 10x Flex probe axis) and the 300 target gene names. Submissions are 400 cells per target of raw integer counts, checked by `vcc prep`. Max 2 submissions per UTC day.
- **Scoring** (`cell_eval2` 0.18.0, preset `vcc2026`).
  - Six metrics, each scaled as `(u − b)/(r − b)`, where b is the context mean-response baseline arm and r is the split-half replicate. The context score is their mean; overall is the mean over contexts.
  - The metrics: `pds_cosine`, `expr_mse_unbiased_capped_norm` (clamped to [0,1]), `de_wilcoxon_direction_fidelity_yield_raw` (fid), `de_wilcoxon_direction_reach_raw` (reach), `de_wilcoxon_sig_jaccard` (jac), `de_wilcoxon_lfc_nmae` (floored at −6).
- **Current LB.**
  - Ours: E032 **0.1077** (rank 688).
  - SOTA: #1 Illumina **0.461** (pds .874, mse .787, nmae .419, fid .153, reach .444, jac .088). #2 is about 0.44 (Xaira), #3–5 about 0.32–0.33.
  - The gap is **0.353**, measured on the same LB under the same protocol.
- **Repo:** `/home/claude/vcc`.
  - Code is in `src/vcc26/`, scripts in `scripts/`, plans in `docs/`, agent reports in `reports/`, results in `results/`, model specs in `specs_*.json`, and the source registry in `loco.json`.
  - The installed scorer is at `/usr/local/lib/python3.13/dist-packages/cell_eval2/`. Its source comments record measurements on the official val bundles; cite them as evidence.
- **What we can and can't run.**
  - The instance data (`$DATA` = `/lambda/nfs/LambdaFilesystem/vcc-data`) is **not reachable** from here; only the repo and the installed scorer are.
  - Synthetic experiments are allowed in your own scratch directory: `/tmp/claude-0/-home-claude/262e3074-1c21-59b7-85fd-709b892ecec9/scratchpad/<your letter>/`. Use `PYTHONPATH=/home/claude/vcc/src`, CPU only; the `scanpy` DE backend is slow, so keep problems small.
  - **Do not edit anything under `src/`, `scripts/`, `docs/`, `specs_*`, `loco*.json`.** Write only your findings file.

## 2. File inventory (one line each)
**Core code (`src/vcc26/`)**
- `pseudobulk.py`: builds per-context summaries (`pb/*.npz`) of per-target pseudobulk CPM and log2FC (pseudocount 1 CPM) and knockdown; `--strata-col` gives composition-matched controls (D7); `--layer` now reads lazily (batch 3).
- `loco.py`: leave-one-context-out runner.
  - `prepare_holdout` builds a challenge-shaped truth: up to 300 targets, ≤ 400 cells each, ≤ 18,400 controls, filtered by summary `ncells` and `kd ≤ 0.7`.
  - New options: `--min-target-cells`, `--umi-target` (binomial thinning), `--holdout-tag`, `--match-cells`, `--far`.
  - Scores with `local_eval` and writes `scores_*.csv` and `pertarget_*.parquet`.
- `vstar.py`: V\* runs `loco` over every line with ≥ 100 panel targets.
- `local_eval.py`: local scaled score. **`build_anchors` builds b with `cell_eval2.build_generic_baseline(real, config)` (default emit = dispersed)** and r from 5 split halves.
- `emit.py`: turns predicted log2FC into cells.
  - `random`: per-target resample with thinning/Poisson.
  - `balanced`: herded shared base with exact per-gene totals; **LB emitter since E021**.
  - `balanced2`: random base; genes with \|lfc\| ≤ 1e-3 untouched.
  - `balanced3`: random base with exact totals.
- `models.py`:
  - B0 control, B1 generic, B2 transfer (E021 config `B2_raw_gPL`);
  - B4 consensus (retired);
  - **B5 sparse consensus** (LB config `B5_z2_a0.5_cis5000`), with the new `common` option;
  - `de_budget` post-processing (lift top-n genes to Wilcoxon-detectable size), the ENS ensemble, `apply_post`.
- `translator.py`: M1 gradient-boosted translator, trained by rotating source lines.
- `detect.py`: per-gene Wilcoxon detection thresholds for a context.
- `proxy.py`: fast pseudobulk proxy metrics: half-split oracles, `dirprec@k`, `top50_rep`.
- `compare.py`: paired bootstrap over targets.
- `predict_challenge.py`: builds the A/B/C/D/E/F submission h5ad.
- `context_id.py`: control-profile similarity of a context to the sources.
- `neighbors.py`: CRISPRi cis-neighbour pairs.

**Scripts**
- `scripts/final_pipeline.sh`: context_id, predict and `vcc prep` for D/E/F (no submit).
- `scripts/regime_check.py`: truth shape (N_conf) and anchors against official numbers.
- `scripts/ccle_match.py`: DepMap/CCLE identity match.
- `scripts/pick_specs.py`: proxy-based shortlist.
- `scripts/make_subset.py`: builds holdout subsets.
- `scripts/convert_*.py`: dataset converters.

**Registry and specs**
- `loco.json`: 13 source contexts with fields line, library, lineage, platform, licence. Orion is NC-licensed.
- `loco_candidates.json`: A549 CRISPR-KO, opt-in only.
- `specs_E0xx.json`: model specs per experiment.

**Docs and reports**
- `docs/07_RUNBOOK_INSTANCE.md`: runbook for the instance agent.
- `docs/12`, `14`, `15`: diagnoses rounds 1–3.
- `docs/EXPERIMENT_LOG.md`: experiment log.
- Reports:
  - `reports/REPORTS_E0xx_*.md` (agent REPORT blocks), `DATA_DONE*.md` (curation);
  - `E041_ccle_match.json`;
  - `results/E0xx/` (CSVs and parquet of per-target metrics);
  - `results/E033_E0{21,32}_status.json` (official LB status JSONs).

## 3. Experiment timeline (LB = leaderboard; V\* = local leave-one-line-out)
| run | date | commit (report) | config | data | metric | changed vs previous |
|---|---|---|---|---|---|---|
| E001 | 14 Oct | 2ae1640 | B1 generic shift (K562 essential), random emit | K562 essential | **LB −0.081** (fid −0.453) | first entry |
| E003–E005 | 14 Oct | 2ae1640 | LOCO anchors and B0–B3 | Replogle K562/RPE1, Nadig HepG2/Jurkat, H1 | local | – |
| E011/E012 | 15 Oct | 33be04c | B2_transfer, random emit, 6 summaries | + K562_GWPS | **LB 0.069** (fid −0.014) | transfer instead of generic |
| E020/E021 | 15 Oct | ddb1623 | `B2_raw_gPL`, **balanced** emit, 11 summaries | + CD4T×3, KOLF, HipSci, H1 rebuilt | V\* 0.167 (3 lines); **LB 0.106** | emitter, data |
| E025/E026 | 16 Oct | 7c35759, 6fdc1f7 | B4 consensus | + D7 composition-matched summaries | proxy/V\*; B4 retired | – |
| E030/E031 | 16 Oct | 64f733c, e51859f | B5 sparse; 5-line V\* | + Orion HCT116/HEK293T (NC) | V\* 0.263 vs E021 0.234 (CI +0.011..+0.039) | model |
| **E032** | 16 Oct | ffbad3e (report); code 58ca775/b532b79 | **`B5_z2_a0.5_cis5000`, balanced, 13 summaries** (`specs_E031.json`) | 13 `pb/*.npz` (unhashed) | **LB 0.1077** (pds .583 mse .144 nmae .111 fid −.293 reach .102 jac .000) | model; LB entry `n0phFb0FI8GRgERAALGD` |
| E034 | 16 Oct | bfe98a3 | M1 translator | same | V\* 0.240 (< B5) | – |
| E035/E036 | 16 Oct | 3ac92b3 | NC on/off; dress rehearsal | same | NC +0.015; pipeline OK | – |
| E037 | 16 Oct | 6d6f462, 9ea55c5 | regime check (H1-R400 on its own targets, 400 cells, 20k UMI) | `subsets/H1.h5ad` **rebuilt** (400/target; old file kept as `H1_cap100`) | baseline fid 0.030 vs official 0.51 → stopped | validator |
| E041 | 16 Oct | eec1a37 | CCLE match | DepMap 24Q4 | A = Jurkat, B = HeLa, C = CAL-33 | – |
| Batch 3 | 16 Oct | 3919854, dde5802 | curation | A549_KO candidate; DepMap mutations | – | – |

**Planned but not run:** E038/E038b/E039/E040 (call budget, emitter null, proxy diagnostics, LB).

**Traceability (O-03).** E032's code and spec can be reconstructed. The 13 summaries have no recorded hash, and the stored `$DATA/preds/E032.vcc` has not been checked for reproducibility. No LB config has ever had its seed variance measured.

## 4. Baseline numbers
- **Trustworthy:** the LB values (official scorer, status JSONs `results/E033_E0*_status.json`): E032 0.1077, E021 0.1060. Gap to SOTA 0.353.
- **Untrustworthy (O-01, P0):** every local scaled V\*/E0xx score for the DE metrics (fid, jac, reach) and MSE, because the local baseline anchor is built differently from the official one (below). Local *raw* metric values are fine; local *scaled* values and selection scores are not.
- **Seed variance:** unmeasured. The V\* paired-bootstrap 90% CI half-width is about 0.015 (target resampling only).

## 5. Eval-integrity findings already confirmed by the orchestrator (don't re-find these)
- **O-01 (P0, VERIFIED): the local baseline arm ≠ the official baseline arm.**
  - The official val bundles' baseline arm has **identical cells**. `competition.py` L304–305: "the baseline arm's cells are identical so its `jk_pred` is exactly 0". That is `emit="tile"`: every emitted cell equals the context mean profile.
  - `local_eval.build_anchors` calls `build_generic_baseline` with the library default `emit="dispersed"` (resampled, scaled control cells).
  - Consistent evidence:
    - official baseline fid 0.506/0.523/0.509 is the "theoretical random point" (`catalog.py` L598–613), reached when every gene is called;
    - official baseline jac (val A 0.0333) ≈ mean N_conf ÷ gated genes (335.9 / ~9,930 = 0.034), the value an all-genes-called arm gets;
    - official baseline reach (val A 0.042) "already sits at the no-skill point" (`metrics/direction.py` L970–972);
    - the stored context_mean arms are "95.3–95.6% fractional", which fits tile cells stored sparse next to integer control rows, not dispersed cells (~87%) (`prep.py` L170–178);
    - a rebuild through the library's default path "reads smaller" than the stored arms (`prep.py` L186–189).
  - Local H1-R400 (E037): baseline fid 0.030, jac 0.012, reach 0.096.
    - **Synthetic test (orchestrator, run):** 40 targets × 400 cells, 4,000 controls, 2,000 genes, scorer's own `build_generic_baseline`:
      - tile: fid **0.576**, jac **0.0493** (= mean N_conf/universe 0.0493 exactly), reach 0.043, pds 0.500;
      - dispersed: fid 0.004, jac 0.000, reach 0.067, pds 0.540.
    - **Fix applied in the working tree (not yet pushed):** `local_eval.build_anchors(..., emit="tile")` is now the default; `loco` moves old dispersed anchors to `anchors_dispersed.json` and rebuilds; `scripts/rescale_rows.py` re-scales stored rows with the new anchors.
  - **Consequence:** local scaled fid/jac/reach/mse are on the wrong scale, which explains why V\* forecast fid −0.04 for E021 → E032 while the LB gave −0.23.
- **O-02 (VERIFIED): the per-metric scoring policies match.** Clamps in `local_eval.CLAMP` (mse [0,1], nmae ≥ −6, the others unclamped) match the scorer's catalog policies (pds/fid/reach/jac `metric_min=0`, no clamp; mse clamp [0,1]; nmae `clamp_low=-6`). Aggregation (mean of six, mean over contexts) matches the LB values backed out from E021/E032.
- **O-03 (P0 traceability):** see §3.
- **O-04 (VERIFIED): fid definition.** `match = in_denom & committed & sign(lfc_pred)==sign(lfc_real)`, with `in_denom = lfc_real non-zero (any significance)`, and `fid = k/max(n_pred, N_conf)`. When **N_conf = 0**, fid = 1 if n_pred = 0, else 0 (`metrics/direction.py` L735–760). jac(∅,∅) = 1 (`metrics/de.py` ~L215).
- **O-05 (VERIFIED): the nmae gate** drops targets with fewer than 10 real-significant genes (`metrics/de.py` `min_gate_size=10`). It returns 272/229/218 of 300 targets on val A/B/C, so **28/71/82 targets have N_conf < 10**: B and C have many weak or no-response targets. Val A's minimum N_conf is 4.
- **O-06 (VERIFIED by agent artefacts):** the H1-R400 truth now matches A/B/C on cells (400), depth (20k UMI) and controls (18,400). Its N_conf mean is 855 (val A 336) and median 135.5.

## 6. Open suspicions to pursue (per auditor)
- **A, data and splits:**
  - truth selection biases in `prepare_holdout` (`kd ≤ 0.7` and ncells filters drop weak-knockdown and weak targets, which A/B/C keep);
  - same-line and lineage leakage;
  - gene-axis mapping (symbols, duplicates, Flex probe set vs 3′ genes);
  - D7 strata controls;
  - the H1 subset rebuild (controls from train only, cells pooled across 2025 splits);
  - CD4T donor D4 only;
  - whether V\* targets are representative of the panel;
  - A549_KO (KO vs CRISPRi), Song Jurkat;
  - coverage claims (300/300 ≥ 2 lines).
- **B, training and inference engineering:**
  - emitter correctness (balanced/b2/b3; sum-exact rounding; library; shared base across targets → common-mode artefacts in pds/MSE);
  - `predict_challenge` gene/target alignment and integer validity;
  - B5 numerical path (pc, `_noise_var`, Birge), `de_budget` and `detect` approximations;
  - `local_eval` anchors (O-01) and replicate construction;
  - compare/bootstrap correctness, determinism and seeds;
  - the proxy's fidelity to the real metric;
  - whether **target-expression gating** is applied anywhere in the LB config.
- **C, biology and modelling assumptions:**
  - A = Jurkat, B = HeLa, C = CAL-33 (TP53/HPV status, what they express);
  - **CRISPRi of a target not expressed in the context does nothing.** Are panel targets expressed in A/B/C controls (we have those cells)? N_conf = 0 targets reward predicting nothing (fid = jac = 1);
  - platform (Flex probes vs 3′/5′);
  - common versus target-specific response;
  - knockdown strength;
  - compositional/CPM artefacts;
  - whether cross-line transfer of target-specific responses is a sound premise at all, and what else carries signal (paralog compensation, pathway membership, DepMap co-essentiality, target expression level).
- **D, runbook-agent behaviour:**
  - report fidelity versus artefacts (numbers in reports vs CSVs/JSONs in `results/`);
  - undocumented changes (H1 subset rebuild "approved by R");
  - stop/continue decisions;
  - any LB submission outside the runbook rules;
  - data changes on shared files;
  - whether the agent ran anything not in the runbook;
  - commit hygiene (data or secrets in git);
  - whether its diagnoses were right (E037: "local baseline under-calls" ⇒ checked as O-01);
  - claims of "approved by R".

## 7. FINDING SCHEMA (all auditors use this, one block per finding, in `review/findings_<letter>.md`)
```
- id: [A|B|C|D|R|O]-NN
  class: Eval | Data | Engineering | Biology | Method | Agent | Other
  title: one line
  severity: P0 (invalidates results / blocks progress) | P1 (large drag on metric) | P2 (moderate drag or risk) | P3 (minor/hygiene)
  confidence: VERIFIED | LIKELY | SUSPECTED, plus a percentage
  impact: estimated effect on the primary metric (LB overall), number or range, labelled measured / bounded / estimated
  evidence: file paths with line numbers, commits, run IDs, log excerpts, commands run and their output
  mechanism: why this hurts the score, causally
  confirm: the exact check to confirm, if not VERIFIED
  fix: recommended fix, and how to verify that it worked
  effort: hours | days | weeks
  depends_on: other finding IDs that must be fixed first
  seams: related issues outside this auditor's scope
```
Rules:
- VERIFIED needs an inspected artefact or an executed check, and its output quoted.
- Put speculation in a final "Open questions" section, not in the register.
- Quantify impact and label how you got the number.
