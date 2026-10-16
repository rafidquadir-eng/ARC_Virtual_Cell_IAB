# REPORT blocks E037–E041 — Lambda instance, 16 Oct 2026

Runbook: `docs/07_RUNBOOK_INSTANCE.md` (E037–E041, commit e8f30cf); diagnosis `docs/15_DIAGNOSIS_ROUND3.md` §0.

---

## REPORT E037 — can a validation line match the A/B/C DE regime?

**E037a** (`vstar ... --min-target-cells 400 --umi-target 20000 --holdout-tag R400 --dry-run`): eligible R400 lines = **[CD4T_Stim48hr (174 panel targets)] only. H1 is missing.**
Check as the runbook asks: `pb/H1.npz` has 299 targets, 254 with ≥ 400 cells, but only **20 panel targets with ≥ 400 cells** (25 in total), so it's below the 100-target cut. That's expected,
and E037b holds H1 out on its own targets. Thresholds were not changed.

**E037b:** `loco --holdout H1 ... --holdout-tag R400 --min-target-cells 400 --umi-target 20000` → 254 H1 targets, 253 measured in ≥ 1 source; UMIs thinned by 0.369
to a median of 20,000/cell. `vstar` built CD4T_Stim48hr_R400 (174 targets, all covered). B0 scored in both.

**E037c regime check** (`scripts/regime_check.py`; official val A/B/C: 400 cells/target, 18,400 controls, ~20k UMI, N_conf mean 335.9 (val A), baseline fid 0.506 / 0.523 / 0.509,
baseline pds 0.53 / 0.53 / 0.51, baseline jac 0.033, baseline reach 0.042):

| holdout | targets | cells/target (median) | median UMI | N_conf mean / median / min / p90 / max | baseline raw pds / mse / **fid** / reach / jac / nmae | replicate raw pds / mse / fid / reach / jac / nmae |
|---|---|---|---|---|---|---|
| CD4T_Stim48hr_R400 | 174 | 167 | 12014 | 123.0 / 22.0 / 0 / 360 / 1616 | 0.521 / 0.999 / **0.005** / 0.111 / 0.035 / 1.025 | 0.966 / 0.076 / 0.629 / 0.873 / 0.192 / 0.508 |
| CD4T_Stim8hr | 278 | 127 | 8907 | 100.2 / 10.0 / 0 / 177 / 4816 | 0.516 / 0.903 / **0.028** / 0.153 / 0.079 / 1.117 | 0.936 / 0.150 / 0.522 / 0.759 / 0.230 / 0.787 |
| H1_R400 | 254 | 100 | 20006 | 303.5 / 15.5 / 0 / 932 / 5282 | 0.497 / 0.993 / **0.019** / 0.204 / 0.083 / 0.962 | 0.899 / 0.038 / 0.763 / 0.939 / 0.416 / 0.403 |
| K562_GWPS | 213 | 181 | 7790 | 13.8 / 4.0 / 0 / 41 / 274 | 0.494 / 1.089 / **0.025** / 0.248 / 0.188 / 0.979 | 0.885 / -0.034 / 0.674 / 0.878 / 0.477 / 0.467 |
| KOLF2.1J | 258 | 236 | 3817 | 103.2 / 42.0 / 4 / 291 / 543 | 0.479 / 1.039 / **0.005** / 0.058 / 0.000 / 1.042 | 0.882 / -0.026 / 0.691 / 0.861 / 0.178 / 0.717 |
| Orion_HCT116 | 255 | 163 | 12110 | 15.6 / 2.0 / 0 / 18 / 739 | 0.493 / 1.337 / **0.022** / 0.284 / 0.228 / 1.006 | 0.664 / 0.644 / 0.623 / 0.853 / 0.491 / 0.453 |
| Orion_HEK293T | 250 | 208 | 14998 | 27.6 / 2.0 / 0 / 35 / 970 | 0.499 / 1.054 / **0.035** / 0.297 / 0.240 / 1.006 | 0.772 / 0.037 / 0.561 / 0.842 / 0.490 / 0.525 |

All have 18,400 controls.

**Detection thresholds** (`vcc26.detect`, per-gene thresholds; `$DATA/detect/<ctx>.npz`):

