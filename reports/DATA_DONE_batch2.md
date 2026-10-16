# DATA DONE — curation batch 2 (16 Oct 2026, ~05:00 UTC)

The runbook session did batch 2 (`docs/09` D7–D11, `docs/13` §2 B1) in the order R asked: D10 first, then D7, D8, D9, D11.
Per-dataset rows: `reports/data_ingest.csv`. D7 numbers: `reports/d7_artifact_check.csv`. Experiments on the new data: `reports/REPORTS_E025_E027.md` (E025b).

## Ranked catalog additions

| rank | dataset | line | panel targets measured (≥ 50 cells) | licence | status |
|---|---|---|---|---|---|
| 1 | X-Atlas/Orion HCT116 (Xaira, HF parquet) | HCT116 (colorectal carcinoma, epithelial) | 255 (300 in raw) | CC BY-NC-SA 4.0 (approved by R, 15 Oct) | **ingested** |
| 2 | X-Atlas/Orion HEK293T | HEK293T (embryonic kidney, epithelial) | 250 (300 in raw) | CC BY-NC-SA 4.0 | **ingested** |
| 3 | X-Atlas/Pisces (Jurkat rest/active, HepG2, iPSC, …) | several | – | CC BY-NC-SA 4.0 | **not released**: the HF repo holds only its README/LICENSE ("Coming Soon") |
| 4 | Myllia A549 Perturb-seq (GEO GSE337804) | A549 (lung carcinoma) | 15 of 218 library genes | GEO public | below the ≥ 20 cut; catalog only |
| 5 | Jurkat genome-scale CRISPRi (Nat Cell Biol 2025, s41556-025-01626-9) | Jurkat | – | – | TAP-seq readout of 374 genes only, so it can't give full-axis summaries; no accession found (**unverified**) |
| – | LINCS L1000 CRISPR KO (CMap LINCS 2020) | 248 lines, 978 landmark genes | not checked | CMap terms: academic, non-profit only; redistribution prohibited | **blocked** (licence) |

D8 search (HeLa, cervical/ovarian, squamous/keratinocyte/airway basal, MOLT-4/CCRF-CEM): no other single-cell CRISPR screen with ≥ 20 panel targets found.

## What was ingested

**D10 Orion** (`scripts/convert_orion.py`: streams the 332 parquet batch files into a CSR h5ad on the challenge axis, keeping `pass_guide_filter` cells)

| context | cells | perts kept | median remaining (kd) | panel in summary / ≥ 50 cells | ctrl cells | median UMI | GEM batches |
|---|---|---|---|---|---|---|---|
| Orion_HCT116 | 3,409,169 | 15,476 | 0.245 | 277 / 255 | 165,777 | 17,292 | 109 |
| Orion_HEK293T | 4,534,299 | 14,280 | 0.434 | 263 / 250 | 218,838 | 20,699 | 223 |

- Summaries: `--strata-col sample --max-kd 0.7 --min-cells 25`. Knockdown matches the paper (75.4 % / 51.5 %).
- Subsets: ≤ 400 cells per panel target, ≤ 100 for other targets, 18,400 controls (84 GB and 111 GB).
- `loco.json` entries `Orion_HCT116` / `Orion_HEK293T`: `line` HCT116 / HEK293T, `library` genome_wide, `lineage` epithelial,
  `licence` "CC BY-NC-SA 4.0".
- The V\* dry run now lists 5 held-out lines: CD4T_Stim8hr 278, KOLF2.1J 258, K562_GWPS 255, **Orion_HCT116 255, Orion_HEK293T 250**.
- Code fix: `pseudobulk --strata-col` kept a dense (targets × strata) × genes array (about 300 TB for Orion). It now keeps per-target totals plus
  per-stratum control totals; output is identical (checked against the old code).

