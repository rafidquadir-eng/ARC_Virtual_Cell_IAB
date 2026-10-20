# Round 4 plan (19 Oct 2026, 01:00 UTC): a validator we can trust, the last 6 leaderboard slots, and D/E/F

**Author:** planning session (chief scientist / engineer review).
**Inputs:**
- the E042 report (commit fdca9e2);
- `review/FINAL_REPORT.md`, `review/findings_{A,B,C,D}.md`, and the red-team report, now saved as `review/findings_RT.md`;
- my re-analysis of the committed rows CSVs (commands below).

**Executes as:** runbook stages E044–E049 in `docs/07_RUNBOOK_INSTANCE.md`.

---

## 0. Where we stand

| | Value | Source |
|---|---|---|
| Our best LB | **0.1077** (E032, B5 @ balanced), rank 688. E021 = 0.1060. | `results/E033_E032_status.json`, `results/E033_E021_status.json` |
| #1 | Illumina 0.461. #3–#5 were at about 0.25–0.33 on 16 Oct (may have moved). | LB snapshot, 16 Oct |
| LB entries left | **At most 6**: 19, 20 and 21 Oct UTC, 2 per day. Whether 22 Oct UTC still counts is unverified. | docs/01 [2] |
| After 22 Oct | Final entries on D/E/F, 2 per UTC day, **no leaderboard shown, only the last final entry counts**. Deadline Thu 5 Nov 23:59 UTC (18:59 ET, after the 1 Nov clock change). | docs/01 [1][2] |
| Compute | 1× A100, $1.99/h. About $250–300 spent if one instance has run continuously since 14 Oct (estimate; **check the Lambda console**). Far below the 50% warning ($3,500). | docs/05 |

**What follows from this.** From 22 Oct the local validator is our only judge, for two weeks. So this round does three things, in order:
1. make the validator trustworthy (seed noise, a second bracket, an out-of-sample test on every LB entry);
2. use it on the cheap levers we already built;
3. have the D/E/F pipeline ready, with branches for whatever the test lines turn out to be.

---

## 1. What E042 established

Re-analysis commands:
- `python scripts/lb_check.py retro --rows results/E031/vstar_rows_E031_seen.csv ...`
- `python scripts/lb_check.py rank --rows results/E020/... results/E031/... results/E034/...`
- `results/E042/regime_holdout_*.json`

| Question | Answer | Status |
|---|---|---|
| Does the tile baseline fix the anchors? | Yes. Baseline fid is 0.50–0.54 on all 7 holdouts (official 0.513). H1-R400 jac is 0.074, against the 0.079 expected. | VERIFIED |
| Are per-line tile anchors usable? | **No.** Baseline reach is 0.06–0.43 against the LB's 0.076; jac is 0.001–0.074 against 0.031; replicate fid spans are 0.02–0.31 against 0.30. `lb_check calib` ALERTs, and retro FAILs (forecast −0.075, LB +0.002). | VERIFIED |
| Does LB-span scaling of raw values work? | **Yes on the one pair we have.** E032 − E021 forecast −0.003, LB +0.002. Levels 0.112 / 0.115 against LB 0.108 / 0.106. Consistent with E001 and E012 too. | VERIFIED (n = 1 pair) |
| Is E032 reproducible? | First 20k of 360k rows are identical; summaries are md5'd. | VERIFIED (partial) |
| Are the panel targets expressed in A/B/C? | Yes. ≥ 5 CPM: A 299, B 295, C 294 of 300. **The null gate has nothing to gate. Retired.** | VERIFIED |
| Does low target expression predict a null response on V\*? | **No.** The N_conf = 0 fraction is flat across target-CPM bins (K562 0.14–0.24; Orion 0.20–0.45). Nulls are a power effect (cells × depth), not "target not expressed". | VERIFIED |
| Emission-seed variance | **Not run** (E042b step 3 skipped, without a note). | OPEN → E045 |

Under the calibrated validator (5 lines, LB spans), the ranking is:
- E021 0.115 ≈ B5 0.112;
- then B5x_tl 0.070, M1_b1.3 0.069, B5x_ml2 0.058, every M1 variant 0.03–0.06;
- the learned translator and the stricter B5 variants are not better. That matches the LB.

---

## 2. Problems: round-4 register

