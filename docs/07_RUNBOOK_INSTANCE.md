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

## ⏸ PAUSED (15 Oct ~03:30 UTC): don't start E013–E017
Wait until the curation agent has pushed `reports/DATA_DONE.md`. If E013 is already running, let it finish and push its report, then stop. E013/E015 are folded into **E020** below; E014/E017 are replaced by **E021**. The earlier stages stay here for the record.

## ▶ ROUND 4 (from 19 Oct, 01:00 UTC): run E044 → E049 in order. Read `docs/16_PLAN_ROUND4.md` first.
The selection rule is in docs/16 §3; it supersedes the 17 Oct rule kept below. The standing rules in docs/16 §6 apply to every stage.

**The six most important rules:**
- no silent skips;
- one REPORT section per stage in `reports/REPORTS_E044_E049.md`, each with an Anomalies list;
- commit small results;
- pre-register every LB entry;
- stop on a FAIL;
- no Phase B without a planning update.

Common setup for every stage:
```bash
source ~/.vcc_env; cd ~/vcc; git pull
PANEL=$(find $DATA/challenge -name pert_counts.csv | head -1); AXIS=$DATA/challenge/controls/gene_axis.csv
S="--status results/E033_E021_status.json results/E033_E032_status.json"
SUMS=$(python -c "import json;print(' '.join(c['summary'] for c in json.load(open('loco.json'))['contexts']))")
REF="B5_z2_a0.5_cis5000@@balanced"
```

### E044 — validator on the instance, reproduction, strength study, test-day mechanics (CPU, ~1.5 h)
```bash
mkdir -p results/E044 results/forecasts
# 1. the calibrated validator reproduces here (planning got: retro PASS; B5 0.112, E021 0.115)
python scripts/lb_check.py spans $S --out results/E044/lb_spans_check.json > /dev/null
python -c "
import json; a=json.load(open('results/lb_spans.json')); b=json.load(open('results/E044/lb_spans_check.json'))
d=max(abs(a[k][m]-b[k][m]) for k in ('baseline','replicate') for m in a[k]); print('max |span diff|', d); assert d < 1e-9"
python scripts/lb_check.py retro --rows results/E031/vstar_rows_E031_seen.csv --a "B5_z2_a0.5_cis5000" --b "B2_raw_gPL(E021)" \
  --lb-a results/E033_E032_status.json --lb-b results/E033_E021_status.json | tee results/E044/lb_retro_lbspans.txt
python scripts/lb_check.py rank $S --rows results/E020/vstar_rows_E020_seen.csv results/E031/vstar_rows_E031_seen.csv results/E034/vstar_rows_E034_seen.csv \
  --ref "$REF" --out results/E044/rank_E020_E031_E034.csv | tee results/E044/rank_E020_E031_E034.txt

# 2. full-matrix reproduction of E032 with today's code (review R4-12; the R-01 emitter change may only touch all-zero rows)
python -m vcc26.predict_challenge --controls-dir $DATA/challenge/controls --contexts A,B,C --perts $PANEL --gene-names $AXIS \
  --registry loco.json --summaries $SUMS --spec-file specs_E031.json --spec "B5_z2_a0.5_cis5000" --n-control 0 \
  --out $DATA/preds/E044_E032repro.h5ad 2>&1 | tail -3
python - <<PY | tee results/E044/E032_full_repro.txt
import anndata as ad, numpy as np
a = ad.read_h5ad("$DATA/preds/E032.h5ad", backed="r"); b = ad.read_h5ad("$DATA/preds/E044_E032repro.h5ad", backed="r")
print("shape", a.shape, b.shape, "obs index equal", bool((a.obs.index == b.obs.index).all()))
pc = [c for c in a.obs.columns if "target" in c.lower()][0]; diff = []
for i in range(0, a.n_obs, 20000):
    A = a.X[i:i + 20000]; B = b.X[i:i + 20000]
    d = np.asarray(abs(A - B).sum(1)).ravel(); diff += list(np.where(d > 0)[0] + i)
print("rows differing:", len(diff), "of", a.n_obs)
if diff:
    print(a.obs.iloc[diff][pc].astype(str).value_counts().head(40).to_string())
PY

# 3. per-target N_conf tables (E042c's were not committed)
HOLD="$DATA/loco/E037/holdout_H1_R400 $DATA/loco/E037/holdout_CD4T_Stim48hr_R400 $DATA/loco/E020/holdout_CD4T_Stim8hr $DATA/loco/E020/holdout_KOLF2.1J $DATA/loco/E020/holdout_K562_GWPS $DATA/loco/E020/holdout_Orion_HCT116 $DATA/loco/E020/holdout_Orion_HEK293T"
for d in $HOLD; do
  python scripts/regime_check.py --holdout-dir $d --per-target-out results/E044/pertarget_nconf_$(basename $d).csv > results/E044/regime_$(basename $d).json
done

# 4. strength study (docs/16 R4-05): can zero-shot features rank the held-out N_conf?
python scripts/strength_study.py --config loco.json --pertarget "results/E044/pertarget_nconf_holdout_*.csv" \
  --depmap $DATA/priors/depmap/CRISPRGeneEffect.csv --models $DATA/priors/depmap/Model.csv \
  --line-names K562_GWPS=K562,Orion_HCT116=HCT116,Orion_HEK293T=HEK293T \
  --out results/E044/strength_study.json | tee results/E044/strength_study.txt
python -c "
import pandas as pd; ids=set(pd.read_csv('$DATA/priors/depmap/CRISPRGeneEffect.csv', usecols=[0]).iloc[:,0])
[print(c, m, 'screened' if m in ids else 'NOT screened') for c,m in [('A','ACH-000995'),('B','ACH-001086'),('C','ACH-000518')]]" | tee results/E044/depmap_ABC.txt

# 5. TP53 from DepMap for A/B/C (check the hand-written contexts_meta.json; do NOT overwrite it)
python scripts/context_meta.py --match reports/E041_ccle_match.json \
  --damaging $DATA/priors/depmap/OmicsSomaticMutationsMatrixDamaging.csv --hotspot $DATA/priors/depmap/OmicsSomaticMutationsMatrixHotspot.csv \
  --out results/E044/contexts_meta_check.json

# 6. test-day mechanics: how is a FINAL entry made, and how is the test bundle fetched?
(vcc --help; echo; vcc submit --help; echo; vcc download --help 2>&1; echo; vcc status --help 2>&1) > reports/vcc_help_round4.txt 2>&1
grep -n -i "final\|test\|phase\|bundle\|context" reports/vcc_help_round4.txt | head -40
```
7. Create `results/submissions.csv` from the reports, one row per past entry (E001, E012, E021, E032, and any other). Columns:
   `entry,utc,spec,emit,nc,git,vcc_md5,forecast,overall,pds,mse,fid,reach,jac,nmae,rank`.
   Fill `vcc_md5` where the `.vcc` still exists; otherwise write `unknown`.

**REPORT E044:**
1. The retro verdict and the rank table. Both should match planning's numbers: PASS; E021 0.115, B5 0.112.
2. Rows differing in the E032 reproduction, and their targets. Expected 0, or only targets whose predicted lfc is all zero.
3. The strength study: the per-line Spearman table, the LOLO table, and the `decision` block.
4. Is DepMap screened for A/B/C? Does `contexts_meta_check.json` agree with `contexts_meta.json`?
5. What the CLI says about final entries and the test bundle: exact flags, or "nothing about final" if the help is silent.
6. The submissions ledger.
7. Anomalies.

