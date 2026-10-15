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
