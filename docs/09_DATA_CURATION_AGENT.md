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

**Why this matters.** Our current model scores too low. Its strongest component transfers the measured response of the *same target gene* from other cell lines into the unseen test context. So a dataset is worth fetching if it does any of these:
- measures panel targets in a cell context we don't have yet (most valuable);
- adds more cells or contexts for panel targets we have in only one or two lines;
- adds new cell contexts at all, even without panel targets. These help us learn how responses change between cell types, and they can serve as extra held-out contexts for local validation.

**The task we predict.**
- **Targets:** 300 target genes, listed in the `target_gene` column of `pert_counts.csv` under `$DATA/challenge/`.
- **Output:** single-cell raw counts after CRISPRi knockdown, in three unseen cell contexts, on a fixed 18,533-gene axis (`gene_axis.csv`).
- **Scoring:** six metrics, each scaled between a mean-response baseline and a replicate ceiling: perturbation discrimination (cosine), expression MSE, DE log-fold-change error, DE direction fidelity, DE direction reach, DE significance overlap (Jaccard).
- **Format of the test data:** the challenge contexts are roughly 10x 3′ data at about 20k UMI per cell. Data that looks like that is the best match.

**Already have (don't re-fetch):**
- Replogle 2022: K562 essential, K562 genome-wide, RPE1
- Nadig 2025: HepG2 and Jurkat
- VCC 2025 H1 training split
- The challenge's A/B/C control cells

Flag any new dataset in one of these cell lines; it is still useful if it adds panel targets or more depth.

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
4. **Rank** by marginal value. For each dataset, count new (panel target, cell context) pairs it adds beyond what we already hold. Weight each pair by:
   - **quality:** median on-target knockdown for CRISPRi (lower residual expression is better), cells per perturbation, UMI depth;
   - **novelty:** a target we have in only one context gains more than one we have in four.

   Add a smaller term for new cell contexts that have no panel overlap. Show the formula you used in the report.
5. **Report Phase 1:**
   - the ranked table;
   - the total download volume;
   - the resident-storage plan;
   - a cost estimate (storage ≈ $0.20/GiB-month; check the actual rate shown in the Lambda console);
   - the list of datasets blocked by a license, DUA or gating, with what permission each needs.

   Then start Phase 2 on the unblocked datasets in rank order. Don't wait for approval unless a rule below says to.

## Phase 2: ingest the first batch (stream and summarize, one dataset at a time)

**First batch:** the top-ranked unblocked datasets, totalling no more than **700 GB** of raw downloads. That fits within one day of Drive's upload quota (750 GB per user per 24 h). After the batch, stop and report (see "Finish with"). The planning session reruns local validation with the new sources, and Rafid decides whether to fetch more.

For each dataset, in rank order:
1. **Download** to local scratch (`$DATA/scratch/<name>/`) in a tmux window with a log (`logs/data_<name>.log`). Use resumable tools (`aria2c -c -x8`, `wget -c`, `huggingface-cli download`, `prefetch` for SRA). Then archive the raw files to Drive with `rclone copy -P --drive-chunk-size 256M $DATA/scratch/<name> gdrive:VCC2026/data/raw/<name>`, and check that the sizes match (`rclone check`). Run at most two datasets at once, and never let scratch exceed 80% of local free space.
2. **Validate:**
   - `X` holds integers; there are more than 15,000 genes;
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
6. **Register** the dataset by adding a context entry to `loco.json` (`name`, `h5ad` = the subset, `pert_col` = `target`, `control`, `summary`).
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
