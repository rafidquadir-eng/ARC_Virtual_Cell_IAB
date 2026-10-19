# FINAL REPORT: full review of the VCC 2026 effort (17 Oct 2026; completed 19 Oct with E042 and the red team)

**Who did what.** The planning session (Claude) acted as lead reviewer. Four auditors covered A data/splits, B engineering, C biology and D agent behaviour, followed by a red team.

**Read with:**
- `review/SHARED_BRIEF.md` (context, timeline, schema);
- the auditor registers `review/findings_{A,B,C,D}.md`;
- the red-team report `review/findings_RT.md`;
- the plan that executes this review, **`docs/16_PLAN_ROUND4.md`** (runbook E044–E049).

**19 Oct update, read this first:**
- §1's "single highest-leverage action" (E042) is done: the key check PASSed.
- The red team cut the recoverable share from 0.05–0.11 to **0.02–0.06**, so §1's "0.15–0.20" is now **about 0.12–0.15**.
- The working validator is **raw metrics scaled with the LB spans**, not per-line anchors (R-02).

**Status key:** CONFIRMED / REFUTED / PARTIAL / UNRESOLVED (red team); VERIFIED (inspected artefact or executed check); LIKELY / SUSPECTED.

---

## 1. Executive summary

**The score we can trust: LB 0.1077** (E032, rank 688; official status JSON `results/E033_E032_status.json`).
- SOTA is Illumina at 0.461, scored on the same LB under the same protocol, so the gap is **0.353**.
- The LB uses r4 bundles. Their rule and config digests and their anchors are byte-identical to r3 (cell_eval2 0.19.0 `real_bundle.py` L73–76), so our installed scorer, 0.18.0 at rule v3, has the same semantics.
- **Every local scaled score before 17 Oct is untrustworthy** for the DE metrics (fid, jac, reach) and for MSE. Their raw values are fine.
- The emission-seed spread of any LB config has never been measured. So the E032 − E021 improvement of +0.0018 is statistically meaningless.

**Root causes of the gap, ranked:**
1. **We never checked local validation against the LB, so for two days we optimised the wrong thing** (O-01, A-01, A-03, B-04, D-01).
   - The local baseline was built "dispersed", with resampled control cells. The official baseline uses identical cells ("tile").
   - As a result, local fid/jac/reach sat on the wrong scale. Local baseline fid was 0.03, the official one is 0.51.
   - Three further distortions:
     - most V\* lines are full of no-response targets;
     - two V\* lines are sibling lines from one study (Orion HCT116/HEK293T);
     - the CI was too narrow.
   - Together these made B5 look +0.029 better; on the LB it was +0.002.
   - One back-out from the E033 status JSON on 16 Oct at 07:15 would have shown all of this. That was about 15 h and about 8 GPU-hours before anyone acted on it.
2. **The output layer treats all 300 targets the same and calls too few DE genes, so fid sits below chance** (O-08, C-02, C-01/C-04, B-02, F4).
   - fid = k/max(n_pred, N_conf), and a match is counted on any gene, so calling at least as many genes as the truth has, with coin-flip directions, scores about 0.51.
   - B5 calls fewer genes than that and scores 0.42, which is −0.29 scaled (−0.049 overall).
   - True response size N_conf ranges from 0 to about 7,000 per target, with a median of about 40 and a mean of 336 on val A. Yet every config gives every target the same treatment.
   - The emitter we've submitted with since E021 makes the scorer call about 2.7% of genes even on a no-change prediction.
3. **Target-specific predictive accuracy is the dominant real deficit, about 0.22–0.29 of the gap, mostly MSE, then reach, nmae and pds. It has not been shown to be a biological limit** (C-03, C-05, C-06, B-03, C-08).
   - The "transfer at chance" reading is a measurement artefact: noise caps cosine and top-k overlap even under perfect transfer, and LB reach is above no-skill.
   - The transferred signal is contaminated in three ways:
     - p53 and T-cell-activation programmes that Jurkat, HeLa and CAL-33 can't mount pass B5's filter;
     - source CPM includes genes the Flex probe set lacks;
     - B5's noise model has no overdispersion floor.
   - Unused priors (dependency, paralogs, pathways, target expression) are sitting on the instance.
