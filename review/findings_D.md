# Findings D: runbook-agent behaviour (Auditor D)

Saved by the orchestrator: the auditor was not allowed to write files.

**Window:** E030–E041 plus the LB entries E001/E012/E021/E032. Runbook line numbers are as of `9ea55c5`.

**Short verdict:**
- **Faithful:** about 120 recomputed numbers match their artefacts.
- **Compliant:** all four LB entries were allowed and the 2-per-day cap was respected.
- **Commit hygiene:** clean.
- **Weak at analysis:** red flags went unflagged; the LB-vs-local fid contradiction was provable from E033 (16 Oct 07:15 UTC) but was escalated only about 15 h later; post-hoc explanations misattributed gaps; the "approved by R" H1 rebuild is unrecorded.

---

- id: D-01
  class: Agent
  title: The agent's own artefacts showed the LB-vs-local anchor contradiction from 16 Oct 07:15 UTC (E033), with earlier red flags from E020, but no report flagged it
  severity: P1
  confidence: VERIFIED 90% (the signal was present; counterfactual impact estimated)
  impact: >
    No LB loss is measured from this alone. Estimated cost:
    - about 15 h of diagnosis latency;
    - about 8.4 GPU-h of V\* selection (E031, E034b, E035) and about 2.3 CPU-h of proxy runs (E030, E034a), all chosen on DE-scaled V\* scores now known to be on the wrong scale;
    - one LB slot (E032) spent on a config whose V\* edge was mostly a fid-scaling artefact.
  evidence: |
    1. E033 table (REPORTS_E030_E036 L25; results/E033_E021_status.json): fid raw 0.4926, scaled −0.0667, which implies b_LB(fid) > 0.4926. Local fid baselines: E003 0.051–0.292; E011 0.025; V\* 0.005–0.035.
    2. Two-point back-out after E032, recomputed:
         pds   b 0.4984 r 0.9541
         nmae  b 0.9924 r 0.4635
         fid   b 0.5126 r 0.8121   (official mean 0.5126)
         reach b 0.0763 r 0.9902
         jac   b 0.0309 r 0.3561
    3. Unflagged red flags:
       - E020: ORACLE balanced fid 1.530, pds 1.246, nmae 2.101 (scaled > 1); B1_generic fid +0.507; every jac < 0.
       - E031: B0 fid +0.467; B5 HCT116 pds 1.147.
       - The runbook already said (L77): "if not … something is wrong with emission or anchors".
  mechanism: Selection kept trusting V\* scaled fid/jac/reach, which sat on a dispersed-baseline scale (O-01).
  confirm: n/a; the E042 rescale shows how much changes.
  fix: >
    1. An LB calibration check after every `vcc status`: back out b and r, diff them against local anchors, and raise a CALIBRATION ALERT that stops work if any raw gap > 0.05.
    2. Sanity asserts written into an "Anomalies" section of every REPORT.
    Verify: replaying E033 fires the check.
  effort: hours
  depends_on: O-01
  seams: O-01; B (balanced-emitter spurious calls inflate B0 fid)

- id: D-02
  class: Agent
  title: The E037 diagnosis was right in direction but late; the first hypothesis (100-cell cap) was falsifiable from the agent's own table, and the rerun report misstated jac and reach as "in the official range"
  severity: P2
  confidence: VERIFIED 85%
  impact: >
    Estimated: about 3.6 h of critical-path time, plus a 9.1 GB rebuild and re-download. The rebuild does have lasting value (O-06).
  evidence: >
    - The first table already showed baseline fid 0.005–0.035 on all 7 holdouts, unrelated to depth or N_conf. For example, CD4T_Stim48hr at 167 cells reads 0.0051 and H1 at 100 cells reads 0.0188.
    - The rerun at 400 cells gave 0.0295, which falsified the hypothesis.
    - L69 claims baseline jac/reach are "in the official range". They aren't: jac 0.0121 vs 0.0333; reach 0.096 vs 0.042; the tile prediction for jac is about 0.079.
    - Missed but reachable: `cell_eval2/cli.py` L384–387 (`baseline --emit {dispersed,tile}`) and competition.py L305. Mitigation: the CLI help calls tile "legacy, known-biased".
  mechanism: A data rebuild driven by a hypothesis, with no cheap falsification test first.
  confirm: n/a
  fix: >
    A falsify-first rule: before any rebuild or rerun longer than 30 min, state the prediction and run the cheapest disproving test. Require official/local ratios rather than adjectives.
  effort: hours
  depends_on: none
  seams: O-01; scorer docs vs official bundles

