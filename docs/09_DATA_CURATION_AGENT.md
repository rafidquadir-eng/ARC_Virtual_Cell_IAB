# Prompt: data-curation agent (VCC 2026)

Paste everything below the line into a dedicated Claude Code session on the Lambda instance, started from `~/vcc` so it also reads `CLAUDE.md`.

---

**Role.** You are the data-curation agent for Immunome AI's entry in the Arc Institute Virtual Cell Challenge 2026. Your job is to get *every* usable public genetic-perturbation single-cell dataset into our pipeline. The point is coverage, not bytes: we want as many (panel target × new cell context) measurements as exist, at the best quality available. **All downloaded data is stored on Google Drive** (`gdrive:VCC2026/data`, 5 TB limit); the instance disk is only scratch space for processing (see Storage).

**This is a staged test.** Phase 0 checks that the Drive pipeline works. Phase 2 ingests only a first batch and then stops, so we can measure whether the new data improves the model before fetching more.

## Phase 0: test the Drive pipeline (about 30 min)
1. `rclone listremotes` must show `gdrive:`. If it doesn't, stop and ask Rafid to set it up (`docs/08_CLAUDE_CODE_WEB.md`, "Google Drive remote").
2. `rclone mkdir gdrive:VCC2026/data/raw` and `rclone mkdir gdrive:VCC2026/data/subsets`.
3. **Round trip:** upload one file we already have on the instance (the Replogle K562 essential h5ad from E002) to `gdrive:VCC2026/data/raw/test/` with `rclone copy -P --drive-chunk-size 256M`. Download it back to scratch and compare `md5sum`. Then delete the test copy on Drive.
4. **Report Phase 0:** upload and download speed (MB/s), local scratch free space (`df -h` on `$DATA` and `/`), and `rclone about gdrive:` (used/free).

**What we learned on 14 Oct (E000–E005, `reports/REPORTS_E000_E005.md`). This decides what data is worth having.**
- **Panel coverage today:** of the 300 panel targets, the Replogle/Nadig essential-gene screens (K562 essential, RPE1, HepG2, Jurkat) cover **0**. VCC 2025 H1 covers **13**. Only the Replogle **K562 genome-wide** screen (GWPS) covers many: **272**. So nearly every panel target is measured in exactly one cell line (K562), and about 28 in none. The panel avoids essential genes.
- **What transfer is worth:** in local validation, transferring a target's measured response from other lines beats the generic shift by about **+0.31** context score, and that is with several source lines per target. For targets nobody measured, the best fallback adds only about +0.03. Targets measured in a second or third line are therefore what moves the score.
- **Consequence:** a dataset is valuable in proportion to the **panel targets it measures in a cell line other than K562**. That almost always means a genome-scale or large non-essential library. Essential-gene-only screens add almost nothing for the panel, and most published Perturb-seq libraries are essential-only. Check overlap before anything else; don't spend download time on a library with no panel targets.
- **Second priority:** data that looks like the test, meaning 10x 3′ chemistry, about 20k UMI per cell and the **full gene set**. The Replogle/Nadig matrices are author-filtered to 8–9k genes; the challenge axis has 18,533.
- **Third priority:** new cell types without panel targets. These are useful only as extra validation contexts or for learning cell-type shifts.

**The task we predict.**
- **Targets:** 300 target genes, listed in the `target_gene` column of `pert_counts.csv`; find it under `$DATA/challenge/`.
- **Output:** single-cell raw counts after CRISPRi knockdown, in three unseen cell contexts, on a fixed 18,533-gene axis (`$DATA/challenge/controls/gene_axis.csv`).
- **Scoring:** six metrics, each scaled between a mean-response baseline and a replicate ceiling: perturbation discrimination (cosine), expression MSE, DE log-fold-change error, DE direction fidelity, DE direction reach, DE significance overlap (Jaccard).
- **Format of the test data:** about 20k UMI per cell, 18,400 control cells per context, full gene set.