### E045 — seed variance, emitter choice, the H1-R400 bracket (GPU, ~2.5–3 h)
Seed 0 of `specs_E045ref.json` reruns the E031 rows: the raw metrics must match those rows. The only exception is a target whose prediction is all zero (R-01 random base).

`scripts/run_E045.sh` runs the V\* jobs (`vstar_par.sh`, 2 holdouts at a time) and the H1-R400 job concurrently: 3 GPU processes. If a line OOMs, its log is `logs/<tag>_<line>.log`, and `vstar_par.sh` prints FAILED. Rerun that line alone with `VSTAR_LINES=<line> VSTAR_PAR=1 bash scripts/vstar_par.sh <specs> <tag> <seed> results/E045`, then rebuild that tag's rows file the same way.
```bash
tmux new -d -s E045 "bash scripts/run_E045.sh 2>&1 | tee logs/E045.log"     # ~2.5-3 h; poll logs/E045.log
```
Then:
```bash
python scripts/lb_check.py rank $S --rows results/E045/vstar_rows_E045s*.csv results/E045/vstar_rows_E045b3s*.csv --ref "$REF" \
  --out results/E045/rank_vstar.csv | tee results/E045/rank_vstar.txt
python scripts/lb_check.py rank $S --rows results/E045/scores_H1_R400_seen_E045*h.csv --ref "$REF" | tee results/E045/rank_H1.txt
for s in 0 1 2; do echo "== seed $s"; python scripts/lb_check.py retro --rows results/E045/vstar_rows_E045s$s.csv --a "B5_z2_a0.5_cis5000" \
  --b "B2_raw_gPL(E021)" --lb-a results/E033_E032_status.json --lb-b results/E033_E021_status.json | tail -3; done | tee results/E045/retro_by_seed.txt
python scripts/lb_check.py retro --rows results/E045/scores_H1_R400_seen_E045refh.csv --a "B5_z2_a0.5_cis5000" --b "B2_raw_gPL(E021)" \
  --lb-a results/E033_E032_status.json --lb-b results/E033_E021_status.json | tee results/E045/retro_H1.txt
python - <<'PY' | tee results/E045/repro_vs_E031.txt
import pandas as pd
o = pd.read_csv("results/E031/vstar_rows_E031_seen.csv").drop_duplicates(["model", "holdout"]); n = pd.read_csv("results/E045/vstar_rows_E045s0.csv")
m = o.merge(n, on=["model", "holdout"], suffixes=("_old", "_new"))
for k in ["pds", "mse", "fid", "reach", "jac", "nmae"]:
    m["d_" + k] = (m[f"raw_{k}_new"] - m[f"raw_{k}_old"]).abs()
print(m[["model", "holdout"] + [c for c in m.columns if c.startswith("d_")]].round(6).to_string())
PY
for x in "B5_z2_a0.5_cis5000" "B2_raw_gPL(E021)"; do
  python -m vcc26.compare --dir $DATA/loco/E020 --tag E045b3s0 --a "$x@b3" --tag-b E045s0 --b "$x" --n 1000 \
    --anchors-override results/lb_spans.json > "results/E045/boot_b3_vs_balanced_$x.json"
done
```
**Decisions (write them in the REPORT):**
- **seed SD\*** = the larger `seed_sd` of the two balanced references. This is the noise floor used in docs/16 §3.
- **Emitter.** Adopt `balanced3` for everything later only if all of these hold:
  - Δ(B5@b3 − B5) ≥ 2·SD\* on V\*;
  - Δ ≥ −0.005 on H1-R400;
  - the E021 pair moves in the same direction.

  Otherwise keep `balanced`. If adopted, make b3 copies of the E046 spec files:
  ```bash
  for f in specs_E046 specs_E046r specs_E046same; do python -c "import json,sys;s=json.load(open('$f.json'));[x.update(emit='balanced3',name=x['name']+'@b3') for x in s];json.dump(s,open('${f}b3.json','w'),indent=1)"; done
  ```
  Use those in E046, with `REF="B5_z2_a0.5_cis5000@b3@@balanced3"`.
- **Validator stability.** Retro must PASS on all 3 seeds. H1-R400 retro is the second bracket: report it either way (it may FAIL on magnitudes; it is one line).

**REPORT E045:**
1. Both rank tables, including `seed_sd`.
2. Retro by seed, and retro on H1.
3. The E031 reproduction diffs.
4. The two bootstraps.
5. The two decisions above.
6. GPU hours.
7. Anomalies.

### E046 — the lever sweep on both brackets (GPU, ~3 h)
Specs (docs/16 §4):

| Spec | Lever | What it does |
|---|---|---|
| `ENS_E021B5_w55`, `ENS_E021B5_w37` | L2 | Blends E021 and B5 |
| `B5_z2_p53w0.3` | L4 | Down-weights p53-mismatched sources |
| `B5_z2_vfloor` | L5 | Overdispersion floor |
| `B5_z2_bud600md0.3`, `B5_z2_bud1500md0.15` | L3 | Cheap DE calls |
| `B5_z2_ALL` | L3+L4+L5 | All three combined |

Also:
- `specs_E046r.json` runs under `VCC_RENORM_AXIS=1` (L6);
- `specs_E046same.json` runs on CD4T_Stim8hr with its same-line datasets allowed as sources (L8 proxy).

```bash
tmux new -d -s E046 "bash scripts/run_E046.sh 2>&1 | tee logs/E046.log"      # add the argument b3 if E045 adopted balanced3; ~3 h
```
Then:
```bash
python scripts/lb_check.py rank $S --rows results/E045/vstar_rows_E045s0.csv results/E045/vstar_rows_E045b3s0.csv results/E046/vstar_rows_E046.csv \
  results/E046/vstar_rows_E046r.csv --ref "$REF" --out results/E046/rank_vstar.csv | tee results/E046/rank_vstar.txt
python scripts/lb_check.py rank $S --rows results/E045/scores_H1_R400_seen_E045*h.csv results/E046/scores_H1_R400_seen_E046h*.csv --ref "$REF" \
  --out results/E046/rank_H1.csv | tee results/E046/rank_H1.txt
python scripts/lb_check.py rank $S --rows results/E045/vstar_rows_E045s0.csv results/E046/vstar_rows_E046same.csv --holdouts CD4T_Stim8hr \
  --ref "$REF" | tee results/E046/rank_sameline.txt      # B5_z2_sameW1/3/10 = same-line sources allowed, line weight 1/3/10
for x in $(python -c "import json;print(' '.join(s['name'] for s in json.load(open('specs_E046.json'))))"); do
  python -m vcc26.compare --dir $DATA/loco/E020 --tag E046 --a "$x" --tag-b E045s0 --b "B5_z2_a0.5_cis5000" --n 1000 \
    --anchors-override results/lb_spans.json > results/E046/boot_$x.json
done
python -m vcc26.compare --dir $DATA/loco/E020 --tag E046r --a "B5_z2_a0.5_cis5000" --tag-b E045s0 --b "B5_z2_a0.5_cis5000" --n 1000 \
  --anchors-override results/lb_spans.json > results/E046/boot_renorm_B5.json
```
(If balanced3 was adopted, the spec names carry `@b3`. Pass `--tag-b E045b3s0 --b "B5_z2_a0.5_cis5000@b3"`.)

**REPORT E046:**
1. A table, one row per spec, with:
   - V\* Δ vs the reference, lines positive, and P(Δ > 0) from the bootstrap;
   - H1-R400 Δ;
   - the six LB-span metric deltas;
   - which docs/16 §3 rules pass.