- id: D-03
  class: Method
  title: Explanations after E021, E032 and E034 misattributed the V\*-vs-LB gaps and steered planning to demote the proxy, the one tool that got the fid sign right
  severity: P2
  confidence: LIKELY 70%
  impact: >
    Decision quality. The M1 rejection survives re-weighting by LB spans (M1 − B5: −0.0225 → −0.045). The proxy was demoted on the strength of a wrong framing.
  evidence: |
    Gap decomposition for E021 → E032, contribution = (LB Δ − V\* Δ)/6:
      metric  V*_delta  LB_delta  gap_contrib
      pds     +0.101    +0.082    −0.0032
      mse     +0.259    +0.144    −0.0192
      nmae    −0.035    +0.025    +0.0100
      fid     −0.039    −0.226    −0.0312
      reach   −0.117    −0.006    +0.0186
      jac     +0.006    −0.007    −0.0023
      total   V* +0.0291, LB +0.0018, gap −0.0273
    fid alone is 114% of the gap, which is a calibration failure, not a lineage effect.
    The E032 explanation "test contexts likely have broader DE sets" is not supported: val A N_conf mean is 336, while B5 keeps a median of 1,002 genes.
    E034 (L303) "proxy overrates M1" goes against the only LB-calibrated pair: proxy de_sign 0.541 → 0.355 predicted the LB fid drop; V\* did not.
    The proxy's MSE term is 0 for every non-oracle spec (all mse_sc < 0).
    Planning adopted the framing (docs/15 P12).
  mechanism: Each misattribution moved trust toward the miscalibrated local metric.
  confirm: After E042, compare proxy de_sign/dirprec with the rescaled V\* fid and with the next LB pair.
  fix: >
    A forecast-vs-LB per-metric table after every LB result; an explanation must cover at least 50% of the gap; a tool may only be called miscalibrated against an LB pair.
  effort: hours
  depends_on: D-01
  seams: B

- id: D-04
  class: Agent
  title: The H1 subset rebuild ("approved by R") has no approval record; it overwrote the loco.json-referenced file in place and left mixed-version artefacts in results/E037
  severity: P2
  confidence: VERIFIED 85% (the approval is unverifiable from the repo, not shown to be fabricated)
  impact: No LB impact. Older H1 holdouts can't be regenerated from the registry, and E037 artefacts mix two truths.
  evidence: >
    - The claim appears only at REPORTS_E037_E041 L54; there is no planning commit or EXPERIMENT_LOG update between 6d6f462 and 9ea55c5.
    - The agent's own "cleanest" option was a separate file; instead it rebuilt in place (`H1_cap100.h5ad` reportedly kept, unhashed).
    - Readers of the file: `loco.py` L94 and `scripts/data_qc.py` L33.
    - Regime/detect JSONs were overwritten in place, while `scores_`/`pertarget_H1_R400_seen_E037` are still the cap100 run.
  mechanism: An untracked registry change breaks provenance.
  confirm: R's chat excerpt; md5 of `$DATA/subsets/H1*.h5ad`; `H1_cap100` reproduces 6d6f462.
  fix: >
    An approvals ledger (`docs/APPROVALS.md`); write-once registry files; versioned `results/` files.
  effort: hours
  depends_on: none
  seams: A-04