**D7 composition-matched controls** (swapped into `$DATA/pb/` in place; originals kept as `*_pooled.npz`)
- K562, K562_GWPS, RPE1, HepG2, Jurkat: `--strata-col gem_group`. CD4T ×3: `--strata-col donor_id` (4 donors).
- Donor artefact, measured as the median |lfc| on male-specific chrY genes (CPM ≥ 5) above the noise floor at matched expression:
  CD4T_Rest 0.417 → 0.077 (**5.4×**), CD4T_Stim8hr 0.404 → 0.122 (3.3×), CD4T_Stim48hr 0.380 → 0.070 (**5.4×**). The single-donor lines are unchanged.
  There are no HLA genes on the challenge axis, so that part of the check can't be run.
- HipSci was **not** rebuilt. Only 48 cells carry NonTarget guides (499,950 are "unassigned"), below D7's ≥ 2,000 cells. The old summary stays.
- E025b proxy: the E021 config goes from 0.454 to 0.457 and B1_gPL from 0.394 to 0.407; the top B4s are unchanged.

**D11:** DepMap 24Q4 `OmicsExpressionProteinCodingGenesTPMLogp1.csv` (1,673 models, md5 matches figshare) is in `$DATA/priors/depmap/`,
next to the existing `Model.csv` (CC BY 4.0, figshare 10.25452/figshare.plus.27993248).

## Panel-target coverage (by distinct cell line, "measured" = in a summary)

| | ≥ 1 line | ≥ 2 lines | ≥ 3 lines |
|---|---|---|---|
| before batch 2, ≥ 25 cells | 299 | 290 | 240 |
| **after**, ≥ 25 cells | **300** | **300** | **293** |
| before batch 2, ≥ 50 cells | 299 | 284 | 221 |
| **after**, ≥ 50 cells | **300** | **298** | **287** |

EPHB2, the only previously unmeasured target, is now measured. Per line (≥ 50 cells): CD4T 281, KOLF2.1J 258, HCT116 255, K562 254, HEK293T 250, H1 25, HipSci 19.

## Blocked list (updated)

| dataset | why |
|---|---|
| X-Atlas/Pisces | not uploaded yet ("Coming Soon"); approved when it appears |
| LINCS L1000 / CMap | academic, non-profit terms; commercial access only by contacting the Broad |
| CollecTRI | licence unverified (unchanged) |
| Illumina Billion Cell Atlas, EMBL CD4⁺ T (Moonen 2026) | unchanged (gated / not public) |

## Storage

- **Drive** (own OAuth client, rclone v1.75.2): 1.508 TiB used of 2 TiB, 502 GiB free. Archived and verified with `rclone check` (0 differences):
  - KOLF raw (189 GB);
  - CD4T×3 / KOLF / H1 / HipSci subsets;
  - Orion subsets (195 GB);
  - Orion summaries (`VCC2026/data/pb/`).

  The KOLF raw is deleted from scratch.
- **Not archived (public sources):** the Orion raw parquet (HF, re-download about 4 min at 650 MB/s) and the CD4T D4 cell files (S3, unchanged).
- **Instance scratch still held, deletable when you say so (it can all be rebuilt):**

  | path | size | rebuild time |
  |---|---|---|
  | `~/scratch/orion/data` (parquet) | 120 GB | re-download ~4 min |
  | `$DATA/scratch/orion/*.h5ad` (converted) | 308 GB | ~3 h with `convert_orion.py` |
  | `$DATA/scratch/d7` (CD4T pseudobulk file + HipSci CSVs/h5ad) | 92 GB | on Drive / re-convertible |
- **Network FS:** subsets 371 GB, pb 16 GB, priors 1.3 GB.

## Next batch, if asked
1. Pisces when Xaira uploads it (Jurkat genome-wide is the closest public line to context A; HepG2; iPSC). Size unknown.
2. KOLF2.1J chromatin-modifier screen (4.6 GB; > 20k UMI, same line).
3. HipSci targeted screen (4.5 GB; 5 panel targets at > 1,000 cells; needs a chunked converter).
4. Re-run V\* (E020-style) with the 5 held-out lines, the D7 summaries and Orion as sources/held-out lines. That's planning's call.