| context | callable up | median threshold up | callable down | median threshold down |
|---|---|---|---|---|
| A | 9,929 | 0.4 | 9,928 | 0.6 |
| B | 9,626 | 0.4 | 9,621 | 0.6 |
| C | 10,124 | 0.4 | 10,124 | 0.6 |
| H1_R400 | 10,775 | 0.4 | 10,775 | 0.4 |

### Key question: is H1-R400's baseline fid near 0.5, with an N_conf mean in the hundreds? **No → stopped here (E038–E040 not run).**
- N_conf mean 303.5 is in the hundreds (val A 335.9), but the median is 15.5, and **baseline fid is 0.019**, not ≈ 0.5. The same is true of every holdout (0.005–0.035).
- **Cause: the H1-R400 truth has 100 cells for most targets, not 400** (median 100, max 400; 49,800 cells). `--min-target-cells 400` filters on the *summary's*
  `ncells` (H1 median 1,065 cells), but the truth cells come from `subsets/H1.h5ad`, which was built with the standard caps: ≤ 400 cells for challenge-panel targets, **≤ 100 for all others**.
  Only 21 targets in that subset have ≥ 400 cells. So 233 of the 254 held-out targets have a 100-cell truth, which is the shallow regime we wanted to leave.
  CD4T_Stim48hr_R400 has the same problem: its subset is donor D4 only, median 167 cells, min 34.
- The thinning to 20k UMI worked (median 20,006).
- **Fix (needs a decision; not done):** build the H1 truth from a file holding all H1 cells. The original VCC 2025 counts are in `$DATA/raw/h1_2025`
  (`h1_train_counts.h5ad` plus val/test), or rebuild `subsets/H1.h5ad` with `--other-cap 400` or more (H1 is 1.15 GB now, so it would be about 4×). Alternatively, make `prepare_holdout` apply `--min-target-cells` to the cells actually present in the subset.
  The first option is the cleanest: H1 then gives about 254 targets × 400 cells. Then rerun E037b/c.

Files: `results/E037/` (eligible list, regime JSONs, detect JSONs). E039 also uses the H1-R400 holdout, so it's on hold for the same reason.


### E037 rerun with a 400-cell H1 truth (approved by R, 16 Oct)

- **Rebuilt `subsets/H1.h5ad`** from all VCC 2025 H1 cells: local train counts plus validation/test re-downloaded from Drive (`VCC2025_H1/`), with `make_subset.py --panel-cap 400 --other-cap 400`,
  and controls from train only (the 38,176 NTC are shared across splits). Result: 130,343 cells, 300 targets (**255 with 400 cells**, median 400), 18,400 controls, 9.1 GB.
  The old file is kept as `subsets/H1_cap100.h5ad`, and the old holdout as `$DATA/loco/E037/holdout_H1_R400_cap100`. `loco.json` is unchanged; it still points at `subsets/H1.h5ad`.
- E037b rerun: 254 targets, UMIs thinned by 0.371 to a median of 20,002.

| holdout | targets | cells/target (median) | median UMI | N_conf mean / median / min / p90 / max | baseline raw pds / mse / **fid** / reach / jac / nmae | replicate raw pds / mse / fid / reach / jac / nmae |
|---|---|---|---|---|---|---|
| **H1_R400 (400-cell truth)** | 254 | 400 | 20002 | 855.2 / 135.5 / 0 / 2993 / 7358 | 0.508 / 0.976 / **0.029** / 0.096 / 0.012 / 0.959 | 0.960 / 0.006 / 0.853 / 0.977 / 0.429 / 0.346 |
| official val A/B/C | – | 400 | ~20k | 335.9 (val A) / – / 4 / – / – | 0.53/0.53/0.51, –, **0.506/0.523/0.509**, 0.042, 0.033, – | reach 0.965/0.802/0.943, jac ~0.38 |

Detection thresholds H1_R400: up 10,772 callable (median 0.4), down 10,772 (median 0.4).

