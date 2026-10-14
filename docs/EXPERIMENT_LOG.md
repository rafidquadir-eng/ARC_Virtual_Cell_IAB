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
