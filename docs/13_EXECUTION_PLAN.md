# Execution plan: fixing every problem in `12_DIAGNOSIS.md`

Written 15 Oct 2026 ~18:00 UTC (14:00 ET). It turns each problem P1–P21 into owned, testable work with commands, code, acceptance tests and dates. `11_BUILD_PLAN.md` still holds the long-range model architecture (M-1/M-2, C-1/C-2); this file is the working queue.

Owners:
- **CUR** = curation agent (tmux `data`, `docs/09`)
- **RUN** = runbook agent (tmux `cc`, `docs/07`)
- **PLAN** = planning session (writes code, specs and runbook stages)
- **R** = Rafid

Each task is done when its acceptance test passes and its REPORT is pushed.

---

## 0. Decisions recorded today

| Decision | By | Consequence |
|---|---|---|
| **Use X-Atlas/Orion and X-Atlas/Pisces** (Hugging Face, licence CC BY-NC-SA 4.0) | R, 15 Oct | Unblocks P8 (CUR task D10). PLAN's flag: NC means non-commercial and SA means share-alike. Immunome AI is a company competing for a cash prize, and a model trained on the data may count as an adaptation. R has accepted this; asking counsel or Xaira remains the clean option. To keep it reversible, every X-Atlas dataset gets `licence: "CC BY-NC-SA 4.0"` in `loco.json`, and the final pipeline must be able to run with and without it (`--exclude-licence NC`). |
| rclone gets its own Google OAuth client | R | Unblocks archiving (P21); steps in §6 |
| Other project moves off this instance, or onto a GPU schedule | R (pending) | P20 |

## 1. Phase A — stop the bleeding (15–16 Oct): noise, weighting, data artefacts

These are the largest effects per hour of work. Nothing here needs new data.

### A1. P1/P2/P3/P4/P12/P16: B4 consensus model, proxy sweep, confirmation
- **Code (PLAN, done 15 Oct):**
  - `models.predict_consensus` (`B4_consensus`): low-rank Gavish–Donoho denoising per source, inverse-variance merging within a line, random-effects pooling across lines (τ²), empirical-Bayes shrinkage, similarity weights, `gate_up_cpm`, `gate_target_cpm`, pseudocount space `pc`, `generic` zero/gw, and `beta`;
  - `vcc26.proxy` (fast metric proxies + anatomy);
  - `scripts/pick_e025.py`.
- **RUN:** E025 (CPU) → `specs_E026.json` → E026 real V\* + V\*-far (GPU) → E027 leaderboard.
- **Accept:** E026 best V\* > E020's B2_raw_gPL (0.167) by ≥ 0.02 with raw MSE < 1.0 on every line; E027 leaderboard > 0.106.
- **If it fails:** read the anatomy JSON (where the squared error lives: expression bins, target tiers, best scale per tier). PLAN adjusts B4 (stronger gating, per-tier β) and reruns the proxy only. That loop takes minutes.

### A2. P7: composition-matched controls (donor/batch artefacts)
- **Code (PLAN, done):** `pseudobulk --strata-col`.
- **CUR (D7):**
  - re-summarise CD4T by donor;
  - re-summarise K562, K562_GWPS and RPE1 by GEM group;
  - re-summarise HepG2/Jurkat by batch if one exists;
  - rebuild HipSci with NonTarget-only controls;
  - report median |lfc| of Y/HLA genes before vs after.
- **RUN:** E025b (proxy on the new summaries); if better, E026 uses them.
- **Accept:** Y/HLA artefact |lfc| drops ≥ 5× in CD4T; E025b proxy ≥ E025 proxy for the same spec.

### A3. P6: paired bootstrap confidence intervals (PLAN, 16 Oct)
- **Code:** `local_eval.score(..., per_target=True)` returns per-target raw metrics. `vcc26/compare.py` bootstraps the difference between two specs over targets (1,000 resamples; MSE as a ratio of sums) and reports Δ with a 90% CI.
- **Accept:** reproduces the E020 table; E026 decisions are quoted with CIs.

