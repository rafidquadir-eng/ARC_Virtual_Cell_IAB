# REPORT blocks E016, E020, E021 — Lambda instance, 15 Oct 2026

Runbook: `docs/07_RUNBOOK_INSTANCE.md` (E016 + E020 + E021, after `reports/DATA_DONE.md`, commit 9e95e58).
`loco.json` has 11 contexts, each with `line` and `library`. Scores are scaled vcc2026 metrics
(0 = mean-response baseline, 1 = replicate); context score = mean of the six. DE backend gpudge on the A100.

---

## REPORT E016 — what are contexts A/B/C?

`python -m vcc26.context_id --controls-dir $DATA/challenge/controls --contexts A,B,C --gene-axis gene_axis.csv --summaries <11 summaries> --out reports/context_id.json`
(55 s after a fix: the controls gene set was rebuilt once per axis gene, which took more than 10 min.)
XIST and SOX11 are not on the challenge gene axis, so sex rests on the Y genes.

### Similarity: Pearson r of log1p control CPM (genes both measure)

| source | A | B | C |
|---|---|---|---|
| CD4T_Stim48hr | **0.856** | 0.753 | 0.771 |
| CD4T_Rest | 0.852 | 0.736 | 0.750 |
| CD4T_Stim8hr | 0.848 | 0.746 | 0.756 |
| H1 | 0.752 | **0.792** | **0.791** |
| HipSci_iPSC | 0.737 | 0.733 | 0.744 |
| KOLF2.1J | 0.679 | 0.683 | 0.687 |
| Jurkat | 0.524 | 0.303 | 0.341 |
| K562 | 0.364 | 0.293 | 0.344 |
| K562_GWPS | 0.342 | 0.268 | 0.326 |
| HepG2 | 0.265 | 0.296 | 0.335 |
| RPE1 | 0.242 | 0.337 | 0.350 |
| context A | – | 0.780 | 0.749 |
| context B | 0.780 | – | **0.842** |
| context C | 0.749 | 0.842 | – |

The full-transcriptome sources (H1, CD4T, KOLF2.1J, HipSci; 17.8–18.5k genes) correlate at 0.68–0.86 with every
context. The Replogle/Nadig essential-library lines (7.7–9.0k author-filtered genes) correlate at 0.24–0.52, so the gene
set inflates this r. Compare within a group, not across groups.

### Markers (control CPM)

| panel | A | B | C |
|---|---|---|---|
| T cell (CD3E, CD2, LCK, CD1A, TRBC1, PTPRC) | **759, 248, 429, 140, 3358, 21** | all 0 | all 0 |
| epithelial (EPCAM, KRT8, KRT18, KRT19, CDH1, CLDN4) | 0, 3, 0, 0, 0, 0 | 2, **2533, 848, 140**, 0, 6 | **312, 1401, 672**, 4, **128, 188** |
| mesenchymal (VIM, COL1A1, FN1, TAGLN, ACTA2, SPARC) | 1626, 4, 0, 6, 2, 21 | **6132, 369, 92, 154**, 4, 1 | 2, 10, 0, 11, 14, 224 |
| pluripotent (POU5F1, NANOG, LIN28A, SOX2) | 0, 0, 1, 0 | 2, 0, 1, 0 | 6, 0, 0, **143** |
| erythroid, hepatocyte, myeloid, colon | ≈ 0 (TAL1 145) | ≈ 0 | ≈ 0 (CD14 20, CD74 130) |
| proliferation (MKI67, TOP2A, PCNA) | 431, 698, 768 | 407, 467, 352 | 321, 335, 358 |
| Y genes (DDX3Y, UTY, KDM5D, EIF1AY) | 11, 32, 52, 169 → **male** | all 0 → **female (or Y loss)** | 94, 39, 39, 224 → **male** |

### Most specific genes (vs the other two contexts, top 15)

