# REPORT blocks E000–E005 — Lambda instance, 14 Oct 2026

Instance: Lambda `gpu_1x_a100_sxm4` (150.136.70.112), Ubuntu 24.04. Runbook: `docs/07_RUNBOOK_INSTANCE.md`.
Raw results: `results/E003/anchors_<ctx>.json`, `results/E004/scores_<ctx>_<mode>_specs_baselines.csv`.
Scores are scaled vcc2026 metrics (0 = mean-response baseline, 1 = replicate); context score = mean of the six.

---

## REPORT E000 — environment + controls inventory

| Item | Finding |
|---|---|
| Per-context control files | `$DATA/challenge/controls/context_A.h5ad`, `context_B.h5ad`, `context_C.h5ad` (from `vcc datasets download controls`, `vcc_2026_controls.zip`). 18,400 control cells each, 46 `ntc_id`s, 18,533 genes, raw integer counts, var_names = gene symbols |
| Gene-name file | `gene_names.csv` **has a header row** (`gene_name`), 18,533 genes. Header-less copy written to `$DATA/challenge/controls/gene_axis.csv` and used everywhere |
| Perturbation list | `pert_counts.csv`, one column `target_gene`, 300 rows (no `n_cells` column → default 400 cells per perturbation). Same 300 targets in A, B and C |
| obs columns / control label | `target_gene`, `context`, `ntc_id`; control label `non-targeting` (`manifest.json`: pert_col `target_gene`, context_col `context`) |
| Median UMIs / cells per context | A 20,150 · B 19,935 · C 20,017 UMIs/cell; 18,400 control cells per context; ground truth 138,400 cells per context (300 × 400 + controls); panel `vcc2026-val-1` |
| `vcc whoami` | team "Rafid Quadir", Immunome AI Biotechnologies, status *ready to submit* |
| GPU | NVIDIA A100-SXM4-40GB. The image had **no NVIDIA driver**: installed `nvidia-driver-595-server` and rebooted. torch must be the cu128 build (cell-eval2[gpu] pins `cupy-cuda12x`; cu132 breaks cupy). Final env: torch 2.11.0+cu128, cell-eval2 0.18.0, DE backend `gpudge` |
| Free disk | 491 GB local (`/`); persistent filesystem `/lambda/nfs/LambdaFilesystem` mounted |

`import cell_eval2, gpudge` works, so `--de-backend pdex` was not needed.

### `vcc prep` contract (`vcc prep --help`, CLI saved in `reports/vcc_help.txt`)
- `vcc prep <in.h5ad> -g gene_axis.csv --perts pert_counts.csv --contexts A,B,C -o out.vcc`
- `-g` must be a **header-less** CSV of the 18,533 gene symbols in order (`--expected-gene-dim 18533`).
- Perturbation column `target_gene` (`-p`, default); context column `context` (`--context-col`, default); NTC label `non-targeting`.
- `--require-counts` (default): X must be raw integer counts (2026 scores in counts space).
- `--check-cell-counts` (default): exactly 400 cells per perturbation per context.
- `--reject-controls` (default): no control cells in the submission.
- `--verify-targets` (default): each context predicts exactly the official 300 targets.
- Caps: ≤ 400,000 cells, ≤ 1,000,000 counts per cell, nnz ≤ scoring hardware limit.

---

## REPORT E001 — pipeline-check leaderboard entry (B1 generic)

Command: `predict_challenge --model B1_generic --summaries pb/K562.npz --n-control 0` (controls omitted because `vcc prep` rejects them), then `vcc prep` → `vcc submit --wait`.
Submissions used on 14 Oct (UTC): **1 of 2**.

| | |
|---|---|
| Entry | `nurtW5XlQHa9XLcPGbdY`, "E001 B1 generic (pipeline check)", submitted 2026-10-14T21:04Z, status published |
| `vcc prep` | passed: 360,000 cells × 18,533 genes, A/B/C = 120,000 each, targets verified, counts preserved |
| **Overall** | **−0.0813** |
| Perturbation discrimination (pds) | 0.0125 |
| Expression accuracy (mse) | 0.0000 |
| DE log-FC accuracy (nmae) | 0.0149 |
| DE direction fidelity (fid) | −0.4533 |
| DE direction reach (reach) | −0.0004 |
| DE significance overlap (jac) | −0.0615 |
| Rank | 1194 at publish, 1192 shortly after |
| Partition / anchors | val, panel `vcc2026-val-1`, anchor set `vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4` |

Interpretation: the pipeline works end to end. Scores sit near the baseline except fid, which is strongly negative: the generic shift is the average K562 *essential-gene* knockdown response, and none of the panel targets is in the essential library (see E002), so its DE directions disagree with the truth. Not used for tuning.

---

## REPORT E002 — public data and summaries

All summaries: `python -m vcc26.pseudobulk ... --gene-axis gene_axis.csv --max-kd 0.7`, output `$DATA/pb/<ctx>.npz`.