### A4. P19: V\*-far, a stricter validation (PLAN 16 Oct; RUN with E026)
- **Code:** a `lineage` field in `loco.json` (`T_lymphoid`: CD4T, Jurkat; `pluripotent`: H1, KOLF2.1J, HipSci; `myeloid_leukemia`: K562; `epithelial`: RPE1, HepG2, HCT116, HEK293T). `vstar --far` drops same-lineage sources as well as same-line ones.
- **Selection rule from E026 on:** `0.5·V* + 0.5·V*-far`. B and C have no same-lineage source; A has one (CD4T), so both halves of the score matter.

### A5. P20/P21: operations (R)
- **P20:** move the other project to its own instance (`gpu_1x_a100_sxm4` ≈ $1.99/h on its own budget line), or agree GPU hours.
  - RUN checks `nvidia-smi` before every GPU stage and records the free memory.
  - RUN never installs into `~/vcc/.venv` from another project; it re-verifies `torch==2.11.0+cu128` with `python -c "import torch, cupy; print(torch.__version__)"` before each stage.
- **P21:** rclone OAuth client (§6). Then CUR runs the archive commands in `DATA_DONE.md`.

## 2. Phase B — the epithelial/T-cell data gap (15–18 Oct)

### B1. P8: X-Atlas/Orion and Pisces (CUR task D10, unblocked)
Sources:
- Orion on Hugging Face: `Xaira-Therapeutics/X-Atlas-Orion` (parquet, 126 GB, HCT116 ~2.09M and HEK293T ~3.51M rows, CC BY-NC-SA 4.0). **Prefer the processed h5ad files on figshare+ (doi 10.25452/figshare.plus.29190726)**, which avoids parquet conversion.
- Pisces: `Xaira-Therapeutics/X-Atlas-Pisces`. 16 contexts: HCT116, HEK293T, HepG2, iPSC, resting and CD3/CD28-activated Jurkat, and differentiating iPSC. **Parts are marked "Coming Soon" on the card**, so take whatever is uploaded today and list the rest.

