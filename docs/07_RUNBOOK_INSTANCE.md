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
`WORK=~/vcc` (code, cloned from the private GitHub repo — see `08_CLAUDE_CODE_WEB.md`), `DATA` = `<first /lambda/nfs/* mount>/vcc-data`, else `~/vcc-data`. `setup_lambda.sh` writes both, plus `PYTHONPATH` and the venv, to `~/.vcc_env`; **every command below assumes `source ~/.vcc_env` first**. In `loco.example.json`, replace `/lambda/nfs/vcc-data` with the real `$DATA`.

---

## E000 — environment + controls inventory
```bash
cd ~/vcc && mkdir -p logs && bash setup_lambda.sh 2>&1 | tee logs/E000_setup.log     # non-interactive; ~10 min
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

## E010–E012 — add K562 GWPS, test-like validation, second leaderboard entry (do these before E007–E009)
Why: E002 showed the panel has no essential genes, and only K562 GWPS measures it (272/300). E004's "seen" setting transferred essential-gene targets between essential-gene screens, which is not what the test looks like. A unit test also showed that B2 adds the *source library's* average response (the essential-gene stress signature) to every prediction. New options fix this: `raw` (use the measured log2FC itself) and `generic_from` (take the generic shift only from panel-like sources, GWPS and H1). `loco.py` now skips source datasets from the same cell line as the held-out one (`line` field), and adds `--panel-file`, `--sources` and `--tag`. `pseudobulk.py` now makes one sequential pass, about 20× faster.

```bash
source ~/.vcc_env; cd ~/vcc; git pull
AXIS=$DATA/challenge/controls/gene_axis.csv
PANEL=$(find $DATA/challenge -name pert_counts.csv | head -1); echo $PANEL
```

**E010: summarise GWPS** (check the obs column and control label with a backed read first; expected `gene` / `non-targeting`, symbols in var `gene_name`):
```bash
tmux new -d -s E010 "source ~/.vcc_env; cd ~/vcc; python -m vcc26.pseudobulk --h5ad $DATA/raw/K562_gwps_raw_singlecell_01.h5ad \
  --pert-col gene --control non-targeting --symbol-col gene_name --gene-axis $AXIS --max-kd 0.7 \
  --out $DATA/pb/K562_GWPS.npz 2>&1 | tee logs/E010.log"
```
Then edit `loco.json`:
- add `"line": "K562"` to the existing K562 entry;
- add a new entry `{"name": "K562_GWPS", "line": "K562", "h5ad": <gwps h5ad>, "pert_col": "gene", "control": "non-targeting", "symbol_col": "gene_name", "summary": "$DATA/pb/K562_GWPS.npz"}` (the real path, not the variable);
- commit.

**CHECK:** report perts kept, genes on the axis, median knockdown, and how many of the 300 panel targets survive the `--max-kd 0.7` filter. If fewer than 200 survive, rerun without `--max-kd` to `K562_GWPS_nokd.npz` and report both.

**E011: test-like local validation** (at most 2 GPU jobs at once; RPE1 ran out of memory with 4–5):
```bash
# (a) panel-aligned holdout: K562 GWPS restricted to the challenge's 300 targets. Sources = the other lines;
#     K562 essential is excluded automatically (same line). Mimics the panel targets nobody else measured.
for mode in seen unseen; do
  python -m vcc26.loco --config loco.json --holdout K562_GWPS --mode $mode --out $DATA/loco/E011 \
    --panel-file $PANEL --specs specs_E011.json 2>&1 | tee -a logs/E011_K562_GWPS_$mode.log