The 17 Oct register (`review/FINAL_REPORT.md` §2) still holds. This adds what E042, the red team and this review found.

| id | Class | Sev | Problem | Evidence | Fix (stage) |
|---|---|---|---|---|---|
| **R4-01** | Eval | **P0** | **The validator rests on one retrodicted pair, chosen after seeing the per-line version fail, and its per-metric agreement is poor.** On E021 vs E032, the overall forecast was within 0.004, but the metric errors cancel: fid under-forecast 2.5× (−0.088 vs −0.226), reach over-forecast (−0.075 vs −0.006), nmae the wrong sign (−0.037 vs +0.025). So V\* still under-rewards anything that improves fid (DE calling), and over-rewards reach and nmae changes. | `lb_check verify` on the E021 forecast (§3) | (i) A second bracket, H1-R400 (below). (ii) **Pre-register every LB entry** (`lb_check forecast` → commit → submit → `lb_check verify`), so each entry is an out-of-sample test. (iii) Stop on a verify FAIL. (E044–E047) |
| **R4-02** | Eval | **P0** | Seed SD is still unknown (D-08 open; E042b.3 skipped). Every Δ < ~0.01 is uninterpretable, including E032 − E021 (+0.0018). | — | E045: 3 seeds of the LB config and E021; 2 seeds at balanced3 |
| **R4-03** | Strategy | **P0** | No feedback after 21 Oct, and only the last final entry counts. | docs/01 | Freeze the protocol (§3). Insurance entry on 22 Oct. Last entry by **4 Nov 23:59 UTC** (24 h margin). Never submit an experimental final after the chosen one. (E048–E049) |
| **R4-04** | Eval | P1 | **The V\* truth regime differs from A/B/C.** N_conf means are K562_GWPS 14, Orion 16 / 28, CD4T 100–123, KOLF 103, against val A 336. LB spans fix the scale but not the composition: an oracle scores LB-span jac 0.30 on V\*. Decisions that trade DE calls against MSE are biased toward under-calling there. | `rank` table; regime JSONs | Bracket every decision with **H1-R400** (N_conf 855, above A/B/C). A candidate must not lose on either side. (E045–E046) |
| **R4-05** | Biology | P1 | **Per-target response strength in an unseen line is untested as a predictor.** R-2 refuted noisy budgets *as implemented*; the oracle-budget arm was killed (OOM), so the upside is unresolved. N_conf is heavy-tailed (val A 4 to about 7,000). | `findings_RT.md` R-2 | `scripts/strength_study.py` (E044): do source strength, DepMap Chronos (pan-line and matched-line), target expression and knockdown rank held-out N_conf? Build only if LOLO Spearman ≥ 0.45 (Phase B). |
| **R4-06** | Method | P1 | **MSE is the largest share of the gap (0.107 of 0.353), and every DE-call lever so far sells MSE** (R-04: lifted arms cross raw MSE 1.0 even at 20k UMI). | `findings_RT.md` R-1, R-04 | `de_budget(max_delta=...)` lifts only genes that are cheap to call. E046 tests n600 / max_delta 0.3 and n1500 / max_delta 0.15. They must hold MSE on both brackets. |
| **R4-07** | Method | P1 | **E021 and B5 are complementary on the LB, but have only ever been compared, never combined.** B5 − E021: pds +0.082, mse +0.144, nmae +0.025, fid **−0.226**, reach −0.006, jac −0.008. | status JSONs | ENS blends 0.5 / 0.5 and 0.3 / 0.7 (E046) |
| **R4-08** | Data | P1 | **D/E/F come with their own perturbation list**, and nothing is known yet about how well our sources cover it, or whether a D/E/F line *is* one of our source lines. If one is (say HCT116 or HEK293T, where Orion is genome-wide), same-line data is the biggest lever we could have, and nothing exploits it today. | docs/01 [3] | Branches built: `scripts/panel_coverage.py`; `contexts_meta` `same_line` plus spec `same_line_w` (`predict_challenge`); `loco --allow-same-line` to measure the gain now on a proxy (CD4T_Stim8hr with CD4T_Stim48hr/Rest allowed; E046). TP53 via `scripts/context_meta.py`. (E049) |
| **R4-09** | Licence | P1 | The NC decision (A-05) needs numbers by 21 Oct. The case for B5 leans on Orion (NC), and KOLF *loses* with NC (−0.031). | `findings_A.md` A-05 | E048: V\* NC on/off on the 3 non-NC lines, plus one pre-registered NC-off LB entry. Rafid decides. |
| **R4-10** | Agent | P2 | Process slips in E042: a step skipped without a note; no E042b/E042c REPORT sections; per-target CSVs not committed; duplicated rows in the retro input (the means were unaffected). | `reports/REPORTS_E037_E041.md` | Standing rules (§6) |
| **R4-11** | Integrity | P2 | The red team found that herded bases produce Wilcoxon calls by narrowing distributions, not by moving means: a scorer-exploit route. | `findings_RT.md` | **We don't pursue it.** An emitter change must be justified by realism (independent cells from a random base), never by call farming. |
| **R4-12** | Engineering | P2 | R-01 (herded base on untouched null rows gives 1 spurious call per null target) is fixed in code: random base. B5 rarely emits all-zero rows, so the LB config should reproduce bit-for-bit, but that hasn't been checked on all 360k rows. | `emit.py` | E044: full-matrix reproduction of E032 |