- **A:** TRBC1, MYO7B, CHI3L2, CD1E, GYPC, LCP1, CD3D, ITM2A, AIF1, ALDH1A2, IKZF1, CD3E, CORO1A, TSPAN7, ZAP70 (also DNTT, LEF1, MYB, SELL, LCK, CD1A, TAL1)
- **B:** COL5A1, SPINK6, KRT7, GNG11, PDE3A, FOLR1, ITGA11, CT83, PDK4, SMOC1, NNMT, LIMCH1, ARMCX2, TPM2, CDKN2A
- **C:** FXYD3, KRT5, KRT15, KRT13, TUBA1B, CSTA, CYCS, TP63, CP, NDUFB4, ATP5MD, TNFSF10, TINAGL1, ACTB, TMPRSS4 (also COL17A1, SCGB1A1, TRIM29, IRF6, AKR1B10, S100A9)

### Best guess per context (*inference*, not confirmed)

- **A — immature (cortical-thymocyte-like) T-ALL cell line, male, proliferating.** CD3/TCR/LCK/ZAP70 with CD1A/CD1E, DNTT and TAL1 and no PTPRC-high mature signature; nearest source CD4T (0.85), then Jurkat as the closest line from the essential-library group (0.52). Candidates: a T-ALL line such as Jurkat, MOLT-4 or CCRF-CEM. CD1A/CD1E/DNTT are high for Jurkat, so a different T-ALL line is plausible.
- **B — female (no Y expression) carcinoma-like line with a strong mesenchymal component.** KRT7/8/18 with VIM, COL1A1/COL5A1, FOLR1, CT83 and very high CDKN2A (p16, typical of RB-loss or HPV-positive cells). Fits an ovarian or cervical carcinoma line (e.g. HeLa-like). No source line is close (H1 0.79 is the nearest).
- **C — male squamous / basal epithelial cells.** TP63, KRT5/13/15, COL17A1, TRIM29 with SOX2 and AKR1B10/SCGB1A1: a squamous carcinoma line (head-and-neck, oesophageal or lung) or airway basal cells. No source line is close (H1 0.79).
- B and C are closest to each other (0.84). None of the three is K562, RPE1 or HepG2. A is the only context with a source of the same lineage (CD4T, primary T cells).

---

## REPORT E020 — V\* leave-one-line-out on the challenge panel (`specs_E020.json`)

`python -m vcc26.vstar --config loco.json --panel-file pert_counts.csv --specs specs_E020.json --out $DATA/loco/E020 --tag E020 --mode {seen,unseen}`

**CHECK:** the dry run listed 3 held-out lines (≥ 100 panel targets with ≥ 50 cells): CD4T_Stim8hr (278), KOLF2.1J (258),
K562_GWPS (254). That passes the ≥ 3 check. Every `loco.json` entry has `line` and `library`. Run one V\* job at a time.

Fixes needed before it ran (committed):
- `loco.prepare_holdout` canonicalizes the truth CSR (9301381). The CD4T subsets have unsorted column indices, and cell-eval2's
  anchor builder refuses non-canonical matrices. No values change (nnz is identical after `sum_duplicates`).

| held-out | sources | panel (`n_panel`) | measured in ≥ 1 source (seen) | in ≥ 2 sources | unmeasured |
|---|---|---|---|---|---|
| CD4T_Stim8hr | K562, RPE1, HepG2, Jurkat, H1, K562_GWPS, HipSci_iPSC, KOLF2.1J | 278 | 272 | 233 | 6 |
| KOLF2.1J | all except KOLF2.1J (incl. 3 CD4T) | 258 | 257 | 249 | 1 |
| K562_GWPS | all except K562 / K562_GWPS | 213 | 213 | 207 | 0 |

K562_GWPS has 213 panel targets, not 254, because the holdout panel uses `ncells ≥ 50` **and** `kd ≤ 0.7`.
Seen mode: 36 runs, about 4.4 min each, 2.6 h of scoring in total.

### Seen mode: `vstar_summary_E020_seen.csv` (selection = mean context score over the 3 lines)

