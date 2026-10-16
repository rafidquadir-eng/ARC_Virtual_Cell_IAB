# REPORT blocks E030–E036 — Lambda instance, 16 Oct 2026

Runbook: `docs/07_RUNBOOK_INSTANCE.md` (E030–E036, commit 278bbb5); diagnosis `docs/14_DIAGNOSIS_ROUND2.md`.
`loco.json`: 13 contexts (including Orion HCT116/HEK293T, licence-tagged), with the D7 composition-matched summaries in `pb/`.

---

## REPORT E033 — per-context breakdown of our leaderboard entries (no submission)

```
vcc --json status QJexGFhKagEpbvXkiUku > results/E033_E021_status.json   # works
vcc --json status aZXPOs2QkOuKb5oZQzYu                                     # E012: "No such submission for your account" (not_found)
vcc --json status nurtW5XlQHa9XLcPGbdY                                     # E001: same not_found
```
Only the latest entry (E021) can still be looked up. The server seems to keep one entry per team, the most recent, and `vcc` has no list command.
**The status JSON has no per-context (A/B/C) fields**, only the aggregate. So the per-context breakdown isn't available from `vcc status`.

E021 aggregate, raw and scaled (`results/E033_E021_status.json`):

| metric | raw | scaled |
|---|---|---|
| pds (`pds_cosine`) | 0.7266 | 0.5009 |
| mse (`expr_mse_unbiased_capped_norm`) | 4.6628 | 0 |
| nmae (`de_wilcoxon_lfc_nmae`) | 0.9468 | 0.0862 |
| fid (`de_wilcoxon_direction_fidelity_yield_raw`) | 0.4926 | −0.0667 |
| reach (`de_wilcoxon_direction_reach_raw`) | 0.1748 | 0.1078 |
| jac (`de_wilcoxon_sig_jaccard`) | 0.0333 | 0.0076 |
| overall | | 0.1060 (rank now **690**, down from 684 as others submit) |

The raw MSE of 4.66 is the figure `docs/12` started from (about 5× the true effect size). `de_score`, `pert_score` and `mae_score` are null.