2. The renorm effect: V\* and H1.
3. The same-line proxy: B5 with CD4T_Stim48hr/Rest allowed, at line weight 1 / 3 / 10, against B5 without them.
4. Which specs qualify for an LB slot.
5. GPU hours.
6. Anomalies.

**E046c (20 Oct, only if ≥ 2 levers each pass rules 1–2):**
1. Write `specs_E046c.json`: at most 4 combinations of the qualifying levers.
2. Run them exactly like E046, with tag `E046c` (V\*) and `E046ch` (H1).
3. Report in the same format.

### E047 — leaderboard entries (19–21 Oct; max 2 per UTC day; docs/16 §3)
For each entry `<x>` (E047a, b, …):
```bash
# 0. state the UTC day's entry count. Pick the candidate per docs/16 §3 (or a calibration entry) and write down why.
# 1. build the predictions (NC on unless Rafid has said otherwise)
python -m vcc26.predict_challenge --controls-dir $DATA/challenge/controls --contexts A,B,C --perts $PANEL --gene-names $AXIS \
  --registry loco.json --summaries $SUMS --spec-file <specs file> --spec "<spec>" --n-control 0 --out $DATA/preds/E047<x>.h5ad
vcc prep $DATA/preds/E047<x>.h5ad -g $AXIS --perts $PANEL --contexts A,B,C -o $DATA/preds/E047<x>.vcc
# 2. pre-register: forecast from the V* rows that hold both the candidate and the reference; commit + push BEFORE submitting
python scripts/lb_check.py forecast $S --rows <V* rows CSVs> --cand "<spec>@@<emit>" --ref "$REF" \
  --out results/forecasts/E047<x>.json --note "<why this entry>"
git add results/forecasts/E047<x>.json && git commit -m "E047<x> forecast (pre-registration)" && git push
# 3. submit, save the official status JSON (same command as for E033), verify
vcc submit $DATA/preds/E047<x>.vcc -m "E047<x> <spec> (forecast <overall>)" --wait
vcc --json status <submission id printed by vcc submit> > results/E047<x>_status.json   # as for E033
python scripts/lb_check.py verify --forecast results/forecasts/E047<x>.json --status results/E047<x>_status.json | tee results/E047<x>_verify.txt
md5sum $DATA/preds/E047<x>.vcc      # -> results/submissions.csv row
```
If `verify` FAILs: no further LB entries. Report, and wait for planning.

If the new entry's scaled MSE lies strictly between 0 and 1, and differs from E032's by more than 0.05, report its raw and scaled MSE. Planning will then solve the MSE span, which today is assumed.

**Calibration entries**, only if nothing qualifies that day:
- **19/20 Oct:** `B5_z2_a0.5_cis5000@b3`, if E045 found balanced3 V\*-neutral (|Δ| < 2·SD\*). Only the real Flex controls can settle the emitter question.
- **21 Oct:** the frozen candidate with NC off (E048).

**REPORT E047\<x\>:** the candidate and why; the forecast; the LB result; verify; md5; the day's entry count.

### E048 — freeze, NC decision data, dress rehearsal (21 Oct)
1. **Freeze.** Write `results/E048/FROZEN.json`:
   - the chosen spec, copied in full;
   - the emitter;
   - `git rev-parse HEAD`;
   - the md5 of every `loco.json` summary;
   - the md5 of `contexts_meta.json`;
   - the NC choice (pending Rafid).

   Also write `specs_FROZEN.json` (one spec) and commit both.
2. **NC on/off on V\*** (the three non-NC lines):
   ```bash
   VSTAR_LINES="CD4T_Stim8hr KOLF2.1J K562_GWPS" bash scripts/vstar_par.sh specs_FROZEN.json E048nc0 0 results/E048 --exclude-licence NC
   VSTAR_LINES="CD4T_Stim8hr KOLF2.1J K562_GWPS" bash scripts/vstar_par.sh specs_FROZEN.json E048nc1 0 results/E048
   python scripts/lb_check.py rank $S --rows results/E048/vstar_rows_E048nc0.csv results/E048/vstar_rows_E048nc1.csv --label-files | tee results/E048/rank_nc.txt
   python -m vcc26.compare --dir $DATA/loco/E020 --tag E048nc0 --a "<spec>" --tag-b E048nc1 --b "<spec>" --n 1000 --anchors-override results/lb_spans.json > results/E048/boot_nc_off_vs_on.json
   ```
   (Both runs use the same spec name, so `--label-files` keeps them apart.)
3. **Dress rehearsal** on A/B/C with NC on and off:
   ```bash
   bash scripts/final_pipeline.sh $DATA/challenge/controls A,B,C specs_FROZEN.json "<spec>" E048reh on
   bash scripts/final_pipeline.sh $DATA/challenge/controls A,B,C specs_FROZEN.json "<spec>" E048reh off
   ```
   Report the timings. If the frozen spec was an LB entry, check that `E048reh_ncon.h5ad` is identical to that entry's `.h5ad`.
4. **Test-day script.** From `reports/vcc_help_round4.txt` (E044), write the exact commands for E049 steps 1 and 8 into the report: download the test bundle, make a final entry, check which entry counts. If the CLI doesn't say, write "unverified" and ask Rafid to check the challenge page.
5. **NC-off LB entry** (calibration, pre-registered): the frozen spec with `--exclude-licence NC`. Rafid uses its result together with step 2 to make the NC decision.

**REPORT E048:**
1. `FROZEN.json`.
2. NC on/off on V\*, and the NC-off LB result.
3. Rehearsal timings and the identity check.
4. The E049 command script.
5. Anomalies.

### E049 — test day (22 Oct): identify, check, predict, insurance entry
```bash
TEST=$DATA/challenge_test; mkdir -p $TEST results/E049     # never write into $DATA/challenge
# 1. download the test bundle into $TEST with the command found in E048, then inventory it
#    (unpack so that the D/E/F control files sit in $TEST/controls, as the validation ones sit in $DATA/challenge/controls)
python -m vcc26.inspect_controls --dir $TEST/controls --out reports/controls_inventory_test.json | head -120   # the five E000 items
TPANEL=$(find $TEST -name pert_counts.csv | head -1); echo "D/E/F perturbation list: $TPANEL"
md5sum $AXIS $(find $TEST \( -name gene_axis.csv -o -name gene_names.csv \) | head -2)   # must match validation (after header handling)
# 2. identity + TP53 (merge D/E/F into contexts_meta.json; the A/B/C entries are kept)
python scripts/ccle_match.py --controls-dir $TEST/controls --contexts D,E,F --expr $DATA/priors/depmap/OmicsExpressionProteinCodingGenesTPMLogp1.csv \
  --models $DATA/priors/depmap/Model.csv --out reports/E049_ccle_match.json
python scripts/context_meta.py --match reports/E049_ccle_match.json --damaging $DATA/priors/depmap/OmicsSomaticMutationsMatrixDamaging.csv \
  --hotspot $DATA/priors/depmap/OmicsSomaticMutationsMatrixHotspot.csv --out contexts_meta.json --merge
# 3. coverage of the D/E/F perturbation list by our sources, and target expression
python scripts/panel_coverage.py --config loco.json --perts $TPANEL --out results/E049/panel_coverage_DEF.csv | tee results/E049/panel_coverage_DEF.txt
python scripts/panel_coverage.py --config loco.json --perts $TPANEL --out results/E049/panel_coverage_DEF_noNC.csv --exclude-licence NC | tail -6
python scripts/target_expr.py --controls-dir $TEST/controls --contexts D,E,F --perts $TPANEL --out results/E049/target_expr_DEF.csv | tee results/E049/target_expr_DEF.txt
```
4. **Same-line check.** Does any D/E/F top CCLE match name one of our source lines? Our source lines:
   - K562, RPE1, HepG2, Jurkat;
   - H1, HipSci, KOLF2.1J;
   - CD4T (primary cells, so not in CCLE);
   - HCT116, HEK293T.

   If one does, with margin ≥ 0.05:
   - add `"same_line": "<line as in loco.json>"` to that context's entry in `contexts_meta.json`;
   - **stop and report** before any prediction. Planning decides `same_line_w` from the E046 proxy.