4. **The test lines are far from our data, and the leaders likely aren't** (C-04, A-05, docs/15 F8).
   - A = Jurkat, B = HeLa, C = CAL-33 (E041). None has public single-cell CRISPRi data on the panel.
   - Most sources use a different chemistry (3′/5′, not Flex).
   - The case for the current LB config rests on NC-licensed Orion.
   - Illumina announced a 1-billion-cell atlas in 200+ lines (January 2026). That the leaders' advantage comes from this kind of data is an inference.

**Single highest-leverage next action.** Pull and run **E042 → E042b → `lb_check`**:
- rebuild every local anchor with the tile baseline;
- hash the data and test that E032 reproduces;
- measure seed spread;
- require local validation to retrodict E021 → E032 on the LB.

Only then run E038, the call-budget sweep including per-target budgets. Every later decision depends on a validator that passes that gate.

*Outcome (19 Oct):*
- E042 confirmed the tile fix: baseline fid is 0.50–0.54 everywhere.
- Per-line tile anchors still failed retrodiction (R-02). Scaling raw values with the LB spans passes.
- Seed spread is still unmeasured (moved to E045).
- E038 is superseded by E045/E046.

**If the team fixes exactly these items, do we close the gap?** No.
- ~~Fixing root causes 1–2 plausibly takes the LB from 0.108 to about 0.15–0.20, and root cause 3's fixable parts add perhaps another 0.02–0.06.~~ **Corrected by the red team (R-6):**
  - protocol and output-layer fixes recover about 0.02–0.06 in total;
  - the call-budget lever nets only −0.01 to +0.02, because it sells MSE (R-1, R-04);
  - realistic Phase A target: **0.12–0.15**.
- ~~That would put us in contention for the 0.25–0.33 band (#3–5).~~ **It would not.** At 0.12–0.15 we are well short of the 0.25–0.33 band. The mechanism behind the remaining ~0.2–0.3 is **unexplained** in detail; per-target strength (R4-05) is the one untested in-house lever of size.
- ~~E039's noise ceilings~~ (E039 was not run; the strength study in E044 replaces it as the cheap test of what's achievable.)
- Reaching Illumina's 0.46 almost certainly needs perturbation data in or near the test lines; this is an inference and can't be verified.

---

## 2. Findings register
Sorted by severity, then estimated impact. RT = red-team verdict.

