# Findings B: training and inference engineering (Auditor B)

Saved by the orchestrator: the auditor was not allowed to write files.

- **Checks:** `scratchpad/B/t1_emit.py` … `t7_budget.py`, with logs `t1.log`, `t3.log`, `t6.log`.
- **Code version:** findings are against d222976. `t1` ran the pre-d222976 emitter; `t5`–`t7` ran the new code.
- **Result:** 7 findings, none P0/P1.

---

- id: B-01
  class: Engineering
  title: Emitting all-zero rows untouched (d222976) adds the shared base's common-mode error and loses the #348 MSE credit; DE calls are the same as with pinning (synthetic)
  severity: P2
  confidence: VERIFIED 85% (synthetic)
  impact: >
    Estimated ≤ ~0.01 LB overall per spec that uses null_gate. Measured on synthetic: aggregate raw MSE +0.24 (balanced) / +0.26 (balanced3).
  evidence: >
    - **Code:** `emit.py` L115–120.
    - **t6_null** (400 cells/target, ~20k UMI, 6,000 controls, 12 null + 4 responding targets): null jac = 1 on 10 of 12 in both the untouched and the pinned arm.
    - **Aggregate MSE, untouched vs pinned:** balanced −0.080 vs −0.317; balanced3 −0.070 vs −0.334.
    - **t5c:** with zero lfc on the new code, 154 of 1,183 genes with CPM ≥ 5 sit more than 0.1 log2 off the population mean (up to 0.43). The offset is identical in every gated target.
    - **Scorer note:** `scales.py` ~L320 says "an arm reusing ONE emitted cell block … r = 0".
  mechanism: >
    An untouched base's pseudobulk is the base's own mean, not the control mean. The error is common to every gated target, so #348 credits none of it. Pinned rows sit exactly on the control mean.
  confirm: Repeat t6 on real A/B/C controls (18,400): pinned vs untouched; compare null-target n_pred and MSE.
  fix: Pin zero rows (the pre-d222976 behaviour), or pin them on a random base. Keep "untouched" only if real controls show pinning creates calls.
  effort: hours
  depends_on: O-01
  seams: C
  **CONFLICT:** the orchestrator's structured synthetic (`test_null.py`, 3 latent programmes, 6,000 controls, 1,479 genes) gave 40/1,479 spurious calls per target for balanced (herded + pinned) and 4/1,479 for balanced3 (random + pinned), against 0 untouched. Sent to the red team (R-5).

