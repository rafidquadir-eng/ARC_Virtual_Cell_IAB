# Red-team report (review stage 4, 16–17 Oct 2026)

Saved verbatim from the red-team agent's final message on 19 Oct, so the record is in the repo. Its
scratch scripts (`gen.py`, `arms.py`, `null_emit.py`, `null_check.py`, `res_*.json`, logs) were in the
planning session's scratchpad and are not in the repo. Two arms (tile-plus-replicate anchors, oracle
per-target budgets) were killed for lack of memory, so those results are UNRESOLVED.

Follow-ups since then: R-01 is fixed in code (random base for null rows, 19 Oct); R-02 is adopted
(LB-span scaling, `scripts/lb_check.py`); R-03 is tested in E045; R-04 led to `de_budget(max_delta=...)`,
tested in E046.

---

I tested all six claims. **Three need correcting, and one finding is new and urgent:** with our leaderboard emitter, the null-target fix in d222976 cannot earn the jac credit it was built for.

| Claim | Verdict | Confidence |
|---|---|---|
| R-1 (call budget lifts fid, +0.045 net) | PARTIAL: the fid mechanism is real, the net gain is not | 75% |
| R-2 (per-target budgets beat uniform) | REFUTED as implemented (noisy budgets); oracle budgets UNRESOLVED | 60% |
| R-3 ("transfer at chance" not established) | CONFIRMED, but reach is the wrong evidence; pds is the right one | 85% |
| R-4 (which mechanism explains the forecast miss) | Additive; both attributions are partly wrong | 80% |
| R-5 (how to emit predicted-null rows) | Neither pinned nor untouched, with our emitter; use a random base | 85% |
| R-6 (gap split: 0.05–0.11 recoverable, 0.25+ real deficit) | Mostly CONFIRMED; the recoverable share is overstated | 75% |

