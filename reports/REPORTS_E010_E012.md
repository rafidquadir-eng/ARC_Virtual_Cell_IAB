# REPORT blocks E010–E012 — Lambda instance, 14–15 Oct 2026

Runbook: `docs/07_RUNBOOK_INSTANCE.md` (E010–E012, commit eabd2d0). Raw results: `results/E011/`.
Scores are scaled vcc2026 metrics (0 = mean-response baseline, 1 = replicate); context score = mean of the six. DE backend gpudge on the A100.

---

## REPORT E010 — K562 GWPS summary

Input `$DATA/raw/K562_gwps_raw_singlecell_01.h5ad` (65.8 GB, 1,989,578 cells × 8,248 genes). Checked with a backed read: obs `gene` = target symbol, control `non-targeting` (75,328 cells), symbols in var `gene_name`, Ensembl var_names, raw counts.

`python -m vcc26.pseudobulk --pert-col gene --control non-targeting --symbol-col gene_name --gene-axis gene_axis.csv --max-kd 0.7 --out $DATA/pb/K562_GWPS.npz`

| Perts kept | Genes on axis (of 18,533) | Median knockdown | Panel targets surviving `--max-kd 0.7` | Run time / peak RAM |
|---|---|---|---|---|
| 9,315 | 7,681 | 0.153 | **263 / 300** | 1,016 s / 12.7 GB |

**CHECK:** 263 ≥ 200, so the no-`--max-kd` rerun (`K562_GWPS_nokd.npz`) was not needed. (272/300 panel targets are in the raw screen; 9 are dropped by the knockdown filter or min-cells.)

`loco.json` updated and committed: `"line": "K562"` on the K562 entry, new `K562_GWPS` entry (line K562, pert_col `gene`, control `non-targeting`, symbol_col `gene_name`, summary `$DATA/pb/K562_GWPS.npz`).

---

## REPORT E011 — test-like local validation (`specs_E011.json`)

Run two jobs at a time (`scripts/run_e011.sh`); all 10 runs exit 0. E003 anchors reused for RPE1/HepG2/Jurkat/H1; K562_GWPS anchors built fresh (`results/E011/anchors_K562_GWPS.json`).

Coverage per run (from the loco log):

| Held-out | Sources | Panel targets (`n_panel`) | Measured in ≥ 1 source (`n_covered`) |
|---|---|---|---|
| K562_GWPS (a, seen) | RPE1, HepG2, Jurkat, H1 (K562 excluded: same line) | 213 | 12 |
| K562_GWPS (a, unseen) | same | 213 | 0 |
| RPE1 testlike / all | H1, K562_GWPS / all five others | 300 | 280 / 299 |
| HepG2 testlike / all | H1, K562_GWPS / all five others | 300 | 281 / 300 |
| Jurkat testlike / all | H1, K562_GWPS / all five others | 300 | 289 / 300 |
| H1 testlike / all | K562_GWPS / all five others | 147 | 127 / 130 |

K562_GWPS (a) has 213 rather than 300 panel targets because `--panel-file` keeps the challenge targets that GWPS measured with enough cells.

### (a) K562_GWPS panel holdout, seen

| model             |   context_score |    pds |   mse |   fid |   reach |    jac |   nmae |
|:------------------|----------------:|-------:|------:|------:|--------:|-------:|-------:|
| B1_generic        |           0.042 | -0.005 |     0 | 0.791 |   0.083 | -0.632 |  0.017 |
| B1_gPL            |          -0.026 | -0.044 |     0 | 0.485 |   0.066 | -0.624 | -0.042 |
| B2_transfer       |           0.059 |  0.065 |     0 | 0.796 |   0.093 | -0.632 |  0.029 |
| B2_raw_gPL        |          -0.011 |  0.046 |     0 | 0.508 |   0.033 | -0.623 | -0.029 |
| B2_raw_gPL_a0.8   |          -0.007 |  0.057 |     0 | 0.506 |   0.019 | -0.616 | -0.009 |
| B3_raw_gPL_linear |           0.024 |  0.094 |     0 | 0.601 |   0.065 | -0.613 | -0.005 |
| A1_gPL            |          -0.007 |  0.057 |     0 | 0.506 |   0.019 | -0.616 | -0.009 |
| A1_gPL_linear     |           0.001 | -0.003 |     0 | 0.575 |   0.047 | -0.606 | -0.007 |