**Retired:**
- null gate (C-04, C-01): A/B/C express 294–299 of 300 targets;
- constant common response (C-07): R-6 showed the official baseline already contains it, and a target-invariant prediction scores pds 0.5 exactly. A *strength-scaled* common response stays open under R4-05.

---

## 3. The selection rule (supersedes the 17 Oct rule)

**Reference** = the E032 LB config: `B5_z2_a0.5_cis5000` @ `balanced`, seed 0. If E045 adopts balanced3, the reference is the same spec at balanced3.

Scoring uses raw metrics scaled with the LB spans (`results/lb_spans.json`) and the official clamps, through `lb_check rank`, `lb_check forecast` and `compare --anchors-override results/lb_spans.json`.

A candidate gets an **LB slot** only if all four hold:
1. **V\*** (5 lines): Δ ≥ max(0.005, 2 × seed SD), and ≥ 3/5 lines positive.
2. **H1-R400**: Δ ≥ −0.005. No regression on the large-N_conf bracket.
3. **Two-level bootstrap**: P(Δ > 0) ≥ 0.8.
4. **Forecast committed and pushed** (`lb_check forecast`) before `vcc submit`.

After scoring, run `lb_check verify`.
- **FAIL** (overall error > 0.015 or the wrong Δ sign): stop LB entries and report. The validator is suspect until planning reviews it.
- **PASS**: add the entry to the calibration set.

**Calibration entries.** If no candidate qualifies on a UTC day, at most one entry that day may measure something V\* can't (the emitter on real Flex controls; NC off). It is pre-registered the same way.

**Final (D/E/F) choice.** The highest V\* mean among configs that:
- pass rules 1–3 against the reference; and
- did not FAIL `verify`, if they were LB-tested.

Ties go to the simpler config. The LB number is **not** a selection criterion, only a veto (LB below the reference by more than 0.015). This is what "don't tune on the leaderboard" means here.

**Reasoning check.** With 6 entries left and a seed SD likely around 0.003–0.01, choosing the final by LB score would mostly pick noise and A/B/C idiosyncrasies. D/E/F are different lines.

---

## 4. Levers, ranked by expected overall LB gain

The ranges are honest ones: they come from the red team's corrections, not from our earlier hopes.

