# Experiment log

Scores are scaled vcc2026 metrics (0 = context mean-response baseline, 1 = replicate). "Local" = mean context score over LOCO held-out lines. Leaderboard column filled only for submitted runs (A/B/C, until 22 Oct).

| ID | Date | Hypothesis | Change | Mode | pds | mse | fid | reach | jac | nmae | Local mean | Leaderboard | Cost | Decision | Next |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E000 | 14 Oct | Instance + pipeline work end to end | setup, controls inventory; NVIDIA driver 595 installed, venv rebuilt on torch cu128 (cupy-cuda12x) | – | | | | | | | | | | done: controls A/B/C 18,400 ctrl cells each, ~20k UMI/cell; gene_names.csv has header → gene_axis.csv | E001 |
| E001 | 14 Oct | Submission accepted by `vcc prep` and scorer | B1 generic on A/B/C (pipeline check), K562 essential source | LB | 0.012 | 0.000 | −0.453 | −0.000 | −0.062 | 0.015 | | −0.081 (rank 1192) | 1 submission | done: pipeline works; fid negative (essential-gene stress signature, panel has no essential genes) | |
| E002 | 14 Oct | Public screens map onto the 18,533-gene axis | K562/RPE1 (figshare), HepG2/Jurkat (GEO GSE264667), H1 (VCC2025 train) summaries; K562 GWPS downloaded | – | | | | | | | | | | done: Replogle-library lines only 7.9–9.0k genes on axis and 0/300 panel targets; H1 18.1k genes, 13/300; GWPS covers 272/300 (not summarised yet) | GWPS? |
| E003 | 14 Oct | Local anchors behave as official (PDS b = 0.5) | anchors per public line (gpudge) | – | | | | | | | | | | done: all 5 PASS (pds b 0.497–0.507, r 0.90–0.98, sd ≤ 0.024) | E004 |
| E004 | 14 Oct | Transfer beats generic when targets were measured elsewhere | B0–B3 (row: B2 α=1) | seen | 0.744 | 0.000 | 0.717 | 0.238 | 0.132 | 0.121 | 0.325 (B0 −0.113, B1 0.011, B3 0.325) | | ~50 GPU-min | done: yes, B2 ≫ B1 in all 5 lines; α=0.6 worse | E007 |
| E005 | 14 Oct | Linear fallback beats generic for never-measured targets | B0–B3 (row: B3 linear) | unseen | 0.039 | 0.000 | 0.409 | −0.060 | −0.010 | −0.149 | 0.038 (B1 = B2 = 0.008) | | (with E004) | done: small gain over generic in 4/5 lines (not H1) | E008 |
| E010 | 14–15 Oct | GWPS gives panel coverage | summarise K562 GWPS (272/300 panel targets), add to loco.json with line K562 | – |  |  |  |  |  |  |  |  | 17 min CPU | done: 9,315 perts, 7,681 genes on axis, median kd 0.15, 263/300 panel targets kept (≥ 200, no nokd rerun) | E011 |
| E011 | 15 Oct | Validation that looks like the test; fix B2's essential-signature leak | GWPS holdout restricted to the 300 panel targets; other lines with GWPS-only sources; raw transfer + panel-like generic (specs_E011) | both |  |  |  |  |  |  | sel: B2_transfer 0.211 (b-testlike 0.230, a-unseen 0.032); B2_raw_gPL / B3_raw_gPL_linear 0.205 |  | ~90 GPU-min | done: top spec B2_transfer; raw/gPL tie on b-testlike; (a) K562_GWPS holdout ≈ baseline for all specs | E012 |
| E012 | 15 Oct | Transfer from GWPS lifts the leaderboard score | top E011 spec on A/B/C, all 6 summaries | LB | 0.313 | 0.000 | −0.014 | 0.088 | −0.013 | 0.042 |  | 0.069 (rank 827) | 1 submission (15 Oct) | done: +0.150 over E001 (pds 0.01 → 0.31, fid −0.45 → −0.01) | E007/E008 testlike |
| E013 | 15 Oct | Denoising K562 lfc (EB shrinkage) and effect scale help on non-essential targets | specs_E013 on V1 (H1 ← GWPS), V2 (GWPS@H1 targets ← H1), V3 (essential lines ← GWPS+H1), V4 (panel, generic only) | seen | | | | | | | | | | planned | E014 |
| E014 | 15 Oct | E013 winner lifts the leaderboard | submit only if selection beats B2_transfer by ≥ 0.01 | LB | | | | | | | | | ≤ 1 submission | planned | |
| E015 | 15 Oct | Emission noise, not prediction, is capping MSE/PDS/DE | ORACLE and B2 variants × emit random/balanced on V1–V4 (specs_E015) | seen | | | | | | | | | | planned | E017 |
| E016 | 15 Oct | Identify A/B/C cell types | control similarity to public lines + markers | – | | | | | | | | | CPU 1 min | done (inference): A = male immature T-ALL-like (CD3/TRBC1/CD1A/DNTT; nearest CD4T r 0.85); B = female carcinoma-like with mesenchymal component (KRT7/8/18, VIM, COL, FOLR1, CDKN2A high); C = male squamous/basal epithelial (TP63, KRT5/13/15, SOX2). B~C 0.84; no source of B/C lineage. `reports/context_id.json` | E020 |
| E017 | 15 Oct | Balanced emission lifts the leaderboard | top E015 spec, --emit balanced | LB | | | | | | | | | 1 submission | planned | |
| E020 | 15 Oct | V* (leave-one-line-out on panel targets): emitter, multi-line transfer, new baseline | specs_E020 via vcc26.vstar, seen + unseen; held out CD4T_Stim8hr, KOLF2.1J, K562_GWPS | seen | 0.303 | 0.000 | 0.774 | 0.090 | −0.303 | 0.138 | 0.167 (worst 0.154) | | GPU 2.6 h (seen) | seen done: top B2_raw_gPL balanced 0.167 ≈ B2_transfer random 0.164 > B1 0.046; ORACLE balanced 1.239 > random 1.204 (jac); mse 0 not an emitter issue. unseen (rerun 16 Oct): all specs fall back to generic, 0.03–0.05 (B1 = B2 = 0.046) | E021 |
| E021 | 15 Oct | E020 winner on the leaderboard | B2_raw_gPL --emit balanced, all 11 summaries | LB | 0.501 | 0.000 | −0.067 | 0.108 | 0.008 | 0.086 | | 0.106 (rank 684) | 1 submission (2/2 on 15 Oct) | done: +0.037 over E012; LB now close to V* seen selection | |
| E025 | 16 Oct | Source noise is what zeroes MSE; B4 (low-rank + line pooling + shrinkage) fixes it | proxy sweep, specs_E025 (47), 3 V* lines, CPU | seen | | | | | | | proxy 0.454 (E021) vs 0.380 (best B4) | | CPU ~75 min | done: B4 cuts raw MSE 4.4→1.1–1.7 but loses pds/de_sign as fast; no B4 beats E021 on the proxy; E021 per-target cos(pred,truth) ≈ 0.01–0.08. specs_E026 = E021, B1_gPL, 2 best B4 | E026 |
| E026 | 16 Oct | Proxy winners hold on the real metric, incl. V*-far | vstar + far runs, specs_E026 | seen | 0.303 | 0.000 | 0.774 | 0.090 | −0.303 | 0.138 | 0.167 (worst 0.154) | | GPU 2.8 h | done: top is still the E021 config (0.167); best B4 0.104 (first mse_sc > 0, 0.026; raw MSE ≈ 1.0) but loses pds/fid; V*-far: E021 −0.006 on KOLF w/o pluripotent, 0 on CD4T w/o Jurkat | E027 not submitted (top = E021, already on LB) |
| E027 | 16 Oct | B4 lifts the leaderboard | E026 top, balanced | LB | | | | | | | | | 1 submission | planned | |
| E030 | 16 Oct | Truth is sparse/cis; B5 sparse consistent consensus + cis beats dense transfer | proxy, specs_E030 (32), 5 V* lines incl. Orion | seen | | | | | | | | | CPU | planned | E031 |
| E031 | 16 Oct | B5 wins on the real metric, incl. V*-far | vstar 5 lines + far | seen | | | | | | | | | GPU | planned | E032 |
| E032 | 16 Oct | B5 lifts the leaderboard | E031 top, balanced, all summaries | LB | | | | | | | | | ≤ 1 | planned | |
| E033 | 16 Oct | Where the leaderboard score comes from (A vs B/C) | vcc status JSON, no submission | – | | | | | | | | | – | planned | |
| E034 | 16–17 Oct | Learned translator (M1) and context-programme projection beat B5/E021 | proxy + V* + bootstrap, specs_E034 | seen | | | | | | | | | CPU+GPU | planned | E035 |
| E035 | 17 Oct | NC (Orion) sources help non-NC lines | V* with/without NC | seen | | | | | | | | | GPU | planned | |
| E036 | 17 Oct | Final pipeline runs end to end in time | dress rehearsal A/B/C, NC on/off | – | | | | | | | | | – | planned | |
| E006 | 17–19 Oct | iMEMORY gene vectors add signal | kNN on iMEMORY vs shuffle vs public prior | unseen | | | | | | | | | | blocked (EC2 files) | |
| E007 | 17 Oct | A1: source weighting + target-expression gating | | both | | | | | | | | | | planned | |
| E008 | 18 Oct | A1: per-target shrinkage + β and DE-count calibration | | both | | | | | | | | | | planned | |
| E009 | 19–20 Oct | A2: CRISPRi neighbour silencing | | both | | | | | | | | | | planned | |