| model                | emit     |   selection |   worst line |   pds |   mse |   fid |   reach |    jac |   nmae |   CD4T_Stim8hr |   KOLF2.1J |   K562_GWPS |
|:---------------------|:---------|------------:|-------------:|------:|------:|------:|--------:|-------:|-------:|--------------------:|----------------:|-----------------:|
| ORACLE               | balanced |       1.239 |        1.012 | 1.246 | 1     | 1.53  |   1.248 |  0.308 |  2.101 |               1.285 |           1.42  |            1.012 |
| ORACLE               | random   |       1.204 |        0.994 | 1.246 | 1     | 1.581 |   1.253 | -0.179 |  2.324 |               1.303 |           1.315 |            0.994 |
| **B2_raw_gPL**       | balanced |   **0.167** |        0.154 | 0.303 | 0     | 0.774 |   0.09  | -0.303 |  0.138 |               0.175 |           0.173 |            0.154 |
| B2_transfer (E012)   | random   |       0.164 |        0.146 | 0.226 | 0     | 0.808 |   0.108 | -0.325 |  0.163 |               0.146 |           0.189 |            0.155 |
| B2_transfer          | balanced |       0.162 |        0.145 | 0.249 | 0     | 0.781 |   0.093 | -0.303 |  0.153 |               0.163 |           0.179 |            0.145 |
| B2_raw_gPL_dn_b1.6   | balanced |       0.152 |        0.131 | 0.256 | 0.021 | 0.728 |   0.045 | -0.266 |  0.126 |               0.152 |           0.172 |            0.131 |
| B2_raw_gPL_dn_b1.3   | balanced |       0.145 |        0.124 | 0.257 | 0.021 | 0.694 |   0.038 | -0.272 |  0.133 |               0.151 |           0.162 |            0.124 |
| B2_raw_gPL_dn        | balanced |       0.134 |        0.115 | 0.257 | 0.021 | 0.647 |   0.03  | -0.284 |  0.133 |               0.145 |           0.142 |            0.115 |
| B3_raw_gPL_dn_linear | balanced |       0.134 |        0.115 | 0.253 | 0.021 | 0.647 |   0.032 | -0.284 |  0.134 |               0.144 |           0.141 |            0.115 |
| A1_gPL_dn            | balanced |       0.106 |        0.072 | 0.219 | 0     | 0.582 |   0.007 | -0.299 |  0.128 |               0.137 |           0.11  |            0.072 |
| B1_generic           | balanced |       0.046 |       -0.001 | 0.009 | 0     | 0.507 |  -0.014 | -0.331 |  0.105 |               0.104 |           0.036 |           -0.001 |
| B1_gPL               | balanced |       0.031 |       -0.04  | 0.009 | 0     | 0.468 |  -0.044 | -0.341 |  0.091 |               0.095 |           0.037 |           -0.04  |

### ORACLE rows (truth pseudobulk re-emitted from the held-out line's controls), random vs balanced

| emit     | holdout      |   pds |   mse |   fid |   reach |    jac |   nmae |   context score |   raw mse |   raw jac |
|:---------|:-------------|------:|------:|------:|--------:|-------:|-------:|----------------:|----------:|----------:|
| random   | CD4T_Stim8hr | 1.153 |     1 | 1.844 |   1.392 | -0.293 |  2.72  |           1.303 |    -3.959 |     0.035 |
| balanced | CD4T_Stim8hr | 1.153 |     1 | 1.812 |   1.378 | -0.095 |  2.464 |           1.285 |    -4.485 |     0.065 |
| random   | KOLF2.1J     | 1.292 |     1 | 1.428 |   1.173 |  0.36  |  2.638 |           1.315 |    -3.103 |     0.064 |
| balanced | KOLF2.1J     | 1.292 |     1 | 1.303 |   1.173 |  1.461 |  2.288 |           1.42  |    -4.555 |     0.261 |
| random   | K562_GWPS    | 1.295 |     1 | 1.471 |   1.194 | -0.605 |  1.612 |           0.994 |    -8.153 |     0.013 |
| balanced | K562_GWPS    | 1.295 |     1 | 1.475 |   1.194 | -0.441 |  1.55  |           1.012 |   -10.877 |     0.06  |

