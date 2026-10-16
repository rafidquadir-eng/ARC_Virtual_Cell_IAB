# DATA DONE — curation batch 3 (16 Oct 2026, ~18:40 UTC)

Done by session vcc-21 (`docs/09` Batch 3, D12–D15), coordinated with the runbook session (vcc-56): no `loco.json`/`pb/`
edit while its jobs ran. Per-dataset rows: `reports/data_ingest.csv`. Priors: `reports/priors.md`.

**Summary.** No new public 10x Flex CRISPR(i) data with ≥ 20 panel targets exists beyond what we already have
(H1, CD4T). No single-cell CRISPRi exists in the test lineages besides Jurkat (Nadig, essential library; Song 2025,
genome-wide but unusable, see below). One CRISPR-KO epithelial set (A549, 21 panel targets) was ingested **as a
candidate only**: it is not in `loco.json`, so no V\*/LB run changes until planning opts in.

## D12: public 10x Flex CRISPR(i) Perturb-seq

Searched GEO (E-utilities: "fixed RNA profiling"/Flex/probe-based × Perturb-seq/CRISPRi/CRISPR screen, human, 2024–2026),
bioRxiv, 10x datasets and the Arc Virtual Cell Atlas.

| dataset | line | platform | perturbation | targets | panel overlap | cells / UMI | licence | status |
|---|---|---|---|---|---|---|---|---|
| VCC 2025 H1 (Arc) | H1 | Flex | CRISPRi | 300 | 25 | – | Arc VCC terms (batch 1) | already in `loco.json` (H1) |
| Zhu/Dann 2026 CD4⁺ T (GSE314342) | primary CD4T | Flex (probe-based) | CRISPRi | genome-wide | 281 (≥ 50 cells) | ~22M cells | MIT | already in `loco.json` (CD4T ×3) |
| VIPerturb-seq (Bradu…Satija, bioRxiv 10.64898/2026.02.12.705613) | not stated in abstract | Flex Apex (split probes) | CRISPRi (GuEST-List, genome-wide) | genome-wide; 880k-cell unbiased screen | unknown | 880k cells | preprint CC BY-NC-ND; **no data accession found** (GEO, lab page) — **unverified** | catalog only; recheck |
| Jiang 2025 signalling (GSE281048, Nat Cell Biol) | A549, MCF7, HT29, HAP1, BxPC3, K562 | Flex | CRISPRi | ~ signalling regulators | ≤ 7 per line (batch 1) | – | GEO | below cut (batch 1) |
| Perturb-Multimodal (GSE275483, Cell 2025) | mouse liver; K562 check | Flex + split probes | KO / CRISPRi | few | ≈ 0 | – | GEO | out (mouse; tiny K562 check) |
| FlexPlex (bioRxiv 10.1101/2025.08.27.672635) | – | Flex | pooled | mTOR regulators | – | – | no accession found | catalog only |