## Synthetic harness check (14 Oct, planning session, not challenge data)
3 synthetic contexts, held-out C1, seen mode: control −3.05, generic −0.37, per-target transfer +0.26. Confirms the pipeline (summaries → models → emission → official metrics → anchors → scaled score) runs end to end.

## A1 synthetic check (14 Oct, planning session, not challenge data)
4 synthetic lines (two similar pairs; 25% of targets unexpressed per line), held-out C1, seen mode:
B1 −0.04, B2 +0.38, A1 +0.41 (sharp source weights), A1 equal weights +0.46, A1 without agreement-shrinkage +0.51.
Expression gate: +0.41 with, +0.36 without. Effect scale beta trades fidelity against Jaccard
(beta 1.0 → 1.2 → 1.5: fid 0.32 → 0.64 → 0.77, jac 0.49 → 0.31 → 0.00). Defaults softened to tau 0.2,
alpha_min 0.6. Real tuning happens in E007/E008 on held-out public lines.

## Planning note, 14 Oct evening (after E000–E005)
- The panel has no essential genes. Essential-library lines cover 0/300 targets, H1 covers 13/300 and K562 GWPS 272/300. So LOCO "seen" (E004) measured essential-to-essential transfer, which flatters the test. E011 adds test-like validation.
- B2 builds each prediction as pooled generic + (source lfc − source generic). When the generic comes from essential-library sources but a target is measured only in GWPS, the essential stress signature is added to every panel prediction. This matches E001's strongly negative fid (−0.45). A unit test confirmed it; the fix is `raw=True` plus `generic_from=["K562_GWPS","H1"]`.
- Data curation must target panel genes measured outside K562 (`docs/09_DATA_CURATION_AGENT.md`, revised).