**Key question again: N_conf mean in the hundreds?** Yes (855; higher than val A). **Baseline fid ≈ 0.5?** **No: 0.030. Stopped here again; E038–E040 not run, nothing submitted.**
- The truth now matches the A/B/C regime on cells, depth and N_conf, and the baseline pds/jac/reach anchors are in the official range. **Only the baseline fid differs**, by about 0.48.
- So the gap isn't the truth any more. It's how the local mean-response baseline is built (`local_eval.build_anchors` → `cell_eval2.build_generic_baseline`).
  By `docs/15` §0's own formula, fid = k / max(n_pred, N_conf), so a baseline only reaches ≈ 0.5 if it calls about N_conf or more genes with coin-flip directions.
  The official baseline evidently does this (0.51 on val A/B/C); the locally built baseline calls almost nothing (raw fid 0.03).
- Planning should check how the official val baseline prediction is emitted (emitter / cell sampling) and make `build_anchors` do the same. Then rerun `regime_check` on this holdout:
  the holdout files and anchors are cached, and only `anchors.json` needs rebuilding. E038 can then run as written.


---

## REPORT E041 — which cell lines are A/B/C? (DepMap/CCLE expression match, no submission)

```
python scripts/ccle_match.py --controls-dir $DATA/challenge/controls --contexts A,B,C \
  --expr $DATA/priors/depmap/OmicsExpressionProteinCodingGenesTPMLogp1.csv --models $DATA/priors/depmap/Model.csv --out reports/E041_ccle_match.json
```
DepMap 24Q4: 1,673 models × 19,193 genes. Ranked by the rank sum of Spearman and centred Pearson.

### Context A
Sex markers (log2 TPM+1 scale in the controls; XIST/RPS4Y1 are not on the challenge axis): `{'XIST': nan, 'RPS4Y1': nan, 'DDX3Y': 3.63, 'UTY': 5.05}`

| rank | DepMap ID | line | Spearman | centred Pearson | lineage | disease / subtype | sex |
|---|---|---|---|---|---|---|---|
| 1 | ACH-000995 | **JURKAT** | 0.884 | 0.856 | Lymphoid | T-Lymphoblastic Leukemia/Lymphoma / T-Lymphoblastic Leukemia/Lymphoma | Male |
| 2 | ACH-000937 | PF-382 | 0.760 | 0.727 | Lymphoid | T-Lymphoblastic Leukemia/Lymphoma / T-Lymphoblastic Leukemia/Lymphoma | Female |
| 3 | ACH-000101 | KE-37 | 0.755 | 0.661 | Lymphoid | Mature T and NK Neoplasms / Adult T-Cell Leukemia/Lymphoma | Male |
| 4 | ACH-000964 | MOLT-3 | 0.748 | 0.669 | Lymphoid | Mature T and NK Neoplasms / Adult T-Cell Leukemia/Lymphoma | Male |
| 5 | ACH-000372 | P12-ICHIKAWA | 0.728 | 0.660 | Lymphoid | T-Lymphoblastic Leukemia/Lymphoma / T-Lymphoblastic Leukemia/Lymphoma | Male |
| 6 | ACH-001737 | CTV-1-DM | 0.728 | 0.630 | Lymphoid | Mature T and NK Neoplasms / Adult T-Cell Leukemia/Lymphoma | Male |
| 7 | ACH-000920 | CML-T1 | 0.707 | 0.660 | Myeloid | Myeloproliferative Neoplasms / Chronic Myeloid Leukemia, BCR-ABL1+ | Female |
| 8 | ACH-000636 | RPMI-8402 | 0.693 | 0.630 | Lymphoid | T-Lymphoblastic Leukemia/Lymphoma / T-Lymphoblastic Leukemia/Lymphoma | Female |
| 9 | ACH-000918 | MOLT-16 | 0.697 | 0.625 | Lymphoid | T-Lymphoblastic Leukemia/Lymphoma / T-Lymphoblastic Leukemia/Lymphoma | Female |
| 10 | ACH-000519 | PEER | 0.670 | 0.601 | Lymphoid | T-Lymphoblastic Leukemia/Lymphoma / T-Lymphoblastic Leukemia/Lymphoma | Female |
| 11 | ACH-000953 | SUP-T1 | 0.668 | 0.604 | Lymphoid | T-Lymphoblastic Leukemia/Lymphoma / T-Lymphoblastic Leukemia/Lymphoma | Male |
| 12 | ACH-002676 | TK-6 | 0.684 | 0.586 | Myeloid | Myeloproliferative Neoplasms / Chronic Myeloid Leukemia, BCR-ABL1+ | Male |
| 13 | ACH-000942 | HPB-ALL | 0.628 | 0.587 | Lymphoid | T-Lymphoblastic Leukemia/Lymphoma / T-Lymphoblastic Leukemia/Lymphoma | Male |
| 14 | ACH-000104 | Loucy | 0.647 | 0.582 | Lymphoid | T-Lymphoblastic Leukemia/Lymphoma / Early T-Cell Precursor Lymphoblastic Leukemia | Female |
| 15 | ACH-000981 | DND-41 | 0.596 | 0.571 | Lymphoid | T-Lymphoblastic Leukemia/Lymphoma / T-Lymphoblastic Leukemia/Lymphoma | Male |

