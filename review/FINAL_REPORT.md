# FINAL REPORT: full review of the VCC 2026 effort (17 Oct 2026)

**Who did what.** The planning session (Claude) acted as lead reviewer. Four auditors covered A data/splits, B engineering, C biology and D agent behaviour, followed by a red team.

**Read with:** `review/SHARED_BRIEF.md` (context, timeline, schema) and the auditor registers `review/findings_{A,B,C,D}.md`. The red-team verdicts are in §2.

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

**If the team fixes exactly these items, do we close the gap?** No.
- Fixing root causes 1–2 plausibly takes the LB from 0.108 to about 0.15–0.20, and root cause 3's fixable parts add perhaps another 0.02–0.06.
- That would put us in contention for the 0.25–0.33 band (#3–5). The mechanism behind the remaining ~0.2 is **unexplained** in detail.
- E039's noise ceilings will show how much target-specific accuracy is achievable with the data we have.
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

### 2a. Red-team verdicts
_(to be filled from the red-team report)_

---

## 3. P0/P1 write-ups
_(see §3 below, filled after the red team)_

## 4. Gap decomposition
_(after the red team)_

## 5. Error analysis
_(after the red team)_

## 6. Runbook-agent assessment
_(after the red team)_

## 7. Action plan
_(after the red team)_

## 8. Open questions
_(after the red team)_

## 9. Coverage
_(after the red team)_