## Planning note, 15 Oct ~02:00 UTC (after E010–E012)
- Leaderboard 0.069 (rank 827), +0.15 from GWPS transfer, almost all of it from pds (0.31) and from fid recovering to about 0. The DE metrics (fid, jac) sit at the baseline, and mse is 0 by construction.
- E011(b) (0.23) overstates the test because those holdouts score essential targets with strong effects. E011(a) (≈ 0) is the panel with nothing measured, about 37 targets in A/B/C. The realistic proxies are H1 ↔ K562 GWPS: V1/V2 in E013.
- jac ≈ −0.6 in E011(a), with every spec below the mean-response baseline on significant-gene overlap. Hypothesis: transferred K562 sampling noise plus emission produce spurious DE calls. Test: `denoise` (E013). On synthetic data jac rose by about 0.3 and context score by 0.06.
- No leaderboard command in vcc-cli; the top-10 scores have to be read from the website.

## Planning note, 15 Oct ~02:30 UTC (leaderboard reference)
Leaderboard top 5 (screenshot from Rafid, 14 Oct evening ET), scaled scores:
| Rank | Team | Overall | PDS | MSE | JAC | NMAE | FID | REACH |
|---|---|---|---|---|---|---|---|---|
| 1 | Illumina AI (iCell) | 0.4610 | 0.874 | 0.787 | 0.088 | 0.419 | 0.153 | 0.444 |
| 2 | cqawesome | 0.3304 | 0.830 | 0.455 | 0.026 | 0.288 | 0.089 | 0.295 |
| 3 | Excell | 0.3302 | 0.847 | 0.488 | 0.019 | 0.265 | 0.074 | 0.288 |
| 4 | X-team | 0.3271 | 0.776 | 0.458 | 0.084 | 0.284 | −0.000 | 0.362 |
| 5 | JJJ | 0.3197 | 0.818 | 0.472 | 0.018 | 0.257 | 0.068 | 0.285 |
| 827 | us (E012) | 0.069 | 0.313 | 0.000 | −0.013 | 0.042 | −0.014 | 0.088 |
| 684 | us (E021) | 0.106 | 0.501 | 0.000 | 0.008 | 0.086 | −0.067 | 0.108 |