5. **Stop-and-report triggers:**
   - fewer than 80% of D/E/F targets are measured in ≥ 2 source lines;
   - the gene axis differs from validation;
   - any context is unexpressed for more than 10% of its targets (< 1 CPM).
6. **Predict with the frozen config:**
   ```bash
   bash scripts/final_pipeline.sh $TEST/controls D,E,F specs_FROZEN.json "<spec>" F1 <on|off per Rafid>
   ```
7. **Sanity checks**, before submitting:
   - cells per target and context;
   - the `non-targeting` label is present;
   - counts are non-negative integers, with every cell total ≤ 1e6;
   - the targets match the D/E/F list exactly;
   - the distribution of predicted DE-gene counts per target is similar to the frozen config's A/B/C run.
8. **Insurance final entry F1**, with the exact command from E048. State the UTC day's count.
   - Record the md5 and argv in `results/submissions.csv`.
   - Confirm with the CLI that it registered as a final entry.

**REPORT E049:**
1. The test inventory.
2. D/E/F identities, margins and TP53.
3. Coverage and expression tables.
4. The same-line verdict.
5. Sanity checks.
6. The F1 confirmation.
7. Anomalies.

Then **stop**: Phase B is planned from this report.

---

## Selection rule from 17 Oct (review R-02) — SUPERSEDED on 19 Oct by docs/16 §3; kept for the record
- **Scale local raw metrics with the official LB spans, not per-line anchors.**
  - `results/lb_spans.json` holds the (b, r) values backed out of the LB entries E021/E032 (`scripts/lb_check.py spans`).
  - Per-line tile anchors are degenerate on small truths: fid spans are 0.012–0.18, against the official 0.30.
  - With LB spans, the committed 5-line E031 V\* **retrodicts** the LB: E032 − E021 forecast −0.003 vs LB +0.002, and levels 0.112/0.115 vs LB 0.108/0.106 (`lb_check retro`: PASS).
- **Rank** with `python scripts/lb_check.py rank --status results/E033_E021_status.json results/E033_E032_status.json --rows <scores or vstar_rows CSVs>`.
- **Compare** with `python -m vcc26.compare ... --anchors-override results/lb_spans.json`. The bootstrap now resamples lines, then targets.
- **LB entry** only when both hold:
  - the two-level CI lower bound vs the current LB config is > 0 under LB spans;
  - the 5-line V\* (LB spans) Δ is ≥ −0.01.
- After every new LB entry:
  - re-run `lb_check spans` with the two most informative entries;
  - run `lb_check retro` on the new pair. If retrodiction FAILs, stop and report.

## E042 — corrected local anchors (review O-01, 17 Oct) — DONE 18 Oct (fdca9e2); E042b step 3 (seeds) moved to E045
**Why.** The official baseline arm emits **identical cells** (`emit="tile"`: every cell = the context mean profile). `cell_eval2` 0.18.0 `competition.py` L304–305 says "the baseline arm's cells are identical so its `jk_pred` is exactly 0".

Our `local_eval.build_anchors` used the library default `emit="dispersed"`, which calls almost no DE genes. That is why H1-R400's baseline fid was 0.03 instead of ~0.5, and why V\* misjudged fid (−0.04 vs −0.23 on the LB).

A synthetic check with the scorer's own builder confirms the fix:
- tile: fid 0.58, and jac = mean(N_conf/genes) exactly;
- dispersed: fid 0.004, jac 0.

The code now defaults to tile. `loco` moves any old anchors to `anchors_dispersed.json` and rebuilds automatically.

```bash
source ~/.vcc_env; cd ~/vcc; git pull
PANEL=$(find $DATA/challenge -name pert_counts.csv | head -1)
mkdir -p results/E042
HOLD="$DATA/loco/E037/holdout_H1_R400 $DATA/loco/E037/holdout_CD4T_Stim48hr_R400 $DATA/loco/E020/holdout_CD4T_Stim8hr $DATA/loco/E020/holdout_KOLF2.1J $DATA/loco/E020/holdout_K562_GWPS $DATA/loco/E020/holdout_Orion_HCT116 $DATA/loco/E020/holdout_Orion_HEK293T"
for d in $HOLD; do
  [ -f $d/anchors.json ] && mv $d/anchors.json $d/anchors_dispersed.json
  python -m vcc26.local_eval anchors --real $d/real.h5ad --out $d/anchors.json 2>&1 | tail -2
  python scripts/regime_check.py --holdout-dir $d > results/E042/regime_$(basename $d).json
done
python scripts/rescale_rows.py --dir $DATA/loco/E020 \
  --rows results/E020/vstar_rows_E020_seen.csv results/E031/vstar_rows_E031_seen.csv results/E034/vstar_rows_E034_seen.csv \
  --out results/E042/rescaled_E020_E031_E034.csv | tee results/E042/rescaled_summary.txt
python scripts/rescale_rows.py --dir $DATA/loco/E020 --rows results/E031/scores_*_seen_E031far.csv \
  --out results/E042/rescaled_E031far.csv | tee results/E042/rescaled_far_summary.txt
# guardrails (review D-01/A-01): local anchors vs LB-implied anchors; does the rescaled V* retrodict E021 -> E032?
python scripts/lb_check.py calib --status results/E033_E021_status.json results/E033_E032_status.json \
  --anchors $(for d in $HOLD; do echo $d/anchors.json; done) | tee results/E042/lb_calib.txt
python scripts/lb_check.py retro --rows results/E031/vstar_rows_E031_seen.csv --a "B5_z2_a0.5_cis5000" --b "B2_raw_gPL(E021)" \
  --lb-a results/E033_E032_status.json --lb-b results/E033_E021_status.json | tee results/E042/lb_retro.txt
```
- **`lb_check calib`** must report "calibration OK" for fid/jac/reach/pds/nmae, i.e. every local baseline within 0.05 of the LB-implied one. jac's baseline depends on the truth's N_conf, so on lines whose N_conf differs from A/B/C it may legitimately differ; report the gap.
- **`lb_check retro`** prints PASS/FAIL and per-line sign agreement. **A V\* configuration that FAILs retrodiction may not be used to choose an LB entry** (review A-01: the null-heavy lines K562_GWPS/Orion broke it before). If the 5-line V\* fails, rerun `retro` on KOLF2.1J/CD4T alone by filtering the rows CSV, and report both.
The tile baseline holds a dense matrix: about 9–11 GB per holdout, which is fine.

**REPORT E042:**
1. Per holdout: old vs new baseline raw fid/jac/reach/pds/mse/nmae; the replicate is unchanged.
2. **Key check:** H1-R400's new baseline fid should sit near 0.5 (official 0.506–0.523), and its jac near N_conf mean ÷ gated genes (≈ 855/10,775 ≈ 0.08).
3. The rescaled V\* table: new vs old selection per spec.
4. **Calibration:** Δ(`B5_z2_a0.5_cis5000` − `B2_raw_gPL(E021)`) per metric under the new anchors, next to the LB Δ (pds +0.082, mse +0.144, nmae +0.025, **fid −0.226**, reach −0.006, jac −0.008).