| id | class | sev | title | conf | impact (overall LB) | RT |
|---|---|---|---|---|---|---|
| O-01 | Eval | P0 | Local baseline anchors used "dispersed" emission; the official arm is "tile" (identical cells). Local scaled fid/jac/reach/mse were on the wrong scale. **Fixed** (7e8025f), verification on the instance pending (E042). | VERIFIED 95% | Caused the wrong selection of the E032 config; measured forecast miss 0.027 | not sent (verified) |
| O-03/D-08 | Eval | P0 | LB entries not reproducible from the record: no data hashes, no exact argv, seed spread never measured. E032's +0.0018 can't be told from noise. | VERIFIED 90% | Decision risk; seed SD unknown | n/a |
| D-01 | Agent | P1 | Every alarm (E033 back-out, scaled values > 1, B0 fid +0.47) went unflagged for about 15 h | VERIFIED 90% | About 8.4 GPU-h and 1 LB slot spent on miscalibrated selection | n/a |
| A-01 | Method | P1 | V\* lines are null-heavy (19–24% of targets with N_conf = 0 on K562/Orion), and they flip the LB deltas; KOLF (0% null) matched the LB 6/6 | VERIFIED 90% | They alone produced the +0.029; ranks future specs wrongly | §2a R-4 |
| O-08 | Method | P1 | Under-calling puts fid below chance (B5 0.425 raw vs chance about 0.51); `de_budget` built | LIKELY 75% | +0.03 to +0.05 gross; net depends on the MSE/jac cost | §2a R-1 |
| C-02 | Method | P1 | No per-target budget or magnitude, while N_conf is heavy-tailed and predictable | LIKELY 70% | +0.01–0.03 over a uniform budget | §2a R-2 |
| C-03 | Method | P1 | "Transfer is at chance / a biological limit" is not established; the metrics are noise-limited | VERIFIED 80% | Strategic: re-opens the 0.2+ target-specific gap | §2a R-3 |
| A-02 | Data | P2 | Holdout panel chosen from summary-level filters (kd ≤ 0.7, summary ncells), not the truth cells; 7–29% of targets dropped | VERIFIED 90% | Bias of unknown sign | – |
| A-03 | Method | P2 | Orion sibling lines inflate V\* (+0.031 on the selection Δ) | VERIFIED 80% | Selection error | – |
| A-05 | Data | P2 | The case for the LB config rests on NC-licensed Orion; KOLF gets worse with NC (−0.031); `final_pipeline` defaults to NC on | VERIFIED 85% | Licence risk for the D/E/F entry; ± about 0.01 | – |
| B-01 | Engineering | P2 | Untouched null rows (d222976) add a common-mode MSE error; **conflicts** with the orchestrator's null test | VERIFIED 85% (synthetic) | ≤ 0.01 | §2a R-5 |
| B-02 | Engineering | P2 | balanced2/2h leave unpinned genes on a shared base (MSE 1.87 vs 1.04); **@b2 specs removed from E038** | VERIFIED 95% | ≤ 0.024 if submitted | – |
| B-03 | Method | P2 | B5's noise variance has no overdispersion floor, so it keeps 2–5× too many noise genes in the top CPM quintile; **`var_floor` option added** | VERIFIED 85% | Unknown sign; test in E038 | – |
| B-04 | Eval | P2 | Bootstrap CI ignores between-line variance and is about 4× too narrow; **fixed** (two-level) | VERIFIED 90% | Selection error (E031 CI +0.011..+0.039 vs LB +0.002) | – |
| C-04 | Biology | P2 | No target-expression gating on the LB path. A expresses 299/300 targets; B/C unknown. `null_gate` built | VERIFIED (A) / SUSPECTED (B, C) | ≤ +0.02 (B/C, jac only) | – |
| C-05 | Biology | P2 | p53, RB and T-cell-activation programmes from p53-WT and stimulated sources pass B5's filter for p53-deficient, unstimulated A/B/C | LIKELY 65% | 0.002–0.01 | – |
| C-06 | Data | P2 | Source CPM is normalised over genes absent from the Flex axis, so it carries composition shifts the truth doesn't have | LIKELY 60% | 0.005–0.02 | – |
| C-07 | Biology | P2 | Common (context-mean) response not predicted; the exact-line Jurkat data is unused for A | LIKELY 60% | 0.005–0.02 | – |
| C-08 | Biology | P2 | Dependency, paralog, pathway and expression priors are on disk and unused | LIKELY 60% | via C-02/C-07 | – |
| D-02 | Agent | P2 | E037 rebuild was driven by a hypothesis its own table could falsify; jac/reach reported as "in the official range" when they weren't | VERIFIED 85% | About 3.6 h | – |
| D-03 | Method | P2 | Post-hoc explanations misattributed the V\*-vs-LB gaps; the proxy, which got the fid sign right, was demoted | LIKELY 70% | Decision quality | – |
| D-04 | Agent | P2 | H1 subset overwritten in place on an unrecorded "approved by R"; mixed-version E037 artefacts | VERIFIED 85% | Provenance | – |
| O-10 | Method | P2 | My own round-3 diagnosis (docs/15 P8) blamed truth size and depth for the V\* fid anomaly. E037 refuted it; the cause was O-01. | VERIFIED | About half a day of agent time | – |
| C-01 | Eval | P2 | For N_conf = 0 with nothing called, the scored fid is NaN (dropped), not 1. Abstention pays through jac only. **Brief and docstrings corrected.** | VERIFIED 95% (spot-checked) | Halves the null-gate value | – |
| A-04 | Data | P2 | H1-R400 is mostly off-panel and 2.5× denser than val A; stale per-target files | VERIFIED 85% | Budget calibration bias | – |
| A-06…A-11, B-05…B-07, C-09, C-10, D-05…D-10 | – | P3 | Hygiene and latent issues (see the auditor files). Fixed this round: B-05 (official replicate leg), B-07 (M1 cache key). | VERIFIED | ≤ 0.005 each | – |