Steps for CUR:
1. Read the dataset card, file list and preview.
2. Cells: keep `pass_guide_filter == True` (two guides from the same pair). The perturbation label is `gene_target`; controls are "Non-Targeting". Map genes through `metadata/gene_metadata.parquet` (Ensembl → symbol).
3. Summaries with `--strata-col sample` (batch-matched controls) and `--max-kd 0.7`.
4. Subsets as before: panel targets ≤ 400 cells each, ≤ 100 cells for other targets, 18,400 controls.
5. `loco.json` entries:

   | dataset | `line` | `library` | `lineage` |
   |---|---|---|---|
   | Orion HCT116 | `HCT116` | `genome_wide` | `epithelial` |
   | Orion HEK293T | `HEK293T` | `genome_wide` | `epithelial` |
   | Pisces Jurkat (resting and activated) | `Jurkat` (same line as Nadig's) | `genome_wide` | `T_lymphoid` |
   | Pisces HepG2 | `HepG2` | `genome_wide` | — |
   | Pisces iPSC contexts | own line names | `genome_wide` | `pluripotent` |

   Every entry also gets `"licence": "CC BY-NC-SA 4.0"`.
6. Report: panel coverage per line, median UMI, median knockdown, and the new ≥ 1/≥ 2/≥ 3-line coverage table.

Why this matters: **HCT116/HEK293T become epithelial V\* held-out lines**, our first validation that resembles B and C, and sources for them. Jurkat genome-wide is the closest public line to A. Sizes: Orion 126 GB parquet / smaller as h5ad; Pisces unknown. Ask R before > 1 TB.

### B2. P8: more epithelial/carcinoma and T-ALL data (CUR D8, D9)
Same as `docs/09` batch 2: HeLa and cervical/ovarian, squamous, and T-ALL lines; check LINCS L1000. Ingest anything with ≥ 20 panel targets.

### B3. P13: CCLE expression for context matching (CUR D11)
DepMap 24Q4 expression and `Model.csv`, to `$DATA/priors/`.

## 3. Phase C — biology-aware prediction (16–21 Oct)

### C1. P11: project predictions onto the target context's own programs (PLAN code 16 Oct → RUN E029)
- **Code:** `models.project_ctrl(lfc, ctrl_cells, k, lam)`.
  - PCA of the context's control cells (log-normalised, top 3,000 genes).
  - Each predicted effect vector is projected onto the top-k PCs: `lam·proj + (1−lam)·pred` on those genes.
  - Available as a post-processing option for every model (`"post": {"project": {"k": 200, "lam": 0.5}}` in a spec).
- **Test:** proxy grid k ∈ {50, 200, 1000} × λ ∈ {0.25, 0.5, 1} on V\* and V\*-far, then a real V\* confirmation.

### C2. P11/P14: learned translator M-1 (PLAN code 16–17 Oct → RUN E030–E032)
- **Data tables (`vcc26/dataset.py`):** every target measured in ≥ 2 lines gives (source line → target line) training pairs. After Phase B that's about 10k targets × ~45 ordered line pairs among CD4T, K562_GWPS, KOLF, HipSci, HCT116, HEK293T, Jurkat-GW, iPSC-Pisces, and the essential lines. Labels are B4-denoised.
- **Features per (target, gene):**
  - source consensus lfc (B4) and per-line lfcs;
  - noise;
  - the gene's control CPM in the source and in the target, and their ratio;
  - the target gene's expression in the target context;
  - control-profile similarity of each source to the target;
  - the gene's typical response amplitude;
  - STRING/GO/DepMap relations between target and gene;
  - the target context's PCA loading of the gene.
- **Model:** LightGBM (GPU), leave-one-line-out folds matching V\*/V\*-far.
- **Accept:** ≥ +0.02 over the best B4 on `0.5·V* + 0.5·V*-far`.

### C3. P12: target-expression gating, already in B4 (`gate_target_cpm`); tuned in E025. Extended in C2 as a feature.

### C4. P13: context-specific dependencies (PLAN code 18 Oct → RUN E033)
- **Code:** `vcc26/context_dep.py`.
  1. Find the 10 DepMap lines whose CCLE expression is nearest to each context's control pseudobulk.
  2. Each panel target's predicted fitness effect in that context is the mean Chronos gene effect over those neighbours.
  3. Learn a "fitness response programme" from the sources: the response component that correlates with the target's fitness effect in that source line (DepMap effect of the same gene in the nearest DepMap line to each source).
  4. Add `predicted_fitness × programme` to each target's prediction.
- **Test:** proxy on V\* (CD4T/KOLF/HCT116 holdouts), then real V\*.

### C5. P14: effect magnitude. β per context comes from the C-2 optimiser (§4); per-tier scaling from the anatomy ("best scale by tier") in E025.

### C6. P15: neighbour silencing (A2, built 14 Oct) → RUN E028
`specs_E028.json` = best B4 with and without `tss` (the A2 prior learned from all sources), run on proxy and real V\*.

### C7. P10: unmeasured targets (EPHB2, plus thin targets) → M-4 prior encoders (`11_BUILD_PLAN` §5), 18–19 Oct. Small weight: about 10 targets.

## 4. Phase D — metric-aware emission and calibration (19–21 Oct)

### D1. P17/P18: DE-count calibration (C-1) and expected-score optimiser (C-2), as specified in `11_BUILD_PLAN.md` §6.
New inputs from Phases A–C: B4 provides per-gene predictive variance, and the anatomy tells which tiers to scale. The optimiser runs per context and chooses β, shrinkage strength, DE-count targeting and the projection λ. It must keep the across-target spread above the noise level, so that MSE keeps its noise credit.

### D2. Ensemble
Out-of-fold weights over B4, M-1, (M-2) and the projection variants, fitted on `0.5·V* + 0.5·V*-far`.

## 5. Phase T — final test (unchanged; `11_BUILD_PLAN.md` §7)
- **21 Oct:** dress rehearsal on A/B/C.
- **22 Oct:** D/E/F released; run `context_id` first; first final entry the same day.
- **Until 4 Nov:** refresh only on local wins; freeze 4 Nov.
- **Licence switch:** the final pipeline is run with and without NC data (`--exclude-licence NC`). Both entries' V\* scores are recorded, so R can choose with numbers.

## 6. rclone: your own Google OAuth client (P21) — instructions for R
(From rclone's docs, "Making your own client_id".) About 10 minutes. You can use any Google account for steps 1–5; step 6 must be the account that owns the Drive.

1. **Google Cloud console** → https://console.cloud.google.com → project picker → **New project**, name `vcc-rclone` → Create, and select it.
2. **Enable the Drive API:** APIs & Services → **Library** → search "Google Drive API" → **Enable**.
3. **Consent screen** (Google Auth Platform / OAuth consent screen) → **Get started**:
   - app name `rclone-vcc`, your support email;
   - Audience: **Internal** if the Drive is a Google Workspace account (e.g. immuneome-ai.com), otherwise **External**;
   - contact email → agree → Create.
4. **Data access** → Add or remove scopes → tick or paste `https://www.googleapis.com/auth/drive` (also `.../auth/docs` and `.../auth/drive.metadata.readonly`) → Update → **Save**.
   - **External only:** Audience → **Test users** → add the Gmail that owns the Drive → Save.
   - Testing-mode grants expire after 7 days. Either re-run step 6 weekly (three times before 5 Nov), or **Publish app** (you may need a home-page and privacy-policy URL under Branding). Internal apps don't expire.
5. **Clients** → **Create client** → Application type **Desktop app** → name `rclone` → Create. Copy the **Client ID** and **Client secret**. Keep them private: not in chat, files or git.
6. **Point rclone at it** (on the Mac, with the same tunnel as before):
   ```bash
   ssh -L localhost:53682:localhost:53682 -i ~/.ssh/A10.pem ubuntu@150.136.70.112
   sudo -v ; curl https://rclone.org/install.sh | sudo bash     # upgrade rclone (instance has v1.60)
   rclone config
   ```
   In the menu:
   1. `e` (edit existing remote) → pick `gdrive`.
   2. Paste the **client_id** and **client_secret**, and keep the scope as `drive`.
   3. Advanced config `n`.
   4. "Already have a token — refresh?" → `y`.
   5. "Use web browser" → `y`. Open the printed `http://127.0.0.1:53682/auth…` link on the Mac and sign in **with the account that has the large Drive plan**.
   6. If Google warns "hasn't verified this app": Advanced → Go to rclone-vcc. It's your own app.
   7. Shared Drive `n` → keep `y` → `q`.
7. **Check:**
   - `rclone about gdrive:` should show the plan's total. Today it reports **2 TiB**, not 5 TB, so the remote may be signed in to a different Google account. Sign in with the 5 TB account in step 6.
   - `rclone lsd gdrive:VCC2026` should list the folder.

   Then tell CUR: "rclone has its own client now; run the archive commands in DATA_DONE.md (KOLF raw, CD4T/KOLF subsets), check, then delete the KOLF raw from scratch."

## 7. Calendar and queue

| Date (UTC) | CUR | RUN | PLAN | R |
|---|---|---|---|---|
| 15 Oct | D7 strata re-summaries; D10 X-Atlas download + ingest | E025 (CPU) | this plan; A3 bootstrap; A4 V\*-far | rclone client; instance decision |
| 16 Oct | D10 finish; D8, D9, D11 | E025b; E026 (V\*, V\*-far incl. HCT116/HEK293T if in); E027 leaderboard | C1 projection; M-0 tables; C2 GBM | — |
| 17 Oct | archive to Drive | E028 neighbours; E029 projection; E030 GBM | C2 tune; C4 dependency feature | — |
| 18–19 Oct | more data only if found | E031–E033 | M-4 priors; C-1 DE calibration | — |
| 19–21 Oct | — | E06x optimiser; ensemble; dress rehearsal (E070) | C-2 optimiser; final pipeline script | — |
| 22 Oct → | D/E/F identity support | final entries | improvements on local wins only | final calls (NC data in or out) |

**Leaderboard use:** one confirmation per day, from E027 on (A/B/C phase ends 22 Oct).

## 8. Expected effect (honest ranges, to be replaced by measurements)

| Step | Expected leaderboard change | Confidence |
|---|---|---|
| A1 + A2 (noise, weighting, artefacts) | +0.05 to +0.15 (MSE off 0, PDS up) | medium: proxy within hours |
| B1 (X-Atlas epithelial + Jurkat-GW) | +0.03 to +0.10, mostly for A (Jurkat) and B/C (HCT116/HEK293T) | medium |
| C1/C2/C4 (projection, translator, dependencies) | +0.03 to +0.10 | low–medium |
| D1/D2 (calibration, optimiser, ensemble) | +0.02 to +0.08 (DE metrics) | low–medium |

All of it together could plausibly reach the 0.30s. Beyond that depends on how far the translator generalises to B/C-like lines, which V\*-far on HCT116/HEK293T will tell us before 22 Oct.
