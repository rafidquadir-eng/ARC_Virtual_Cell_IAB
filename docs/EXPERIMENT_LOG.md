# Experiment log

Scores are scaled vcc2026 metrics (0 = context mean-response baseline, 1 = replicate). "Local" = mean context score over LOCO held-out lines. Leaderboard column filled only for submitted runs (A/B/C, until 22 Oct).

| ID | Date | Hypothesis | Change | Mode | pds | mse | fid | reach | jac | nmae | Local mean | Leaderboard | Cost | Decision | Next |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E000 | 14 Oct | Instance + pipeline work end to end | setup, controls inventory | – | | | | | | | | | | planned | E001 |
| E001 | 14–15 Oct | Submission accepted by `vcc prep` and scorer | B1 generic on A/B/C (pipeline check) | LB | | | | | | | | | | planned | |
| E002 | 15 Oct | Public screens map onto the 18,533-gene axis | downloads + summaries | – | | | | | | | | | | planned | |
| E003 | 15 Oct | Local anchors behave as official (PDS b = 0.5) | anchors per public line | – | | | | | | | | | | planned | |
| E004 | 16 Oct | Transfer beats generic when targets were measured elsewhere | B0–B3 | seen | | | | | | | | | | planned | |
| E005 | 16 Oct | Linear fallback beats generic for never-measured targets | B0–B3 | unseen | | | | | | | | | | planned | |
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