**Added after the red team and E042 (19 Oct).** Full details are in `review/findings_RT.md` and `docs/16_PLAN_ROUND4.md` §2.

| id | class | sev | title | conf | impact | status |
|---|---|---|---|---|---|---|
| R-01 | Engineering | P1 | A herded base on untouched null rows still makes 1 spurious call per null target (jac = 0) and loses MSE/pds | VERIFIED 85% (synthetic) | −0.01 to −0.02 if a null gate shipped with `balanced` | **Fixed** 19 Oct: null rows use a random base (`emit.py`) |
| R-02 | Eval | P1 | Per-line tile anchors give degenerate fid spans (0.012–0.18 vs 0.30) | VERIFIED 85%; E042 retro FAIL | Forecast −0.032 to −0.075 vs LB +0.002 | **Adopted:** raw values scaled with the LB spans; retro PASS |
| R-03 | Engineering | P2 | The random-base pinned emitter (balanced3) may beat herded `balanced` on jac/fid at equal MSE | SUSPECTED 60% | 0 to +0.01 | E045 |
| R-04 | Method | P1 | `de_budget` lifting pushes MSE past no-skill even at 20k UMI | VERIFIED 75% (synthetic) | −0.024 for any uniform n ≥ 300 | `max_delta` built; E046 |
| R4-01…R4-12 | – | P0–P2 | Validator rests on one pair; seed SD unknown; no feedback after 21 Oct; V\* truth regime; strength untested; MSE trade-off; E021+B5 complementarity; D/E/F branches; NC decision; agent process slips; scorer-exploit risk; full E032 reproduction | see docs/16 §2 | – | E044–E049 |

### 2a. Red-team verdicts
`review/findings_RT.md`, 16–17 Oct. Two arms (tile-plus-replicate anchors, oracle per-target budgets) were killed by OOM, so those results are UNRESOLVED.

| Claim | Verdict | Conf | What changes |
|---|---|---|---|
| R-1: a call budget lifts fid, +0.045 net (O-08) | **PARTIAL.** The fid mechanism is real; the net gain is about −0.01 to +0.02 | 75% | Every lifted arm crosses raw MSE 1.0 (R-04). fid < 0.5 also comes from sign precision ≈ 0.5, not only from under-calling. A uniform n can't reach 0.5 when N_conf is heavy-tailed: best 0.468 at n = 600. |
| R-2: per-target budgets beat uniform (C-02) | **REFUTED as implemented** (noisy budgets, `cap_others`); oracle budgets UNRESOLVED | 60% | Only a floor-only budget driven by a *good* strength predictor is still open → strength study (E044) |
| R-3: "transfer at chance" not established (C-03) | **CONFIRMED.** But reach is the wrong evidence; pds is the right one | 85% | A target-invariant prediction scores pds 0.5 exactly. LB raw pds 0.764 (E032) is target-specific signal, and cis effects can't explain it (cis-only oracles 0.57–0.61). |
| R-4: which mechanism explains the forecast miss (A-01 vs D-03) | **Additive; both attributions partly wrong** | 80% | The driver on null-heavy lines is small N_conf on *responding* targets. Once n_pred ≥ N_conf, fid equals precision ≈ 0.5 for any model, so those lines can't separate models on fid. |
| R-5: how to emit predicted-null rows (B-01) | **Neither pinned nor untouched with `balanced`; use a random base** | 85% | Fixed (R-01) |
| R-6: gap split | **Mostly CONFIRMED; the recoverable share is overstated** (0.02–0.06, not 0.05–0.11) | 75% | MSE gains can't be farmed: the noise credit is capped. A constant common response is worth about 0 (the baseline already contains it). Strength-scaled common response untested. |

The red team also found the herded base produces Wilcoxon calls by changing distribution *shape*, a scorer-exploit route. We don't pursue it (docs/16 R4-11).

