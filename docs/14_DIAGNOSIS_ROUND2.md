# Diagnosis, round 2: after E025–E026 and curation batch 2

Written 16 Oct 2026 ~07:30 UTC. Sources: `reports/REPORTS_E025_E027.md`, `reports/DATA_DONE_batch2.md`, `results/E025*`, `results/E026`, `results/E020` (unseen). Round 1 is `12_DIAGNOSIS.md`; this file supersedes its priorities.

## 1. What we learned

| Finding | Evidence | Meaning |
|---|---|---|
| **B4 failed.** No B4 setting beats the E021 configuration: proxy 0.38 vs 0.454; real V\* 0.104 vs 0.167. | E025, E026 | B4 fixed raw MSE (4.4 → 1.0–1.7) by shrinking everything, and lost PDS (0.30 → 0.16–0.19) and FID with it. |
| **Transferred per-gene effects barely correlate with the truth.** Per-target cosine is 0.003–0.08 for E021; the MSE-optimal scale of the dense transfer is 0.01–0.11; predicted energy is 1.6–39× the true energy. | E025 anatomy | Copying a target's full response from other lines is mostly noise at the gene level. The signal is in a **small set of genes**, not spread across 18k. |
| B4's residual predictions **anti-correlate** slightly (cos −0.01 to −0.08). | E025 anatomy | **Code problem (B4):** τ² sits in log2FC² units, far above typical per-gene effects, so the empirical-Bayes factor collapses to ~0. What survives is dominated by the induction gate, which clips positives only and so leaves a negative bias. B4 stays in the code but is retired from selection. |
| The donor/batch fix works but adds little: CD4T Y-gene artefact cut 3.3–5.4×; E021 config +0.003 proxy. | E025b, D7 | Necessary hygiene, not the main lever. |
| Unseen mode: every spec reduces to generic (0.03–0.05). | E020 unseen | Expected. Now irrelevant: **all 300 targets are measured in ≥ 2 lines** (293 in ≥ 3). |
| **Orion HCT116/HEK293T are in** (255/250 panel targets); Pisces is not released. | DATA_DONE_batch2 | Two **epithelial** held-out lines for V\*, our first validation resembling B/C. |
| V\*-far ≈ V\* (Δ 0 to −0.019) | E026 | Same-lineage sources barely matter yet, so the gene-level transfer is not lineage-specific. That fits finding 2. |
| Leaderboard and local agree in ranking: E021 0.106 on the leaderboard vs 0.167 on V\*. | E021, E026 | Local is optimistic by ~0.06 but usable. |

## 2. Problem register, round 2 (open-ended)

### Modelling
| ID | Problem | Solution | Where |
|---|---|---|---|
| R1 | **Dense transfer.** We predict every gene for every target, and most of that is noise. | **B5 sparse consensus:** per target, meta-analyse its response across *lines* (inverse-variance fixed effect, standard error inflated for between-line disagreement). Keep only genes with \|z\| ≥ z_thr **and** the same sign in ≥ `agree` of the lines, at full size. Predict 0 elsewhere (or a small `trans_lambda`). On simulated sparse data: error 2.1 → 0.78, cosine 0.55 → 0.68. | `models.predict_sparse` (**built**), E030 |
| R2 | **CRISPRi cis effects are unmodelled.** dCas9-KRAB at the target promoter also silences genes with nearby TSSs: bidirectional partners and divergent lncRNAs. Only the target itself is excluded from the metrics, so these neighbours are scored. They are strong, conserved across lines and predictable from the genome, and they're a distinctive per-target fingerprint for PDS. The A2 code from 14 Oct was never tested on real data. | B5 `cis_bp`: neighbours get their measured cross-line knockdown, or the distance-bin prior, gated by the neighbour's expression in the context. **First measure how much of the true signal is cis** (`ORACLE_CIS` and the anatomy `share_true_signal_within_*bp`). | **built**, E030 |
| R3 | **We don't know how sparse the truth is.** | `ORACLE_TOPK` (truth kept only on its top-k genes) gives the ceiling of a perfect sparse predictor for k = 10/50/200/1000. `top50_overlap` measures whether we point at the right genes. | proxy (**built**), E030 |
| R4 | B4's shrinkage was mis-scaled (above). | Retired. B5 uses no global shrinkage; sparsity comes from the significance and consistency gate. | done |
| R5 | **Line weighting for context A.** A is T-ALL-like and CD4T is its nearest source (r 0.85), but similarity weighting can't be validated well on V\*. | B5 `sim_tau` in the grid; per-context leaderboard breakdown (R14) to see whether A behaves differently | E030, E033 |
| R6 | **Magnitude.** Knockdown strength differs (HEK293T 0.43 remaining, KOLF 0.32, HCT116 0.25), and so do effect sizes. | B5 β grid now; learned translator later (C2 in `13_EXECUTION_PLAN`). Its features now include cis distance, cross-line z and agreement, expression in the target, and the target's knockdown in each source | E030, M-1 |
| R7 | **Trans responses are context-specific.** Low cosine even between pluripotent lines (KOLF holdout). | The translator (M-1) learns *which* genes transfer, from (line, line) pairs across 8 lines. B5 is its hand-built special case. | M-1 next |
| R8 | **The context's mean response is unknown.** The baseline uses the truth's own mean; our generic shifts are worse than zero (B1 raw MSE 1.07–1.22). | Default zero. Later: predict the shared component from the translator using the context controls. | — |

