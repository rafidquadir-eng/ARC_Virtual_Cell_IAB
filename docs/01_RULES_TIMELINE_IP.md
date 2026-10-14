# Rules, timeline, scoring and IP

**Recommendation: GO.** Nothing in the rules forces disclosure of iMEMORY. Keep iMEMORY out of the final entry unless it measurably helps and counsel approves the published description.

## Task (verified)
- Predict CRISPRi knockdown responses in cell lines never seen perturbed, from their non-targeting control cells and a target list. No challenge training set. [1]
- Six cell lines: A, B, C drive the live leaderboard; D, E, F decide the winners. [1]
- Validation bundle: per context 18,400 control cells (46 NTC guides × 400), median ~20k UMI/cell, plus 300 targets to predict in every context. [3]
- Test bundle (Thu 22 Oct): D, E, F controls with their own perturbation list. Final ranking uses only the test set. [3]

## Submission format (verified)
- Raw, non-negative integer counts per cell; no cell total above 10^6; gene axis = 18,533 genes in reference order; perturbation labels must match the reference **including the `non-targeting` label** (our local scorer rejects predictions without it). Cells per perturbation unconstrained. [4]
- One `.vcc` file covering all contexts, made by `vcc prep`, with a context column. [6]

## Timeline and limits (verified)
| Date (UTC) | Event |
|---|---|
| Thu 20 Aug | Validation data, leaderboard open [1] |
| until Thu 22 Oct | **Leaderboard entries: max 2 per UTC day** — 16 left including 14 Oct [2] |
| Thu 22 Oct | Test set released [1][2] |
| 22 Oct – 5 Nov | **Final entries: max 2 per UTC day; no leaderboard shown; only the last final entry counts** [2] |
| Thu 5 Nov 23:59 | Final deadline (18:59 ET; US clocks change 1 Nov) [1][2] |
| mid–late Nov | Winners announced [1] |

## Scoring (verified, cell-eval2 `vcc2026` profile) [4][5]
Per metric: s = (u − b) / (r − b). b = the context's own mean perturbation response (an oracle built from hidden data); r = split-half replicate of the experiment. Context score = mean of six; overall = mean over contexts. Values above 1 and below 0 occur. All metrics exclude the knocked-down target gene (PDS excludes all panel targets).

| Metric | Baseline b | Replicate r | Exact-copy scaled |
|---|---|---|---|
| pds_cosine | 0.500 | 0.927–0.984 | 1.03–1.17 |
| expr_mse_unbiased_capped_norm (clamp 0..1) | 0.986–0.992 | 0.028–0.045 | 1.00 |
| direction fidelity (yield) | 0.505–0.522 | 0.795–0.832 | 1.51–1.72 |
| direction reach | 0.047–0.097 | 0.958–0.978 | 1.02–1.05 |
| sig-gene Jaccard | 0.021–0.037 | 0.375–0.423 | 2.48–2.85 |
| LFC nMAE (floor −6) | 1.0009–1.0017 | 0.369–0.431 | 1.58–1.75 |

Implications: predicting "no change" scores badly on direction metrics (−1.72 on fidelity per a public benchmark [7]); the number of DE genes called per target is a direct lever on Jaccard and fidelity; on-target knockdown earns nothing, but neighbouring genes silenced by CRISPRi are scored.

## Teams and eligibility (verified) [2]
1–8 members; all members eligible and in the **same capacity** (all as company employees, or all university, or all personal). Prize split equally among listed members. Rules effective 4 Aug, revised 16 Sept.

## IP and disclosure
- No open code or weights required. [2]
- Finalists must submit a **high-level description, which Arc publishes**; need not be reproducible; must include data processing and how model inputs were constructed. The full list of required items is **unverified** (page renders in a browser only). [2]
- If iMEMORY is in the final entry, the description would mention it → counsel signs off first, or leave it out.
- **Flag for counsel (verified 14 Oct):** the GitHub repo `rafidquadir-eng/iMEMORY-Agentic-Orchastration-Infrastructure-for-Machine-Learning-Computational-Biology` is **public** and describes the HetGAT architecture and pipeline (with synthetic weights). Whether the preprint PDF is public is unverified. Either may already count as disclosure for the unfiled patent.
- Data licenses that matter for a company entry: State, Stack (non-commercial); X-Atlas/Orion (non-commercial). See `03_DATASETS.md`.

## Sources
1. [Arc Institute — The 2026 Virtual Cell Challenge](https://arcinstitute.org/news/virtual-cell-challenge-2026)
2. [Virtual Cell Challenge 2026 Rules](https://virtualcellchallenge.org/rules)
3. [Datasets page](https://virtualcellchallenge.org/datasets)
4. [cell-eval2 vcc2026 metric spec](https://github.com/ArcInstitute/cell-eval2/blob/main/docs/vcc2026_metrics/vcc2026-metrics-brief.md)
5. [cell-eval2 0.18.0 (PyPI)](https://pypi.org/project/cell-eval2/)
6. [vcc-cli (PyPI)](https://pypi.org/project/vcc-cli/)
7. [vcc2026-h1-benchmark](https://github.com/forrestsheldon/vcc2026-h1-benchmark)