**E042b — integrity checks** (cheap; run right after E042)
```bash
# (1) data manifest: hash every summary the LB configs read
python -c "import json,hashlib;[print(hashlib.md5(open(c['summary'],'rb').read()).hexdigest(), c['name'], c['summary']) for c in json.load(open('loco.json'))['contexts']]" | tee results/E042/data_manifest_md5.txt
# (2) is E032 reproducible from the current code + summaries? (only if $DATA/preds/E032.h5ad still exists)
python -m vcc26.predict_challenge --controls-dir $DATA/challenge/controls --contexts A,B,C --perts $PANEL --gene-names $DATA/challenge/controls/gene_axis.csv \
  --registry loco.json --summaries $(python -c "import json;print(' '.join(c['summary'] for c in json.load(open('loco.json'))['contexts']))") \
  --spec-file specs_E031.json --spec "B5_z2_a0.5_cis5000" --emit balanced --n-control 0 --out $DATA/preds/E032_repro.h5ad
python -c "
import anndata as ad, numpy as np
a=ad.read_h5ad('$DATA/preds/E032.h5ad', backed='r'); b=ad.read_h5ad('$DATA/preds/E032_repro.h5ad', backed='r')
print('shape', a.shape, b.shape, 'obs equal', (a.obs.index==b.obs.index).all())
import scipy.sparse as sp; A=a.X[:20000]; B=b.X[:20000]; print('first 20k rows identical:', (abs(A-B)).sum()==0)" | tee results/E042/E032_repro.txt
# (3) emission-seed variance of the LB config on H1-R400 (holdout cached, so the seed only changes the emitted cells)
for s in 1 2; do
  python -m vcc26.loco --config loco.json --holdout H1 --mode seen --out $DATA/loco/E037 --specs specs_E042seed.json --tag E042seed$s --seed $s \
    --holdout-tag R400 --min-target-cells 400 --umi-target 20000 2>&1 | tail -3
done
```
The seed-0 row for this spec comes from E038 (`B5_z2_a0.5_cis5000`).

**REPORT E042b:**
- the md5 manifest;
- whether E032 reproduces (if `E032.h5ad` is gone, say so);
- context score and the six metrics for seeds 0/1/2: mean, SD, range.

**E042c — are panel targets expressed in A/B/C, and does low target expression mean no response?** (cheap)
```bash
python scripts/target_expr.py --controls-dir $DATA/challenge/controls --contexts A,B,C --perts $PANEL --out results/E042/target_expr_ABC.csv | tee results/E042/target_expr_ABC.txt
for d in $HOLD; do
  python scripts/regime_check.py --holdout-dir $d --per-target-out results/E042/pertarget_nconf_$(basename $d).csv > results/E042/regime_$(basename $d).json
done
```
(This re-runs the regime check with the per-target output. It replaces the files from E042, with the same numbers plus `N_conf_by_target_cpm`.)

**REPORT E042c:**
- the A/B/C table: number of panel targets per control-CPM bin per context, and how many are < 1 CPM in one context but > 20 CPM in another;
- for each held-out line, `N_conf_by_target_cpm`: per target-CPM bin, n, the fraction with N_conf = 0, and the fraction with N_conf < 10.

**E043 — null gate** (GPU; after E038b, on the 5 standard lines with `--match-cells` and on H1-R400)
```bash
mkdir -p results/E043
python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_E043.json --out $DATA/loco/E020 --tag E043 --match-cells 2>&1 | tee logs/E043.log
python -m vcc26.loco --config loco.json --holdout H1 --mode seen --out $DATA/loco/E037 --specs specs_E043.json --tag E043 --holdout-tag R400 --min-target-cells 400 --umi-target 20000 2>&1 | tee logs/E043_H1.log
python -m vcc26.compare --dir $DATA/loco/E020 --tag E043_mc --a "B5x_tl0.05_bud600@b3_null1" --b "B5x_tl0.05_bud600@b3" --n 1000 --anchors-override results/lb_spans.json | tee results/E043/boot_null1.json
```
**REPORT E043:** the summary, per-line scores and raw fid/jac, and the bootstrap.

**Review changes on 17 Oct (pull before E038):**
- `specs_E038` no longer has the `@b2` specs (review B-02: a shared, unpinned base adds MSE error).
- `specs_E038` adds `B5_z2_vfloor@b3` (B-03: overdispersion floor) and `B5x_tl0.05_budfrac0@b3` (C-02: per-target budget, abstaining where the model predicts nothing).
- `local_eval` builds the replicate with the scorer's own `compute_replicate_anchor` (B-05).
- `compare.py` now bootstraps lines and then targets (B-04); pass `--targets-only` for the old CI.

**After E042/E042b:** *(superseded 19 Oct: E038/E038b/E039/E040/E043 are not run. Their useful specs are folded into E045/E046; the null gate is retired, docs/16 §2.)*
- If the key check passes, run **E038, E038b and E039 as written below**. They use the new anchors automatically.
- **Do not run E040 (leaderboard) until planning confirms**; a full review is in progress (`review/`).
- If the key check fails, report and stop.