| # | Lever | Finding | Expected Δ | Evidence so far | Test | When |
|---|---|---|---|---|---|---|
| L1 | Random-base pinned emitter (balanced3) instead of herded balanced | R-03 | 0 to +0.01 | Synthetic only: jac 0.256 vs 0.166, fid 0.627 vs 0.582, equal MSE | E045 (V\* + H1); possibly a calibration LB entry | 19 Oct |
| L2 | Blend E021 + B5 | R4-07 | +0.005 to +0.02 | LB per-metric complementarity | E046 | 19 Oct |
| L3 | Cheap DE calls (`de_budget` + `max_delta`) | O-08, R-04 | −0.01 to +0.02 | Red-team synthetic: fid real, MSE lost | E046; must hold on H1-R400 | 19 Oct |
| L4 | TP53-mismatch source weighting | C-05 | +0.002 to +0.01 | A/B/C all p53-deficient; 9 of 13 sources p53-WT | E046 | 19 Oct |
| L5 | Overdispersion floor | B-03 | ±0.01 | 2–5× noise-gene excess in the top CPM quintile | E046 | 19 Oct |
| L6 | Renormalise source CPM over the Flex axis | C-06 | +0.005 to +0.02 | Unit tests only | E046r | 19 Oct |
| L7 | Per-target strength (budget / magnitude) | C-02, R4-05 | +0.01 to +0.03 *if a predictor exists* | R-2: noisy budgets refuted; oracle unresolved | E044 study; build in Phase B | 19 Oct / 23 Oct+ |
| L8 | Same-line weighting for D/E/F | R4-08 | 0 if no test line matches a source line; potentially the largest lever if one does (unmeasured) | none yet | E046 proxy (CD4T) → E049 | 19 Oct / 22 Oct |
| L9 | New data (Pisces; epithelial / T-ALL Perturb-seq) | C-04, F8 | Unknown; the only plausible route past ~0.2 | Nothing new exists (curation batch 3); Pisces unreleased | Curation agent, batch 4 | ongoing |

**Realistic outlook.** Phase A plausibly moves A/B/C from 0.108 to about **0.12–0.15**.
- The red team corrected the recoverable share from protocol and output-layer fixes to 0.02–0.06.
- **Top 3 (~0.3) is not reachable with transferred public data and these levers.** That needs perturbation data in or near the test lines. This is an inference: Illumina's raw pds of 0.897 is 94% of the replicate's, which looks like in-line data.
- The only branch with a large upside is L8, and it depends on what D/E/F turn out to be.

---

## 5. Timeline (UTC) and stages

| When | Stage | What | GPU h |
|---|---|---|---|
| 19 Oct, first | **E044** (CPU, ~1.5 h) | Validator reproduces on the instance (spans, retro, rank). Full-matrix E032 reproduction. Per-target N_conf tables. Strength study. `context_meta` check. DepMap coverage of A/B/C. `vcc submit --help` (final-entry semantics). Submissions ledger. | 0 |
| 19 Oct | **E045** (GPU, ~2.5–3 h) | Seed variance (ref and E021, seeds 0/1/2). Emitter balanced3 (seeds 0/1). H1-R400 bracket and H1 retro. Seed-0 reproduction of the E031 rows. | ~3 |
| 19 Oct | **E046** (GPU, ~3 h) | 7 specs (L2–L5 and a combination) on V\* and H1-R400. Renorm variants (L6). Same-line proxy (L8). Bootstraps vs reference. | ~3 |
| 19 Oct, late | **E047a** | First LB slot, per §3 (or a calibration entry: the emitter). | — |
| 20 Oct | **E046c** + **E047b/c** | Combinations of the winners (≤ 4 specs). Two LB slots per §3. | ~2 |
| 21 Oct | **E048** + **E047d/e** | Freeze. NC on/off. Dress rehearsal. Test-bundle mechanics. Last two LB slots: the frozen candidate if not yet on the LB, then its NC-off twin as a calibration entry. | ~2 |
| 22 Oct | **E049** | Test bundle. D/E/F identity, TP53, coverage, target expression. Frozen pipeline. **Insurance final entry F1.** Stop for planning if a D/E/F line matches a source line. | ~1 |
| 23 Oct – 3 Nov | Phase B | Only what E044–E049 justify, planned after E049: L7 if the strength study passes; L8 if a line matches; Pisces if released. At most one final entry per day, each a full candidate under §3. | ≤ 20 |
| 4 Nov ≤ 23:59 | **Last final entry** | 5 Nov is margin only. | — |

**Compute:** about 30 GPU-h in total, about $60. Remind Rafid to stop the instance whenever it sits idle for more than 1 h. Phase B planning will say whether it is needed at all between stages.

---

## 6. Standing rules for the runbook agent (from D-01…D-10 and R4-10)

