# Plan to the top of the leaderboard (target ≥ 0.50 overall)

Written 15 Oct 2026, ~02:30 UTC, after E012 (0.069, rank 827). Final test contexts D/E/F are released Thu 22 Oct, and the final deadline is Thu 5 Nov 23:59 UTC. There is no size limit on the modelling work; the $7,000 compute budget is barely touched.

## Where the gap is
Leaderboard scaled scores (the top-5 table is in `EXPERIMENT_LOG.md`):

| | PDS | MSE | JAC | NMAE | FID | REACH | Overall |
|---|---|---|---|---|---|---|---|
| Illumina AI (#1) | 0.874 | 0.787 | 0.088 | 0.419 | 0.153 | 0.444 | 0.461 |
| #2–#5 (about) | 0.78–0.85 | 0.46–0.49 | 0.02–0.08 | 0.26–0.29 | 0.00–0.09 | 0.29–0.36 | 0.32–0.33 |
| us, E012 | 0.313 | 0.000 | −0.013 | 0.042 | −0.014 | 0.088 | 0.069 |
| what 0.50 needs (one way) | 0.90 | 0.85 | 0.10 | 0.50 | 0.20 | 0.50 | 0.51 |

Facts that decide the plan:
1. **MSE is 0 in every run we have, local and leaderboard,** even when local PDS is 0.74. The cause is the emitter: it resamples random control cells per target, and that sampling noise (about 0.2 log2 RMSE on synthetic data) is as large as the effects. The metric only credits prediction noise when predictions spread enough across targets, so the noise is charged to us. It also blurs PDS and creates spurious Wilcoxon calls. Fixed in code (`emit balanced`); measured on real holdouts in E015.
2. **The panel is non-essential genes,** which have weak effects. Public per-target measurements exist almost only in K562 (GWPS, 263/300). The full 2025 H1 set (about 300 targets) is public via Arc's Virtual Cell Atlas [1].
3. Arc confirms **six unnamed cell lines** (A/B/C validation, D/E/F test), no training set, and any data or model allowed [1]. E016 infers what A/B/C are.
4. **Illumina AI is #1, and Illumina announced a 1-billion-cell, 200+-line genome-wide CRISPR atlas** in Jan 2026 with pharma partners; nothing says it is public [2]. #2–#5 sit at about 0.33, which is the realistic bar for a top-3 finish on public data. 0.50 means beating a team that very likely has proprietary multi-line genome-wide data, so it needs everything below to work. I'll say so plainly if it stops looking reachable.

## Work packages (order = expected gain per day)

| WP | What | Main metrics it moves | Local test | Status |
|---|---|---|---|---|
| 1 | **Emission without sampling noise** (`emit balanced`: shared herded base cells, exact per-gene totals) | MSE, NMAE, REACH, PDS | E015: ORACLE and B2 × random/balanced on V1–V4 | code done, E015 queued |
| 2 | **Per-target signal**: empirical-Bayes denoising of source lfc, effect scale β, pooling every measurement of a target (GWPS + full H1 + new data) | PDS, JAC, FID | E013/E015 | code done |
| 3 | **Learned context translator**: predict a target's response in a new line from its measured response elsewhere + both lines' control profiles. Training pairs: ~2k essential targets measured in K562/RPE1/HepG2/Jurkat (12 directed line pairs), GWPS↔H1 (127+ shared), and any new data. Start with a gene-wise gradient-boosted model on (target, gene) features; then a low-rank neural model on GPU, trained with **metric-aligned losses** (contrastive loss across targets for PDS, sign/rank losses for the DE metrics) and **split-half augmentation**: every measured target splits into many random half-pairs of cells, which gives real, noise-labelled training examples. Leave-one-line-out validation; must beat WP2 on V1/V2. | PDS, MSE, NMAE | new E018+ | to build next |
| 4 | **DE calibration**: per target, predict how many genes the truth will call significant (from the source's own call count, scaled by depth and cell number) and set each target's emitted effect scale so our Wilcoxon calls match. FID penalises under-calling, JAC rewards set overlap, and REACH needs the ranking. | FID, JAC, REACH | E019 | design |
| 5 | **Unmeasured targets (~37 + any filtered)**: kNN over gene-function embeddings (STRING, GO, ESM-2 protein, LM text; iMEMORY gene vectors only if the EC2 files come back) trained to predict a target's GWPS response from its neighbours'. Test each embedding against a shuffled control. | PDS on uncovered targets | E020 | design |
| 6 | **Data**: full 2025 H1 (confirmed public), then the curation agent's catalog; X-Atlas/Orion if Xaira grants permission | everything via WP2/3 | E021 | agent running |
| 8 | **Optimise each submission for expected score** (test-time compute). Sample plausible true responses from the model's uncertainty, simulate how 400 cells at about 20k UMI would measure them using the context's own real control cells, and score candidate submissions with the official cell-eval2 code. Choose, per target and context, the effect scale, how many genes to push to significance, and the shrinkage that maximise *expected* score. The verifier is the exact metric. This targets the DE metrics (FID, JAC, REACH, NMAE), where even #1 is weak (0.09–0.44) and data is not the bottleneck. | FID, JAC, REACH, NMAE, MSE | simulated truth from held-out lines first, then V1–V4 | design |
| 9 | **Use the abundant unperturbed data**: 18,400 real control cells per context, plus large public atlases. Express predicted effects in the target context's own co-variation basis (PCs of its controls) and shrink components outside it, since knockdown responses mostly move cells along a line's natural programs. Test on LOCO, because every held-out line has its own controls. | PDS, MSE | E022 | design |
| 7 | **Final-test strategy**: D/E/F have no leaderboard. Pick by local validation only, ensemble the robust variants, refresh the final entry only on local wins, and freeze by Wed 4 Nov. | — | — | Oct 22 → |

## How we can beat a team with more data
The score is an equal mean of six metrics. Illumina's lead comes mostly from PDS and MSE, the metrics that reward having measured the targets in many lines. Its DE metrics are modest (JAC 0.09, FID 0.15, REACH 0.44, NMAE 0.42). Our route: get close on PDS/MSE through the emitter fix, more public data and the translator (WP1–3, 6, 9), and beat them on the DE metrics through calibration and expected-score optimisation (WP4, 8), which need compute and care rather than data. Example: PDS 0.85, MSE 0.75, JAC 0.20, FID 0.35, REACH 0.55, NMAE 0.50 averages 0.53.

## Decision rules
- Every change must win on the pre-registered local selection score (V1 H1←GWPS, V2 GWPS@H1←H1, V3 essential lines, V4 panel-generic) before it reaches the leaderboard. At most one leaderboard entry per day is used as a confirmation, never for tuning.
- If WP1 doesn't lift local MSE above 0 on V1/V2, stop and debug against the metric code before anything else.
- WP3 is worth its cost only if it beats WP2 by ≥ 0.02 on V1/V2. Otherwise fold its features into WP2's simpler model.

## Calendar
| Dates | Work |
|---|---|
| 15 Oct | E013, E015, E016, E017 (leaderboard: emission fix) |
| 15–16 Oct | full H1 2025 ingested; WP4 design; WP3 data tables built |
| 16–19 Oct | WP3 translator (CPU GBM first, then GPU neural); WP5 embeddings |
| 19–21 Oct | WP4 calibration; ensemble; daily leaderboard confirmations |
| 22 Oct | D/E/F released: rerun E016 on them, run the final pipeline, first final entry |
| 23 Oct – 4 Nov | improve only on local wins; 2 final entries per day max; freeze 4 Nov |


## Update 15 Oct ~03:00 UTC: the model we build (v2), the new validation, and which outside ideas we use

**New data changes the picture.** The curation agent has ingested the full 2025 H1 set (about 300 targets) and is bringing in a CD4⁺ T-cell and a KOLF iPSC Perturb-seq set that cover panel targets outside K562. So for the first time we have **several lines where the panel's non-essential targets were measured**, both as training sources and as honest held-out tests.

**New primary validation, V\*:** leave-one-line-out over every line with ≥ 100 measured panel targets (K562 GWPS, H1, CD4 T, KOLF iPSC, and more as they land). Each held-out line is scored on the challenge panel targets it measured (`--panel-file pert_counts.csv`), with all *other* lines as sources (same-line datasets excluded automatically). This is the closest local copy of the test, and it replaces the V1–V4 mix for selection once two new lines are in.

**Model v2: a context-conditioned response model** (X-Cell's structure, our scale; iMEMORY's graph encoder where it earns its place):

| Part | What it does | Built from |
|---|---|---|
| Context encoder | Summarises the target line from its own control cells: pseudobulk, PCs (WP9), and the set of 256 sampled control cells via attention | the 18,400 controls per context, plus every source line's controls |
| Evidence tokens (in-context) | The target gene's **measured** responses in every other line where it was screened, each tagged with that line's context embedding and noise level | GWPS, H1, CD4 T, KOLF, essential lines, new data |
| Prior encoder for the knocked-down gene | Graph neural network over a gene graph (STRING, GO, regulatory edges), plus ESM-2 protein and DepMap dependency features. **This is where an iMEMORY-style heterogeneous GAT fits**, as one candidate encoder tested against simpler ones. It carries most of the weight for unmeasured targets. | STRING, GO, ESM-2, DepMap (licences to be checked before use) |
| Decoder | Predicts the mean log-fold-change vector in the target line, plus per-gene noise; the balanced emitter (WP1) and the expected-score optimiser (WP8) turn it into cells | — |
| Training | Every (target, line) pair, held out line by line; split-half augmentation; losses = denoised MSE + contrastive (PDS) + sign/rank on significant genes | ~30–50k pairs once the new lines are in |

The model is deliberately small (millions of parameters, not billions): the limit is examples and noise, not capacity. It trains on the current A100; one larger GPU only if the set-attention version needs it (LAUNCH REQUEST then).

**Outside ideas: what we use, and what we don't (for this challenge)**
| Idea | Verdict | Why |
|---|---|---|
| Mechanistic priors / knowledge graph | **use** (prior encoder) | essential for unmeasured targets; X-Cell does the same |
| In-context conditioning on the target's cells | **use** (context encoder + evidence tokens) | that's exactly the zero-shot setting. Arc's own in-context models (State, Stack) have non-commercial licences, so we build our own small version |
| Harmonisation | **use, narrowly** | one gene axis, depth-aware denoising, knockdown filters, the same pseudobulk for every source. Re-aligning raw reads isn't worth 3 weeks |
| Perturbational (causal) training | **use** | that's all our training data |
| Self-supervised pretraining on unperturbed cells | **maybe, later** | only via the context encoder on control cells, or permissively licensed pretrained embeddings |
| Test-time compute (expected-score search) | **use** (WP8) | the only verifier we have that is exact: the metric code plus the real controls |
| Synthetic cells (latent diffusion), cross-species transfer, federated learning, multi-modal stitching, billion-parameter architectures | **skip** | no verifier, no time, or no data for the unknown test lines; capacity isn't our bottleneck |
| Active learning with a robotic wet lab | **skip for this challenge** | can't produce data before 5 Nov. It's the right idea for Immunome's own platform next year |

**IP flag (stop-and-flag rule):** if any iMEMORY-derived component ends up in the winning model, the finalist write-up Arc publishes could count as a disclosure before the patent is filed. Get counsel's view before 5 Nov, or keep that component out of the final entry.

## Sources
1. [Arc Institute — The 2026 Virtual Cell Challenge](https://arcinstitute.org/news/virtual-cell-challenge-2026)
2. [Illumina press release, 13 Jan 2026 — Billion Cell Atlas](https://www.illumina.com/company/news-center/press-releases/2026/fda84c92-b4b3-4691-a402-35555abe8605.html)
3. [cell-eval2 vcc2026 metric brief](https://github.com/ArcInstitute/cell-eval2/blob/main/docs/vcc2026_metrics/vcc2026-metrics-brief.md)
4. [PRiMeFlow (Altos Labs), the 2025 generalist-prize approach Arc recommends reading](https://www.alphaxiv.org/abs/2604.13986)
