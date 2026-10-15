# DATA DONE — curation batch 1 + Phase 3 (15 Oct 2026, ~06:10 UTC)

The data-curation agent's first batch is finished, so **the experiment session can resume**. Details:
`reports/data_catalog.csv` (ranked catalog), `reports/data_ingest.csv` (per-dataset ingest rows),
`reports/data_qc.md` + `reports/panel_coverage.csv` (QC and per-target coverage), `reports/priors.md` (priors).

## What's in (`loco.json`, 11 contexts, every entry has `line` and `library`)

| context | line | library | perts (summary) | panel measured (≥50 cells) | genes on axis | median kd | source |
|---|---|---|---|---|---|---|---|
| K562 | K562 | essential | 1,952 | 0 | 7,940 | 0.17 | Replogle 2022 |
| RPE1 | RPE1 | essential | 2,087 | 0 | 8,260 | 0.09 | Replogle 2022 |
| HepG2 | HepG2 | essential | 1,970 | 0 | 9,024 | 0.12 | Nadig 2025 |
| Jurkat | Jurkat | essential | 2,117 | 0 | 8,284 | 0.12 | Nadig 2025 |
| K562_GWPS | K562 | genome_wide | 9,315 | 263 (254) | 7,681 | 0.15 | Replogle 2022 |
| **H1** (rebuilt) | H1 | targeted | 299 | 25 (25) | 18,077 | 0.06 | VCC 2025 train+val+test |
| **CD4T_Rest** | CD4T | genome_wide | 10,754 | 280 (273) | 17,771 | 0.12 | Zhu/Dann, Cell 2026 |
| **CD4T_Stim8hr** | CD4T | genome_wide | 10,929 | 284 (278) | 17,771 | 0.12 | Zhu/Dann, Cell 2026 |
| **CD4T_Stim48hr** | CD4T | genome_wide | 10,701 | 279 (273) | 17,771 | 0.14 | Zhu/Dann, Cell 2026 |
| **KOLF2.1J** | KOLF2.1J | genome_wide | 9,613 | 260 (258) | 17,971 | 0.32 | Nourreddine, Nat Biotech 2026 |
| **HipSci_iPSC** | HipSci_iPSC | genome_wide | 3,463 | 85 (19) | 18,513 | 0.24 | Feng, Cell Genomics 2025 |

*Measured* = in the summary (≥ 25 cells and CRISPRi remaining fraction ≤ 0.7). `python -m vcc26.vstar --dry-run`
now lists three held-out lines: **CD4T_Stim8hr (278), KOLF2.1J (258), K562_GWPS (254)**. HipSci (19 targets with
≥ 50 cells) and H1 (25) are below the 100-target cut.

H1 is now one entry: `pb/H1.npz` is built from all 300 VCC 2025 perturbations (414,694 cells; the 38,176 shared
controls were deduplicated), and `subsets/H1.h5ad` holds all three splits. The old train-only summary is kept as
`pb/H1_train_only.npz`. The temporary `H1_valtest` entry was removed.

**Notes for modelling**
- **CD4T:** the three stimulation conditions share one line (`CD4T`), so LOCO and V* never transfer between them.
  Summaries pool all 4 donors (from the authors' pseudobulk: guide × donor × condition counts, weighted by
  `n_cells`). The holdout subsets are **donor D4 only** (≈1.05M cells each). Targets use the authors' curated
  guide→gene map. The chemistry is 10x Flex (probe-based, 18,129 genes).
- **KOLF2.1J:** about 5k UMI per cell, a quarter of the test depth. Median knockdown 0.32 is weaker than the other lines.
- **HipSci_iPSC:** controls are NonTarget plus "unassigned" (no guide detected) cells, as in the paper. Depth per
  target is shallow (median 37 cells). KOLF2.1J, HipSci and H1 are all pluripotent, so transfer among them will
  look optimistic in LOCO.
- **Subset sizes:** CD4T 43–50 GB each and KOLF2.1J 35 GB (uncompressed, ~1M cells each, because the spec keeps
  100 cells for each of ~10k non-panel targets). Load panel targets and controls by `target` rather than whole files.

## Panel coverage (300 targets; by distinct cell line)

| | ≥1 line | ≥2 lines | ≥3 lines |
|---|---|---|---|
| before batch 1 (K562_GWPS + H1 train) | 264 | 12 | 0 |
| **after** (measured, ≥ 25 cells) | **299** | **290** | **240** |
| after, ≥ 50 cells | 299 | 284 | 221 |