| Context | File | Source | Cells | Perts kept | Genes on axis (of 18,533) | Median knockdown | A/B/C targets covered |
|---|---|---|---|---|---|---|---|
| K562 | K562_essential_raw_singlecell_01.h5ad | Replogle 2022, figshare 20029387 | 310,385 | 1952 | 7,940 | 0.17 | 0/300 |
| RPE1 | rpe1_raw_singlecell_01.h5ad | Replogle 2022, figshare 20029387 | 247,914 | 2087 | 8,260 | 0.09 | 0/300 |
| HepG2 | hepg2.h5ad (GSE264667_hepg2_raw_singlecell_01) | Nadig 2025, GEO GSE264667 | 145,473 | 1970 | 9,024 | 0.12 | 0/300 |
| Jurkat | jurkat.h5ad (GSE264667_jurkat_raw_singlecell_01) | Nadig 2025, GEO GSE264667 | 262,956 | 2117 | 8,284 | 0.12 | 0/300 |
| H1 | h1_train_counts.h5ad (from competition_train.h5) | VCC 2025 support set | 221,273 | 149 | 18,077 | 0.06 | 13/300 |
| K562 GWPS | K562_gwps_raw_singlecell_01.h5ad (66 GB) | Replogle 2022, figshare 20029387 | downloaded, **not summarised** | ~9,867 (bulk file) | – | – | **272/300** |

Union of the five summarised sources covers 13/300 A/B/C targets (all from H1).