### (a) K562_GWPS panel holdout, unseen

| model             |   context_score |    pds |   mse |   fid |   reach |    jac |   nmae |
|:------------------|----------------:|-------:|------:|------:|--------:|-------:|-------:|
| B1_generic        |           0.032 |  0.014 |     0 | 0.794 |   0.025 | -0.632 | -0.009 |
| B1_gPL            |          -0.015 |  0.059 |     0 | 0.459 |   0.048 | -0.628 | -0.028 |
| B2_transfer       |           0.032 |  0.014 |     0 | 0.794 |   0.025 | -0.632 | -0.009 |
| B2_raw_gPL        |          -0.015 |  0.059 |     0 | 0.459 |   0.048 | -0.628 | -0.028 |
| B2_raw_gPL_a0.8   |          -0.015 |  0.059 |     0 | 0.459 |   0.048 | -0.628 | -0.028 |
| B3_raw_gPL_linear |          -0.025 | -0.064 |     0 | 0.56  |   0.023 | -0.619 | -0.05  |
| A1_gPL            |          -0.015 |  0.059 |     0 | 0.459 |   0.048 | -0.628 | -0.028 |
| A1_gPL_linear     |          -0.016 | -0.003 |     0 | 0.497 |   0.038 | -0.612 | -0.015 |

Notes on (a): every spec is within ±0.06 of the baseline. jac is about −0.62 for all specs, i.e. every prediction's significant-gene set overlaps the truth less than the mean-response baseline does. In this holdout `generic_from = [K562_GWPS, H1]` can only use H1 (K562_GWPS is held out), so the *gPL* specs use an H1-only generic shift; that lowers fid (0.79 → 0.46–0.60).

### (b) held-out lines, sources = testlike (K562_GWPS + H1), seen: context score

| model             |   RPE1 |   HepG2 |   Jurkat |     H1 |   mean |
|:------------------|-------:|--------:|---------:|-------:|-------:|
| B1_generic        | -0.242 |  -0.113 |   -0.051 | -0.069 | -0.119 |
| B1_gPL            | -0.242 |  -0.113 |   -0.051 | -0.069 | -0.119 |
| B2_transfer       |  0.127 |   0.264 |    0.356 |  0.175 |  0.23  |
| B2_raw_gPL        |  0.132 |   0.264 |    0.346 |  0.175 |  0.229 |
| B2_raw_gPL_a0.8   |  0.101 |   0.249 |    0.338 |  0.181 |  0.217 |
| B3_raw_gPL_linear |  0.129 |   0.265 |    0.352 |  0.175 |  0.23  |
| A1_gPL            |  0.102 |   0.24  |    0.335 |  0.172 |  0.212 |
| A1_gPL_linear     |  0.109 |   0.242 |    0.336 |  0.173 |  0.215 |

### (b) held-out lines, sources = all, seen: context score

| model             |   RPE1 |   HepG2 |   Jurkat |     H1 |   mean |
|:------------------|-------:|--------:|---------:|-------:|-------:|
| B1_generic        | -0.183 |  -0.017 |    0.036 |  0.076 | -0.022 |
| B1_gPL            | -0.242 |  -0.113 |   -0.051 | -0.069 | -0.119 |
| B2_transfer       |  0.253 |   0.434 |    0.42  |  0.169 |  0.319 |
| B2_raw_gPL        |  0.261 |   0.42  |    0.411 |  0.184 |  0.319 |
| B2_raw_gPL_a0.8   |  0.216 |   0.404 |    0.394 |  0.189 |  0.301 |
| B3_raw_gPL_linear |  0.265 |   0.42  |    0.411 |  0.19  |  0.321 |
| A1_gPL            |  0.181 |   0.39  |    0.386 |  0.186 |  0.286 |
| A1_gPL_linear     |  0.181 |   0.39  |    0.386 |  0.192 |  0.287 |

