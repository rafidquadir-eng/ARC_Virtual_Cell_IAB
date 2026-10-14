# vcc26 — Immunome AI entry, Virtual Cell Challenge 2026

Runs on the Lambda instance (planning happens in the Claude session). Python 3.12, `cell-eval2==0.18.0`.

| file | what it does |
|---|---|
| `setup_lambda.sh` | env, rclone (Drive + read-only Box), challenge controls, inventory, iMEMORY files for the probe |
| `fetch_public_data.sh` | Replogle 2022 / Nadig 2025 / VCC-2025 H1 downloads + per-context summaries |
| `src/vcc26/inspect_controls.py` | describes `controls.zip` (cells, genes, obs columns, UMIs) → `reports/controls_inventory.json` |
| `src/vcc26/pseudobulk.py` | any Perturb-seq h5ad → compact summary (CPM, log2FC, knockdown) on the challenge gene axis |
| `src/vcc26/models.py` | B0 control, B1 generic, B2 transfer, B3 linear fallback, kNN fallback over any gene embedding |
| `src/vcc26/emit.py` | predicted log2FC → single-cell raw counts by thinning/augmenting real control cells |
| `src/vcc26/local_eval.py` | official vcc2026 metrics + locally built baseline/replicate anchors → scaled scores |
| `src/vcc26/loco.py` | leave-one-context-out validation, `--mode seen|unseen` |
| `src/vcc26/imemory_probe.py` | exports iMEMORY gene vectors (raw text features + trained projection) for the go/no-go |
| `src/vcc26/predict_challenge.py` | builds the A/B/C (or D/E/F) submission h5ad for `vcc prep` |

## Order of operations on day 1
```bash
bash setup_lambda.sh                         # then read reports/controls_inventory.json
# check gene_names.csv has no header row; check the context file names and obs columns
bash fetch_public_data.sh                    # summaries -> $DATA/pb/*.npz
python -m vcc26.predict_challenge --controls-dir $DATA/challenge/controls --contexts A,B,C \
   --perts <pert_counts.csv> --gene-names <gene_names.csv> --summaries $DATA/pb/*.npz \
   --model B1_generic --out $DATA/preds/E001_B1.h5ad
vcc prep $DATA/preds/E001_B1.h5ad -g <gene_names.csv> --perts <pert_counts.csv> --contexts A,B,C -o E001.vcc
vcc submit E001.vcc -m "E001 B1 generic (pipeline check)" --wait
python -m vcc26.loco --config loco.json --holdout RPE1 --mode seen --out $DATA/loco/E002
```

## Verified on synthetic data (planning session, 14 Oct)
The full path (summaries → models → emission → official metrics → anchors → scaled score) runs end to end
on a 3-context synthetic screen. Ordering behaves as expected: control ≈ −3.0, generic ≈ −0.4,
per-target transfer ≈ +0.26 (held-out context, targets measured elsewhere). These are harness checks,
**not** challenge baselines — real numbers come from the instance.

## Ground rules baked in
* Box is read-only (`rclone copy` from `box:` only). iMEMORY files stay on the instance / private Drive.
* Secrets only as shell variables on the instance (`VCC_TOKEN`, `HF_TOKEN`), never in files or chat.
* Model selection uses LOCO scores; leaderboard submissions are logged as calibration points only.