Inspection notes:
- Replogle/Nadig files: obs `gene` = target symbol, control `non-targeting`, var_names are Ensembl IDs with symbols in var `gene_name`, X raw integer counts. They are expression-filtered by the authors (8.6–9.6k genes), not HVG-only.
- **CHECK genes on axis > 12,000: fails** for K562, RPE1, HepG2, Jurkat (7.9–9.0k) because of that author filtering; passes for H1 (18,077).
- **CHECK median knockdown < 0.4: passes** for all five.
- The four Replogle-library lines contain **none** of the 300 panel targets (the panel avoids essential genes). Only K562 GWPS has substantial overlap.
- HF `arcinstitute/Replogle-Nadig` lists only `.gitattributes`; Nadig raw counts taken from GEO instead.
- VCC 2025 H1: only the training split is public (`storage.googleapis.com/vcc_data_prod/datasets/state/competition_support_set.zip`, 151 perts). X was `log1p(counts)` without depth normalisation; `expm1` recovers integers (max deviation 5e-4), written as `h1_train_counts.h5ad`. The val/test templates contain placeholder values and were not used.
- Script fixes (committed): use `gene_axis.csv`; figshare listing `page_size=100` (was capped at 10, hiding the RPE1 file); single-stream resumable `curl` (aria2 got HTTP 403 on figshare's signed S3 redirect).
- GENCODE v46 TSS table written to `$DATA/tss.csv`.

---

## REPORT E003 — LOCO anchors (mode seen, `specs_B0.json`, gpudge DE)

b = generic baseline, r = replicate (split halves, 5 splits), sd = replicate SD. mse and nmae are errors (lower is better).

| Context | Panel perts | pds b / r (sd) | mse b / r (sd) | fid b / r (sd) | reach b / r (sd) | jac b / r (sd) | nmae b / r (sd) | Run time |
|---|---|---|---|---|---|---|---|---|
| K562 | 300 | 0.500 / 0.923 (0.005) | 0.911 / −0.006 (0.008) | 0.068 / 0.700 (0.015) | 0.168 / 0.928 (0.007) | 0.075 / 0.319 (0.011) | 0.918 / 0.478 (0.015) | 375 s |
| RPE1 | 300 | 0.498 / 0.896 (0.003) | 0.708 / −0.010 (0.007) | 0.292 / 0.773 (0.013) | 0.303 / 0.964 (0.005) | 0.039 / 0.327 (0.006) | 0.815 / 0.488 (0.012) | 62 s* |
| HepG2 | 300 | 0.507 / 0.898 (0.005) | 0.792 / −0.010 (0.008) | 0.135 / 0.704 (0.021) | 0.237 / 0.942 (0.013) | 0.026 / 0.300 (0.010) | 0.862 / 0.516 (0.005) | 334 s |
| Jurkat | 300 | 0.507 / 0.934 (0.002) | 0.885 / −0.028 (0.024) | 0.051 / 0.680 (0.020) | 0.167 / 0.914 (0.009) | 0.065 / 0.280 (0.011) | 0.937 / 0.553 (0.013) | 374 s |
| H1 | 147 | 0.497 / 0.980 (0.005) | 0.957 / 0.003 (0.001) | 0.170 / 0.880 (0.015) | 0.099 / 0.990 (0.004) | 0.008 / 0.428 (0.005) | 0.943 / 0.325 (0.003) | 545 s |

**CHECK: PASS in all five contexts** — pds baseline 0.497–0.507 (within 0.500 ± 0.01); replicate pds 0.896–0.980 (> 0.85); all replicate sd ≤ 0.024 (≤ 0.03); replicate better than baseline on every metric.

\* RPE1 ran out of GPU memory when 4–5 anchor jobs shared the 40 GB GPU and was rerun nearly alone; the other times are with 4–5 concurrent jobs. H1 has 147 panel targets because the VCC 2025 training set has only 149 perts with enough cells.

---

## REPORT E004 / E005 — baselines B0–B3

`specs_baselines.json` (B0 control, B1 generic, B2 transfer α 1.0 and 0.6, B3 = B2 α 1.0 + linear fallback k = 10); held-out context × {seen, unseen}; E003 anchors reused. Sources for each held-out line = the other four lines.

### E004 (seen): context score

| model            |   K562 |   RPE1 |   HepG2 |   Jurkat |     H1 |   mean |
|:-----------------|-------:|-------:|--------:|---------:|-------:|-------:|
| B0_control       | -0.047 | -0.249 |  -0.135 |   -0.064 | -0.071 | -0.113 |
| B1_generic       |  0.062 | -0.174 |   0.019 |    0.067 |  0.079 |  0.011 |
| B2_transfer      |  0.422 |  0.264 |   0.435 |    0.387 |  0.119 |  0.325 |
| B2_transfer_a0.6 |  0.386 |  0.166 |   0.383 |    0.347 |  0.123 |  0.281 |
| B3_linear        |  0.42  |  0.261 |   0.435 |    0.387 |  0.12  |  0.325 |

Per-metric scaled means across contexts (seen):

| model            |    pds |   mse |    fid |   reach |    jac |   nmae |
|:-----------------|-------:|------:|-------:|--------:|-------:|-------:|
| B0_control       | -0.021 |     0 | -0.247 |  -0.176 |  0.052 | -0.288 |
| B1_generic       | -0.013 |     0 |  0.374 |  -0.084 | -0.039 | -0.173 |
| B2_transfer      |  0.744 |     0 |  0.717 |   0.238 |  0.132 |  0.121 |
| B2_transfer_a0.6 |  0.567 |     0 |  0.686 |   0.226 |  0.128 |  0.078 |
| B3_linear        |  0.752 |     0 |  0.712 |   0.234 |  0.129 |  0.121 |

**CHECK B0 < B1: PASS in all contexts.**

### E005 (unseen): context score

| model            |   K562 |   RPE1 |   HepG2 |   Jurkat |     H1 |   mean |
|:-----------------|-------:|-------:|--------:|---------:|-------:|-------:|
| B0_control       | -0.047 | -0.249 |  -0.135 |   -0.064 | -0.071 | -0.113 |
| B1_generic       |  0.061 | -0.158 |   0.001 |    0.059 |  0.08  |  0.008 |
| B2_transfer      |  0.061 | -0.158 |   0.001 |    0.059 |  0.08  |  0.008 |
| B2_transfer_a0.6 |  0.061 | -0.158 |   0.001 |    0.059 |  0.08  |  0.008 |
| B3_linear        |  0.102 | -0.136 |   0.059 |    0.089 |  0.077 |  0.038 |

Per-metric scaled means across contexts (unseen):

| model            |    pds |   mse |    fid |   reach |    jac |   nmae |
|:-----------------|-------:|------:|-------:|--------:|-------:|-------:|
| B0_control       | -0.021 |     0 | -0.247 |  -0.176 |  0.052 | -0.288 |
| B1_generic       | -0.018 |     0 |  0.368 |  -0.082 | -0.042 | -0.175 |
| B2_transfer      | -0.018 |     0 |  0.368 |  -0.082 | -0.042 | -0.175 |
| B2_transfer_a0.6 | -0.018 |     0 |  0.368 |  -0.082 | -0.042 | -0.175 |
| B3_linear        |  0.039 |     0 |  0.409 |  -0.060 | -0.010 | -0.149 |

**CHECK B0 < B1: PASS in all contexts.**

### Notes
- Seen: per-target transfer (B2) beats generic by +0.31 mean context score in every held-out line; α = 0.6 is worse than α = 1.0; the linear fallback changes nothing in seen mode (all panel targets measured).
- Unseen: with panel targets removed from all sources B2 reduces to the generic shift (identical to B1); the linear fallback adds +0.03 mean, helping in 4/5 lines (not H1).
- Scaled mse is 0 for every model (also on the leaderboard): the replicate's raw mse is ≈ 0 and the scale is clamped to [0, 1], so no baseline improves on the anchor.
- Caveat: the Replogle-library lines share the essential-gene library, so "seen" here means transfer between essential-gene knockdowns; the A/B/C panel has no essential genes and only K562 GWPS (272/300) covers it.
- Results appended to `docs/EXPERIMENT_LOG.md`; CSVs and anchors also on `gdrive:VCC2026/logs/`.

---

## Open questions for the planning session
1. K562 GWPS (272/300 panel targets) is downloaded but not summarised or in `loco.json`. Same cell line as K562 essential — how to add it without leakage in LOCO?
2. LOCO "seen" is not representative of A/B/C target coverage (0/300 panel targets in the essential-library lines).