## E037–E041 — round 3: make validation match the leaderboard, fix the DE call count and the emitter (see `docs/15_DIAGNOSIS_ROUND3.md`)
**Why.**
- fid = k / max(n_pred, N_conf), where k counts called genes whose direction matches the real log2FC of ANY sign. Calling ≥ N_conf genes therefore scores about chance (≈ 0.51, the official baseline). B5 under-calls and scores 0.42 (−0.29 scaled).
- Our V\* truths are too small and shallow for the DE metrics to behave as they do on the leaderboard: baseline fid is 0.02 in V\* vs 0.51 on the LB. So V\* rewarded the wrong things. **[Superseded 17 Oct: E037 refuted this mechanism. The cause was the local baseline's emission (dispersed vs the official tile), fixed in E042. Truth shape still matters for N_conf.]**
- `--emit balanced` (our LB emitter since E021) makes the scorer call ~2.7% of genes on a no-change prediction.

**New code (pull first):**
- `vcc26/detect.py`: per-gene detection thresholds.
- `models.de_budget`: spec `"post": {"de_budget": {"n": 600}}`.
- `models.predict_ensemble`: model `"ENS"`.
- Emit modes `balanced2` / `balanced3`.
- Options in loco/vstar/proxy:
  - `--min-target-cells`, `--umi-target`, `--holdout-tag`: regime-matched truths;
  - `--match-cells`;
  - `--far`: lineage tags are now in `loco.json`.
- Proxy changes:
  - oracles now come from truth half A, scored against half B;
  - new `ORACLE_HALF` and `ORACLE_MEAN` oracles;
  - new `top50_rep` and `dirprec@k` columns.
- New scripts: `scripts/regime_check.py`, `scripts/ccle_match.py`.

```bash
source ~/.vcc_env; cd ~/vcc; git pull
PANEL=$(find $DATA/challenge -name pert_counts.csv | head -1)
mkdir -p results/E037 results/E038 results/E039 logs $DATA/detect
nvidia-smi        # GPU must be free for E037b/E038
```

**E037a — which lines can look like A/B/C?** (CPU, 1 min)
```bash
python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_B0.json --out $DATA/loco/E037 --tag E037 \
  --min-target-cells 400 --umi-target 20000 --holdout-tag R400 --dry-run | tee results/E037/eligible_R400.txt
```
- The list should include **H1** (Arc 2025: ~1,000 cells/target).
- If H1 is missing, check that `pb/H1.npz` `ncells` has ≥ 100 panel targets with ≥ 400 cells, and report what you find. Don't change thresholds.

**E037b — build the R400 holdouts and anchors** (GPU; one cheap spec)
H1 measures only 25 of the 300 challenge targets, so it is held out on **its own** targets with `loco` (no `--panel-file`). That's fine: it tests the DE-regime mechanics, not panel biology.
```bash
python -m vcc26.loco --config loco.json --holdout H1 --mode seen --out $DATA/loco/E037 --specs specs_B0.json --tag E037 \
  --holdout-tag R400 --min-target-cells 400 --umi-target 20000 2>&1 | tee logs/E037_build_H1.log
# only if E037a listed panel lines:
python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_B0.json --out $DATA/loco/E037 --tag E037 \
  --min-target-cells 400 --umi-target 20000 --holdout-tag R400 2>&1 | tee logs/E037_build.log
```
The logs print the thinning factor and how many H1 targets the sources cover (`n_covered`).

**E037c — regime check and detection thresholds** (CPU/GPU, ~30 min)
```bash
for d in $DATA/loco/E037/holdout_*_R400 $DATA/loco/E020/holdout_{CD4T_Stim8hr,KOLF2.1J,K562_GWPS,Orion_HCT116,Orion_HEK293T}; do
  python scripts/regime_check.py --holdout-dir $d > results/E037/regime_$(basename $d).json
done
for c in A B C; do
  f=$(python -c "from vcc26.predict_challenge import find_ctx; print(find_ctx('$DATA/challenge/controls','$c'))")
  python -m vcc26.detect --ctrl $f --out $DATA/detect/$c.npz | tee results/E037/detect_$c.json
done
python -m vcc26.detect --ctrl $DATA/loco/E037/holdout_H1_R400/ctrl.h5ad --out $DATA/detect/H1_R400.npz | tee results/E037/detect_H1_R400.json
```
**REPORT E037:**
- the eligible R400 lines;
- per holdout: targets, cells/target, median UMI, N_conf mean/median/min/p90/max, and the local baseline/replicate raw anchors next to the official values the script prints;
- per context: detection-threshold summaries (callable genes; median threshold up/down).

**Key question:** is H1-R400's baseline fid near 0.5 and its N_conf mean in the hundreds? If yes, H1-R400 is the primary validator from now on. If not, report and stop.

**E038 — emitter null + call budget on H1-R400** (GPU, ~3 h; longer if E037a found panel lines)
```bash
R="--holdout-tag R400 --min-target-cells 400 --umi-target 20000"
python -m vcc26.loco --config loco.json --holdout H1 --mode seen --out $DATA/loco/E037 --specs specs_E038.json --tag E038 $R 2>&1 | tee logs/E038.log
python -m vcc26.loco --config loco.json --holdout H1 --mode seen --out $DATA/loco/E037 --specs specs_E038f.json --tag E038far --far $R 2>&1 | tee logs/E038f.log
# only if E037a listed panel lines:
python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_E038.json --out $DATA/loco/E037 --tag E038 $R 2>&1 | tee logs/E038_panel.log
cp $DATA/loco/E037/scores_*E038* $DATA/loco/E037/vstar_*E038* results/E038/ 2>/dev/null
B=<best spec of specs_E038.json on H1-R400 by context_score, excluding ORACLE*>
python -m vcc26.compare --dir $DATA/loco/E037 --tag E038 --a "$B" --b "B5_z2_a0.5_cis5000" --n 1000 --anchors-override results/lb_spans.json | tee results/E038/boot_vs_LBconfig.json
python -m vcc26.compare --dir $DATA/loco/E037 --tag E038far --a "$B" --b "B5_z2_a0.5_cis5000" --n 1000 --anchors-override results/lb_spans.json | tee results/E038/boot_far_vs_LBconfig.json
```
- The first spec that uses `de_budget` computes the context's thresholds (~3 min), and they are cached for the rest of the run.
- The M1/ENS specs fit M1 once per source set (~40 GB RAM).
- If `$B` isn't in `specs_E038f.json`, compare the far run with the best spec that is.

**REPORT E038:**
1. The H1-R400 table (and the panel-line summary, if any): context score, six scaled metrics, raw fid/reach/jac/mse per spec.
2. **Emitter null:** B0 under balanced / b2 / b3. Raw fid and the number of genes called (fid ≈ 0 means nothing called).
3. **Calibration check:** Δ(`B5_z2_a0.5_cis5000` − `B2_raw_gPL(E021)`) per metric on H1-R400, next to the leaderboard Δ: pds +0.082, mse +0.144, nmae +0.025, **fid −0.226**, reach −0.006, jac −0.008. Does H1-R400 get the signs right, especially fid?
4. The budget sweep (n 300/600/1,200, snr ranking, per-target frac): raw fid, jac, mse per variant. MSE is the expected cost of lifting genes.
5. Both bootstraps.

**E038b — guard on the standard lines** (GPU, ~4 h; run after E038)
```bash
python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_E038b.json --out $DATA/loco/E020 --tag E038b --match-cells 2>&1 | tee logs/E038b.log
cp $DATA/loco/E020/vstar_*E038b* results/E038/
python -m vcc26.compare --dir $DATA/loco/E020 --tag E038b_mc --a "<best budget spec in E038b>" --b "B5_z2_a0.5_cis5000" --n 1000 --anchors-override results/lb_spans.json | tee results/E038/boot_E038b.json
```
**REPORT E038b:** the summary, per-line scores and the bootstrap.

**E039 — proxy diagnostics** (CPU; can run while E038 is on the GPU)
```bash
python -m vcc26.proxy --config loco.json --holdout H1 --holdout-dir $DATA/loco/E037/holdout_H1_R400 --panel-file $PANEL \
  --tss $DATA/tss.csv --specs specs_E039.json --out results/E039 2>&1 | tee logs/E039_H1.log
python -m vcc26.proxy --config loco.json --holdout H1 --holdout-dir $DATA/loco/E037/holdout_H1_R400 --panel-file $PANEL \
  --tss $DATA/tss.csv --specs specs_E039.json --out results/E039 --far 2>&1 | tee logs/E039_H1far.log
for h in CD4T_Stim8hr KOLF2.1J K562_GWPS Orion_HCT116 Orion_HEK293T; do
  python -m vcc26.proxy --config loco.json --holdout $h --holdout-dir $DATA/loco/E020/holdout_$h --panel-file $PANEL \
    --tss $DATA/tss.csv --specs specs_E039.json --out results/E039 2>&1 | tee logs/E039_$h.log
done
```
**REPORT E039:** per line:
- `dirprec@{50,100,200,400,800,1600}` for every spec. This is direction precision at k calls, i.e. the fid we'd get at n = k; 0.5 = coin flip.
- `ORACLE_HALF`, `ORACLE_MEAN`, `ORACLE_TOPK*`: pds_sc, mse_sc_credit, dirprec.
- `B5_common_only` vs `ORACLE_MEAN` (how much of the context-mean response other lines predict), and `B5z2_common` vs `B5_z2_a0.5_cis5000`.
- `top50_overlap` vs `top50_rep`.
- `genes_kept_median`, `common_genes`, `train_rows`.

**E040 — leaderboard** (state the day's count first)
- **Submit E038's best spec only if** both hold:
  - its two-level bootstrap CI lower bound vs `B5_z2_a0.5_cis5000` (the LB config), **scaled with LB spans** (`--anchors-override results/lb_spans.json`), is > 0 on H1-R400;
  - its E038b Δ is ≥ −0.01.
- Command:
  ```bash
  python -m vcc26.predict_challenge --controls-dir $DATA/challenge/controls --contexts A,B,C --perts $PANEL --gene-names $DATA/challenge/controls/gene_axis.csv \
    --registry loco.json --summaries <all 13 loco.json summaries> --spec-file specs_E038.json --spec "<best>" --n-control 0 --out $DATA/preds/E040.h5ad
  ```
  The emit mode comes from the spec. Then `vcc prep`, then `vcc submit -m "E040 <spec> (round-3 call budget)" --wait`.

**REPORT E040:** the six scaled and raw metrics next to E032, plus the rank. The prediction is fid from −0.29 to about 0…+0.15 (estimate). If fid doesn't rise, say so clearly; that means H1-R400 is still not a faithful validator.

**E041 — which cell lines are A/B/C?** (CPU, ~10 min; no submission)
```bash
python scripts/ccle_match.py --controls-dir $DATA/challenge/controls --contexts A,B,C \
  --expr $DATA/priors/depmap/OmicsExpressionProteinCodingGenesTPMLogp1.csv --models $DATA/priors/depmap/Model.csv \
  --out reports/E041_ccle_match.json | tee logs/E041.log
```
**REPORT E041:**
- the top 15 per context (Spearman, centred Pearson, name, lineage, disease, sex);
- the sex-marker values.

Commit `results/E037–E039/*`, `reports/E041_ccle_match.json` and the REPORT file. Then stop and wait for planning.

## E034–E036 — learned translator (M1), context-programme projection, NC on/off, dress rehearsal
Run after E031/E032 (independent of their outcome). New code: `vcc26/translator.py` (`M1_gbm`), `models.apply_post` (spec `"post": {"project": {...}}`), `vcc26/compare.py` (paired bootstrap; `loco` now writes `pertarget_*.parquet`), `--exclude-licence NC` (loco/vstar/proxy/predict_challenge), `predict_challenge --spec-file/--spec`, `scripts/final_pipeline.sh`.

M1 trains itself on the sources it's given: each source line in turn plays the target, with the others as evidence. So the held-out line is never seen. The fit takes a few minutes per source set and is cached across specs. It needs scikit-learn (already in the venv via scanpy; check `python -c "import sklearn"`) and ~40 GB RAM.

**E034a (CPU, proxy):**
```bash
source ~/.vcc_env; cd ~/vcc; git pull
PANEL=$(find $DATA/challenge -name pert_counts.csv | head -1)
sed "s#__DATA__#$DATA#g" specs_E034.json > specs_E034.local.json
for h in CD4T_Stim8hr KOLF2.1J K562_GWPS Orion_HCT116 Orion_HEK293T; do
  python -m vcc26.proxy --config loco.json --holdout $h --holdout-dir $DATA/loco/E020/holdout_$h --panel-file $PANEL \
    --tss $DATA/tss.csv --specs specs_E034.local.json --out results/E034 --anatomy "M1" 2>&1 | tee logs/E034_$h.log
done
python scripts/pick_specs.py --results results/E034 --specs specs_E034.local.json --out specs_E034b.json | tee results/E034/pick.txt
```
Add the best spec from E031 to `specs_E034b.json` by hand if it isn't already there.

**E034b (GPU, real V\* + bootstrap):**
```bash
python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_E034b.json --out $DATA/loco/E020 --tag E034 --mode seen
python -m vcc26.compare --dir $DATA/loco/E020 --tag E034 --a "<best E034b spec>" --b "B2_raw_gPL(E021)" --n 1000 | tee results/E034/bootstrap.json
```
**REPORT E034:**
- the proxy table, M1 anatomy and `train_rows`;
- the V\* summary;
- the bootstrap Δ with its 90% CI.

**Leaderboard rule from here on:** submit only when the bootstrap CI lower bound vs the current leaderboard config is > 0.

**E035 (GPU): does the NC data help?** For the top spec, run V\* on the three non-NC lines with and without NC sources:
```bash
python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_E035.json --out $DATA/loco/E020 --tag E035nc --mode seen --lines CD4T_Stim8hr,KOLF2.1J,K562_GWPS
python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_E035.json --out $DATA/loco/E020 --tag E035nonc --mode seen --lines CD4T_Stim8hr,KOLF2.1J,K562_GWPS --exclude-licence NC
```
(`specs_E035.json` = the top spec only; write it from `specs_E034b.json`.)
**REPORT E035:** selection with vs without NC sources, per line. R decides the NC question with these numbers.

**E036 (dress rehearsal, no submission):** run the full final pipeline on A/B/C as if they were unknown, with and without NC:
```bash
bash scripts/final_pipeline.sh $DATA/challenge/controls A,B,C specs_E035.json "<top spec>" E036 on
bash scripts/final_pipeline.sh $DATA/challenge/controls A,B,C specs_E035.json "<top spec>" E036 off
```
**REPORT E036:** timings, whether `vcc prep` passed for both, file sizes, and any failure. This is the procedure for 22 Oct.

## E030–E033 — sparse consistent consensus + cis effects (B5), 5-line V\*, per-context leaderboard (see `docs/14_DIAGNOSIS_ROUND2.md`)
Why: E025/E026 showed the dense transfer is mostly noise per gene (cos 0.003–0.08), and B4's shrinkage killed what signal there was. B5 keeps only genes that are significant and sign-consistent across lines, plus CRISPRi neighbour (cis) effects. The ORACLE_TOPK/ORACLE_CIS ceilings tell us how sparse the truth is and how much of it is cis. B4 is retired; don't include it in new runs.

**E030 (CPU, proxy; ~15–30 min per line):**
```bash
source ~/.vcc_env; cd ~/vcc; git pull
PANEL=$(find $DATA/challenge -name pert_counts.csv | head -1)
sed "s#__DATA__#$DATA#g" specs_E030.json > specs_E030.local.json
for h in CD4T_Stim8hr KOLF2.1J K562_GWPS Orion_HCT116 Orion_HEK293T; do
  python -m vcc26.proxy --config loco.json --holdout $h --holdout-dir $DATA/loco/E020/holdout_$h --panel-file $PANEL \
    --tss $DATA/tss.csv --specs specs_E030.local.json --out results/E030 \
    --anatomy "B2_raw_gPL(E021),B5_z3_a0.75_cis5000" 2>&1 | tee logs/E030_$h.log
done
python scripts/pick_specs.py --results results/E030 --specs specs_E030.local.json --out specs_E031.json | tee results/E030/pick.txt
```
(`--panel-file` builds the Orion holdouts in `$DATA/loco/E020/holdout_Orion_*` the first time, so E031 reuses them.)
**REPORT E030:**
- the ORACLE diagnostics table from `pick.txt` (TOPK 10/50/200/1000, CIS 1k/5k/20k/100k: pds_sc, mse_sc, mse_raw, de_sign);
- the full ranked table, with `genes_kept_median`, `cis_genes_median` and `top50_overlap`;
- anatomy for the two specs, including `share_true_signal_within_{1000,5000,20000,100000}bp` per line.

Commit `results/E030/*` and `specs_E031.json`.

**E031 (GPU):** real V\* on all 5 lines plus V\*-far:
```bash
nvidia-smi    # must be free
python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_E031.json --out $DATA/loco/E020 --tag E031 --mode seen
for pair in "Orion_HCT116:Orion_HEK293T" "Orion_HEK293T:Orion_HCT116"; do h=${pair%%:*}; x=${pair##*:}
  SRC=$(python -c "import json;print(','.join(c['name'] for c in json.load(open('loco.json'))['contexts'] if c['name'] not in ('$h','$x')))")
  python -m vcc26.loco --config loco.json --holdout $h --mode seen --out $DATA/loco/E020 --panel-file $PANEL --specs specs_E031.json --sources $SRC --tag E031far
done
python -m vcc26.loco --config loco.json --holdout KOLF2.1J --mode seen --out $DATA/loco/E020 --panel-file $PANEL --specs specs_E031.json \
  --sources K562,RPE1,HepG2,Jurkat,K562_GWPS,CD4T_Rest,CD4T_Stim8hr,CD4T_Stim48hr,Orion_HCT116,Orion_HEK293T --tag E031far
```
**REPORT E031:** the V\* summary (selection, worst line, six metrics, per line, raw MSE) and the V\*-far rows.

**E032: leaderboard** (state the day's count first). Submit E031's top spec **only if** it beats `B2_raw_gPL(E021)` by ≥ 0.01 on V\* **and** isn't worse on V\*-far. Use `--emit balanced --registry loco.json`, all summaries (including Orion), and the spec's `--kw` (its tss path is already absolute in `specs_E031.json`). Report the six metrics, the rank, and the comparison with E021 (0.106).

**E033 (no submission):** the per-context breakdown of our leaderboard entries:
```bash
vcc --json status QJexGFhKagEpbvXkiUku > results/E033_E021_status.json     # E021
vcc --json status aZXPOs2QkOuKb5oZQzYu > results/E033_E012_status.json     # E012
```
**REPORT E033:** per-context (A/B/C) overall and six metrics, if the JSON has them. Do the same for E032 once it's scored.

## E025–E027 — noise-aware consensus (B4), proxy sweep, confirmation (see `docs/12_DIAGNOSIS.md`)
Why: E021's raw MSE is 4.66 (V\* 3.2–6.8), almost 5× the true effect size, because source sampling noise is copied onto every gene. B4 denoises (low-rank), pools by line with noise weights, and shrinks; `vcc26.proxy` scores specs in seconds on CPU.

**E025 (CPU only; can run while the GPU is busy):**
```bash
source ~/.vcc_env; cd ~/vcc; git pull
for h in CD4T_Stim8hr KOLF2.1J K562_GWPS; do
  python -m vcc26.proxy --config loco.json --holdout $h --holdout-dir $DATA/loco/E020/holdout_$h \
    --specs specs_E025.json --out results/E025 --anatomy "B2_raw_gPL(E021),B4_lr1_pc20_t0.02_s0" 2>&1 | tee logs/E025_$h.log
done
python scripts/pick_e025.py results/E025 | tee results/E025/pick.txt     # writes specs_E026.json
```
Low-rank denoising runs a randomized SVD per source (cached per run). Expect ~10–30 min per held-out line, dominated by CD4T/KOLF/GWPS. The process needs ~30–60 GB RAM.
**REPORT E025:**
- the full ranked table from `pick.txt` (proxy, pds_sc, mse_sc_credit, mse_raw, de_sign, nmae_p, worst);
- `n_lines` and `lowrank_k` per source if printed;
- the anatomy JSON for the two specs.

Commit `results/E025/*` and `specs_E026.json`.

**E025b (after the curation agent's D7 re-summaries):** rerun E025 into `results/E025b`. Report how E021's config and the top B4 change.

**E026 (GPU; when free):** real-metric V\* for the picked specs, plus V\*-far:
```bash
PANEL=$(find $DATA/challenge -name pert_counts.csv | head -1)
python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_E026.json --out $DATA/loco/E020 --tag E026 --mode seen
# V*-far: same lineage removed from the sources
python -m vcc26.loco --config loco.json --holdout KOLF2.1J --mode seen --out $DATA/loco/E020 --panel-file $PANEL --specs specs_E026.json \
  --sources K562,RPE1,HepG2,Jurkat,K562_GWPS,CD4T_Rest,CD4T_Stim8hr,CD4T_Stim48hr --tag E026far
python -m vcc26.loco --config loco.json --holdout CD4T_Stim8hr --mode seen --out $DATA/loco/E020 --panel-file $PANEL --specs specs_E026.json \
  --sources K562,RPE1,HepG2,K562_GWPS,H1,HipSci_iPSC,KOLF2.1J --tag E026far
```
(`--out $DATA/loco/E020` reuses the E020 holdouts and anchors.) If the GPU is still busy, add `--de-backend pdex --device cpu` (slower).
**REPORT E026:** the V\* summary (selection, worst line, six metrics, per line) and the V\*-far rows; raw MSE per row.

**E027: leaderboard** (state the day's count): E026's top spec with `--emit balanced --registry loco.json` and all summaries, as in E021. Report the metrics and compare with E021 (0.106).

## E016 + E020 + E021 — first stages after the data is in (`docs/11_BUILD_PLAN.md` §3)
```bash
source ~/.vcc_env; cd ~/vcc; git pull
AXIS=$DATA/challenge/controls/gene_axis.csv
PANEL=$(find $DATA/challenge -name pert_counts.csv | head -1)
# E016: what are A/B/C? (CPU, a minute)
python -m vcc26.context_id --controls-dir $DATA/challenge/controls --contexts A,B,C --gene-axis $AXIS \
  --summaries $(python -c "import json;print(' '.join(c['summary'] for c in json.load(open('loco.json'))['contexts']))") \
  --out reports/context_id.json
# E020: V* = leave-one-line-out on the challenge panel, every line with >= 100 panel targets measured
python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_E020.json --out $DATA/loco/E020 --tag E020 --dry-run
tmux new -d -s E020 "source ~/.vcc_env; cd ~/vcc; \
  python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_E020.json --out $DATA/loco/E020 --tag E020 --mode seen 2>&1 | tee logs/E020_seen.log; \
  python -m vcc26.vstar --config loco.json --panel-file $PANEL --specs specs_E020.json --out $DATA/loco/E020 --tag E020 --mode unseen 2>&1 | tee logs/E020_unseen.log"
```
- **CHECK first:** the `--dry-run` must list at least 3 held-out lines (expected K562_GWPS, H1, CD4 T, KOLF iPSC). If it lists fewer, stop and report. Every entry in `loco.json` must have `line` and `library` (ask the curation agent if not).
- Run one V\* job at a time; it already runs the held-out lines one after another.

**REPORT E016:** similarity table, markers, most-specific genes per context, best guess per context (marked as an inference).

**REPORT E020:**
- `vstar_summary_E020_seen.csv` and `_unseen.csv` as markdown tables: (model, emit) × {selection, worst line, six metrics, per-line};
- the ORACLE rows, random vs balanced;
- the top (model, emit) in *seen* mode.

Copy both CSVs to `results/E020/` and push.

**E021: leaderboard confirmation** (state the day's count first). Submit E020's top seen-mode spec on A/B/C with all summaries:
```bash
python -m vcc26.predict_challenge --controls-dir $DATA/challenge/controls --contexts A,B,C --perts $PANEL \
  --gene-names $AXIS --registry loco.json \
  --summaries $(python -c "import json;print(' '.join(c['summary'] for c in json.load(open('loco.json'))['contexts']))") \
  --model <model> --kw '<kw JSON>' --fallback <none|linear> --emit <emit> --n-control 0 --out $DATA/preds/E021.h5ad
vcc prep $DATA/preds/E021.h5ad -g $AXIS --perts $PANEL --contexts A,B,C -o $DATA/preds/E021.vcc
vcc submit $DATA/preds/E021.vcc -m "E021 <spec> emit=<emit>" --wait
```
**REPORT E021:** overall and the six metrics, rank, and the comparison with E012 (0.069).

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