---

## 3. P0/P1 write-ups

**O-01. Local baseline used dispersed emission (P0).** VERIFIED and FIXED.
- *Claim:* the official baseline arm emits identical cells (`competition.py` L304–305); ours resampled controls, so local fid/jac/reach/mse were mis-scaled.
- *Evidence:* E042, after the fix, gives baseline fid 0.50–0.54 on all 7 holdouts (official 0.513). H1-R400 jac is 0.074, against 0.079 expected.
- *Residual:* fixing the arm wasn't enough. Per-line spans stay degenerate on small truths (R-02), so selection now uses the LB spans.

**O-03 / D-08. Reproducibility and seed spread (P0).** PARTIALLY VERIFIED.
- md5 manifest of all 13 summaries: done.
- E032 rebuilt from current code: identical on the first 20k of 360k rows.
- *Open:* full-matrix check (E044), and emission-seed SD, never run, because E042b step 3 was skipped (E045).
- Until the SD is known, no Δ below about 0.01 means anything, including E032 − E021 = +0.0018.

**R4-01. The validator rests on one retrodicted pair (P0).**
- LB-span V\* forecast E032 − E021 at −0.003, against the LB's +0.002 (PASS). Levels 0.112/0.115 against 0.108/0.106.
- But the per-metric errors cancel: fid under-forecast 2.5×, reach and nmae over-forecast.
- We chose the LB-span method after seeing per-line anchors fail, so one pass is weak evidence.
- *Mitigation* (docs/16 §3):
  - an H1-R400 bracket;
  - pre-registered forecasts for every LB entry, with `verify`;
  - stop on FAIL.

**R4-02 / R4-03. No seed SD; no feedback after 21 Oct (P0).**
- At most 6 LB entries remain. From 22 Oct, only the last final entry counts and no LB is shown.
- *Action:*
  - E045 measures seeds;
  - E048 freezes a protocol;
  - E049 makes an insurance entry on 22 Oct;
  - the last final entry goes in by 4 Nov 23:59 UTC.

**D-01. Alarms unflagged for about 15 h (P1).** VERIFIED; process fix.
- The E033 back-out on 16 Oct 07:15 already showed the LB-implied fid baseline of 0.51.
- *Fix:* standing stop-and-report triggers (docs/16 §6) and `lb_check calib`/`retro`/`verify` as gates.

**A-01 → R-4 / R4-04. V\* line composition (P1).** Reframed by the red team.
- Null share isn't the mechanism; small N_conf on responding targets is.
- V\* N_conf means are 14–123, against 336 on A/B/C. LB spans fix the scale, not the composition.
- *Action:* bracket every decision with H1-R400 (N_conf 855).

**O-08 / R-04 / R4-06. Under-calling vs MSE (P1).** PARTIAL.
- fid is below chance (B5 0.425 raw). Lifting calls recovers fid but sells MSE, the largest share of the gap.
- *Action:* `de_budget(max_delta)`, which lifts only cheap genes, tested on both brackets in E046.
- Expected −0.01 to +0.02.

**C-02 / R4-05. Per-target strength (P1).**
- As implemented, it was refuted (noisy budgets).
- Whether *any* zero-shot predictor of per-target response strength exists is untested. That is the one in-house lever with a plausible +0.01–0.03.
- *Action:* `scripts/strength_study.py` (E044). Build in Phase B only if LOLO Spearman ≥ 0.45.

**C-03 / R-3. Transfer is not at chance (P1).** CONFIRMED.
- pds proves target-specific signal (0.764 raw vs 0.5 for any target-invariant prediction).
- So the 0.2+ target-specific deficit is a modelling/data deficit, not a proven biological limit.

**R-01. Null rows on a herded base (P1).** FIXED (random base); verified on synthetic data.
- It only matters for all-zero rows, which B5 rarely emits. E044 checks the full E032 reproduction.

**R4-07. E021 + B5 never blended (P1).**
- On the LB they are complementary: B5 +0.08 pds, +0.14 mse, +0.03 nmae; E021 +0.23 fid.
- E046 tests 0.5/0.5 and 0.3/0.7 blends.