Notes:
- **Emitter.** For ORACLE, balanced beats random on jac in all three lines (+0.20, +1.10, +0.16) and on the mean
  context score (1.239 vs 1.204). For B2_transfer, balanced vs random is +0.023 pds and −0.027 fid, about a wash (0.162 vs 0.164).
  Scaled mse is 1 for ORACLE in both emitters, while raw mse is negative. So the emitter is not why mse is 0 for every
  non-oracle spec; the predicted means are. Only the denoised (`dn`) specs reach mse > 0 (0.021).
- **Multi-line transfer** (B2 vs B1 generic, same balanced emitter): +0.12 selection (0.162 vs 0.046), mostly pds (+0.24) and fid (+0.27).
- **Denoise** costs fid (0.774 → 0.647) and buys a little jac and mse. β 1.3/1.6 recovers part of the fid; B2_raw_gPL_dn_b1.6 is
  0.015 below B2_raw_gPL. The linear fallback changes nothing (B3 = B2_raw_gPL_dn); only 0–6 targets per line are unmeasured.
- **New baseline: top (model, emit) in seen mode = `B2_raw_gPL`, emit `balanced`** (B2_transfer α 1.0, raw, `generic_from`
  `@genome_wide` + `@targeted`, no fallback), selection 0.167, worst line 0.154. The margin over the E012 config is 0.003;
  without the paired bootstrap (E-4, not built yet), that is within noise.

### Unseen mode: `vstar_summary_E020_unseen.csv` (panel targets dropped from every source; `n_covered` = 0 on all 3 lines)

| model                | emit     |   selection |   worst_line |    pds |   mse |   fid |   reach |    jac |   nmae |   line_CD4T_Stim8hr |   line_KOLF2.1J |   line_K562_GWPS |
|:---------------------|:---------|------------:|-------------:|-------:|------:|------:|--------:|-------:|-------:|--------------------:|----------------:|-----------------:|
| ORACLE               | balanced |       1.239 |        1.012 |  1.246 |     1 | 1.53  |   1.248 |  0.308 |  2.101 |               1.285 |           1.42  |            1.012 |
| ORACLE               | random   |       1.204 |        0.994 |  1.246 |     1 | 1.581 |   1.253 | -0.179 |  2.324 |               1.303 |           1.315 |            0.994 |
| B1_generic           | balanced |       0.046 |       -0.001 |  0.009 |     0 | 0.507 |  -0.014 | -0.331 |  0.105 |               0.104 |           0.035 |           -0.001 |
| B2_transfer          | balanced |       0.046 |       -0.001 |  0.009 |     0 | 0.507 |  -0.014 | -0.331 |  0.105 |               0.104 |           0.035 |           -0.001 |
| B2_raw_gPL_dn_b1.6   | balanced |       0.033 |       -0.044 |  0.009 |     0 | 0.477 |  -0.054 | -0.333 |  0.101 |               0.097 |           0.047 |           -0.044 |
| B2_raw_gPL_dn_b1.3   | balanced |       0.032 |       -0.053 |  0.009 |     0 | 0.466 |  -0.048 | -0.335 |  0.102 |               0.102 |           0.048 |           -0.053 |
| B1_gPL               | balanced |       0.031 |       -0.039 |  0.009 |     0 | 0.467 |  -0.042 | -0.341 |  0.089 |               0.094 |           0.037 |           -0.039 |
| B2_raw_gPL           | balanced |       0.031 |       -0.039 |  0.009 |     0 | 0.467 |  -0.042 | -0.341 |  0.089 |               0.094 |           0.037 |           -0.039 |
| B2_raw_gPL_dn        | balanced |       0.03  |       -0.055 |  0.009 |     0 | 0.457 |  -0.056 | -0.334 |  0.102 |               0.098 |           0.046 |           -0.055 |
| B3_raw_gPL_dn_linear | balanced |       0.029 |       -0.061 | -0.001 |     0 | 0.453 |  -0.048 | -0.334 |  0.103 |               0.098 |           0.05  |           -0.061 |
| B2_transfer          | random   |       0.028 |       -0.01  |  0.019 |     0 | 0.432 |  -0.034 | -0.367 |  0.117 |               0.044 |           0.05  |           -0.01  |
| A1_gPL_dn            | balanced |       0.027 |       -0.043 |  0.009 |     0 | 0.461 |  -0.067 | -0.343 |  0.1   |               0.097 |           0.026 |           -0.043 |