done
# (b) other lines with GWPS as a source; E003 anchors reused. "testlike" = only GWPS (+H1) as sources,
#     which mimics the test (the panel is measured in K562 only).
mkdir -p $DATA/loco/E011; for c in RPE1 HepG2 Jurkat H1; do cp -rn $DATA/loco/E003/holdout_$c $DATA/loco/E011/; done
for c in RPE1 HepG2 Jurkat H1; do
  python -m vcc26.loco --config loco.json --holdout $c --mode seen --out $DATA/loco/E011 \
    --specs specs_E011.json --sources K562_GWPS,H1 --tag testlike 2>&1 | tee -a logs/E011_${c}_testlike.log
  python -m vcc26.loco --config loco.json --holdout $c --mode seen --out $DATA/loco/E011 \
    --specs specs_E011.json --tag all 2>&1 | tee -a logs/E011_${c}_all.log
done
```
The `linear` fallback specs run an SVD over GWPS's ~10k perturbations, which takes a few minutes each.
**REPORT E011:** (a) a table per mode: model × context score and per-metric scaled means, plus `n_panel` / `n_covered`. (b) a table model × held-out line for `testlike` and for `all`. Then compute the **selection score** = 0.9 × (b-testlike mean over the 4 lines) + 0.1 × (a-unseen context score), and name the top spec. Commit the CSVs to `results/E011/`.

**E012: leaderboard entry** (first entry of a new UTC day; state the count before submitting). Use the top E011 spec, written here as `<model>`, `<kw JSON>` and `<fallback>` (`linear` or `none`):
```bash
python -m vcc26.predict_challenge --controls-dir $DATA/challenge/controls --contexts A,B,C --perts $PANEL \
  --gene-names $AXIS --summaries $DATA/pb/K562.npz $DATA/pb/K562_GWPS.npz $DATA/pb/RPE1.npz $DATA/pb/HepG2.npz \
  $DATA/pb/Jurkat.npz $DATA/pb/H1.npz --model <model> --kw '<kw JSON>' --fallback <fallback> --n-control 0 \
  --out $DATA/preds/E012.h5ad
vcc prep $DATA/preds/E012.h5ad -g $AXIS --perts $PANEL --contexts A,B,C -o $DATA/preds/E012.vcc
vcc submit $DATA/preds/E012.vcc -m "E012 <spec name> with K562 GWPS" --wait
```
(The summary file names must stay `K562_GWPS.npz` and `H1.npz`, because `generic_from` matches file names.)
**REPORT E012:** overall and six per-metric scores, and the rank. Compare with E001 (−0.081).

## E013–E014 — validation on non-essential targets, denoising, effect scale, leaderboard entry
Why: E012 scored 0.069 on the leaderboard, while E011(b)'s local estimate was 0.23. Those (b) holdouts score *essential* targets, which have strong effects that transfer easily; the panel's non-essential targets have weak ones. The closest pairs we have are **H1 (VCC 2025 targets) and K562 GWPS, scored in both directions**. New option `denoise`: empirical-Bayes shrinkage of each source's log2FC by its sampling noise, so K562 noise stops producing spurious DE calls (on synthetic data jac rose by about 0.3).

```bash
source ~/.vcc_env; cd ~/vcc; git pull
python -c "import numpy as np, pandas as pd; z=np.load('$DATA/pb/H1.npz', allow_pickle=True); pd.DataFrame({'target_gene': z['perts']}).to_csv('$DATA/h1_targets.csv', index=False); print(len(z['perts']))"
mkdir -p $DATA/loco/E013; cp -rn $DATA/loco/E003/holdout_{H1,RPE1,HepG2,Jurkat} $DATA/loco/E013/
mkdir -p $DATA/loco/E013u; cp -rn $DATA/loco/E011/holdout_K562_GWPS $DATA/loco/E013u/
```
Runs (at most 2 GPU jobs at once):
```bash
# V1: H1 held out, K562 GWPS the only source (most test-like: non-essential targets measured in K562 only)
python -m vcc26.loco --config loco.json --holdout H1 --mode seen --out $DATA/loco/E013 --specs specs_E013.json --sources K562_GWPS --tag V1
# V2: K562 GWPS held out on H1's targets, H1 the only source (reverse direction; new anchors)
python -m vcc26.loco --config loco.json --holdout K562_GWPS --mode seen --out $DATA/loco/E013 --specs specs_E013.json \
  --panel-file $DATA/h1_targets.csv --sources H1 --tag V2
