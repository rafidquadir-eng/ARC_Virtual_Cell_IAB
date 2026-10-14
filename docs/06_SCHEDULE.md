# Schedule (working back from Thu 5 Nov 23:59 UTC)

## Submission policy
- **Until 22 Oct (leaderboard phase):** 2 scored entries per UTC day, 16 left. Use them for (a) the E001 pipeline check, (b) one entry per materially different method, to measure whether LOCO ranks methods the way the leaderboard does. Never pick a method because of its leaderboard score alone.
- **22 Oct – 5 Nov (final phase):** 2 entries per UTC day, **unscored, only the last counts**. We submit a valid entry on 22 Oct and replace it each time a new version wins in LOCO. Every upload goes through `vcc prep` validation plus a local re-score of the exact file. **Last change by Wed 4 Nov**; 5 Nov is for emergency fixes only, because a broken late upload would replace a good one.

## Week by week
| Dates | Work | Exit criterion |
|---|---|---|
| Wed 14 – Thu 15 Oct | Launch LR-1; E000 controls inventory; E001 pipeline-check entry; E002 public data + summaries; E003 anchors | E001 scored; anchors for ≥4 public lines |
| Fri 16 – Sun 18 Oct | E004/E005 baselines B0–B3, both modes; A1 (source weighting, expression gating, shrinkage, β); A3 priors download; leaderboard calibration entries | Baseline table; A1 beats B1 in LOCO |
| Mon 19 – Wed 21 Oct | A2 neighbour silencing; A3 target prior; A4 iMEMORY test if files arrived; **freeze recipe v1 Wed night**; LOCO-vs-leaderboard rank agreement | Recipe v1 frozen |
| Thu 22 Oct | Test set: inventory D/E/F; target overlap with public screens; recipe v1 on D/E/F; **first final entry same day** | Valid final entry on file |
| Fri 23 Oct – Sun 1 Nov | Recipe v2 aimed at the actual test targets (A3 weight if overlap is low); optional A5 on LR-3 only if v2 work is done by 27 Oct; refresh the final entry on each LOCO win | v2 beats v1 in LOCO on a test-like split |
| Mon 2 – Wed 4 Nov | Freeze; final entry by Wed 4 Nov; terminate instances; draft the high-level method description for counsel | Final entry accepted |
| Thu 5 Nov | Buffer only | — |

## After each round I report
Rank (leaderboard phase only), what moved the score and on which metrics, spend to date vs budget, what to try next, and a reminder to terminate idle instances.