- id: B-02
  class: Engineering
  title: balanced2/balanced2h (adjust_eps > 0) leave |lfc| ≤ 1e-3 genes at the shared base's sampled mean, an uncorrected common-mode error
  severity: P2
  confidence: VERIFIED 95%
  impact: >
    Bounded ≤ 0.024 overall (all of E032's MSE contribution) if any @b2 spec is submitted. Synthetic raw MSE: 1.869 vs 1.044 with zero lfc; −0.550 vs −0.741 with the true lfc.
  evidence: >
    - **Code:** `emit.py` L117–118.
    - **t1.log:** zero lfc gives balanced2 1.8690, balanced 1.0439, balanced3 1.0457; #348 scales the correction to ~0.
    - **Exposure:** `specs_E038.json` includes `B0_control@b2` and `B5x_tl0.05_bud600@b2`.
  mechanism: Every target reuses one random sample's mean, so the error is common to all of them, r ≈ 0, and no credit offsets it.
  confirm: n/a
  fix: Retire balanced2/2h for submissions; `detect` may keep balanced2 internally.
  effort: hours
  depends_on: none
  seams: D

- id: B-03
  class: Method
  title: B5 `_noise_var` has no overdispersion floor, so the |z| ≥ 2 gate keeps excess noise genes, concentrated in highly expressed genes; agree = 0.5 does nothing for k ≤ 2 lines
  severity: P2
  confidence: VERIFIED 85% (miscalibration on NB synthetic); LB magnitude LIKELY 55%
  impact: Estimated; sign and size on the LB unknown (diluted DE calls plus MSE noise).
  evidence: >
    - **Code:** `models.py` L348–355 sets var = c/(n·(cpm+pc)); L626–630 sets Birge = 1 when k = 1.
    - **t2:** NB sources with NO trans effects; nominal false-keep rate at |z| ≥ 2 is 4.55%.
    - **Null genes kept, by number of lines:** 1 line 7.7%; 2/3/4 lines 4.9%/4.4%/4.3%.
    - **By CPM quintile (1 line):** 2.4/2.7/3.5/6.5/**23.4**%.
    - **Top quintile with 2 or 3 lines:** 13.2% and 11.0%.
    - **Real B5_z2:** keeps a median of 600/716/1,238 genes per target (E030), while noise alone would give about 500.
  mechanism: Overdispersion adds a variance floor of about φ/n, which the formula leaves out. High-CPM genes get inflated z, become Wilcoxon-detectable random-direction calls, and add MSE noise.
  confirm: Tile-anchored V\* for z2/a0.5 vs z2 + variance floor vs z3/a0.75.
  fix: Use var = c/(n(cpm+pc)) + φ_s/n with φ_s fitted on top-CPM genes; require min_lines ≥ 2 or z ≥ 3 for single-line targets. Verify the t2 false-keep rate is ≈ 4.5% per quintile.
  effort: hours
  depends_on: O-01
  seams: C

- id: B-04
  class: Eval
  title: compare.py's paired bootstrap resamples targets within lines only, leaving out between-line and emission-seed variance; the CI is about 4× too narrow
  severity: P2
  confidence: VERIFIED 90%
  impact: >
    Wrong selection decisions. Claimed E031 CI +0.011..+0.039 (P > 0 = 0.995) vs LB Δ +0.0017.
  evidence: >
    - **Per-line deltas:** −0.008/−0.030/+0.037/+0.144/+0.002.
    - **5-line t-interval:** −0.036..+0.095; median +0.002.
    - **Code:** `compare.py` L61–71.
    - **What is right:** the MSE ratio of sums is re-derived correctly, and NaN handling matches `aggregate_metrics`.
  mechanism: With 3–5 lines, one outlier line drives the mean, and target resampling can't see it.
  confirm: n/a
  fix: A two-level bootstrap (lines, then targets) or a leave-one-line-out range, plus seed replicates. Promote a spec only if Δ > 0 on most lines.
  effort: hours
  depends_on: O-01
  seams: D

- id: B-05
  class: Eval
  title: The local replicate uses the split-half estimator for lfc_nmae (official: FULL_GATE_RAW) and seeds 0..4 (official: SeedSequence(0).generate_state(5))
  severity: P3
  confidence: VERIFIED 95%
  impact: Estimated ≤ 0.001 overall on local scaled scores.
  evidence: >
    - **Code:** `local_eval.py` L73–80, L96–101; `cell_eval2` competition.py L237 and anchor.py L57–67, L135–140, L243.
    - **t3:** the halves are identical; nmae local vs official 0.2228/0.2334, 0.2879/0.2407, 0.2119/0.2320.
    - **Controls:** control_source is real for scoring and pred for the replicate, both correct.
  mechanism: The cohorts differ and the local estimator is noisier.
  confirm: n/a
  fix: Take r from `cell_eval2.anchor.compute_replicate_anchor(real, config=cfg, base_seed=0, n_splits=5)`.
  effort: hours
  depends_on: O-01
  seams: none

- id: B-06
  class: Engineering
  title: No target-expression gating in the E032 LB path; null_gate exists but no LB spec uses it, and de_budget forces calls on every target with any non-zero lfc
  severity: P3
  confidence: VERIFIED 90% (code); gain ESTIMATED
  impact: >
    Estimated +0.00053 overall per correctly gated N_conf = 0 target per context (jac only), i.e. +0.011–0.021 for 10–20 such targets in each of B/C. Val A has none.
  evidence: >
    - **No gate in the LB path:** the LB spec has no `gate_target_cpm`.
    - **de_budget:** L716–726 lifts the top n for any non-zero row.
    - **null_gate:** runs last, which is correct.
    - **E037 B0:** jac = 1 with fid = NaN on 21/254 (H1_R400) and 6/174 (CD4T_Stim48hr_R400).
    - **t7:** de_budget produces about n calls.
  mechanism: jac(∅,∅) = 1 only when nothing is called; the scored fid is NaN-dropped.
  confirm: `target_expr.py` on A/B/C, `regime_check --per-target-out`, E043.
  fix: Add null_gate to the LB spec once E043 confirms it, with zero rows pinned or untouched per R-5.
  effort: hours
  depends_on: B-01, O-01
  seams: C

- id: B-07
  class: Engineering
  title: The M1 fit cache is keyed on source names and parameters only; a cache hit with new dicts crashes, and a stale model is possible
  severity: P3
  confidence: VERIFIED 90%
  impact: 0 on current flows (latent).
  evidence: >
    - **Code:** `translator.py` L124–126; `_prep` runs only inside `fit`.
    - **t2:** a second `predict_m1` on fresh dicts raised KeyError('_tpos').
  mechanism: A cache hit skips `_prep`.
  confirm: n/a
  fix: Key the cache on a content hash and always call `_prep`.
  effort: hours
  depends_on: none
  seams: none

## Verified OK (checks that found nothing)
1. **The shared pinned base doesn't distort pds or MSE.**
   - Median |log2 error| is 0.00025 on genes with CPM ≥ 5 (worst pinned row 0.02).
   - With the true lfc:

     | emission | MSE | pds | fid | jac |
     |---|---|---|---|---|
     | shared herded pinned | −0.741 | 0.900 | 0.903 | 0.841 |
     | independent bases | −0.741 | 0.825 | 0.879 | 0.836 |
     | random | +0.043 | 0.855 | 0.952 | 0.791 |

   - The #348 bound gives r ≈ 0.95–0.97.
2. **The output file is valid:** integer, non-negative counts; exactly n cells per target; gene order enforced by `ctrl[:, axis]`; target list taken from `pert_counts`; `--n-control 0`.
3. **The prediction's control rows** are ignored with control_source real (`run._pred_de_input`; `delta.py` L252–255).
4. **de_budget and detect** (`t7`, the scorer's DE engine): balanced3 calls 100% of the lifted genes and balanced 99.2%, all with correct signs. Only 0.2 calls per target fall outside the top n. The p < 1e-3 stand-in is conservative.
5. **No B5 state leakage** across specs (max |diff| 0.0).
6. **Determinism:**
   - emit output is bit-identical for a given seed;
   - B5 is deterministic, and M1 uses random_state 0;
   - with ≤ 4,000 controls, the herded base doesn't depend on the seed.

## Out-of-scope observations (seams)
- **Anchor version.** The LB anchors are `vcc2026-val*-r4`, while the installed 0.18.0 has rule_version 3. *Orchestrator resolution:* in cell_eval2 0.19.0's `real_bundle.py` L73–76, the r3 and r4 official bundles have identical rule and config digests and byte-identical anchor parquets; the only difference is `cell_eval2_version`. 0.19.0 still has rule_version 3, with no semantics debt. So our scorer's semantics match the LB.
- **null_gate wording.** The docstring and commit message said fid = jac = 1. Docstrings are now fixed (7b00b75).
- **E030 cis.** cis5000 and cis0 differ only at the 5th–6th decimal, so the cis component is inert.
- **E038 lists @b2 specs** (B-02).

## Open questions
- What is the #348 r for E032 on A/B/C?
- How many val B/C targets have N_conf = 0?
- Does pinning zero rows create calls with 18,400 real controls?
- What is the LB seed variance of herded emission with more than 4,000 controls?