# V3: essential-target lines, sources K562 GWPS + H1 (secondary)
for c in RPE1 HepG2 Jurkat; do
  python -m vcc26.loco --config loco.json --holdout $c --mode seen --out $DATA/loco/E013 --specs specs_E013.json --sources K562_GWPS,H1 --tag V3
done
# V4: challenge-panel targets in K562 GWPS, nothing measured (generic only; reuses E011 anchors)
python -m vcc26.loco --config loco.json --holdout K562_GWPS --mode unseen --out $DATA/loco/E013u --specs specs_E013.json \
  --panel-file $PANEL --tag V4
```
**REPORT E013:**
- a table spec × {V1, V2, V3 mean, V4}, with per-metric scaled scores for V1 and V2;
- `n_panel` / `n_covered` for V1 and V2;
- the **selection score** = 0.35·V1 + 0.35·V2 + 0.2·V3 + 0.1·V4 (pre-registered; don't change the weights after seeing results), and the top spec.

Commit the CSVs to `results/E013/`.

**E014: superseded, don't submit.** The leaderboard entry moves to E017, which also uses the new emission (see E015). Still report E013 in full. Use the E012 command with that spec's `--model`, `--kw` (the spec's kw JSON) and `--fallback none`, output `preds/E014.*`, message `"E014 <spec name>"`.
**REPORT E014:** overall and six per-metric scores, rank, and the comparison with E012 (0.069).

## E015–E017 — emission fix (biggest known lever), context identity, leaderboard entry
Why: the top teams score 0.79 on expression MSE, where every one of our runs scores 0 (clamped), locally too. Our emitter samples a *fresh random* set of control cells for every target, so each predicted pseudobulk carries sampling noise about as large as the weak effects we're predicting. On synthetic data that noise is ~0.2 log2 units RMSE; the new `balanced` emitter gets it to 0.02. That noise counts against MSE (the metric only credits prediction noise when the predictions spread enough), blurs PDS, and creates spurious Wilcoxon calls (jac/fid). The `balanced` emitter uses one herded set of 400 real control cells for all targets and sets each gene's total exactly, so the emitted pseudobulk equals the prediction. On synthetic data: B2 +0.09 to +0.14, MSE 0 → 0.24–0.40 (0.71 with `denoise`); with denoise plus effect scale 1.6, about +0.38.

Run after E013 has finished (it reuses E013's holdouts):
```bash
source ~/.vcc_env; cd ~/vcc; git pull
mkdir -p $DATA/loco/E015 $DATA/loco/E015u
cp -rn $DATA/loco/E013/holdout_* $DATA/loco/E015/; cp -rn $DATA/loco/E013u/holdout_* $DATA/loco/E015u/
# careful: E013 has TWO K562_GWPS holdouts (V2 in E013, V4 in E013u); keep them in separate dirs as above
python -m vcc26.loco --config loco.json --holdout H1 --mode seen --out $DATA/loco/E015 --specs specs_E015.json --sources K562_GWPS --tag V1
python -m vcc26.loco --config loco.json --holdout K562_GWPS --mode seen --out $DATA/loco/E015 --specs specs_E015.json \
  --panel-file $DATA/h1_targets.csv --sources H1 --tag V2
for c in RPE1 HepG2 Jurkat; do
  python -m vcc26.loco --config loco.json --holdout $c --mode seen --out $DATA/loco/E015 --specs specs_E015.json --sources K562_GWPS,H1 --tag V3
done
python -m vcc26.loco --config loco.json --holdout K562_GWPS --mode unseen --out $DATA/loco/E015u --specs specs_E015.json \
  --panel-file $PANEL --tag V4