### Metric and emission
| ID | Problem | Solution |
|---|---|---|
| R9 | FID divides by max(n_pred, n_real). Dense noisy predictions add spurious calls; overly sparse ones under-call. | B5 controls the call count through z_thr. C-1 (DE-count calibration) follows. |
| R10 | MSE noise credit needs enough spread across targets; sparse predictions may lower that spread. | The proxy reports both `mse_sc` and `mse_sc_credit`; the real V\* decides. |
| R11 | Proxy vs real: the proxy overrated B1 (proxy #2, real #4). | `scripts/pick_specs.py` uses a new score: 0.5·PDS + 0.3·MSE (uncredited, clipped) + 0.2·DE-sign. The real V\* always confirms. |

### Validation
| ID | Problem | Solution |
|---|---|---|
| R12 | V\* had no epithelial line. | **5 held-out lines now** (+ Orion HCT116, HEK293T). V\*-far for the epithelial lines removes the other epithelial line from the sources. |
| R13 | No confidence intervals yet (A3 in `13_EXECUTION_PLAN`). | Paired bootstrap (`vcc26/compare.py`); PLAN builds it next. |
| R14 | **We never looked at the leaderboard's per-context scores.** A has a close source and B/C don't; the breakdown says where the 0.106 comes from. This reads our own submission, so it isn't tuning. | E033: `vcc --json status <entry>` for E012/E021 |

### Data
| ID | Problem | Solution |
|---|---|---|
| R15 | Pisces (Jurkat-GW, closest to A) not released | CUR checks the HF repo daily |
| R16 | HipSci controls are "unassigned" cells (only 48 NonTarget) | Keep it, but weight by its noise (B5 does this through per-entry variance) |
| R17 | NC-licensed data now in the sources | The final pipeline is scored with and without it (`13_EXECUTION_PLAN` §0) |

### Operations
| ID | Problem | Solution |
|---|---|---|
| R18 | The other project has moved to its own instance (R, 16 Oct), so the GPU is free | RUN checks `nvidia-smi` before GPU stages |
| R19 | B4's low-rank step made real V\* slow (10 min per spec and line) | B5 has no SVD, so it's fast. Drop B4 from the specs. |

## 3. Next stages (in `07_RUNBOOK_INSTANCE.md`)
- **E030 (CPU, proxy):** 32 specs on the 5 V\* lines (`specs_E030.json`):
  - the ORACLE / TOPK / CIS ceilings;
  - E021 and B0 as references;
  - B5 over z ∈ {2, 3, 4} × agree ∈ {0.5, 0.75} × cis {off, 5 kb};
  - extras: trans_lambda, β, pc 20, similarity, target gate, min_lines, cis 20 kb, z 5.
  - Anatomy, including cis share, for E021 and B5.
- **E031 (GPU):** real V\* on the 5 lines for the shortlist, plus V\*-far.
- **E032:** leaderboard confirmation if E031's top beats the E021 config by ≥ 0.01 on both V\* and V\*-far.
- **E033:** per-context leaderboard breakdown of E012/E021 (no submission).
- **PLAN in parallel:** paired bootstrap (R13), then M-1 translator data tables with B5 features (R6/R7).
