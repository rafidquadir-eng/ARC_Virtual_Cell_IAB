# Build plan: from 0.069 to the top of the leaderboard

Written 15 Oct 2026 ~03:30 UTC (Wed 14 Oct 23:30 ET). It expands `10_PLAN_TO_TOP.md` (strategy) into what gets built, by whom, in what order, and how each piece is accepted or dropped.

- **Deadlines:** test contexts D/E/F released **Thu 22 Oct**; last final entry **Thu 5 Nov 23:59 UTC**; our freeze is **Wed 4 Nov**.
- **Current state:** leaderboard 0.069 (rank 827) with per-target transfer from K562 GWPS and the random emitter. #1 is Illumina AI at 0.461; #2–#5 at ~0.33.

## 0. Who does what

| Role | Where | Does |
|---|---|---|
| **Curation agent** | Claude Code on the instance, tmux `data`, prompt `docs/09` | Phase D: all datasets, summaries, holdout subsets, `loco.json` entries, prior-knowledge resources (D5) |
| **Runbook agent** | Claude Code on the instance, tmux `cc`, `docs/07` | runs every experiment stage, pushes REPORT blocks and CSVs, makes at most 1 leaderboard entry/day (2 allowed) |
| **Planning session** (this chat) | cloud | writes all new code, spec files and runbook stages; reads results; decides |
| **Rafid** | — | relays between agents; launches/terminates instances; decisions (Xaira, counsel, launch requests) |

**Status 15 Oct ~03:30 UTC:** runbook stages E013–E017 are **paused** until the curation agent reports that every first-batch dataset is in (Phase D done). The first stage after that is **E020** (§3).

## 1. Conventions every piece follows

- **Code:** `src/vcc26/<module>.py`, one CLI per module. Spec files at repo root: `specs_E0xx.json`. Results: `results/E0xx/` (small CSV/JSON only). Reports: `reports/REPORTS_E0xx_E0yy.md`.
- **Data products:**
  - `$DATA/pb/<name>.npz`: pseudobulk summary, created by `vcc26.pseudobulk`;
  - `$DATA/subsets/<name>.h5ad`: holdout-ready cells, raw counts, obs `target`;
  - `loco.json`: the registry. Every entry has `name`, `line`, `library` ∈ {`essential`, `genome_wide`, `targeted`}, `h5ad`, `pert_col`, `control`, `symbol_col`, `summary`.
- **Same-line rule:** datasets sharing a `line` never act as source and held-out line for each other. Enforced in `loco.run`.
- **Selection metric = V\*** (§3). Pre-registered; weights never change after results are seen.
- **Adoption rule:** a change is adopted if it raises V\* by ≥ 0.01 *and* doesn't lower any single held-out line by more than 0.03. Once E-4 exists, the paired bootstrap 90% CI must also exclude 0.
- **Leaderboard:** confirmation only. At most one entry per UTC day from this plan, never used to choose between variants.
- **Secrets / Box / iMEMORY rules:** as in `CLAUDE.md`. Never relaxed.

## 2. Phase D — data completion (curation agent; in progress)

| ID | Task | Done when |
|---|---|---|
| D1 | Finish the first batch: full H1 2025 (done), CD4⁺ T cells, KOLF iPSC, any other catalog row with ≥ 20 panel targets outside K562 | each row in `reports/data_ingest.csv` |
| D2 | Per dataset: validate raw integer counts, gene count, control label, knockdown; build `$DATA/pb/<name>.npz` (`--max-kd 0.7` for CRISPRi only) and `$DATA/subsets/<name>.h5ad` | files exist; summary line printed |
| D3 | Register in `loco.json` with `line` and `library`. **Fold H1 val+test into the existing `H1` entry** (one H1 summary of all ~300 perts) rather than a new name. Add `library` to the existing entries: K562/RPE1/HepG2/Jurkat = `essential`, K562_GWPS = `genome_wide`, H1 = `targeted` | `python -m vcc26.vstar --dry-run` lists the new lines |
| D4 | QC table per dataset: cells, perts, panel targets measured (≥ 50 cells), genes on axis, median UMI, median knockdown, controls; plus a **panel coverage table**: for each of the 300 targets, the lines that measured it | `reports/data_qc.md` |
| D5 | Prior-knowledge resources to `$DATA/priors/` with licences recorded (see below) | `reports/priors.md` |
| D6 | **Data-done signal:** write `reports/DATA_DONE.md` (what's in, what's blocked, coverage numbers), commit, push | file in repo |