### Context B
Sex markers (log2 TPM+1 scale in the controls; XIST/RPS4Y1 are not on the challenge axis): `{'XIST': nan, 'RPS4Y1': nan, 'DDX3Y': 0.0, 'UTY': 0.0}`

| rank | DepMap ID | line | Spearman | centred Pearson | lineage | disease / subtype | sex |
|---|---|---|---|---|---|---|---|
| 1 | ACH-001086 | **HeLa** | 0.845 | 0.685 | Cervix | Cervical Adenocarcinoma / Endocervical Adenocarcinoma | Female |
| 2 | ACH-000556 | SIHA | 0.633 | 0.372 | Cervix | Cervical Squamous Cell Carcinoma / Cervical Squamous Cell Carcinoma | Female |
| 3 | ACH-000496 | NCI-H1792 | 0.604 | 0.370 | Lung | Non-Small Cell Lung Cancer / Lung Adenocarcinoma | Male |
| 4 | ACH-000892 | NCI-H1563 | 0.605 | 0.362 | Lung | Non-Small Cell Lung Cancer / Lung Adenocarcinoma | Male |
| 5 | ACH-000237 | JHOM-1 | 0.598 | 0.383 | Ovary/Fallopian Tube | Ovarian Epithelial Tumor / Mucinous Ovarian Cancer | Female |
| 6 | ACH-000630 | YD-8 | 0.595 | 0.389 | Head and Neck | Head and Neck Squamous Cell Carcinoma / Oral Cavity Squamous Cell Carcinoma | Female |
| 7 | ACH-000500 | SNU-46 | 0.602 | 0.368 | Head and Neck | Head and Neck Squamous Cell Carcinoma / Larynx Squamous Cell Carcinoma | Male |
| 8 | ACH-000062 | RERF-LC-MS | 0.591 | 0.364 | Lung | Non-Small Cell Lung Cancer / Lung Adenocarcinoma | Male |
| 9 | ACH-000787 | LXF-289 | 0.593 | 0.357 | Lung | Non-Small Cell Lung Cancer / Lung Adenocarcinoma | Male |
| 10 | ACH-000511 | Calu-1 | 0.596 | 0.338 | Lung | Non-Small Cell Lung Cancer / Lung Squamous Cell Carcinoma | Male |
| 11 | ACH-000516 | CAL-78 | 0.578 | 0.354 | Bone | Chondrosarcoma / Dedifferentiated Chondrosarcoma | Male |
| 12 | ACH-000861 | HOP-62 | 0.585 | 0.313 | Lung | Non-Small Cell Lung Cancer / Lung Adenocarcinoma | Female |
| 13 | ACH-001557 | Mero-41 | 0.589 | 0.300 | Pleura | Pleural Mesothelioma / Pleural Mesothelioma, Epithelioid Type | Male |
| 14 | ACH-001310 | HA1E | 0.574 | 0.332 | Kidney | Non-Cancerous / Immortalized Embyonic Kidney Cells | Male |
| 15 | ACH-000706 | EKVX | 0.574 | 0.330 | Lung | Non-Small Cell Lung Cancer / Lung Adenocarcinoma | Male |

### Context C
Sex markers (log2 TPM+1 scale in the controls; XIST/RPS4Y1 are not on the challenge axis): `{'XIST': nan, 'RPS4Y1': nan, 'DDX3Y': 6.57, 'UTY': 5.32}`