1. **Every step ends in an artefact or an explicit `SKIPPED: <reason>` line in its REPORT.** No silent skips.
2. REPORTs go to `reports/REPORTS_E044_E049.md`, one section per stage, each with an **Anomalies** list: anything unexpected, even if not asked.
3. **Commit small results** (CSV/JSON < 5 MB, including per-target tables) under `results/E0xx/`. Never commit data, predictions, `.vcc` files or tokens.
4. **Pre-register LB entries** (forecast JSON committed and pushed first). State how many entries the UTC day has used before each `vcc submit`. Log each entry in `results/submissions.csv`: entry, UTC time, spec, emitter, NC, git hash, `.vcc` md5, forecast file, then the overall score and the six metrics.
5. **Stop and report** on any of these:
   - a **V\*** retro FAIL or a verify FAIL (H1-R400 retro is informational only, never a stop; clarified 20 Oct, §9.2 item 4);
   - a reproduction mismatch outside predicted-null rows;
   - an OOM twice on the same job;
   - any non-ORACLE LB-span scaled metric > 1.5;
   - fewer than 5 V\* lines in a sweep;
   - a stage running past 1.5× its estimate.
6. **No in-place overwrites** of subsets, summaries, anchors or `contexts_meta.json` entries. Write new names. Record every approval Rafid gives in `docs/APPROVALS.md` (date, his words, scope).
7. **Falsify first:** when proposing a mechanism, name the result that would refute it, and check that result before acting on the mechanism.
8. **Budget:** report instance hours per stage. Ask Rafid to stop the instance when the next step waits on him for more than 1 h.
9. **No scorer exploits** (R4-11).
10. **Phase B is not started without a planning update.**

---

## 7. What we're deliberately not doing

- **iMEMORY in the final.** The patent is not filed, and the finalist description Arc publishes would have to mention it. It stays out unless counsel signs off (docs/01).
- **The M1 translator and larger learned models.** Calibrated V\* puts M1 at 0.05–0.07, below B5 and E021, consistent with the LB. There's no time for a model class that hasn't beaten the simple consensus.
- **Tuning on the LB** (§3).
- **The null gate and a constant common response** (retired, §2).

---

## 8. Open questions for Rafid

1. **NC licence for the final** (R4-09). Decide on 21 Oct from E048's numbers. The default is to keep NC on, per your 15 Oct approval.
2. **Spend.** Please confirm the actual Lambda spend on the console, and stop the instance between stages when nobody is running anything.
3. **22 Oct timing.** When does the test bundle appear (UTC)? Can you be online about 2 h after, for the insurance entry and the same-line decision?

---

## 9. Update 20 Oct, 01:30 UTC: review of E044–E046 and the plan to 21 Oct

### 9.1 What the agent found

Planning re-checked these from the committed rows: the forecasts below were recomputed with `lb_check forecast`.

| Item | Result |
|---|---|
| Validator on the instance | Retro PASS; ranks identical to planning's (E021 0.115, B5 0.112) |
| E032 reproduction | **0 of 360,000 rows differ**, so the R-01 emitter change touches nothing in the LB config. E031 V\* rows reproduce exactly (Δ = 0 on all raw metrics). |
| Seed SD\* | **0.0015** (B5; E021 0.0004). V\* retro PASSes on all 3 seeds. |
| L1 emitter (balanced3) | Null (+0.001 / −0.003). **Closed; keep `balanced`.** |
| L2 blend E021 + B5 | **w55 +0.0141 (4/5 lines, P 0.97); w37 +0.0135 (4/5, P 0.99).** H1 +0.025. Qualifies. |
| L3 cheap calls | **bud600md0.3 +0.0074 (4/5, P 0.95)**, H1 +0.021. Qualifies. bud1500md0.15 is null. |
| L4 TP53 weighting | −0.005. **Closed.** |
| L5 variance floor | −0.007, CI fully negative. **Closed.** |
| L6 Flex-axis renorm | ±0.001. **Closed.** |
| L7 per-target strength | LOLO Spearman 0.31 < 0.45. **Not built.** It works where truths are deep (H1 0.62, K562 0.43) and fails on thin ones (CD4T, KOLF 0.10). |
| L8 same-line data | **CD4T_Stim8hr with Stim48hr/Rest allowed: +0.17 / +0.21 / +0.22 at line weight 1 / 3 / 10, not plateaued.** By far the largest effect in the project. Caveat: same donors, different stimulation state, so this is an upper-end proxy. |
| Final-entry mechanics | No CLI flag. `vcc status --json` carries `is_final` and `partition` (`val`), so the final flag seems to be set server-side or on the website (**unverified**). The test data should appear in `vcc datasets list` (unverified). |
| DepMap | HeLa (B) is not in CRISPRGeneEffect 24Q4. Irrelevant now that L7 isn't built. |

