# Diagnosis: everything holding the score back, and the fix for each

Written 15 Oct 2026 ~17:45 UTC (13:45 ET) after E016, E020 (seen) and E021. Evidence: `reports/REPORTS_E016_E021.md`, `results/E020/`, `reports/DATA_DONE.md`, `reports/data_qc.md`, and the leaderboard screenshot.

## 1. Where we stand

E021 is on the leaderboard: **0.106, rank ~678–684**.

| metric | E021 scaled | E021 raw | #1 Illumina scaled | #2–5 scaled | what the raw value says |
|---|---|---|---|---|---|
| PDS | 0.501 | 0.727 | 0.874 | 0.78–0.85 | we pick the right target over most others, but noisily |
| MSE | **0.000** | **4.663** | 0.787 (raw 0.240) | 0.46–0.49 (raw ~0.55) | **our expression error is 4.7× the true effect size**; predicting "no change" would give ~1.0 |
| JAC | 0.008 | 0.033 | 0.088 | 0.02–0.08 | everyone is weak here |
| NMAE | 0.086 | 0.947 | 0.419 | 0.26–0.29 | on the truth's DE genes our fold changes are almost as wrong as predicting 0 (= 1.0) |
| FID | −0.067 | 0.493 | 0.153 | 0.00–0.09 | we call many genes the truth doesn't (spurious calls inflate the denominator) |
| REACH | 0.108 | 0.175 | 0.444 | 0.29–0.36 | our confidence ranking of genes is poor |

Local V\* (seen) agrees: B2 raw MSE is 3.2–6.8 on the three held-out lines, against ~0.9 for the mean-response baseline. The ORACLE run (truth re-emitted through our emitter) scores 1.0+ on every metric, so **the emitter is not the problem; the predicted means are**. Only the denoised specs got MSE above 0 (raw ~1.01).

## 2. Problem register

Impact: ●●● large (≥ 0.05 overall), ●● medium, ● small. Each fix has an experiment ID; "built" means the code exists and is tested on synthetic data.

### Engineering (how we compute predictions)
| ID | Problem | Evidence | Impact | Fix | Status |
|---|---|---|---|---|---|
| P1 | **Source measurement noise is transferred on every gene.** Each source measures a target with ~25–400 cells at 4–12k UMI. Its log2FC on ~18k genes is mostly sampling noise, and we copy it straight into the prediction. MSE counts every gene equally, so the noise swamps the signal. The same noise blurs PDS and produces spurious Wilcoxon calls (FID, JAC). | raw MSE 3.2–6.8 (B2) vs 1.01 (denoised) vs 0.9 baseline; LB raw 4.66 | ●●● | **B4 consensus model**: Gavish–Donoho low-rank denoising of each source's (targets × genes) matrix; random-effects pooling across lines with per-entry noise variances; empirical-Bayes shrinkage of the consensus | **built**, E025 |
| P2 | **Wrong source weighting.** Each dataset counts once, so CD4T counts 3× (Rest/Stim8hr/Stim48hr), HipSci (37 cells/target) as much as GWPS, and KOLF (5k UMI) as much as deep data. | `pooled_raw` averages datasets equally | ●● | B4: datasets merged within a line by inverse variance; each line weighted by noise + between-line spread τ²; optional similarity weight to the target context | **built**, E025 |
| P3 | **Metric-space mismatch.** We model log2(CPM+1). MSE/PDS live in ln(1 + 5e4·p), roughly a 20-CPM pseudocount, which damps low-expression noise. NMAE uses log2 with no pseudocount on truth-significant genes. | design | ●● | B4 `pc` option (1/5/20) pools in the metric-like space and converts back exactly | **built**, E025 |
| P4 | **Expression created from nothing.** Positive fold changes on genes the target context barely expresses (pseudocount 1) inject expression that never exists. | design; E016 shows A/B/C express different gene sets from the sources | ● | B4 `gate_up_cpm`: no induction of genes below 1 CPM in the target's controls | **built** |
| P5 | **Slow iteration.** One real-metric V\* cell takes ~4.4 min, so 12 specs × 3 lines took 2.6 h, and the GPU is shared. | E020 | ●● (speed) | **`vcc26.proxy`**: pseudobulk-space MSE/PDS/DE-sign/NMAE proxies plus an error anatomy, in seconds on CPU. Rankings match the real metric on synthetic data. Sweep with the proxy, confirm the top few with real V\* | **built**, E025/E026 |
| P6 | **No confidence intervals.** E020's top-2 gap (0.003) is noise. | E020 | ● | E-4 paired bootstrap over targets | to build |

### Data
| ID | Problem | Evidence | Impact | Fix | Status |
|---|---|---|---|---|---|
| P7 | **Donor/batch confounding in pooled pseudobulks.** CD4T pools 4 donors; if the control pool's donor mix differs from a guide's, donor-specific genes (Y genes, HLA, null alleles) show up as fold changes for every target. The same applies to GEM-group/lane batches in Replogle/Nadig, and HipSci uses "unassigned" cells as controls. | `ingest_cd4.sh` pools by `n_cells`; synthetic test: pooled 1.44 log2FC artefact → matched 0.02 | ●● | `pseudobulk --strata-col` (**built**): each target gets a control composition-matched over donors/batches. Re-summarise CD4T by donor, Replogle/Nadig by GEM group, and HipSci with NonTarget-only controls | curation agent, D7 |
| P8 | **No epithelial/carcinoma source.** E016: B is a female carcinoma with a mesenchymal component (HeLa-like by FOLR1/CDKN2A/KRT7; inference) and C is male squamous epithelium (TP63/KRT5/KRT13). Our sources are T cells, iPSC/ESC, K562 and RPE1. The nearest source to B and C is H1 at r = 0.79. A at least has CD4T (0.85). The final D/E/F are also unknown lines. | E016 | ●●● | (a) **X-Atlas/Orion HCT116** (epithelial carcinoma, 146 panel targets): permission request to Xaira. (b) Curation batch 2: perturbation data in HeLa, cervical/ovarian, squamous (head-and-neck, oesophageal, lung) and T-ALL lines. (c) LINCS L1000 shRNA/CRISPR signatures in carcinoma lines (bulk, 978 landmark genes; licence and coverage check). | D8–D10 |
| P9 | **Depth/quality spread** (KOLF 4k UMI, HipSci 37 cells/target, K562 only 7.7k genes) | data_qc | ● | handled by P1/P2 noise weights | built |
| P10 | **Unmeasured or thin targets**: EPHB2 in 0 lines, 9 targets in 1 line | panel_coverage | ● | prior encoders (M-4) | planned |