| rank | DepMap ID | line | Spearman | centred Pearson | lineage | disease / subtype | sex |
|---|---|---|---|---|---|---|---|
| 1 | ACH-000518 | **CAL-33** | 0.823 | 0.750 | Head and Neck | Head and Neck Squamous Cell Carcinoma / Oral Cavity Squamous Cell Carcinoma | Male |
| 2 | ACH-000832 | CAL 27 | 0.761 | 0.628 | Head and Neck | Head and Neck Squamous Cell Carcinoma / Oral Cavity Squamous Cell Carcinoma | Male |
| 3 | ACH-000619 | PE/CA-PJ15 | 0.718 | 0.587 | Head and Neck | Head and Neck Squamous Cell Carcinoma / Oral Cavity Squamous Cell Carcinoma | Male |
| 4 | ACH-000606 | PE/CA-PJ34 (clone C12) | 0.727 | 0.571 | Head and Neck | Head and Neck Squamous Cell Carcinoma / Oral Cavity Squamous Cell Carcinoma | Male |
| 5 | ACH-001523 | HSC-1 | 0.722 | 0.570 | Skin | Cutaneous Squamous Cell Carcinoma / Cutaneous Squamous Cell Carcinoma | Male |
| 6 | ACH-001695 | UPCI-SCC-099 | 0.716 | 0.546 | Head and Neck | Head and Neck Squamous Cell Carcinoma / Oral Cavity Squamous Cell Carcinoma | Male |
| 7 | ACH-001694 | UPCI-SCC-074 | 0.702 | 0.566 | Head and Neck | Head and Neck Squamous Cell Carcinoma / Oral Cavity Squamous Cell Carcinoma | Female |
| 8 | ACH-000694 | TE-9 | 0.700 | 0.572 | Esophagus/Stomach | Esophageal Squamous Cell Carcinoma / Esophageal Squamous Cell Carcinoma | Male |
| 9 | ACH-000682 | SNU-1066 | 0.695 | 0.614 | Head and Neck | Head and Neck Squamous Cell Carcinoma / Larynx Squamous Cell Carcinoma | Male |
| 10 | ACH-000546 | HSC-4 | 0.695 | 0.584 | Head and Neck | Head and Neck Squamous Cell Carcinoma / Oral Cavity Squamous Cell Carcinoma | Male |
| 11 | ACH-000549 | SNU-1076 | 0.697 | 0.568 | Head and Neck | Head and Neck Squamous Cell Carcinoma / Larynx Squamous Cell Carcinoma | Male |
| 12 | ACH-001442 | A388 | 0.727 | 0.502 | Skin | Cutaneous Squamous Cell Carcinoma / Cutaneous Squamous Cell Carcinoma | Male |
| 13 | ACH-000824 | KYSE-510 | 0.705 | 0.497 | Esophagus/Stomach | Esophageal Squamous Cell Carcinoma / Esophageal Squamous Cell Carcinoma | Female |
| 14 | ACH-000802 | BFTC-905 | 0.681 | 0.560 | Bladder/Urinary Tract | Bladder Urothelial Carcinoma / Bladder Urothelial Carcinoma | Female |
| 15 | ACH-000488 | TE-11 | 0.711 | 0.489 | Esophagus/Stomach | Esophageal Squamous Cell Carcinoma / Esophageal Squamous Cell Carcinoma | Male |

**Calls** (expression match, high confidence because of the margin to #2; not confirmed by Arc):
- **A = Jurkat** (T-ALL, male): Spearman 0.884 vs 0.760 for the runner-up PF-382, and DDX3Y/UTY are expressed. This confirms the E016 inference (immature T-ALL, CD1A/DNTT).
- **B = HeLa** (cervical adenocarcinoma, female, HPV18): 0.845 vs 0.633 for SiHa, with no Y expression. It matches E016's "female carcinoma-like, mesenchymal component, CDKN2A high" (p16 high is HPV-driven).
- **C = CAL-33** (oral cavity squamous cell carcinoma, male): 0.823 vs 0.761 for CAL 27. The top 11 are all head-and-neck/skin/oesophageal SCC, matching E016's "male squamous/basal epithelial".

Consequences for sources:
- **A:** Nadig's Jurkat (essential library, 0 panel targets measured) is the same line. X-Atlas/Pisces' Jurkat resting/activated genome-wide screens are the ideal source when released.
- **B / C:** no public Perturb-seq in HeLa or CAL-33 / HNSCC (D8 search). The nearest sources are Orion HCT116 (C 0.81, B 0.78) and H1.