**D5 priors** (each licence checked for commercial use before download; anything unclear is listed, not fetched):

| Resource | Use | Expected licence (verify) |
|---|---|---|
| STRING v12 human links + detailed scores | gene graph for the prior encoder | CC BY 4.0 |
| GO annotations (human GAF) + ontology | gene graph / features | CC BY 4.0 |
| UniProt human reference proteome sequences | input to ESM-2 embeddings (computed by us on the GPU) | CC BY 4.0 |
| ESM-2 weights (`esm2_t33_650M_UR50D`) | protein embeddings | MIT |
| DepMap public CRISPR gene effect (Chronos) | co-dependency features | CC BY 4.0 |
| Reactome pathways (human) | gene sets | CC0 / CC BY |
| A TF→target regulatory network (e.g. CollecTRI) | directed edges | **check** |
| GENCODE v46 (already have `tss.csv`) | neighbour silencing, gene positions | open |

## 3. Phase E — evaluation infrastructure (planning session builds; runbook agent runs)

| ID | Piece | File | Status |
|---|---|---|---|
| E-1 | **V\* runner.** Every line with ≥ 100 panel targets measured (≥ 50 cells) is held out in turn. Its panel is the challenge targets it measured; sources are all other lines. When several datasets share a line, the one with the most panel targets is held out. Outputs per-line rows and a summary (selection = mean context score over held-out lines, plus the worst line). `--mode unseen` drops the panel targets from every source, which measures unmeasured-target performance. | `vcc26/vstar.py` | **done** (tested on synthetic) |
| E-2 | Balanced emitter + ORACLE ceiling | `vcc26/emit.py`, `loco.py` | done |
| E-3 | A/B/C (later D/E/F) identity | `vcc26/context_id.py` | done |
| E-4 | **Paired bootstrap over targets.** Return per-target raw metrics from `local_eval.score` and bootstrap the difference between two specs (MSE recomputed as the ratio of sums). Gives the CI in the adoption rule. | `vcc26/local_eval.py`, `vcc26/compare.py` | to build (16 Oct) |
| E-5 | Result collation: one table across experiments from `results/*/vstar_summary_*.csv` | `scripts/collate.py` | to build |
| E-6 | **Simulated-truth harness** for C-2. Draw truth effects from a predictive distribution, emit "true" cells with the *random* emitter from the context's real controls (real measurement noise), and build anchors for the simulated truth. | `vcc26/simtruth.py` | to build (19 Oct) |

**E020** (first stage after Phase D) runs V\* in both modes with `specs_E020.json`: ORACLE ×2 emitters, B1, B1 panel-like generic, B2 random (the E012 config), B2 balanced, raw + panel-like generic, denoise, β 1.3/1.6, A1, linear fallback. It answers three questions at once: is the emitter the MSE problem, how much does multi-line transfer give, and what's the new baseline. **E021** is the leaderboard confirmation of E020's winner. E013/E015 are folded into E020; E016 runs alongside.

## 4. Phase B — strongest non-learned baseline (16 Oct)

> **15 Oct update:** `12_DIAGNOSIS.md` puts B4 (noise-aware consensus, E025–E027) and the D7 data fixes ahead of B-3…B-5. Baseline-1 is now the best of B4 and the earlier B rows.