### Biology
| ID | Problem | Impact | Fix | Status |
|---|---|---|---|---|
| P11 | **Responses are cell-type specific.** A knockdown's downstream genes depend on what the cell expresses and how it's wired. Copying a T-cell or iPSC response into a squamous line carries the wrong genes. | ●●● | (1) gate by target-context expression (P4); (2) **project onto the target context's own co-variation programs** (PCs of its 18,400 controls; WP9/B-4); (3) **learned translator** (M-1 GBM → M-2): learns how responses change between lines from the ~10k targets measured in both members of each line pair (CD4T, K562 GWPS, KOLF, HipSci, essential lines, H1), with the control profiles as inputs | B-4, M-1 |
| P12 | **The target must be expressed to be knocked down.** Several panel genes are tissue-restricted (e.g. PSMB9, IFNAR2, MYD88, STAT6 in epithelium). With no expression there's no effect apart from neighbour silencing. | ●● | B4 `gate_target_cpm` (scale by target CPM in the context's controls) | built, in E025 |
| P13 | **Context-specific dependencies.** A knockdown that hurts fitness in *this* line gives a large proliferation/stress signature, which dominates D and therefore MSE. Panel genes avoid K562 essentials but may be essential in B or C. | ●● | DepMap gene effects (have 24Q4) + CCLE expression (to fetch) → find the DepMap lines nearest to each context and predict per-target fitness impact → scale a learned "fitness programme" component | D11 + new model feature |
| P14 | **Effect magnitude differs by line, assay and library** (KOLF knockdown 0.32 vs 0.12 elsewhere, Flex vs 3′ chemistry, Arc's guides). NMAE raw 0.95 means our magnitudes on the truth's DE genes are far off. | ●● | β grid now; translator learns magnitude; C-2 expected-score optimiser chooses β per context | E025, M-1, C-2 |
| P15 | **CRISPRi neighbour silencing** (bidirectional promoters): conserved across contexts and strong, so it's high-value for DE calls | ● | A2 (built 14 Oct, untested on V\*) | E028 |
| P16 | **The baseline is the context's own mean response.** Our generic shift (B1) is *worse than zero* on MSE (raw 1.07–1.56 > 1). | ● | B4 `generic='zero'` by default; a learned context-mean predictor later | built |

### Metric mechanics
| ID | Problem | Fix |
|---|---|---|
| P17 | MSE credits the prediction's own jackknife noise only when predictions spread enough across targets (ρ = min(1, spread / noise)). Over-shrunk predictions lose that credit, under-shrunk ones carry noise. | the proxy reports both variants; C-2 tunes shrinkage against the exact metric |
| P18 | FID divides by max(n_pred, n_real): too few calls is penalised, and so are spurious calls. JAC needs the right set; REACH needs the right confidence order. | C-1 per-target DE-count calibration; P1 removes spurious calls |
| P19 | Our V\* lines have closer sources than B/C do (pluripotent ↔ pluripotent, T ↔ T), so local scores run high: 0.167 local vs 0.106 leaderboard. | add **V\*-far**: hold out each line with same-lineage sources removed too (KOLF without HipSci/H1; CD4T without Jurkat) |

### Operations
| ID | Problem | Fix |
|---|---|---|
| P20 | The second project on this instance broke the challenge's Python environment (torch upgraded) and holds 32 of 40 GB of GPU memory, which blocked E020-unseen. | Give the other project **its own instance**, or a strict GPU schedule. The proxy work (E025) is CPU-only and can run now. |
| P21 | Drive archiving is blocked by rclone's shared Google API quota | Rafid: own OAuth client ID for rclone (https://rclone.org/drive/#making-your-own-client-id) |

## 3. What runs next (in order)

1. **E025 (CPU, now):** proxy sweep of 47 specs (`specs_E025.json`: B4 grid over low-rank on/off × pseudocount 1/5/20 × τ² × similarity weighting, plus gates, β and generic variants, against E021's config) on the three V\* lines. Error anatomy for E021's config and the best B4. `scripts/pick_e025.py` writes `specs_E026.json`.
2. **D7 (curation agent, in parallel):** composition-matched re-summaries (CD4T by donor, Replogle/Nadig by GEM group, HipSci NonTarget-only), then **E025b**: rerun the proxy on the new summaries.
3. **E026 (GPU):** real-metric V\* for the picked specs, including the V\*-far variant.
4. **E027:** leaderboard confirmation of E026's winner.
5. Then the build plan continues with this order: B-4 projection, A2 neighbours (E028), M-1 translator with the new pairs, DepMap/CCLE dependency feature, C-1/C-2.

Expectations, honestly: P1/P2/P7 should take MSE off 0 and lift PDS; the proxy will say by how much within hours. Reaching the 0.3+ range also needs P11 (translator) and, most of all, P8 (epithelial data) for contexts B and C.