**Platform fields filled in `loco.json`** (from the papers' methods): KOLF2.1J `10x_3p_ht` ("Chromium Next GEM Single Cell
3′ HT v3.1", PMC11580897); HipSci_iPSC `10x_5p` ("Chromium Next GEM Single Cell 5′ Kit v2", Feng et al., PMC12903452).
HepG2/Jurkat (`10x_3p`) were already set. Flex sources remain H1 and CD4T only.

## D13: perturbation data in the test lineages

Batch 2's D8 found nothing with ≥ 20 panel targets in HeLa/cervical/ovarian, squamous/keratinocyte/airway basal or
MOLT-4/CCRF-CEM (Myllia A549, 15 targets, below the cut). Batch 3 searched again (GEO E-utilities per lineage and per
cell line) and widened to CRISPR-KO:

| dataset | line (lineage) | perturbation | panel targets (≥ 50 cells) | quality check | decision |
|---|---|---|---|---|---|
| **GSE345058** A549 multimodal morphology atlas (2026) | A549 (lung adenocarcinoma, epithelial) | CRISPR-KO CROP-seq, 1,000 genes, GEM-X 3′ | **21** (all ≥ 50; 400-cell subset) | 45,320 NTC; median UMI 26k (test-like); per-target lfc vs Orion_HCT116 r 0.12 (shuffled 0.05; top-50 targets 0.50) | **ingested as candidate**: `pb/A549_KO.npz`, `subsets/A549_KO.h5ad`, entry in `loco_candidates.json` (not `loco.json`) |
| **GSE249595** Song et al. 2025 (Nat Cell Biol) | Jurkat E6 (T-ALL; A's top CCLE match) | genome-wide CRISPRi CROP-seq, 18,595 genes, high MOI (~7 guides/cell), hashed untreated + 6 activated | 151 in summary, 36 ≥ 50 cells (untreated; additive estimator) | median UMI 2.8k; knockdown visible (0.58 remaining at well-expressed targets) but per-target lfc vs Nadig Jurkat **r 0.00** (top-50: −0.01; guide-UMI ≥ 10 variant identical) | **not registered** (no reproducible response signal); summary kept in scratch |
| GSE207330 (translational fidelity, 2023) | HeLa, Jurkat, K562 | CRISPRi, bulk RNA-seq | 1 (**ZNF324**) | – | not ingested; a single exact-line check point for A and B |
| GSE229062 (MED12–p63) | CAL-33 (HNSCC) | CRISPR-KO, bulk RNA-seq | 0 (MED12, TP63) | – | out |
| GSE324388 (MHC-I regulators) | SCC90/SCC152 HPV⁺ HNC, NTert E6/E7 keratinocytes | genome-wide KO, FACS sorting (no RNA readout) | – | – | out |
| LINCS L1000 CRISPR | 248 lines | KO, 978 landmark genes | – | – | blocked (CMap terms: academic/non-profit only; batch 2) |

## D14: DepMap mutations

`OmicsSomaticMutations.csv`, `OmicsSomaticMutationsMatrixDamaging.csv` and `OmicsSomaticMutationsMatrixHotspot.csv`
(DepMap 24Q4 Public, figshare 10.25452/figshare.plus.27993248, CC BY 4.0; md5 match) in `$DATA/priors/depmap/`.
The existing `CRISPRGeneEffect.csv` is confirmed as 24Q4 (md5 6edf7ade… = figshare file 51064667). Both recorded in
`reports/priors.md`.

## D15: perturbation data in the exact top-3 CCLE lines (`reports/E041_ccle_match.json`)

| context | top-3 CCLE lines | public perturbation data with RNA readout |
|---|---|---|
| A | JURKAT (0.884), PF-382, KE-37 | Jurkat: Nadig 2025 essential (in `loco.json`, 0 panel targets), Song 2025 genome-wide (above, unusable), GSE207330 bulk CRISPRi (ZNF324), older CROP-seq TCR screens (GSE137554, GSE148820; few targets); X-Atlas/Pisces Jurkat **not released**. PF-382, KE-37: none found. |
| B | HeLa (0.845), SiHa, NCI-H1792 | HeLa: GSE207330 bulk CRISPRi (ZNF324 only); otherwise bulk genome-wide fitness/FACS screens without RNA readout. SiHa, NCI-H1792: none found. |
| C | CAL-33 (0.823), CAL 27, PE/CA-PJ15 | CAL-33: GSE229062 bulk KO RNA-seq (MED12, TP63; not panel). CAL 27: in vivo/organoid cSCC CRISPRi screens (GSE295657/8, lncRNA) and the 2020 SCC atlas CRISPR screen (GSE144238, fitness). PE/CA-PJ15: none found. |

Nothing worth ingesting. The only exact-line, panel-target measurement is ZNF324 knockdown in HeLa and Jurkat (bulk).

## X-Atlas/Pisces (daily check)

16 Oct 18:10 UTC: `Xaira-Therapeutics/X-Atlas-Pisces` still holds only README/LICENSE (last modified 2026-03-25).

## Panel-target coverage (distinct cell lines, `loco.json`)

| | ≥ 1 | ≥ 2 | ≥ 3 |
|---|---|---|---|
| ≥ 25 cells, `loco.json` (unchanged by batch 3) | 300 | 300 | 293 |
| ≥ 25 cells, + A549_KO candidate | 300 | 300 | 294 |
| ≥ 50 cells, `loco.json` | 300 | 298 | 287 |
| ≥ 50 cells, + A549_KO candidate | 300 | 298 | 288 |

## Blocked list (changes vs batch 2)

- VIPerturb-seq: no public data found (preprint CC BY-NC-ND).
- X-Atlas/Pisces: still not released.
- LINCS L1000: still blocked (licence).

## Storage

- Downloaded in batch 3: 0.5 GB (DepMap) + 3.5 GB (GSE249595) + 23.4 GB (GSE345058) ≈ **27 GB**.
- Instance: `scratch/A549_GSE345058` 24 GB, `scratch/Jurkat_Song2025` 8.6 GB, `subsets/A549_KO.h5ad` 8.0 GB,
  `pb/A549_KO.npz` 0.1 GB, `priors/depmap` +0.5 GB.
- Drive: 1.71 TiB used of 2 TiB (294 GiB free). The daily upload limit was already hit on 16 Oct, so uploads are queued:
  tmux `archive_b3` (DepMap mutations, 17 Oct 08:00 UTC) and `archive_b3b` (both raw scratch dirs, 08:30 UTC), each
  with `rclone check`. Delete the scratch copies only after `UPLOAD_OK` in `logs/archive_b3b.log` (needs Rafid's OK).

## Code

- `pseudobulk --layer` and `make_subset --layer` now read the layer lazily. Backed `read_h5ad` loads every layer into RAM,
  which peaked at 85 GB on GSE345058; it now peaks at 7–20 GB.
- `scripts/convert_song.py`: high-MOI CROP-seq → pseudobulk rows (additive estimator) for `pseudobulk --weight-col`.

## Next batch, if asked

1. Recheck VIPerturb-seq for a data release (genome-wide Flex CRISPRi; line unknown); size unknown.
2. X-Atlas/Pisces Jurkat/HepG2 when released (CC BY-NC-SA, already approved).
3. Planning decision: opt A549_KO in (CRISPR-KO, 21 targets), e.g. as an epithelial source for B/C.