| ID | What | Spec / code | Accept |
|---|---|---|---|
| B-1 | Emitter: balanced vs random, from the ORACLE and B2 rows of E020 | E020 | ORACLE-balanced > ORACLE-random on MSE/NMAE/REACH |
| B-2 | Multi-line transfer: raw + panel-like generic + denoise; A1 similarity weighting across ≥ 5 lines | E020 | best V\* row becomes **Baseline-1** |
| B-3 | Grid over β (1.0–2.0), denoise floor, and A1's similarity temperature `tau` | `specs_E022.json` | adoption rule |
| B-4 | **Co-variation projection (WP9):** project each predicted effect onto the top-k PCs of the *target context's* control cells and blend `λ·proj + (1−λ)·raw`; k ∈ {50, 200, 1000}, λ ∈ {0.5, 1} | new `models.project_ctrl_basis`, `specs_E023.json` | adoption rule |
| B-5 | Neighbour silencing (A2, built earlier) on top of Baseline-1 | `specs_E024.json` | adoption rule |

**Baseline-1** = best of B-1…B-5 → leaderboard confirmation (one entry).

## 5. Phase M — the learned model (16–21 Oct)

### M-0 Training tables (`vcc26/dataset.py`, 16 Oct)
One **example** = (target *t*, line *L*). For every registered dataset and every measured target (≥ 25 cells):
- **Label** `y_{t,L}`: log2FC on the output gene set (genes measured in ≥ 2 lines, about 8–10k), plus a mask of genes valid in *L* (`present` and control CPM > 5), a per-gene noise variance (from cell counts, depth and Poisson/NB approximations), and **two half-split labels** (cells split at random into halves A/B, K = 4 splits stored as float16) for noise2noise augmentation.
- **Context** of *L*: control log-CPM vector, the top 64 PCs of its control cells, library-size stats, and a 256-cell control sample (for the set encoder, M-2b).
- **Evidence** for (*t*, *L*): the target's measured log2FC in every *other* line (same-line datasets excluded), each with that line's context vector, cell count and noise.
- **Target features**: target expression in *L*'s controls and in each evidence line, knockdown achieved in evidence lines, and the number of DE genes in evidence lines.
- **Storage:** `$DATA/train/` as memory-mapped arrays plus a parquet index. Expected size is a few GB.

### M-1 Translator v1: gradient-boosted, per gene (`vcc26/translator_gbm.py`, 16–17 Oct)
- **Rows:** (*t*, *L*, gene *g*), subsampled to about 50M, with weights ∝ 1/(noise + τ).
- **Features:**
  - evidence lfc at *g* (noise-weighted mean, nearest line by control similarity, min/max, number of lines, agreement);
  - *g*'s control CPM in *L* and in the evidence lines, and their log-ratio;
  - target expression in *L* versus the evidence lines;
  - *t*–*g* prior relations (STRING score, shared GO, ESM-2 cosine, DepMap correlation);
  - *g*'s typical response amplitude.
- **Model:** LightGBM on the GPU. Leave-one-line-out folds match V\*.
- **Output:** a model that maps evidence to the predicted lfc in *L*; plugs into `models.MODELS["M1_gbm"]`.
- **Accept:** ≥ +0.02 V\* over Baseline-1. Also check that it *never* loses on lines with ≥ 3 evidence lines (where pooling should be hard to beat).