Per line: CD4T 286, K562 263, KOLF2.1J 260, HipSci_iPSC 85, H1 25. Only EPHB2 is unmeasured. Nine are in one
line only: ABCD1, LENG1 (HipSci); NICN1 (KOLF2.1J); PBLD, PSMB9, SEMA4F, TBC1D19, TESK2, TTBK2 (CD4T).

## Priors (`$DATA/priors/`, 848 MB; see `reports/priors.md`)

STRING v12.0 (CC BY 4.0), GO 2026-07-26 + goa_human (CC BY 4.0), UniProt UP000005640 release 2026_03 (CC BY 4.0),
DepMap 24Q4 CRISPRGeneEffect (CC BY 4.0), Reactome v97 (CC0). **Not fetched:** CollecTRI, because its commercial
use could not be verified (it is a composite licence, and OmniPath's commercial filter is a no-op). DepMap releases
newer than 24Q4 are on the bot-gated portal only.

## Blocked / not taken

| dataset | why | what's needed |
|---|---|---|
| X-Atlas/Orion (HCT116: 146 panel targets; HEK293T: 11) | CC BY-NC-SA 4.0 | written permission from Xaira (126 GB parquet on HF) |
| X-Atlas/Pisces (iPSC, HepG2, Jurkat; 16 contexts) | CC BY-NC-SA 4.0; not released yet | Xaira permission + release |
| Illumina Billion Cell Atlas | gated, commercial agreement | contact Illumina BD |
| EMBL CD4⁺ T genome-wide (Moonen et al. 2026) | data not yet public | wait for publication |
| VIPerturb-seq (Satija, K562) | no data location found; K562 anyway | — |
| CollecTRI TF→target | licence unverified | per-source licence review |
| Jiang 2025 signalling + 10 scPerturb screens | ≤ 7 panel targets each | — (validation contexts only) |

## Storage and Drive usage

- **Drive** (`gdrive:` reports 2 TiB total, not 5 TB): 964.7 GiB used, 1.055 TiB free. `VCC2026/data` holds
  86.6 GiB: raw 82.1 GiB (VCC2025_H1 18.9 GB, CD4T summary files 61.4 GB, HipSci 7.9 GB), subsets 3.7 GiB
  (H1, HipSci), priors 0.8 GiB.
- **Not on Drive yet:**
  - **KOLF raw** (189.4 GB) is kept on `$DATA/scratch/KOLF2.1J_iPSC/`.
  - **CD4T and KOLF subsets** (177 GB) are kept on `$DATA/subsets/`.

  Uploads fail because rclone's built-in shared Google client is out of API quota (`Error 403: Quota exceeded …
  'Queries' … project_number:202264815644`). rclone retried the whole 189 GB file three times. **Fix (Rafid):**
  create a Google Cloud OAuth client ID/secret and re-run `rclone config` for `gdrive:` with it (see
  https://rclone.org/drive/#making-your-own-client-id). Then:
  `rclone copy --drive-chunk-size 256M $DATA/scratch/KOLF2.1J_iPSC gdrive:VCC2026/data/raw/KOLF2.1J_iPSC` and
  `rclone copy $DATA/subsets gdrive:VCC2026/data/subsets`. Delete the KOLF raw only after `rclone check`.
  The installed rclone is v1.60.1; upgrading is advisable.
- **CD4 donor-D4 cell files** (412 GB) were deliberately **not** archived: they are public on the authors' MIT S3
  bucket, re-download at about 430 MB/s, and would have exceeded the daily upload quota. Source of record:
  `s3://genome-scale-tcell-perturb-seq/marson2025_data/`.
- **Instance:** `$DATA` (network FS) holds scratch 177 GB (KOLF raw), subsets 177 GB, pb 4.8 GB, priors 0.8 GB.
  Local `/` has 477 GB free. Downloaded today: about 690 GB from external sources, plus a 57 GB partial that was
  discarded when the CD4 download moved to local disk.

## Still running / not needed for batch 1

Nothing is running. The scPerturb overlap check stopped with 5 small libraries unchecked (Zenodo throttles this IP).

## Next batch, if asked

1. Archive KOLF raw and the CD4T/KOLF subsets to Drive after the rclone client fix (~370 GB upload, nothing new to download).
2. KOLF2.1J chromatin-modifier screen (4.6 GB, >20k UMI, same line): test-like depth for its targets.
3. HipSci targeted screen (4.5 GB; 5 panel targets at >1,000 cells) needs a chunked converter.
4. With permission: X-Atlas/Orion (126 GB), the largest remaining gain (HCT116, 146 panel targets).