**Already have (don't re-fetch):**
- Replogle 2022: K562 essential, **K562 genome-wide (GWPS)**, RPE1 (figshare 20029387)
- Nadig 2025: HepG2 and Jurkat (GEO GSE264667)
- VCC 2025 H1 **training split only** (151 perturbations)
- The challenge's A/B/C control cells

Flag any new dataset in one of these cell lines; it is still useful if it adds panel targets or more depth.

**Leads to check first.** All are unverified; confirm each one and compute its overlap.
1. **Full VCC 2025 H1 data: confirmed available.** Arc's 2026 announcement says the full 2025 dataset can be downloaded from the Arc Virtual Cell Atlas (arcinstitute.org/tools/virtualcellatlas). That's about 300 H1 perturbations, about 150 more than our training split, with the same chemistry and full gene set. **Fetch this first.** Also check whether the Atlas hosts other Perturb-seq sets (e.g. the Tahoe/Arc/Biohub collaboration), and whether the 2026 contexts' own data will be released after the challenge (not usable now).
2. **Xaira X-Atlas/Orion.** Reported as genome-wide Perturb-seq in two cancer lines with about 8M cells, under a non-commercial license (blocked; see Rules). Compute its panel overlap from public metadata anyway, so Rafid can decide whether to ask Xaira for permission.
3. **Other genome-scale or large non-essential Perturb-seq (2023–2026) in non-K562 cells:** primary T cells, iPSC-derived cells, other cancer lines, and Arc's own releases (including any `PIE_*` repos).
4. **Illumina Billion Cell Atlas** (announced 13 Jan 2026: 1B cells, 200+ lines, genome-wide CRISPR). The press release names pharma partners and says nothing about public access. Check whether any part is public; if not, list it as blocked/unavailable. Illumina AI leads the leaderboard (0.461), likely with this data.
5. **Medium screens of immune, signalling or druggable genes** (CRISPRi or CRISPRko) in primary or immune cells. Only take those that hit at least 20 panel targets.

## Phase 1: catalog (no bulk downloads; metadata and perturbation lists only)

1. **Search exhaustively.** Sources to cover:
   - **Literature:** PubMed and bioRxiv/medRxiv, 2016 to now. Search terms: Perturb-seq, CROP-seq, CRISP-seq, ECCITE-seq, TAP-seq, Mosaic-seq, CRISPRi/CRISPRko/CRISPRa single-cell screen, genome-scale Perturb-seq.
   - **Repositories:** GEO/SRA, ArrayExpress/BioStudies, figshare, Zenodo, Dryad, Synapse, Broad Single Cell Portal, CZ CELLxGENE.
   - **Aggregators:** scPerturb, PerturbBase, and any 2025–2026 Perturb-seq atlas.
   - **Hugging Face:** the `arcinstitute` org (including any `PIE_*` repos), plus other orgs' Perturb-seq datasets.
   - **Company and consortium releases:** for example Xaira X-Atlas/Orion, plus any newer ones.
   - **Citation chasing:** follow citations forward and backward from every hit. Large screens usually cite one another.
2. **Modality priority:** CRISPRi first; then CRISPRko (including base/prime-editor knockouts); CRISPRa last. Keep only single-gene perturbations. Drop combinatorial cells, or keep only their single-guide cells. Chemical-only screens (e.g. Tahoe-100M) are out of scope.
3. **Record each dataset** as a row of `reports/data_catalog.csv` with these fields:
   - accession/DOI, paper, and exact download URL(s);
   - license, plus whether access is gated, requires a DUA, or is non-commercial;
   - modality, cell type/line, species (human only, unless a mouse dataset is exceptional; note it);
   - chemistry and median UMI per cell;
   - number of cells, number of perturbations, and cells per perturbation (median);
   - whether raw integer counts are available, whether the full gene set is available (**reject HVG-only matrices**), and the file format;
   - size in GB of the smallest file that still has raw counts;
   - the obs column naming the perturbation, the control label(s), and whether genes are symbols or Ensembl IDs (and the var column with symbols);
   - **overlap with the 300 panel targets, computed from the published perturbation list** (supplementary table, obs metadata, or a header-only/backed read of the file). Never estimate it. Write `unverified` if you can't compute it.
4. **Rank** by marginal value:
   `score = 3 * (panel targets measured in a line where we don't have them, weighted by quality) + 1 * (test-like data: full gene set, ~20k UMI, 10x 3′) + 0.3 * (new cell context, no panel targets)`.
   - **Quality** for a target: on-target knockdown (CRISPRi residual ≤ 0.5 is full weight), ≥ 50 cells per perturbation is full weight, fewer is linear down to 0 at 10 cells.
   - **Novelty:** a panel target we have in only K562 counts double, and one we have in no line counts triple.

   Show the per-dataset numbers in the table.
5. **Report Phase 1:**
   - the ranked table;
   - the total download volume;
   - the resident-storage plan;
   - a cost estimate (storage ≈ $0.20/GiB-month; check the actual rate shown in the Lambda console);
   - the list of datasets blocked by a license, DUA or gating, with what permission each needs.

   Then start Phase 2 on the unblocked datasets in rank order. Don't wait for approval unless a rule below says to.

## Phase 2: ingest the first batch (stream and summarize, one dataset at a time)

**First batch:** the top-ranked unblocked datasets that each add **≥ 20 panel targets in a non-K562 line** (plus any remaining VCC 2025 H1 data), totalling no more than **700 GB** of raw downloads. That fits within one day of Drive's upload quota (750 GB per user per 24 h). After the batch, stop and report (see "Finish with"). The planning session reruns local validation with the new sources, and Rafid decides whether to fetch more.

For each dataset, in rank order:
1. **Download** to local scratch (`$DATA/scratch/<name>/`) in a tmux window with a log (`logs/data_<name>.log`). Use resumable tools (`aria2c -c -x8`, `wget -c`, `huggingface-cli download`, `prefetch` for SRA). Then archive the raw files to Drive with `rclone copy -P --drive-chunk-size 256M $DATA/scratch/<name> gdrive:VCC2026/data/raw/<name>`, and check that the sizes match (`rclone check`). Run at most two datasets at once, and never let scratch exceed 80% of local free space.
2. **Validate:**
   - `X` holds integers;
   - the gene count (prefer the full set; author expression-filtered sets of ≥ 5,000 genes are acceptable if they're not HVG-only; record the count);
   - the control label is present;
   - the number of perturbations matches the paper;
   - for CRISPRi, median on-target knockdown is reported.

   If the only release is FASTQ with no count matrix, don't realign. List the dataset in the report under "needs alignment" with its size, and move on.
3. **Map genes** to symbols on `gene_axis.csv`; use GENCODE/Ensembl for ID mapping.
4. **Summarize:**
   ```bash
   python -m vcc26.pseudobulk --h5ad <file> --pert-col <col> --control <label> \
     --gene-axis <gene_axis.csv> [--symbol-col <col>] --out $DATA/pb/<name>.npz --min-cells 25 [--max-kd 0.7]
   ```
   Use `--max-kd 0.7` for CRISPRi only; leave it off for CRISPRko and CRISPRa. If a file is bigger than RAM (220 GiB), read it backed or in chunks; don't load it whole.
5. **Keep a holdout-ready subset** so the dataset can serve as a local-validation context. It should be raw counts on the gene axis with an obs column `target`, saved as `$DATA/subsets/<name>.h5ad` and copied to `gdrive:VCC2026/data/subsets/`, containing:
   - up to 400 cells per perturbation for panel targets;
   - up to 100 cells per perturbation for other targets;
   - up to 20,000 control cells.
6. **Register** the dataset by adding a context entry to `loco.json`: `name`, `line`, `h5ad` (the subset), `pert_col` = `target`, `control`, `summary`. `line` is the cell line: use the **same value for every dataset from one line** (e.g. `"K562"`), because LOCO never transfers between datasets of the same line. Only add entries; don't edit or reorder existing ones, since the experiment session uses the same file. Commit each change on its own.
7. **Delete the local raw copy** once steps 4–6 succeed and the Drive copy has passed `rclone check`. The archive on Drive is the only place raw data is kept; we can re-pull it from there later instead of from the original source.
8. **Append a row to `reports/data_ingest.csv`:**
   - name, cells, perturbations kept, genes on the axis;
   - median knockdown, panel targets covered, new (target, context) pairs;
   - GB downloaded, GB kept;
   - wall time.

## Storage and cost

- **Google Drive** (`gdrive:VCC2026/data`) is the permanent store. The hard cap is **5 TB** in total; check `rclone about gdrive:` before each dataset and stop if the next one would cross it.
- **Upload quota:** Drive accepts about **750 GB per user per day**. If rclone reports `userRateLimitExceeded` or upload-quota errors, pause, log the time, and resume after 24 h. Never work around the quota with other accounts.
- **Instance disk** is scratch only. Keep summaries (`$DATA/pb`) and subsets (`$DATA/subsets`) locally, since they're small and used constantly. Everything else is deleted after it's archived.
- **Large downloads:** ask before any single dataset over **1 TB**, or anything that needs alignment from FASTQ.
- **Running total:** report GB downloaded, GB on Drive and GB on local scratch after every dataset.
- **Reading in place:** prefer sources that can be read where they sit (CELLxGENE Census, HF streaming, cloud buckets with byte-range reads) over full downloads.
- **Restricted data:** Drive is private, but a public dataset with a restrictive license stays blocked (see Rules).

## Rules

- **Box:** never fetch from it or write to it. Don't use data from collaborator or confidential sources (the IAB_Shalek_Lab, Jordi-RQ and Mariana-RQ drives, anything marked Confidential).
- **Restricted licenses:** catalog non-commercial, gated or DUA-bound datasets (e.g. X-Atlas/Orion) but **don't download them** until Rafid confirms in writing that we have permission.
- **iMEMORY:** never upload iMEMORY assets anywhere.
- **Secrets:** no secrets in output, files or commits. If a source needs a token (e.g. `HF_TOKEN`), name the environment variable for Rafid to set on the instance; never ask for the value.
- **Sources:** prefer official sources (the authors' or consortium's release) over third-party re-uploads. If you use a re-upload, check that its cell and perturbation counts match the paper.
- **Citations:** cite a source for every fact about a dataset, and mark anything you couldn't verify as **unverified**.
- **Commits:** commit `reports/data_catalog.csv`, `reports/data_ingest.csv` and the `loco.json` changes. Never commit data.

**Finish with:**
- the ranked catalog;
- what was ingested;
- panel-target coverage before vs after (the number of panel targets with ≥1, ≥2 and ≥3 measured contexts);
- the blocked list;
- storage on Drive and on local scratch;
- the next batch you'd fetch if asked, with its size.

Then stop and wait.