The gap to #1 is 0.39, and MSE (0.79) plus PDS (0.56) make up 1.35 of the 2.36 summed gap. Our MSE is 0 in every run, local and leaderboard, even at local PDS 0.74, which points at the emitter rather than the predictions. Diagnosis and fix: E015. Plan to the top: `docs/10_PLAN_TO_TOP.md`.

## Planning note, 15 Oct ~03:30 UTC
Full build plan written (`docs/11_BUILD_PLAN.md`). The runbook is paused until the curation agent signals data done (`reports/DATA_DONE.md`). E013/E015 are folded into E020 (V*), and E014/E017 are replaced by E021. New code: `vcc26/vstar.py` (V* runner) and source `library` tags (`generic_from: ["@genome_wide", "@targeted"]`).

## Instance note, 15 Oct ~17:30 UTC (runbook session)
- Done: E016, E020 seen, E021 (0.106, rank 684). Reports: `reports/REPORTS_E016_E021.md`; CSVs: `results/E020/`.
- **E020 unseen is not run.** The A100 is held by another session's job (`~/proj2/scripts/50_pretrain.py`, 32 of 40 GB, `--max-hours 8` from ~16:30 UTC), and unseen hit cupy OOM. Resume when the GPU is free (anchors cached in `$DATA/loco/E020/holdout_*`, ~2.5–3 h):
  `tmux new -d -s E020 "source ~/.vcc_env; cd ~/vcc; python -m vcc26.vstar --config loco.json --panel-file $DATA/challenge/controls/pert_counts.csv --specs specs_E020.json --out $DATA/loco/E020 --tag E020 --mode unseen 2>&1 | tee logs/E020_unseen.log"`
- **Shared-venv hazard:** at 15:44 UTC the `~/proj2` session installed into `~/vcc/.venv` (timm, scikit-image, pydeseq2, …) and pulled torch 2.14.1+cu130, which breaks cupy-cuda12x (`libcublas.so.12`). Restored torch 2.11.0+cu128 / torchvision 0.26.0+cu128 and reinstalled the `nvidia-*-cu12` libs (uninstalling the cu13 packages deletes files shared under `nvidia/*/lib`, so reinstall cu12 after). Other projects should use their own venv.
- Submissions: 15 Oct UTC 2/2 used (E012, E021). Next possible 16 Oct 00:00 UTC.