- id: D-05
  class: Agent
  title: Impossible oracle and anatomy values were reported without comment, and "truth is sparse" was concluded from oracles scored against their own truth
  severity: P3
  confidence: VERIFIED 80% that the values went unflagged; LIKELY 55% that this steered toward sparse models
  impact: Estimated small; it reinforced the sparse direction, which cost fid −0.226 scaled in E032.
  evidence: >
    - E030: ORACLE mse_sc 7.603 (raw −6.417); TOPK1000 3.530; TOPK200 1.312.
    - The conclusion "a few dozen to a few hundred genes" ignored that fid counts any non-zero gene.
    - E034 anatomy N/D "−109960986554465.03"; V\*-far pds 1.147.
  mechanism: Unflagged impossible values let wrong conclusions through.
  confirm: Compare with E039's half-split ORACLE_TOPK.
  fix: The D-01 asserts; a scaled value > 1 or raw MSE < 0 voids that row's conclusions until explained.
  effort: hours
  depends_on: none
  seams: B

- id: D-06
  class: Agent
  title: Report fidelity is high (every sampled number matches), with a handful of unbacked or misstated items
  severity: P3
  confidence: VERIFIED 95%
  impact: None on score; lowers auditability.
  evidence: >
    Matched: E030–E041 tables, bootstraps and the E032 mean-of-six (0.107744).
    Exceptions:
    1. "results/E035/ has per-target data" is false.
    2. H1 ncells, thinning factors, subset size and E036 timings have no artefact (logs/ is gitignored).
    3. Superseded E037 artefacts.
    4. 0.029 vs 0.030.
    5. EXPERIMENT_LOG still shows E037/E041 "planned", with wrong dates on E034–E036.
    6. Sex-marker unit label.
    7. Commands are paraphrased.
  mechanism: Audit and reproduction depend on uncommitted instance state.
  confirm: n/a
  fix: Every number cites a committed artefact; commit a trimmed run.json; update EXPERIMENT_LOG automatically.
  effort: hours
  depends_on: none
  seams: none

- id: D-07
  class: Agent
  title: All LB submissions complied with the runbook and the daily cap; E032 passed only under a lenient reading of "isn't worse on V\*-far"
  severity: P3
  confidence: VERIFIED 90%
  impact: E032 used one slot for +0.0018 (measured).
  evidence: >
    - E001 14 Oct 1/2; E012 15 Oct 1/2; E021 15 Oct 2/2; E032 16 Oct 1/2. E027 was correctly withheld.
    - E032: far aggregate +0.007 [−0.019, +0.026], but 2 of 3 far runs were worse.
    - Deviations: E034a ran early; E036 ran under GPU load; E033 also queried E001; extra bootstraps.
    - No thresholds were changed; the agent stopped correctly at E037.
  mechanism: Ambiguous prose gates.
  confirm: n/a
  fix: Executable gates (`scripts/gate.py`) printing PASS/FAIL; chronological runbook sections.
  effort: hours
  depends_on: none
  seams: none

- id: D-08
  class: Engineering
  title: LB entries are not reproducible from the record (no hashes, no exact argv, logs gitignored); the pipeline is deterministic, so seed variance is invisible unless measured on purpose
  severity: P2
  confidence: VERIFIED 90%
  impact: >
    The E032 − E021 LB Δ of +0.0018 can't be told apart from emission-seed noise. This risks mis-ranking configs for the final, where there is no LB feedback.
  evidence: >
    - No hashes in any REPORT.
    - Identical context_scores to 1e-16 across E031/E034/E035 show determinism and pb/ stability on 16 Oct 08:07–16:35.
    - No seed sweep was ever run.
  mechanism: Every comparison is a single draw; "the same config" may silently differ.
  confirm: E042b.
  fix: >
    A run manifest per experiment. Before a submit: regenerate twice and diff; run 3 emission seeds and report the SD; treat an LB Δ below 2·SD as null.
  effort: hours
  depends_on: none
  seams: O-03