**R4-08. D/E/F unknowns (P1).**
- D/E/F have their own perturbation list, unknown source coverage, and possibly a same-line source.
- *Built:* `panel_coverage.py`, `context_meta.py`, `contexts_meta.same_line` + `same_line_w`, and `loco --allow-same-line`, with a proxy test in E046.

**R4-09. NC licence (P1).**
- *Decision data:* E048 runs V\* NC on/off on the non-NC lines, plus one NC-off LB entry.
- Rafid decides by 21 Oct.

---

## 4. Gap decomposition

**Gap to #1: 0.353** (Illumina 0.461 vs E032 0.108).

Per-metric shares in overall points (each metric is 1/6 of the score; LB snapshot of 16 Oct):

| metric | mse | fid | reach | nmae | pds | jac |
|---|---|---|---|---|---|---|
| share of the gap | **0.107** | 0.075 | 0.057 | 0.051 | 0.049 | 0.015 |

Attribution, after the red team's corrections:

| Component | Overall points | Basis |
|---|---|---|
| Protocol and output-layer fixes: emitter, call budget net of MSE, null handling | **0.02–0.06** | R-6, R-1, R-5 |
| TP53 weighting, variance floor, axis renorm, E021+B5 blend (untested) | 0.01–0.04 combined, probably not additive | docs/16 §4 L2–L6 |
| Per-target strength, *if* a predictor exists | 0.01–0.03 | R4-05 |
| **Remainder: target-specific accuracy in unseen lines** | **≈ 0.22–0.30** | Mostly MSE, then fid precision, reach, nmae, pds |

The remainder is not explained mechanistically.
- The best-supported hypothesis is the one for the leaders' advantage: perturbation data in or near the test lines. Illumina's raw pds of 0.897 is 94% of the replicate's. This is an inference and unverifiable from here.
- No such public data exists for the A/B/C lineages (curation batch 3).
- If a D/E/F line matches one of our source lines, part of this remainder becomes reachable for that line (L8).

---

## 5. Error analysis

**1. The validator's history** (forecast of E032 − E021; LB +0.002):

| Scaling | Forecast |
|---|---|
| Dispersed anchors | **+0.029** |
| Per-line tile anchors | **−0.075** |
| **LB spans** | **−0.003** |

Per-metric errors under the LB spans: fid +0.14, reach −0.07, nmae −0.06, mse −0.03, pds −0.02. They cancel in the overall.
- V\* under-forecasts fid changes 2.5×, because truths are small and fid ≈ precision once n_pred ≥ N_conf (R-4).
- Decisions driven by fid must therefore also hold on H1-R400.

**2. Where B5 loses to E021: fid.**
- B5 calls too few genes. With E021's dense calls, fid sits at chance (0.49–0.51), because sign precision is about 0.5.
- On the LB, B5 wins pds/mse/nmae and E021 wins fid. Neither has direction skill on the extra genes.

**3. Nulls are a power effect, not an expression effect.** The N_conf = 0 fraction is flat across target-CPM bins on every V\* line (E042c regime JSONs).
- A/B/C express 294–299 of their 300 targets, so the null gate is retired.

**4. Per-line spread.** Under LB spans:
- B5's worst line is KOLF2.1J (−0.131) and E021's is also KOLF (−0.056); the Orion lines are the best (0.18–0.26).
- KOLF is the only V\* line with 0% nulls and the line that matched the LB signs 6/6 in round 3. It is also where B5 is weakest.

**5. Learned models.** M1 sits at 0.05–0.07 under LB spans, below both simple configs. Consistent with the LB, where M1 was never submitted.

---

## 6. Runbook-agent assessment

**Strengths:**
- Executes faithfully, with well-built tables.
- Stopped correctly on a retro FAIL, and ran the prescribed KOLF + CD4T follow-up.
- The E032 partial reproduction and the md5 manifest were done cleanly.
- Flagged the jac-depends-on-N_conf caveat correctly.

