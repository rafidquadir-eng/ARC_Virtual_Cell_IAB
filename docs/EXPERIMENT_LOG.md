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
| E020 | 15 Oct | V* (leave-one-line-out on panel targets): emitter, multi-line transfer, new baseline | specs_E020 via vcc26.vstar, seen + unseen; held out CD4T_Stim8hr, KOLF2.1J, K562_GWPS | seen | 0.303 | 0.000 | 0.774 | 0.090 | −0.303 | 0.138 | 0.167 (worst 0.154) | | GPU 2.6 h (seen) | seen done: top B2_raw_gPL balanced 0.167 ≈ B2_transfer random 0.164 > B1 0.046; ORACLE balanced 1.239 > random 1.204 (jac); mse 0 not an emitter issue. **Unseen not run**: GPU held by ~/proj2 pretraining (OOM) | E021; rerun unseen |
| E021 | 15 Oct | E020 winner on the leaderboard | B2_raw_gPL --emit balanced, all 11 summaries | LB | 0.501 | 0.000 | −0.067 | 0.108 | 0.008 | 0.086 | | 0.106 (rank 684) | 1 submission (2/2 on 15 Oct) | done: +0.037 over E012; LB now close to V* seen selection | |
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

The gap to #1 is 0.39, and MSE (0.79) plus PDS (0.56) make up 1.35 of the 2.36 summed gap. Our MSE is 0 in every run, local and leaderboard, even at local PDS 0.74, which points at the emitter rather than the predictions. Diagnosis and fix: E015. Plan to the top: `docs/10_PLAN_TO_TOP.md`.

## Planning note, 15 Oct ~03:30 UTC
Full build plan written (`docs/11_BUILD_PLAN.md`). The runbook is paused until the curation agent signals data done (`reports/DATA_DONE.md`). E013/E015 are folded into E020 (V*), and E014/E017 are replaced by E021. New code: `vcc26/vstar.py` (V* runner) and source `library` tags (`generic_from: ["@genome_wide", "@targeted"]`).