## Planning note, 15 Oct ~17:45 UTC (after E020-seen / E021: LB 0.106, rank ~680)
Full diagnosis in `docs/12_DIAGNOSIS.md`. The headline: raw MSE 4.66 on the leaderboard (3.2–6.8 locally) means source sampling noise transferred on every gene; ORACLE scores 1.0 through the same emitter, so the emitter is fine. Built: B4 consensus model (low-rank denoising, line pooling, random-effects weights, shrinkage, gates, pseudocount space), `vcc26.proxy` (fast metric proxies + error anatomy), `pseudobulk --strata-col` (donor/batch-matched controls). Contexts per E016 (inference): A = T-ALL-like, B = female carcinoma (HeLa-like), C = male squamous epithelium. No epithelial source exists yet: X-Atlas/Orion HCT116 is the key data request.

## Instance note, 16 Oct ~01:10 UTC (usage limit reached mid-batch; jobs left running in tmux)
- Pushed: E025 report (`reports/REPORTS_E025_E027.md`), `specs_E026.json`. E026/E027 NOT started (E020 unseen still on GPU, 27/36 rows; tmux `E020`).
- Curation batch 2 (done by the runbook session): D10 Orion HCT116 done (`pb/Orion_HCT116.npz` 15,476 perts, median kd 0.24; `subsets/Orion_HCT116.h5ad`), HEK293T running (tmux `orion`, `scripts/convert_orion.py`); **not yet in `loco.json`**. Pisces: nothing uploaded on HF yet. D7: gem_group/donor re-summaries in `$DATA/pb/d7/` (K562, RPE1, HepG2, Jurkat, K562_GWPS, CD4T×3 done; HipSci NonTarget-only running, tmux `d7_b`); **not swapped into `pb/` yet** (swap after E020 finishes). CD4T_Rest male-specific expressed chrY excess |lfc| over noise floor drops 5.4× (`scripts/d7_artifact_check.py`); single-donor lines unchanged; no HLA genes on the axis. D8: no new ≥20-panel epithelial/T-ALL set found (A549 GSE337804: 15 panel targets; Jurkat NCB 2025 is a 374-gene TAP-seq readout). D9: CMap/LINCS terms = academic non-profit only → blocked. D11: DepMap 24Q4 `OmicsExpressionProteinCodingGenesTPMLogp1.csv` in `$DATA/priors/depmap` (md5 ok).
- Archive (tmux `archive`): KOLF raw + subsets (excl. Orion) → Drive with own OAuth client; KOLF raw deleted only if `rclone check` passes (see `logs/archive.log`).

## Instance note, 16 Oct ~05:00 UTC
- Done: E020 unseen, E025, E025b, E026 (reports in `reports/REPORTS_E016_E021.md` / `REPORTS_E025_E027.md`). E027 not submitted: E026's top is the E021 config (already on LB).
- Curation batch 2 done: `reports/DATA_DONE_batch2.md`. `loco.json` now 13 contexts (Orion_HCT116, Orion_HEK293T, licence-tagged); D7 summaries swapped into `pb/` (originals `*_pooled.npz`). V* dry run lists 5 held-out lines.
- Archive with own rclone client done and verified; KOLF raw deleted. Scratch held (deletable on request): Orion parquet 120 GB local, Orion converted h5ad 308 GB, d7 inputs 92 GB.

## Planning note, 16 Oct ~07:30 UTC (after E025–E026, batch 2)
B4 retired: its shrinkage was mis-scaled, so it fixed MSE but lost PDS. The E025 anatomy shows dense transfer is noise per gene (cos 0.003–0.08). New: B5 sparse cross-line-consistent consensus + CRISPRi cis effects; proxy ORACLE_TOPK/ORACLE_CIS ceilings and cis-share anatomy; `top50_overlap`; `scripts/pick_specs.py`. V* now has 5 lines (Orion HCT116/HEK293T). See `docs/14_DIAGNOSIS_ROUND2.md`.