Pre-registered forecasts. These are LB overall scores: E032 (0.1077) plus the V\* Δ.

| Candidate | Forecast | Lines positive |
|---|---|---|
| ENS_E021B5_w55 | **0.122** | 4/5 |
| ENS_E021B5_w37 | 0.121 | 4/5 |
| B5_z2_bud600md0.3 | 0.115 | 4/5 |
| B2 (E021) | 0.110 (LB 0.106) | 2/5 |

### 9.2 Problems found in this review

1. **The one retrodiction pair is not like-for-like (new, P1).**
   - The E021 LB entry used **11 summaries, no Orion** (`results/submissions.csv`).
   - Its V\* rows (E031/E045) use Orion as a source on the three non-Orion lines.
   - E035 measured NC as worth about +0.015 on V\*. So the retro PASS compares two configs that differ in data as well as model.
   - *Fix (E050b):* rerun E021 (and B5) on V\* with `--exclude-licence NC`, then retro "E021 without NC vs B5 with NC", as on the LB. The same rows give the NC on/off reference numbers that R4-09 needs, a day early.
2. **The two brackets disagree on ranking (P1).**
   - On H1-R400, plain E021 (0.138) beats the blends (0.088), which beat B5 (0.062).
   - H1's retro FAILs: its pds Δ has the wrong sign against the LB (−0.051 vs +0.082).
   - A/B/C's N_conf (336) sits between V\* (14–123) and H1 (855). On fid, the LB Δ (−0.226) lies between V\* (−0.088) and H1 (−0.318).
   - *Decision:* H1-R400 stays a **no-regression veto** (rule 2) and is **not** used to rank candidates. Its ranking can't be trusted for pds.
   - The LB entries on 20 Oct decide between the blend and the budget lever. The first entry tests L2 and the second tests L3 (or their combination), so each lever is checked separately against its forecast.
3. **`verify` can't detect a gain that disappears (P2).** A +0.014 forecast is within the 0.015 tolerance of "no gain".
   - *Added rule:* an LB entry **confirms** a lever only if LB Δ vs E032 ≥ +0.005 (about 3× the local seed SD). Within ±0.005 it is **unconfirmed**; below −0.005 it is **vetoed**. Only confirmed levers may be combined into the frozen config.
4. **My stop rule cost about 5.9 h of idle instance.** §6 rule 5 said "any retro FAIL", but the runbook expected H1-R400 retro to fail.
   - *Clarified:* only a **V\*** retro FAIL or a **`verify`** FAIL is a stop. H1-R400 retro is reported, never a stop.
   - Within one approved batch of stages, the agent continues from stage to stage without waiting, as long as the rules pass.
5. **D/E/F same-line branch: the gain is now evidenced, but the weight is not chosen** (L8). CD4T conditions share donors, so the effect is likely an upper bound.
   - *Fix (E050c):* a second, more realistic proxy. Hold out **K562_GWPS** with the **K562 essential screen** allowed: same line, different lab, library and depth. This is what a D/E/F match to one of our public sources would look like. Run weights 1 / 3 / 10 / 30, and extend CD4T to 30 / 100.
   - Planning sets `same_line_w` from both proxies before 22 Oct.
6. **The old E038/E039 chain was still on the GPU when round 4 began.** The agent handled it correctly (let the in-flight run finish, then killed the chain). E038's 17 H1-R400 rows exist but are unreported; they aren't needed.

Closed levers: L1, L4, L5, L6, L7. Open: **L2 (blend), L3 (cheap calls), L8 (same-line)**.

### 9.3 Plan for 20–21 Oct (UTC)

| When | Stage | What |
|---|---|---|
| 20 Oct, first | **E047a** | LB: `ENS_E021B5_w55` (forecast 0.122). It already qualifies under §3. |
| 20 Oct, after E047a is built | **E050** (GPU, ~2.5 h) | a) Blend + budget combinations, plus the E021 0.7 / B5 0.3 blend (V\* + H1). b) NC-off V\* of E021 and B5, and the like-for-like retro. c) Same-line proxies (K562_GWPS + K562; CD4T at weights 30/100). |
| 20 Oct, after E050 and the E047a score | **E047b** | LB: see the decision rule in the runbook. In short: the best E050 combination if L2 was confirmed and the combination beats w55 on V\* by ≥ 0.005; otherwise `B5_z2_bud600md0.3`, to test L3 on its own. |
| 21 Oct | E048 | Freeze (rule below), NC on/off, rehearsal, then the last 2 LB slots: the frozen config if not yet on the LB, and its NC-off twin. **Needs Rafid's NC decision.** |
| 22 Oct | E049 | As written. If a D/E/F line matches a source line, `same_line_w` comes from E050c. |