```
Rows are keyed by `model` and `emit`.

**REPORT E015:**
- a table (model, emit) × {V1, V2, V3 mean, V4} with all six scaled metrics for V1 and V2;
- the ORACLE rows (emitter ceiling: random vs balanced);
- the same selection score as E013 (0.35·V1 + 0.35·V2 + 0.2·V3 + 0.1·V4), and the top (model, emit).

Commit the CSVs to `results/E015/`.

**E016: what are A, B and C?** (CPU, a minute)
```bash
python -m vcc26.context_id --controls-dir $DATA/challenge/controls --contexts A,B,C --gene-axis $AXIS \
  --summaries $DATA/pb/*.npz --out reports/context_id.json
```
**REPORT E016:** the printed similarity table, the marker panel and the most-specific genes per context; commit `reports/context_id.json`. Then give your best guess of each context's cell type, marked as an inference.

**E017: leaderboard entry** (state the day's count first). Submit the top E015 spec if its selection score beats `B2_transfer`+`random` by ≥ 0.02. Use the E012 command with that spec's `--model`/`--kw`, `--fallback none`, **`--emit balanced`** (if the winner is balanced), output `preds/E017.*`, message `"E017 <spec> emit=<emit>"`.
**REPORT E017:** overall and six metrics, rank, and the comparison with E012 (0.069).

## E007 / E008 — A1 calibrated transfer sweeps (after E011/E012; rerun them in the E011 "testlike" setting)
Same loop as E004, with the sweep spec files (both modes, every held-out context):
```bash
for E in E007 E008; do for ctx in <all contexts>; do for mode in seen unseen; do
  python -m vcc26.loco --config loco.json --holdout $ctx --mode $mode --out $DATA/loco/$E \
    --specs specs_$E.json 2>&1 | tee -a logs/${E}_${ctx}_${mode}.log
done; done; done
```
- E007 tests source weighting (tau) and the target-expression gate; E008 tests per-target shrinkage, effect scale beta and the linear fallback for unmeasured targets.
- Reuse the E003 anchors instead of recomputing them: before the loop, `mkdir -p $DATA/loco/$E && cp -r $DATA/loco/E003/holdout_* $DATA/loco/$E/` (loco.py skips anchor building when `anchors.json` exists).
- Rows for A1 include `source_r` / `source_w` (similarity of each source line to the held-out line), `mean_gate`, `n_multi_source`, `n_unmeasured`.

**REPORT E007/E008:** for each spec, mean context score per mode across held-out contexts, the per-metric means, and the best spec per mode. Flag any held-out context where A1 loses to B2.

## E009 — A2 neighbour silencing (after E007/E008)
`fetch_public_data.sh` writes `$DATA/tss.csv`. Fill in the path and run both modes for every held-out context:
```bash
sed "s#__DATA__#$DATA#g" specs_E009.json > specs_E009.local.json
python -m vcc26.neighbors learn --tss $DATA/tss.csv --summaries $DATA/pb/*.npz --out reports/neighbor_prior.json
mkdir -p $DATA/loco/E009 && cp -r $DATA/loco/E003/holdout_* $DATA/loco/E009/
for ctx in <all contexts>; do for mode in seen unseen; do
  python -m vcc26.loco --config loco.json --holdout $ctx --mode $mode --out $DATA/loco/E009 \
    --specs specs_E009.local.json 2>&1 | tee -a logs/E009_${ctx}_${mode}.log
done; done
```
Before E009, update `specs_E009.json` so its `A1_default` row uses the best E007/E008 settings (the planning session will say which).
**REPORT E009:** `reports/neighbor_prior.json` (median neighbour log2FC by distance bin and counts), then the per-mode table as in E007/E008, plus `n_neighbor_targets`.

## Then stop
Print all REPORT blocks together, the hours the instance has run, and a reminder to **terminate the instance if nothing is queued** (the filesystem stays).