Notes on (b): in `testlike` the generic shift already comes only from GWPS + H1, so B1_generic = B1_gPL there. Transfer specs gain about +0.35 over generic in both settings; `all` is about +0.09 higher than `testlike` because the essential-library lines add measurements of the held-out line's (essential) panel targets. α = 0.8 and A1 are consistently a little below α = 1.0 B2.

### Selection score = 0.9 × (b-testlike mean) + 0.1 × (a-unseen context score)

| model             |   selection |   b_testlike_mean |   a_unseen |
|:------------------|------------:|------------------:|-----------:|
| B2_transfer       |       0.211 |             0.23  |      0.032 |
| B2_raw_gPL        |       0.205 |             0.229 |     -0.015 |
| B3_raw_gPL_linear |       0.205 |             0.23  |     -0.025 |
| B2_raw_gPL_a0.8   |       0.194 |             0.217 |     -0.015 |
| A1_gPL_linear     |       0.192 |             0.215 |     -0.016 |
| A1_gPL            |       0.189 |             0.212 |     -0.015 |
| B1_generic        |      -0.104 |            -0.119 |      0.032 |
| B1_gPL            |      -0.108 |            -0.119 |     -0.015 |

**Top spec: `B2_transfer`** (alpha 1.0, no `raw`, no `generic_from`, no fallback). The margin over `B2_raw_gPL` / `B3_raw_gPL_linear` is 0.006 and comes entirely from the (a)-unseen term (0.032 vs −0.015/−0.025, where B2_transfer reduces to B1_generic); on the b-testlike mean they are tied (0.230 / 0.229 / 0.230). So the selection does not clearly separate the leak-fixed variants from plain B2.

CSVs: `results/E011/scores_*.csv` (10 files) and `results/E011/anchors_K562_GWPS.json`.

---

## REPORT E012 — leaderboard entry (top E011 spec)

Submissions used on 15 Oct (UTC) before this entry: 0 → this is **1 of 2** for 15 Oct.

```
python -m vcc26.predict_challenge --controls-dir $DATA/challenge/controls --contexts A,B,C --perts pert_counts.csv \
  --gene-names gene_axis.csv --summaries pb/K562.npz pb/K562_GWPS.npz pb/RPE1.npz pb/HepG2.npz pb/Jurkat.npz pb/H1.npz \
  --model B2_transfer --kw '{"alpha": 1.0}' --fallback none --n-control 0 --out preds/E012.h5ad
vcc prep preds/E012.h5ad -g gene_axis.csv --perts pert_counts.csv --contexts A,B,C -o preds/E012.vcc   # passed
vcc submit preds/E012.vcc -m "E012 B2_transfer with K562 GWPS" --wait
```
(`--fallback none` is explicit because `predict_challenge` defaults to `linear`, and the E011 spec has no fallback.)

| Metric | E012 | E001 (B1 generic, K562 essential only) | Δ |
|---|---|---|---|
| Entry | `aZXPOs2QkOuKb5oZQzYu`, published | `nurtW5XlQHa9XLcPGbdY` | |
| **Overall** | **0.0691** | −0.0813 | **+0.150** |
| pds | 0.3125 | 0.0125 | +0.300 |
| mse | 0.0000 | 0.0000 | 0 |
| nmae | 0.0421 | 0.0149 | +0.027 |
| fid | −0.0140 | −0.4533 | +0.439 |
| reach | 0.0876 | −0.0004 | +0.088 |
| jac | −0.0134 | −0.0615 | +0.048 |
| Rank | **827** | 1192 | |

Partition val, panel `vcc2026-val-1`, anchor set `vcc2026-valA-r4+vcc2026-valB-r4+vcc2026-valC-r4`.

Interpretation: adding K562 GWPS (263/300 panel targets measured) turns per-target transfer on: pds rises from 0.01 to 0.31, and the strongly negative fid from the essential-gene generic shift is gone (−0.45 → −0.01). The leaderboard overall (0.069) sits well below the local b-testlike estimate (0.230) and close to the (a) K562_GWPS-holdout scale; mse is still 0, and fid/jac are at about the baseline.