**Freeze rule (E048):**
- The frozen config is the highest-V\* config built **only from confirmed levers** (§9.2 item 3).
- If no lever is confirmed, the frozen config is the better of E032 (B5) and E021 on the LB.
- The two are within noise there, so in that case take B5: it is the current reference, and E032 is our best LB entry.

---

## 10. Update 20 Oct, 04:30 UTC: why E047a didn't move the score, and the fix

**E047a (`ENS_E021B5_w55`) scored 0.1076. E032 is 0.1077; the forecast was 0.122 (verify PASS at err 0.014, unconfirmed).**

LB scaled scores (raw value in brackets):

| | pds | mse | fid | reach | jac | nmae | overall |
|---|---|---|---|---|---|---|---|
| E032 (B5) | 0.583 (0.764) | **0.144 (0.851)** | −0.293 | 0.102 | 0.000 | 0.111 | 0.1077 |
| E047a (blend 0.5/0.5) | **0.620** (0.781) | **0 (1.139)** | −0.264 | **0.139** | 0.007 | **0.143** | 0.1076 |
| E021 (dense) | 0.501 (0.727) | 0 (**4.663**) | −0.067 | 0.108 | 0.008 | 0.086 | 0.1060 |

**Diagnosis.**
- The blend improved **five of six** metrics: pds +0.038, fid +0.029, reach +0.037, jac +0.007, nmae +0.033. That is worth +0.024 overall.
- **MSE gave back exactly that amount.** Raw MSE went from 0.85 to 1.14. That crosses the no-skill point (~0.99), and the score clamps at 0, a loss of −0.144 scaled.
- The dense E021 component is the cause. On A/B/C, E021 alone has raw MSE **4.66**: its transferred effects are mostly noise in magnitude, even where their directions help the DE metrics.
- Our validator under-forecast the damage: V\* E021 raw MSE averages about 2.5, against 4.66 on A/B/C, and the MSE span is still *assumed*.

**This is a magnitude-calibration problem, not a data limit.**
- Mean-squared error of a blend w·E021 + (1−w)·B5 is close to quadratic in w.
- From the three LB points (w = 0, 0.5, 1): MSE(w) ≈ 6.47w² − 2.66w + 0.85.
  - The negative linear term means the two models' errors partly cancel.
  - Minimum ≈ **0.58 at w ≈ 0.2**, i.e. scaled MSE ≈ 0.44 instead of 0.144.
- **Independent local check** (planning, committed V\* rows): fitting the same quadratic per line gives optimal w of 0.24 / 0.30 / 0.21 / 0.25 / 0.15 (CD4T, K562, KOLF, HCT116, HEK293T). So the local data, without the LB, also points to w ≈ 0.2.
- The LB fit is used only as a sanity check. Selection still goes through V\* (§3).

**Expected effect of w ≈ 0.2** (estimate, not a forecast):
- MSE +0.2 to +0.3 scaled, i.e. +0.03 to +0.05 overall;
- the other metrics keep part of the blend's +0.024;
- so **LB ≈ 0.13–0.16**.

The uncertainty is the quadratic assumption: the metric is "unbiased" and "capped", so it isn't exactly quadratic. That is why we run a weight sweep rather than one guess.

**Plan.**
- **E051** (GPU, ~1.2 h): `specs_E051.json` = blends with E021 weight 0.10 / 0.15 / 0.20 / 0.25, on V\* and H1-R400.
- **E047b** (LB): the best E051 weight that passes §3 against B5, replacing the previous E047b rule.
- E050's (a) arm (more-E021 blends, w73) is moot; E050 (b) and (c) are still wanted.
- **21 Oct:** if E047b is confirmed (Δ ≥ +0.005), the frozen config is that blend.
  - Optionally add `de_budget` if E050 shows the combination helps without losing MSE.
  - The second 21 Oct slot is the NC-off twin.