- id: D-09
  class: Agent
  title: No inter-agent race found, but there is no locking, commits can't be attributed to an agent, and unregistered summaries sit in pb/ that two runbook globs still read
  severity: P3
  confidence: VERIFIED 80% (no race found); hazards SUSPECTED
  impact: Latent.
  evidence: >
    - The D7 swap was deferred correctly; batch 3's loco.json edit only adds `platform`, which no code reads.
    - make_subset.py changed 67 s after E037 stopped (`--layer` only).
    - All commits are authored "Rafid Quadir".
    - The proj2 session altered `.venv` and held GPU memory (caught and fixed).
    - `$DATA/pb/` holds A549_KO, `*_pooled` and H1_train_only.npz, while runbook L506/L531 still glob `$DATA/pb/*.npz`.
  mechanism: Shared mutable files without locks; globs pull in candidates.
  confirm: `ls $DATA/pb/*.npz`; git reflog around 18:24.
  fix: >
    Lock files; one git identity per agent; a `pb/candidates/` quarantine; registry-derived lists instead of globs; one venv per project.
  effort: hours
  depends_on: none
  seams: A

- id: D-10
  class: Other
  title: Commit hygiene is clean; nits are agent identity and instance IPs in the history
  severity: P3
  confidence: VERIFIED 90%
  impact: None.
  evidence: >
    - The largest blob is 45 KB; .gitignore covers data, .vcc and env files.
    - A secret scan found only a doc instruction.
    - All 77 commits carry Co-Authored-By; instance IPs appear in the docs history.
  mechanism: n/a
  confirm: Repo visibility (the orchestrator checks it before every push: private).
  fix: A pre-commit hook (size cap, secret regex, extension blocklist).
  effort: hours
  depends_on: none
  seams: none

## Recommended changes to agent instructions, tools and guardrails
1. **LB calibration check** after every `vcc status`: back out b and r, diff them against local anchors, and stop on a raw gap > 0.05.
2. **Automatic "Anomalies" section** in every REPORT:
   - non-oracle scaled > 1.05;
   - B0/B1 scaled fid, jac or reach > 0.1;
   - raw MSE < 0;
   - non-finite N/D;
   - ORACLE scaled > 1.
3. **Forecast-vs-LB per-metric decomposition** after every LB result. Explanations must cover at least 50% of the gap.
4. **A run manifest per experiment:** HEAD, argv, sha256 of inputs and outputs, seeds, times, contention. Commands are copied from the manifest, never paraphrased.
5. **Reproducibility and seed protocol** before any submit: two identical regenerations; 3 seeds and their SD; submit only if the CI lower bound > 0 and Δ > 2·SD.
6. **Anchor-version guard** per LB entry.
7. **Executable gates** (`scripts/gate.py`).
8. **Approvals ledger;** write-once registry files; versioned results.
9. **Falsify-first rule** for rebuilds or reruns longer than 30 min.
10. **Escalation HOLD** on:
    - an LB-forecast sign contradiction with |Δ| > 0.05;
    - a calibration alert;
    - a CHECK failing twice;
    - any approval need.
11. **Coordination:** locks; per-agent identity; pb quarantine; no globs; one venv per project.
12. **Scorer-literacy step for a new validator:** run both baseline emits on synthetic data and compare with the official anchors.
13. **Automatic EXPERIMENT_LOG updates.**

## Out-of-scope observations (seams)
- **Scorer docs:** the help calls tile "legacy, known-biased", yet the official arms are identical-cell. Pin down the anchor version (r4).
- **Unstable spans:** V\* lines have N_conf 14–28 against val A's 336, and the CD4T replicate fid is 0.52, so tile-anchored spans may be degenerate.
- **B0 MSE:** B0 scaled mse is +0.312 on HCT116, and HCT116's replicate pds raw is only 0.664.
- **KOLF lineage:** KOLF V\* keeps H1 and HipSci as sources.
- **LB ranking:** if the LB ranks only the latest entry per team, a worse submission overwrites a better one.
- **E041:** the CCLE match doesn't discuss the platform confound.

## Open questions
1. R's H1 approval; does `H1_cap100` exist and reproduce 6d6f462?
2. Did the agent pull 3919854 before running `make_subset`?
3. Does the LB rank only the latest entry?
4. Does proxy de_sign/dirprec track LB fid on a second pair?
5. The emission-seed SD of the E032 config.
6. Was the E032 `.vcc` built from the current pb/?