Notes:
- With no source measuring any panel target, every transfer spec falls back to a generic shift. B2_transfer (balanced) equals B1_generic
  (0.046), and the `raw`/gPL specs equal B1_gPL (0.031). Denoise, β and A1 change the score by ≤ 0.02. Unmeasured-target performance
  is therefore about 0.03–0.05, close to the mean baseline, and only ~1 % of challenge targets (EPHB2 plus thin ones) are in this regime.
- The random emitter is worse than balanced here (0.028 vs 0.046), mostly on fid and jac.
- ORACLE rows are identical to seen mode (truth-based).
- Run history: the 1st attempt failed with `libcublas.so.12` (the shared venv was changed by another session, then fixed); the 2nd ran out of GPU
  memory (another session's pretraining held 32 GB); the 3rd, 22:19–01:37 UTC on 15/16 Oct, ran clean.

CSVs: `results/E020/vstar_{summary,rows}_E020_{seen,unseen}.csv`.

---

## REPORT E021 — leaderboard confirmation of E020's top seen-mode spec

Submissions used on 15 Oct (UTC) before this entry: 1 (E012), so this is **2 of 2** for 15 Oct.

```
python -m vcc26.predict_challenge --controls-dir $DATA/challenge/controls --contexts A,B,C --perts pert_counts.csv \
  --gene-names gene_axis.csv --registry loco.json --summaries <all 11 loco.json summaries> \
  --model B2_transfer --kw '{"alpha": 1.0, "raw": true, "generic_from": ["@genome_wide", "@targeted"]}' \
  --fallback none --emit balanced --n-control 0 --out $DATA/preds/E021.h5ad
vcc prep $DATA/preds/E021.h5ad -g gene_axis.csv --perts pert_counts.csv --contexts A,B,C -o $DATA/preds/E021.vcc   # passed, 360,000 cells
vcc submit $DATA/preds/E021.vcc -m "E021 B2_raw_gPL emit=balanced (E020 seen top), all 11 summaries" --wait
```

| Metric | **E021** | E012 (B2_transfer, random, 6 summaries) | Δ |
|---|---|---|---|
| Entry | `QJexGFhKagEpbvXkiUku`, published | `aZXPOs2QkOuKb5oZQzYu` | |
| **Overall** | **0.1060** | 0.0691 | **+0.037** |
| pds | 0.5009 | 0.3125 | +0.188 |
| mse | 0.0000 | 0.0000 | 0 |
| nmae | 0.0862 | 0.0421 | +0.044 |
| fid | −0.0667 | −0.0140 | −0.053 |
| reach | 0.1078 | 0.0876 | +0.020 |
| jac | 0.0076 | −0.0134 | +0.021 |
| Rank | **684** | 827 | |

Partition val, panel `vcc2026-val-1`, anchor set `vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4`.

Interpretation: E021 changes three things at once compared with E012: five new summaries (CD4T ×3, KOLF2.1J, HipSci, plus the rebuilt H1),
`raw` + panel-like generic, and the balanced emitter. The leaderboard overall (0.106) is now close to the V\* seen selection (0.167)
and its worst line (0.154). That is much closer than E011 b-testlike (0.230) was to E012. pds rises most (0.31 → 0.50). E016 found context A to be
T-ALL-like, and CD4T is the nearest source for it. mse is still 0 and fid is slightly negative.
