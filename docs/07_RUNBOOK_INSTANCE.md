# Runbook for Claude Code on the Lambda instance (E000–E005)

You are running Immunome AI's Virtual Cell Challenge 2026 baselines. Planning happens in a separate Claude session; your job is to execute these steps, stop at each **CHECK**, and print the **REPORT** blocks so the user can paste them back.

## Hard rules
- Box is **read-only**: only `rclone copy box:... <local>`. Never write, move or delete anything on `box:`.
- Never upload iMEMORY files (`phase2_v4_best.pt`, `gene_mean_embedding.npy`, anything from `$DATA/imemory`) anywhere except the private `gdrive:VCC2026/checkpoints_private`.
- Secrets live only in shell variables (`VCC_TOKEN`, `HF_TOKEN`). Never write them to files, logs or git.
- Do not tune anything against the leaderboard. Leaderboard entries happen only where this runbook says so.
- At most **2 leaderboard submissions per UTC day**. Before each `vcc submit`, state how many have been used today.
- If anything costs more than this runbook implies (new instances, big downloads > 300 GB), stop and ask.

## Paths
`WORK=~/vcc` (code, synced from the repo with rsync — see `08_CLAUDE_CODE_WEB.md`), `DATA` = `<first /lambda/nfs/* mount>/vcc-data`, else `~/vcc-data`. `setup_lambda.sh` writes both, plus `PYTHONPATH` and the venv, to `~/.vcc_env`; **every command below assumes `source ~/.vcc_env` first**. In `loco.example.json`, replace `/lambda/nfs/vcc-data` with the real `$DATA`.

---

## E000 — environment + controls inventory
```bash
cd ~/vcc && bash setup_lambda.sh 2>&1 | tee logs/E000_setup.log     # non-interactive; ~10 min
source ~/.vcc_env
```
**CHECK:**
- `python -c "import cell_eval2, gpudge"` works; otherwise use `--de-backend pdex` everywhere below.
- `vcc whoami` shows the team and that it can submit.
- `reports/controls_inventory.json` exists.
- From the inventory, identify and write down: (1) the per-context control files for A, B, C; (2) the gene-name file (header row or not); (3) the perturbation-list file and its column names; (4) the obs columns and control label; (5) median UMIs and cells per context.
- If `gene_names.csv` has a header row, write a header-less copy `gene_axis.csv` and use that everywhere.
- Run `vcc --help` and `vcc prep --help`; record the exact required flags and obs column names (`target_gene`? `context`?).

**REPORT E000:** the five inventory items above, the `vcc prep` contract, the GPU name, free disk.

## E001 — pipeline-check leaderboard entry (generic shift)
E001 needs at least one source summary, so do the Replogle K562 part of E002 first (below), then:
```bash
python -m vcc26.predict_challenge --controls-dir $DATA/challenge/controls --contexts A,B,C \
  --perts <pert list file> --gene-names <gene_axis.csv> --summaries $DATA/pb/K562.npz \
  --model B1_generic --pert-col <column vcc prep expects> --out $DATA/preds/E001_B1.h5ad
vcc prep $DATA/preds/E001_B1.h5ad -g <gene_axis.csv> --perts <pert list> --contexts A,B,C -o $DATA/preds/E001.vcc
vcc submit $DATA/preds/E001.vcc -m "E001 B1 generic (pipeline check)" --wait
```
If `find_ctx` can't match the context file names, patch `predict_challenge.find_ctx` minimally and note the change.
**CHECK:** `vcc prep` passes; the submission is scored.
**REPORT E001:** overall score and the six per-metric scaled scores as shown by the CLI/leaderboard; leaderboard rank if visible.

## E002 — public data and summaries
```bash
bash fetch_public_data.sh 2>&1 | tee logs/E002_fetch.log
```
- Inspect each downloaded h5ad: `obs` columns, control label, whether `var_names` are symbols or Ensembl IDs, and whether X is raw integer counts. Fix the `summ` calls (pert col, control label, symbol col) accordingly.
- Nadig HepG2/Jurkat: pick raw-count, full-gene files from the HF listing; if only HVG-filtered files exist, report it and skip them (do not use HVG-only data).
- VCC 2025 H1: if no download link is found in 20 minutes, report and skip.
- Build summaries for every context available: `python -m vcc26.pseudobulk ... --max-kd 0.7`.
**CHECK:** every summary prints its number of perts, genes on axis (expect > 12,000 of 18,533 for 10x 3′ data) and median knockdown (expect < 0.4).
**REPORT E002:** table of context, file, cells, perts kept, genes on axis, median knockdown; overlap of the A/B/C 300 targets with each source's perts.

## E003 — LOCO anchors
- Copy `loco.example.json` to `loco.json`; fill in real paths, pert cols, control labels, symbol cols for every context from E002.
- For each held-out context run once (anchors are cached in `$DATA/loco/E003/holdout_<ctx>/anchors.json`):
```bash
python -m vcc26.loco --config loco.json --holdout <ctx> --mode seen --out $DATA/loco/E003 \
  --specs specs_B0.json
```
**CHECK:** `pds_cosine` baseline is 0.500 (± 0.01) in every anchors.json; replicate r for pds above 0.85; replicate_sd small (≤ 0.03 on every metric). If r ≤ b on any metric, report it and stop.
**REPORT E003:** per context, b and r for all six metrics, and run time.

## E004 / E005 — baselines B0–B3
```bash
for ctx in <all contexts>; do
  for mode in seen unseen; do
    python -m vcc26.loco --config loco.json --holdout $ctx --mode $mode --out $DATA/loco/E004 \
      --specs specs_baselines.json 2>&1 | tee -a logs/E004_${ctx}_${mode}.log
  done
done
```
(`specs_baselines.json` = B0, B1, B2 at alpha 1.0 and 0.6, B3 linear fallback.)
**CHECK:** B0 < B1 on mean context score in every context (if not, report it; something is wrong with emission or anchors).
**REPORT E004/E005:** one table per mode: rows = model, columns = held-out context, cell = context score; plus per-metric means across contexts. Then append rows to `EXPERIMENT_LOG.md` and `rclone copy` the CSVs to `gdrive:VCC2026/logs/`.

## Then stop
Print all REPORT blocks together, the hours the instance has run, and a reminder to **terminate the instance if nothing is queued** (the filesystem stays).