### M-2 Model v2: context-conditioned response model (`vcc26/model_v2/`, 17–21 Oct)
Architecture (PyTorch, a few million parameters, trains on the current A100):
1. **Gene embeddings** `e_g` (dim 256): learned, initialised from the best M-4 prior encoder.
2. **Context encoder** `c_L` (dim 256): MLP on the control log-CPM PCs. In variant M-2b, a set-attention encoder over 256 sampled control cells.
3. **Context-conditioned gene programs:** `V_L = f(e_g, c_L, ctrlCPM_L(g)) ∈ R^{G×K}` with K = 128 (shared MLP per gene, so it's linear in G).
4. **Evidence encoder:** each evidence line's lfc is projected onto that line's programs `V_{L'}`, giving coordinates `a_{L'} ∈ R^K` (masked least squares). These are tagged with `c_{L'}`, cell count and noise, and pooled with attention over lines, queried by `c_L`.
5. **Prior encoder** for target *t*: GNN over the gene graph (STRING + GO + TF edges) → `z_t`. Variants: GraphSAGE, GAT, and an **iMEMORY-style heterogeneous GAT** (gene/pathway/GO node types). This path carries the targets with no evidence.
6. **Target code** `u_{t,L} = MLP([pooled evidence, z_t, c_L, target expression in L, has-evidence flag])`.
7. **Prediction:** `ŷ_{t,L} = V_L u_{t,L}`, plus a per-gene log-variance head (uncertainty for C-2).

Training:
- **Losses:** noise-weighted masked MSE on lfc; **InfoNCE across targets within a line** (cosine of predicted vs measured effect, temperature-tuned), which mirrors PDS; BCE on sign for genes that are significant in the label; Gaussian NLL for the variance head.
- **Augmentation:** half-split labels (noise2noise); random evidence dropout (drop all evidence for 20% of examples to train the prior path, keep 1 line for 30%); random line dropout.
- **Regime:** leave-one-line-out (V\* folds) for selection; the final model is trained on all lines. Ensemble of 5 seeds.
- **Ablations, each a spec row:**
  - without context conditioning (`V` shared across lines);
  - without the prior path;
  - each prior encoder alone;
  - without InfoNCE;
  - set encoder (M-2b) vs PCs.
- **Accept:** ≥ +0.02 V\* over the best of Baseline-1/M-1; V\*-unseen above the kNN-prior baseline (M-4).

### M-3 Ensembling (21 Oct)
Weighted average of the lfc predictions from Baseline-1, M-1 and M-2, with weights fitted on V\* out-of-fold predictions (non-negative, sum to 1).

### M-4 Prior encoders for unmeasured targets (17–18 Oct)
- **Task:** predict a target's response in K562 GWPS from its graph/embedding neighbours' responses (kNN/ridge), with 10-fold CV over targets, plus V\*-unseen.
- **Encoders:**
  - STRING spectral/node2vec;
  - GO SVD;
  - ESM-2 mean embedding;
  - DepMap co-dependency profile;
  - gene-summary text embedding (open model);
  - a GNN trained on our data;
  - the iMEMORY-style HetGAT (trained from scratch here; the original weights and gene table aren't needed).
- **Control:** every encoder is compared with a **shuffled control** (permuted gene labels). An encoder is kept only if it beats its shuffle by a clear margin. The winner initialises M-2.

## 6. Phase C — calibration and expected-score optimisation (19–21 Oct)

| ID | What | Detail | Accept |
|---|---|---|---|
| C-1 | **DE-count calibration** | Predict, per (*t*, *L*), how many genes the truth will call significant, from the evidence lines' call counts rescaled to 400 cells × ~20k UMI (a power calculation per gene) and the predicted effect norm. Then set a per-target scale β_t so the emitted cells' Wilcoxon calls hit that count. Fast check: approximate Mann–Whitney z from the emitted means/variances; exact check on the GPU for the final value. | V\* FID/JAC/REACH up, total V\* up ≥ 0.01 |
| C-2 | **Expected-score optimiser** | For each context, draw S = 20–50 truths from the model's predictive distribution (M-2 variance head + ensemble spread, calibrated on V\* residuals) and simulate measurement with E-6. Score candidate submissions with the official cell-eval2 against those simulated truths, and pick the parameters (global β, confidence-based shrinkage, DE-count targeting strength, projection λ) that maximise the mean score. Coordinate search, about 100 candidates × S per context. | the optimiser, run on V\* lines *without* access to their truth, raises their real V\* by ≥ 0.02 |
| C-3 | Emission refinements | Only if C-1/C-2 show a need, e.g. per-gene dispersion change for strongly down-regulated genes, or library-size shifts | adoption rule |

**Compute note:** C-2 runs cell-eval2 thousands of times, a few hours per context on one A100. If it becomes the bottleneck I'll send a LAUNCH REQUEST for a second GPU instance for 2–3 days (~$100–150 on an A100; numbers in the request).

## 7. Phase T — final test (22 Oct → 4 Nov)

| Date | Step |
|---|---|
| 21 Oct | **Dress rehearsal:** run the full final pipeline (context-id → model ensemble → C-1/C-2 → `vcc prep`) on A/B/C as if they were unknown; timing and failure log |
| 22 Oct | D/E/F released: `vcc datasets download` → `context_id` (E016 on D/E/F) → pipeline → **first final entry the same day** (insurance) |
| 23 Oct – 3 Nov | improvements that win on V\* only; refresh the final entry at most once a day, only on a V\* win (≤ 2/day allowed) |
| 4 Nov | **freeze**: final entry = best V\* configuration; checks (counts ≤ 1e6/cell, 400 cells × 300 targets × 3 contexts, no controls, `vcc prep` passes) |
| 5 Nov | buffer only; no changes unless the 4 Nov entry failed |

Validation-phase leaderboard entries (A/B/C) stop mattering on 22 Oct. Before then, use them only as one confirmation per day.

## 8. Experiment calendar (IDs reserved)

| IDs | When | What |
|---|---|---|
| E016, E020, E021 | right after D6 | identity; V\* baselines + emitter; leaderboard confirmation |
| E022–E024 | 16 Oct | β/denoise/τ grid; control-basis projection; neighbour silencing |
| E030–E032 | 16–17 Oct | M-1 GBM translator (folds, ablations, final) |
| E040–E042 | 17–18 Oct | M-4 prior encoders vs shuffles; V\*-unseen |
| E050–E056 | 17–21 Oct | M-2 model v2 and ablations; ensemble M-3 |
| E060–E063 | 19–21 Oct | C-1 DE calibration; C-2 optimiser (E-6 harness first) |
| E070 | 21 Oct | dress rehearsal on A/B/C |
| E080+ | 22 Oct → | final pipeline on D/E/F |

## 9. Compute and budget

- **Now:** one `gpu_1x_a100_sxm4` (~$1.99/h) and Drive for raw data. Spend so far is about $20.
- **Likely additions:**
  - a second A100 for C-2 (~19–22 Oct, ~$150);
  - possibly one H100 for M-2b set-attention (~$4.29/h × 24 h ≈ $100).
- **Expected total < $1,500 of $7,000.** Warnings at 50/75/90% as before. Terminate idle instances; the filesystem keeps the data.

## 10. Risks and how we handle them

| Risk | Handling |
|---|---|
| V\* is noisy (few lines, ~100–300 targets each) | E-4 bootstrap CIs; the worst-line check; prefer changes that win on every line |
| D/E/F are unlike every line we have | context_id on 22 Oct; C-2's uncertainty-aware defaults shrink toward safe predictions when the context is far from all sources |
| The model learns quirks of a line's library (essential vs genome-wide) | `library` tag as a feature; same-line exclusion; V\* held-out lines span libraries |
| Leakage | held-out lines contribute only control cells to the model at evaluation; same-line datasets excluded; any target-level information from the held-out line is banned |
| Licences | D5 records the licence per resource; non-commercial resources stay out (State/Stack weights, X-Atlas/Orion without permission) |
| **IP (iMEMORY)** | an iMEMORY-style encoder is used only if it wins M-4/M-2. Even then, **counsel decides before 5 Nov** whether it can be in the final entry, because Arc publishes finalists' high-level method descriptions and the patent isn't filed. Fallback: the best non-iMEMORY encoder |
| Time | each phase has a no-learning fallback (Baseline-1 + C-2) that can be submitted on 22 Oct regardless |

## 11. What "done" looks like

The final entry is the M-3 ensemble, or Baseline-1 if the learned models don't clear their acceptance bars, plus C-1/C-2, with a documented V\* score and per-line breakdown, its reproducible command in `docs/07`, and the experiment log complete.
