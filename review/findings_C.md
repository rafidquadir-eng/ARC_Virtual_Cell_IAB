# Findings C: biology and modelling assumptions (Auditor C)

Saved by the orchestrator: the auditor was not allowed to write files.

**Checks run** (in `scratchpad/C/`):
- read the committed per-target parquets;
- a noise-ceiling simulation (`work/cos_ceiling.py`).

DepMap downloads were blocked (figshare 403), so no per-gene DepMap values are claimed as verified.

**Value of one target** (official spans from the scorer notes):
- fid spans are about 0.31 / 0.16 / 0.26 on A / B / C (r ≈ 0.816 / 0.687 / 0.770, from the floors at `catalog.py` L640);
- jac span is about 0.35;
- so +1/300 raw on one target is worth about +0.0006–0.0011 overall for fid and +0.0006 for jac.

---

- id: C-01
  class: Eval
  title: For a target with N_conf = 0, the scored fid is NaN and dropped, not 1. Only jac rewards calling nothing on a null target. (Corrects brief O-04.)
  severity: P2
  confidence: VERIFIED 95%; the orchestrator re-checked it (21/21 targets with fid NaN have jac = 1 in `results/E037/pertarget_H1_R400_seen_E037.parquet`)
  impact: >
    Bounded.
    - Correctly abstaining on an N_conf = 0 target is worth about +0.0006 overall, via jac only.
    - Abstaining pays only when P(N_conf = 0) > ~0.44 (B) or ~0.3 (A).
    - Abstaining on a target with N_conf ≥ 1 costs about 0.0005 overall (B), as fid goes 0.42 → 0.
  evidence: >
    - `direction_fidelity_yield_raw = _safe_div(k, max(n_pred, n_conf))` (`metrics/direction.py` L776), and `_safe_div` returns NaN when the denominator is 0 (L689–699). The "1.0 if nothing called" rule applies only to the unscored `fidelity` and `fidelity_yield` (L737–758).
    - With `worst=None` (`catalog.py` L627), NaN is not filled, and `aggregate_metrics` drops it (`run.py` L543–546, L1952–1968). reach omits N_conf = 0 targets.
    - jac(∅,∅) = 1 (`metrics/de.py` L191).
    - Empirical: H1-R400 cap100 has 21 null targets (fid NaN, jac 1); CD4T_Stim48hr_R400 has 6 of 174.
  mechanism: On a null target, calling something scores fid = k/n_pred ≈ 0.5, not 0. Abstention wins jac only.
  confirm: n/a
  fix: Correct O-04 and the docstrings; value abstention as Δjac only.
  effort: hours
  depends_on: none
  seams: B (de_budget floors every target at n calls)