**Weaknesses (recurring):**
- *Alarm latency (D-01):* about 15 h before the LB-implied baseline was acted on.
- *Hypothesis-driven work without a falsification check (D-02):* E037.
- *Provenance:* an in-place overwrite on an unrecorded approval (D-04).
- *In E042:* a step skipped without a note (seed variance); no REPORT sections for E042b/E042c; per-target CSVs not committed; duplicated rows in the retro input (harmless here).
- *Over-acceptance of planning hypotheses:* this includes my own docs/15 P8 (O-10), which the agent ran rather than challenged.

**Corrective rules (docs/16 §6):**
- explicit SKIPPED lines;
- an Anomalies list per REPORT;
- commit small results;
- pre-registration;
- stop triggers;
- no in-place overwrites, plus `docs/APPROVALS.md`;
- falsify first;
- per-stage hours.

---

## 7. Action plan
Executed as runbook stages **E044–E049** (`docs/07_RUNBOOK_INSTANCE.md`); rationale in `docs/16_PLAN_ROUND4.md`.

| When (UTC) | Stage | Purpose |
|---|---|---|
| 19 Oct | E044 (CPU) | Validator on the instance; full E032 reproduction; per-target N_conf; strength study; TP53 check; final-entry CLI semantics; submissions ledger |
| 19 Oct | E045 (GPU) | Seed SD; emitter choice; H1-R400 bracket and retro |
| 19 Oct | E046 (GPU) | Lever sweep L2–L6 on both brackets; same-line proxy |
| 19–21 Oct | E047 | ≤ 6 pre-registered LB entries under docs/16 §3 |
| 20 Oct | E046c | Combinations of qualifying levers |
| 21 Oct | E048 | Freeze; NC on/off; dress rehearsal; test-day commands |
| 22 Oct | E049 | D/E/F identity, coverage, same-line check; insurance final entry F1 |
| 23 Oct – 4 Nov | Phase B | Planned after E049; last final entry by 4 Nov 23:59 UTC |

---

## 8. Open questions

1. **MSE span.** b = 0.99, r = 0.05 is *assumed*: E021's scaled MSE is clamped at 0. An LB entry with 0 < scaled MSE < 1 that differs from E032 by > 0.05 would solve it.
2. **Seed SD vs the Δs we're chasing** (E045).
3. **Does H1-R400 retrodict E021 → E032?** It is one line, so a FAIL on magnitudes is likely. Is the sign right?
4. **D/E/F.** Which lines? Same-line matches? Coverage of their perturbation list? TP53?
5. **NC licence for the final** (Rafid, 21 Oct).
6. **Does a validation LB entry on 22 Oct UTC still count, and how is a final entry marked?** (E044 CLI help; unverified.)
7. **Is the leaders' advantage in-line data?** Inference; unverifiable.
8. **Pisces release:** still README-only on 16 Oct.
9. **Can any zero-shot feature rank per-target response strength** (E044 strength study)?

---

## 9. Coverage

**Reviewed:**
- every report in `reports/` through E042;
- `results/` E003–E042;
- `docs/00–15` and EXPERIMENT_LOG;
- `src/vcc26/` (local_eval, loco, vstar, models B2/B5/ENS/de_budget/null_gate, emit, detect, compare, proxy, translator, predict_challenge);
- `scripts/` (lb_check, rescale_rows, regime_check, target_expr, ccle_match, final_pipeline);
- `loco.json`;
- the scorer sources `cell_eval2` 0.18.0 (competition, delta, direction, discrimination) and 0.19.0 `real_bundle.py`.

**Executed:**
- LB back-outs, retro and rank on committed rows;
- synthetic tests of the emitters, `de_budget`, ENS, p53 weighting, renorm, the strength study, `vstar_par.sh` and `panel_coverage.py`;
- the red team's synthetic arms (`review/findings_RT.md`).

**Not covered:**
- GPU reruns on real data: the planning session has no instance. Everything marked E044–E046 is still to be run.
- The red team's OOM arms.
- Per-context (A/B/C) LB scores: `vcc status` gives aggregates only.
- The challenge web pages that render only in a browser: final-entry rules are "unverified".
- Licence review beyond what docs/03 records.