Synthetic setup for R-1/R-2: one context with 3,000 genes plus one "bulk" gene so per-gene depth matches about 20k UMI (1,826 genes pass the scorer's gate). It has 4,000 controls and 40 targets × 400 cells. On the real-panel scale, N_conf has median 52 and mean 264, and 9 of 40 targets have N_conf = 0. That null share is closer to B/C than to A. Scoring used `compute_metrics` with the LB emitter (`balanced`). My tile-plus-replicate anchor run, the oracle per-target arm and the dense arm were killed for lack of memory, so scaled values use the official A/B/C anchors (b and r backed out of the LB entries) as stand-ins. For MSE I assumed b ≈ 0.99 and r ≈ 0.05.

## R-1: PARTIAL (75%)
**Corrected impact:** about −0.01 to +0.02 overall on the LB, not +0.045.

- **Arithmetic is right but incomplete.** Going from raw fid 0.425 to 0.50–0.51 is +0.25–0.28 scaled, or +0.042–0.047 overall. But a uniform n cannot reach 0.5 when N_conf is heavy-tailed. With 50% sign precision and N_conf shaped like val A, the best possible mean fid is 0.435 at n = 300, 0.468 at n = 600, 0.485 at n = 1,200 and 0.497 at n = 3,000. So n = 600 is worth about +0.02–0.025 from fid, before costs.
- **Synthetic, scaled with official anchors:**

| Arm | Overall-like | pds | MSE | fid (raw) | reach | jac | nmae |
|---|---|---|---|---|---|---|---|
| B5-like (already calls enough) | +0.321 | +0.319 | **+0.443** | −0.028 (0.504) | +0.552 | +0.201 | +0.440 |
| + n = 600 | +0.313 | +0.223 | **0** (raw 1.18) | +0.265 | +0.621 | +0.195 | +0.575 |
| + n = 1,200 | +0.297 | +0.191 | **0** (raw 2.23) | +0.217 | +0.621 | +0.147 | +0.606 |
| Sparse B5 (under-calls) | +0.256 | +0.179 | +0.314 | −0.110 (0.480) | +0.590 | +0.166 | +0.394 |
| Sparse B5 + n = 600 | +0.362 | +0.160 | **0** (raw 1.05) | +0.437 (0.643) | +0.728 | +0.248 | +0.600 |

- **MSE is lost in every lifted arm, even at 20k-UMI depth.** Raw MSE crosses the no-skill point of 1.0 each time, so the docs/15 counterpoint is not just a shallow-depth artefact. On the LB that would erase E032's entire MSE contribution (0.144 scaled, 0.024 overall). pds also falls by 0.02–0.10 scaled.
- **The synthetic is optimistic.** fid rises to 0.59–0.64 there only because my predictor has real sign skill on its top genes. The LB says ours is near chance: E012 dense scored 0.509 and E021 dense 0.493. So the reach and nmae gains in the table are upper bounds.
- **What everyone missed.** fid below 0.5 can also come from precision below 0.5, not only from under-calling. E021, dense, scored 0.493 with the herded emitter against E012's 0.509 with random emission. Lifting more genes with the same directions doesn't fix that.

## R-2: REFUTED as implemented (60%)
- The noisy per-target arm (Spearman 0.49 with true N_conf, `cap_others=True`, 8 targets abstained) was the worst: overall-like +0.231, against +0.313 for n = 600 and +0.321 for no budget.
  - MSE was lost (raw 1.07).
  - `cap_others` held true-signal genes below half their threshold, so reach fell by 0.04 scaled.
  - The 8 abstained targets still got jac = 0, because of the emitter problem in R-5.
- The real upside is narrower than claimed: fid on top-decile targets (N_conf ≫ n) and jac on true nulls, which only pays with a random-base emitter.
- The comparison is confounded by `cap_others`. A floor-only per-target budget is untested, and so is the oracle-budget case (that run was killed).

## R-3: CONFIRMED (85%), with a correction to the evidence
- **Reach doesn't prove target-specific signal.** Reach ranks genes by the prediction's p-value (`direction.py` L120–126), so a good common-response predictor can earn it. The tile baseline's 0.042 doesn't bound this, because its p-values from identical cells reflect count skew, not the mean response.
- **pds does prove it.**
  - Under cosine distance with all 300 panel target genes excluded (`discrimination.py` L225–260), any prediction that is the same for every target, even scaled per target, scores exactly 0.5.
  - LB raw pds is 0.764 (E032) and 0.727 (E021).
  - Cis effects don't explain it. On the K562 proxy, oracles restricted to genes within 5 kb / 20 kb of the target reach pds 0.572 / 0.614 (`results/E030/proxy_K562_GWPS_seen.csv`), and those are scored against their own truth, so they are inflated. B5 reaches 0.792.
- **C-03's simulation logic is sound** (I reran `cos_ceiling.py`; perfect-transfer cosine is 0.014–0.174). But "compatible with perfect transfer" overreaches: the measured low end of 0.003 sits below even the N = 5 ceiling. The right test is a correlation corrected for noise using split-half reliability on both sides.

## R-4: additive, and both attributions are partly wrong (80%)
I recomputed the forecast from `vstar_rows_E031_seen.csv` and the E037 anchor files.

- **Raw Δfid per line (doesn't depend on anchors):** CD4T −0.021, KOLF −0.138, K562 −0.004, HCT116 +0.021, HEK293T +0.011. LB raw Δ is −0.068.
- **Official spans on raw deltas:** V\* Δfid −0.088 (dispersed anchors gave −0.039; LB −0.226). Overall forecast +0.022 (was +0.029; LB +0.002). Per line: −0.010, −0.072, +0.039, +0.143, +0.010.
- **Per-line tile anchors are degenerate.** Replicate fid minus 0.51 gives spans of 0.012 (CD4T), 0.051 (HEK), 0.113, 0.164 and 0.181, against the official 0.30. Scaled Δfid becomes −1.67 on CD4T, the mean −0.40, and the overall forecast −0.032, now wrong the other way.
- **On (a), D-03.** "114%" is a share of the *net* gap; as a share of the gross gaps fid is 37% (0.031 of 0.084). Fixing anchors closes only about 26% of the fid gap.
- **On (b), A-01.** The correlation with null share is real, but the stated mechanism is not. Raw jac on the null-heavy lines is 0.007–0.031, far below null shares of 0.19–0.24. So both models call nothing on at most about 3% of targets, and jac(∅,∅) and fid-NaN barely act. The actual driver is small N_conf on responding targets: once n_pred ≥ N_conf, fid equals precision, about 0.5 for any model. Those lines simply can't tell models apart on fid.
- **Answers:** corrected V\* does reproduce the LB sign of Δfid in aggregate, but only 3 of 5 lines agree. It stays distorted on the null-heavy lines, and the working-tree tile fix makes that worse.

## R-5: emit predicted-null rows from a random base, untouched (85%)
Structured synthetic (`R/null_emit.py`, `R/null_check.py`; same controls as the orchestrator's `test_null.py`; 8 null and 6 responding targets):

| Emitter / null rows | Null targets with jac = 1 | Aggregate MSE | pds |
|---|---|---|---|
| balanced, pinned (before d222976) | 0/8 (45 calls per target) | −0.716 | 0.681 |
| **balanced, untouched (d222976)** | **0/8** (1 call per target) | −0.067 | 0.626 |
| balanced3, pinned | 0/8 | −0.715 | 0.670 |
| **balanced3, untouched** | **6/8** (the most possible; the real side calls genes on 2) | −0.333 | 0.687 |
| independent random resample per target | 5/8 | −0.213 | 0.731 |

- With the LB emitter (`balanced`, herded base), "untouched" still produces exactly one call per null target: the same gene each time, coming from the herded base. So it scores jac = 0 and also loses MSE and pds. For `balanced` as-is, pinning is better, as B-01 said, though B-01's synthetic had no latent structure, so its "no extra calls" result doesn't carry over.
- Recommendation: null rows untouched on a random base. Gate only where P(null) is high. Losing the MSE rebate costs roughly a third of the jac gain per gated row (estimate).
- The re-run `test_null.py` showing 0 spurious calls in every mode doesn't contradict this. It only means that synthetic misses the one-gene artefact; `null_check.py`'s direct `compute_de` count does find it.

## R-6: mostly CONFIRMED (75%)
**Corrected recoverable share:** about 0.02–0.06, not 0.05–0.11.

- The fid recovery net of MSE loss is about −0.01 to +0.02 (R-1). Null abstention adds about +0.01–0.02 on B/C, and only with a random-base emitter.
- **MSE gains can't be farmed.** Injected spread is exactly break-even against the noise credit (`delta.py` L45–64, "−0.003%"), and the credit is capped at the reference's own correction (L36–43).
- **The constant common response is worth about 0 in scaled terms.**
  - Baseline MSE backs out to about 0.977–0.994 (E032 raw 0.851 ↔ scaled 0.144, with r between 0 and 0.1). The baseline is the context mean of the perturbed cells, so it captures only about 1–2% of the effect energy.
  - pds for any target-invariant prediction is exactly 0.5.
  - A common response scaled per target by strength is untested.
- No cheap legitimate path to high MSE or pds turned up.
- **The proprietary-data inference is plausible, but I couldn't verify it from here.** Illumina's raw pds of about 0.897 is 94% of the replicate's.

## New issues found
```
- id: R-01
  class: Engineering
  title: The herded base of the LB emitter makes ≥1 spurious DE call on every untouched null row, so d222976's null gate earns no jac with emit=balanced and loses MSE and pds
  severity: P1
  confidence: VERIFIED 85% (synthetic)
  impact: estimated −0.01 to −0.02 overall if null_gate ships with balanced; +0.01 to +0.02 on B/C if null rows use a random base
  evidence: R/null_check.py: untouched [1]*8 calls, pinned [45]*8; R/null_emit.py table above; emit.py L102–107 (shared herded base_all)
  mechanism: the herded base narrows each gene's distribution, so Wilcoxon calls at least one gene with no mean change; any call gives jac(∅, S) = 0
  fix: emit null rows untouched from a random base (balanced3 path); verify null jac = 1 on a structured synthetic with real-side null calls removed
  effort: hours
  depends_on: none
  seams: B-01, C-04
- id: R-02
  class: Eval
  title: Per-line tile anchors give degenerate fid spans on V* lines (0.012–0.18 against the official 0.30); scaled Δfid is inflated 2–25×
  severity: P1
  confidence: VERIFIED 85%
  impact: a tile-anchored V* forecasts E032 − E021 at −0.032 against LB +0.002
  evidence: replicate fid in results/E037/regime_holdout_*.json; recomputation above
  fix: scale raw V* deltas with the fixed official A/B/C spans; reweight lines by N_conf regime
  effort: hours
  depends_on: O-01
- id: R-03
  class: Engineering
  title: The random-base emitter (balanced3) beats herded balanced on jac and fid for ALL targets at equal MSE (synthetic); the LB emitter choice is unvalidated
  severity: P2
  confidence: SUSPECTED 60%
  impact: estimated; synthetic jac 0.256 vs 0.166 and fid 0.627 vs 0.582, MSE −0.715 vs −0.716
  evidence: R/null.log rows 1 and 3
  confirm: rerun on real A/B/C controls; one LB pair
  effort: hours
- id: R-04
  class: Method
  title: de_budget lifting pushes MSE past no-skill even at 20k-UMI depth
  severity: P1
  confidence: VERIFIED 75% (synthetic)
  impact: −0.024 overall (E032's whole MSE contribution) for any uniform n ≥ 300
  evidence: the arms table under R-1
  fix: score the budget against the official anchors including MSE; lift only genes with low MSE cost, or weigh expected fid gain against MSE cost per gene
  effort: days
```

**Also missed by everyone:** the herded base's spurious calls work by changing each gene's distribution shape rather than its mean. That is a way to get Wilcoxon calls without paying MSE. I'd flag it as a scorer-exploit risk, not something to pursue.