- id: C-02
  class: Method
  title: Per-target response size (N_conf) is heavy-tailed and predictable, but every LB and E038 config treats all targets alike, and `de_budget` can only raise the call count.
  severity: P1
  confidence: VERIFIED that it isn't used and that val N_conf has this shape; LIKELY 70% on the size of the gain
  impact: >
    Estimated +0.01 to +0.03 overall compared with a uniform budget.
    - A uniform n = 600 under-calls top-decile targets (N_conf in the thousands), costing about −0.38 raw fid there.
    - It over-calls targets with N_conf < 40 about 15×, which kills jac and costs MSE.
  evidence: >
    - **Val N_conf shape:** 46–61% of targets have N_conf < 40 and 12–30% < 10 (`direction.py` L918–933); val A mean is 336, minimum 4; the nmae gate keeps 272/229/218. So the median is about 30–50.
    - **No per-target size on the LB path:** the LB spec has no `gate_target_cpm`, `sim_tau` or `common`; `de_budget` k = max(n, …) (`models.py` L720); E038 sweeps a uniform n.
    - **Response size transfers across lines:** Nadig et al. 2024 report transcriptome-wide impact correlating across lines (mean r 0.62; K562/Jurkat 0.74), and growth genes enriched 4.22× for impact (https://www.biorxiv.org/content/10.1101/2024.07.03.601903.full.pdf). Replogle 2022 (https://www.biorxiv.org/content/10.1101/2021.12.16.473013.full.pdf).
  mechanism: The best n_pred is about N_conf, which spans 0 to thousands and depends on knockdown, dependency, paralogs and pathway activity.
  confirm: On H1-R400, regress log(1+N_conf) on cross-line response energy, target CPM and DepMap effect; expect leave-target-out ρ ≳ 0.4.
  fix: >
    Give each target its own budget n_t with a floor of 0; abstain when P(null) > 0.4; scale magnitude by predicted energy. Validate with a paired bootstrap.
  effort: days
  depends_on: O-01; C-04, C-08
  seams: B

- id: C-03
  class: Method
  title: The premise that target-specific responses barely transfer (docs/15 §0.4, §6) is not established; the cited cosine and top-50 numbers can't tell no transfer from perfect transfer on weak targets.
  severity: P1
  confidence: VERIFIED 80% (artefacts and simulation)
  impact: Strategic. LB reach already shows target-specific direction signal above the no-skill and habitual-gene bounds.
  evidence: >
    - **Top-50 overlap:** B0 scores 0.0027/0.0071/0.0021 (random 0.0027), while the transfer specs score 0.017–0.058, i.e. 6–20× chance (`results/E030/proxy_*`).
    - **Simulation of perfect transfer** (the source and the truth measure the same effect): cos(src, truth) is 0.029/0.026/0.057/0.116 for N_true 5/30/300/1500 at 150 cells and 10k UMI, and 0.014–0.174 at 400 cells and 20k UMI. The measured 0.003–0.11 lies inside this range.
    - **fid is diluted by construction:** precision = f·a + (1−f)·0.5, so f = 0.1 and a = 0.8 give only 0.53.
    - **Reach is above no-skill:** E032 raw reach 0.170 vs a no-skill value of about 0.038; the habitual-gene exploit is bounded at about +0.006 overall.
    - **Nadig:** 56% of perturbations correlate highly across cell types.
  mechanism: Noise over 18k genes caps cosine and top-k overlap even under perfect conservation. Reading those caps as biology deprioritised target-specific modelling.
  confirm: E039 (`ORACLE_HALF`, `top50_rep`, `dirprec@k`), corrected for noise attenuation.
  fix: >
    Retire the "chance / biological limit" wording; always report null and ceiling columns; rank calls by cross-line confidence. Verify dirprec@50 > 0.6.
  effort: hours (measure); days (exploit)
  depends_on: O-01
  seams: B, D

- id: C-04
  class: Biology
  title: Target expression. A expresses and knocks down 299/300 targets; B/C are unmeasured. Nothing on the LB path gates on target expression, and neither V\* nor M1 can learn a gate.
  severity: P2
  confidence: VERIFIED for A and for the missing gate; SUSPECTED 50% for the B/C counts
  impact: >
    Bounded. A: 0. B/C: at most about +0.006 to +0.02 overall, together with C-01. Most weak B/C targets are probably expressed but have small downstream responses, so C-02/C-08 matter more.
  evidence: >
    - **A:** val A's own target gene is reference-significant in 299/300 targets (`metrics/de.py` L205), and the control CPM gate is ≥ 5.
    - **A/B/C:** the target is the top-moving gene in 57–66% of perturbations; the target's share of the MSE range is 10.2%/11.3%/6.1% on A/B/C (`delta.py` L311, L1039).
    - **No gate on the LB path:** no `gate_target_cpm` on the LB path; B5's only gate is "no induction from < 1 CPM".
    - **V\* can't see a gate:** `B5x_gt5` equals ungated B5 on the proxy (both 0.264); GWPS targeted expressed genes only.
    - **H1-R400:** 21/254 null targets (8.3%).
    - **Unverified guesses** of targets low in HeLa/CAL-33: KIF21B, PIM2, BCL6, PSMB9, MYRF, EEF1A2, …
  mechanism: An untranscribed gene can't be knocked down, yet B5 still predicts its consensus response (about 1,000 genes).
  confirm: Run `scripts/target_expr.py` on A/B/C, look up DepMap TPM for Jurkat/HeLa/CAL-33, and fit P(N_conf = 0 | CPM) on H1-R400.
  fix: >
    Scale the target-specific part by min(1, CPM/5); give predicted-null targets the common response only (no lifted calls); gate M1's output.
  effort: hours
  depends_on: C-01; emitter fix
  seams: A, B

- id: C-05
  class: Biology
  title: Source programmes A/B/C can't mount (p53, RB/E2F, T-cell activation) pass B5's sign-consistency filter and get predicted for A/B/C.
  severity: P2
  confidence: LIKELY 65%
  impact: Estimated 0.002–0.01 overall; larger on D/E/F if a test line is p53-WT.
  evidence: >
    - **The test lines are p53-deficient:** CAL-33 TP53 R175H (https://www.cytion.com/305496); Jurkat TP53-mutant; HeLa p53 degraded by E6 (https://www.nature.com/articles/1201001).
    - **The sources mostly aren't:** RPE1, HCT116 (https://bpsbioscience.com/p53-luciferase-reporter-hct116-cell-line-78681), H1, KOLF, HipSci and CD4T are p53-WT; HEK293T is inactivated by large T (unverified).
    - **The filter keeps them:** `agree 0.5` passes 3-of-5 consistency.
    - **CD4T Rest/Stim8hr/Stim48hr are merged into one line**, so stimulated T-cell responses leak into transfer.
    - **About 11 panel targets are ligand-dependent** (PLCG1, MYD88, IFNAR2, IFNGR2, IL10RB, STAT6, SOCS5, BCL6, PIM2, PSMB9, ZC3HAV1).
  mechanism: These are among the most consistent responses across lines, so they become confident wrong calls in contexts that can't mount them.
  confirm: Count p53-target genes among B5's kept genes by supporting line; run K562_GWPS with and without p53-WT sources; compare CD4T Rest vs Stim per target.
  fix: Tag sources with TP53/RB status and stimulation state; down-weight genes supported only by p53-WT lines; use CD4T_Rest alone for transfer to unstimulated lines.
  effort: hours
  depends_on: none
  seams: A

- id: C-06
  class: Data
  title: Source CPM divides by a library that includes ribosomal, mitochondrial and ncRNA genes absent from the Flex axis, adding composition shifts the Flex truth doesn't have.
  severity: P2
  confidence: LIKELY 60% (code VERIFIED; size not measured)
  impact: Estimated 0.005–0.02 overall. `de_budget rank="snr"` would make it worse.
  evidence: >
    - `pseudobulk.py` L91 builds `lib` from all source genes, while `cpm_of` (L99–101) keeps only axis genes.
    - 10x Flex probe sets exclude ribosomal proteins and ncRNA (https://www.10xgenomics.com/support/flex-gene-expression/documentation/steps/probe-sets/chromium-frp-probe-sets-overview); XIST and RPS4Y1 aren't on the challenge axis.
    - 10 of 13 sources are 3′ or 5′ capture.
  mechanism: >
    In 3′/5′ sources, off-axis genes are an estimated 25–35% of UMIs. A 3-point drop in that fraction shifts every axis gene by about +0.06 log2. The shift is sign-consistent and passes z ≥ 2 on highly expressed genes.
  confirm: Rebuild K562_GWPS with `lib` = axis genes; compare each target's median lfc and B5's kept-gene counts.
  fix: Normalise over the challenge axis (or use robust size factors); rebuild and hash `pb/*.npz`.
  effort: hours plus rebuild
  depends_on: none
  seams: A, B

- id: C-07
  class: Biology
  title: The context's common (mean) response isn't predicted in the LB config, and the exact-line Jurkat data contributes nothing to A.
  severity: P2
  confidence: VERIFIED that it isn't used; LIKELY 60% on the gain
  impact: Estimated +0.005 to +0.02 overall (mostly MSE and jac on A).
  evidence: >
    - The LB spec has no `common` key (default `"none"`).
    - `common="panel"` needs ≥ 10 panel rows per source, and Jurkat, RPE1, HepG2 and K562-essential have 0.
    - Replogle's shared programmes: growth genes down, ISR (TRIB3 is a panel gene), RNA content.
  mechanism: The common response comes from the panel's dependency targets in that line.
  confirm: E039 `ORACLE_MEAN` vs `B5_common_only`.
  fix: Build a DepMap-weighted common vector from generic programmes (Nadig Jurkat for A); calibrate CD4T → Jurkat transfer on the shared essential targets.
  effort: days
  depends_on: C-05, O-01
  seams: A

- id: C-08
  class: Biology
  title: What decides whether a knockdown responds in a new line (dependency, paralog buffering, pathway activity, expression) is in priors on the instance, and none reaches the model.
  severity: P2
  confidence: VERIFIED that the priors are unused; LIKELY 60% on their value
  impact: Estimated; pays off through C-02/C-04/C-07.
  evidence: >
    - The panel shares 0 targets with the essential libraries (`panel_coverage.csv`).
    - DepMap 24Q4, STRING, GO and Reactome are on the instance, with no reader in `src/`.
    - Nadig: fitness effect is enriched 4.22× for response size, knockdown efficiency is not.
    - About 25 panel targets have an obvious paralog (HDAC1/2, SMARCA5/1, CHD3/4, EZH2/1, CSNK2A1/2, MAP2K2/1, AKT2/1, …; unverified).
  mechanism: Dependency and paralog buffering set response size per line.
  confirm: Ablation on the C-02 regression (Δρ > 0.05).
  fix: A (target, context) feature table feeding the C-02/C-07 models.
  effort: days
  depends_on: C-02
  seams: A

- id: C-09
  class: Biology
  title: Knockdown strength and timing don't set the scored magnitude; V\*'s `kd ≤ 0.7` filter removes the weak-knockdown regime.
  severity: P3
  confidence: LIKELY 65%
  impact: Estimated < 0.005 directly.
  evidence: >
    The target gene is excluded from jac/nmae/MSE/PDS. Nadig shows no enrichment for knockdown efficiency. Remaining fractions are inflated by escapers and the pseudocount.
  mechanism: Above 70–80% knockdown, dependency, protein half-life and collection day set the response.
  confirm: In V\*, the partial correlation of energy with kd, controlling for source energy (< 0.2).
  fix: Don't scale by knockdown ratio.
  effort: hours
  depends_on: none
  seams: A

- id: C-10
  class: Method
  title: Biologically naive readings in the brief and in docs/15 and docs/12.
  severity: P3
  confidence: VERIFIED 75%
  impact: Indirect, through prioritisation.
  evidence: >
    1. "fid ≈ 0.49 ⇒ chance direction" is really dilution (C-03).
    2. P16 says magnitude affects only MSE/nmae; in fact magnitude decides detectability, which drives every DE metric.
    3. Closing cis effects on energy share is the wrong yardstick for set metrics (minor).
    4. docs/12's "tissue-restricted" targets are mostly ligand-dependent instead.
    5. P13d (weight Flex sources) also up-weights stimulated, p53-WT T-cell biology.
    6. O-04 states the unscored variant (C-01).
  mechanism: Undervalues the target-specific signal or aims at the wrong cause.
  confirm: n/a
  fix: Amend these passages.
  effort: hours
  depends_on: C-01, C-03
  seams: D

## Out-of-scope observations (seams)
1. O-04 and `target_expr.py`'s docstring are wrong for the scored fid.
2. The balanced emitter's spurious calls make jac = 1 on null targets impossible. (The orchestrator has since fixed this for all-zero rows, d222976.)
3. `de_budget` floors every target at n; the `snr` ranking is the one most exposed to C-06.
4. V\* has almost no null targets; H1-R400 (21) does.
5. CD4T states are merged into one line.
6. A C-06 rebuild changes every `pb/*.npz`; hash them.
7. `top50_overlap` is reported without its null or ceiling.

## Open questions
- How many val B/C targets have N_conf = 0?
- Did Arc filter the panel for expression? A expresses 299/300.
- Which CRISPRi effector (KOX1 vs ZIM3) and which collection day did Arc use in 2026?
- p53 status of HEK293T, KOLF2.1J and HipSci; RB and HPV status of CAL-33.
- Are MT genes on the axis?
- Is there any exact-line Jurkat/HeLa/HNSCC single-cell CRISPRi data with panel targets? None found.
- How conserved is the common response (E039)?
