# Approaches, ranked

Ranking is by expected gain on the **final** score (contexts D/E/F, unseen lines, new target list) per dollar and per day, given 22 days. Every approach is accepted or rejected on leave-one-cell-line-out (LOCO) validation scored with the official metrics, not on the leaderboard.

## What iMEMORY and X-Cell share, and what transfers here

X-Cell (Xaira) is a diffusion language model up to 4.9B parameters: it starts from a set of control cells and refines them into perturbed cells, with the knocked-down gene injected as a prior-knowledge embedding (literature, protein interactions, morphology; the slide also shows DepMap, STRING, ESM-2, scGPT, JUMP) through cross-attention. It was trained on X-Atlas/Pisces, 25.6M CRISPRi cells across 16 contexts. [1]

iMEMORY has the same *shape* of idea (gene nodes carrying language-model priors, a learned network on top), with a HetGAT instead of a transformer. Three things from X-Cell are worth adopting, and they work without its weights or data:

1. **Condition on the target context's own control cells.** We already do: every prediction is emitted by modifying the real control cells of the new line, and sources are weighted by how similar their controls are to the new line's.
2. **A rich prior embedding of the knocked-down gene.** This is the main thing to borrow. DepMap co-essentiality, STRING, ESM-2, GO and a language-model text embedding, concatenated into one target-gene vector. It decides which measured knockdowns a new target should resemble, and how much to trust its measured effect. Cheap, and it is the part of X-Cell that plausibly transfers zero-shot.
3. **Gating by context.** X-Cell's context generalization comes from seeing many contexts. We approximate it with what the new line's controls tell us: a target that is not expressed there cannot be knocked down, and genes not expressed cannot be called DE.

What does not transfer in 22 days: X-Cell's scale. Its gains come from 25.6M cells across 16 contexts and billions of parameters; we have about 5–7 public contexts, and X-Atlas/Orion is non-commercial. A from-scratch diffusion or HetGAT model trained on ~5 contexts is the setting where published deep models have repeatedly failed to beat linear baselines [2], and where 2025 challenge winners were statistical/hybrid methods [3].

## Ranked

| # | Approach | Hypothesis | Go/no-go (LOCO) | Compute | Expected gain | Risk |
|---|---|---|---|---|---|---|
| A1 | **Calibrated atlas transfer** | Target-specific CRISPRi effects measured in other lines transfer. Gains from: source weighting by control-profile similarity; per-target shrinkage when sources disagree; **target-expression gating** (no knockdown if the target isn't expressed in the new line); effect-size β and DE-call-count calibration. | Beats B1 (generic) on ≥3 of 5 held-out lines, seen and unseen modes | CPU | High | Low |
| A2 | **CRISPRi neighbour silencing** | KRAB-dCas9 at a promoter also silences genes whose TSS lies within ~1 kb (bidirectional promoters). Context-independent and scored (only the target itself is excluded). | Gain on targets that have a close neighbour, measured in public screens | CPU + GENCODE TSS | Medium on affected targets | Low |
| A3 | **X-Cell-style target prior** for unmeasured or noisy targets | A concatenated prior (DepMap co-essentiality, STRING, ESM-2, GO, LM text) predicts which measured knockdowns a new target resembles. | Beats the linear fallback and a shuffled-prior null in unseen mode | CPU + ~1 GPU-h for ESM-2 | Medium; high if D/E/F targets are missing from public screens | Low |
| A4 | **iMEMORY gene vectors** inside A3 | iMEMORY's trained gene projection adds signal beyond the public priors. | Beats a shuffled copy of itself **and** the A3 prior without it, on ≥2 of 3 lines, by more than replicate noise | CPU, < $10 | Low | Needs EC2 files |
| A5 | **Learned cross-context model (HetGAT or set transformer)** | A network over a STRING gene graph, conditioned on the new line's control pseudobulk and the A3 target prior, learns context-specific modulation beyond A1. iMEMORY's HetGAT design can be reused; its weights cannot. | Must beat A1+A2+A3 in LOCO; only start if ≥5 days remain after A1–A3 | 1x H100, ~40 h (LR-3, ~$172) | Uncertain | High |

## Explicitly not doing (and why)

- **LeJEPA / JEPA-style pretraining.** LeJEPA (Balestriero & LeCun) is a self-supervised objective that pushes embeddings toward an isotropic Gaussian (SIGReg); the released work is on images (ImageNet-scale pretraining) [4]. Our score is computed on pseudobulk fold changes and Wilcoxon calls against the new line's controls, and our limit is perturbation-labelled contexts, not cell representations. A better unsupervised cell embedding doesn't move any of the six metrics in 22 days. Worth a look for the iMEMORY roadmap after the challenge, not for this entry.
- **Adapting `insilico_knockout.py`:** no gene-level output.
- **Aligning iMEMORY's patient space to the cell lines:** no perturbation supervision, and building patient graphs from cell-line controls needs the missing preprocessing pipeline.
- **State / Stack zero-shot:** non-commercial licenses, and neither was trained on these six lines.
- **Tuning on the leaderboard:** leaderboard entries are calibration points only (does local LOCO rank methods the same way?). A/B/C are not the scored lines.

## Metric-aware choices that are legitimate
All of these change our predictions, not the scorer: matching the number of DE calls per target to what transfers from sources (Jaccard, fidelity); emitting cells by thinning or augmenting real control cells so Wilcoxon noise is realistic; overall effect scale β chosen on LOCO.

## Sources
1. [GEN — Xaira's X-Cell](https://www.genengnews.com/gen-edge/xairas-first-virtual-cell-model-is-largest-to-date-toward-complex-biology/)
2. Ahlmann-Eltze et al., linear baselines vs deep perturbation models (as implemented in the public [pc_linreg baseline](https://github.com/mmyen/virtual-cell-challenge-2026))
3. [Arc — VCC 2025 wrap-up](https://arcinstitute.org/news/virtual-cell-challenge-2025-wrap-up)
4. [rbalestr-lab/lejepa](https://github.com/rbalestr-lab/lejepa)
