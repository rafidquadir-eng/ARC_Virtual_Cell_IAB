# Datasets

"Unverified" = not confirmed from the source itself; `fetch_public_data.sh` prints file lists before downloading so the instance can confirm.

| Dataset | Role | Source | Size | License | Key | How |
|---|---|---|---|---|---|---|
| Challenge controls A/B/C (D/E/F on 22 Oct) | target contexts | vcc CLI; your Box copy | 662 MB zip | challenge terms | `VCC_TOKEN` | `vcc` CLI or `rclone copy box:...` |
| Replogle 2022 K562 essential, RPE1 essential | source contexts, LOCO | figshare article 20029387 | ~10 GB each (unverified) | CC BY 4.0 (unverified) | none | figshare API in `fetch_public_data.sh` |
| Replogle 2022 K562 genome-wide | covers ~9,866 expressed targets [1] | same | large (unverified) | same | none | `WITH_GWPS=1` |
| Nadig 2025 HepG2, Jurkat | source contexts, LOCO | HF `arcinstitute/Replogle-Nadig` | unverified | unverified | `HF_TOKEN` if gated | huggingface-cli |
| VCC 2025 H1 (train+val+test) | source context, same Flex chemistry as the challenge | Arc Virtual Cell Atlas [2] | unverified | unverified | unverified | link from atlas page |
| **X-Atlas/Orion (Xaira)** | 2 genome-wide cancer lines, ~8M cells, >16k UMI/cell, dose-aware [3] | Xaira (repository unverified) | very large | **non-commercial** [3] | unverified | **needs your decision** |
| Gene priors: DepMap CRISPR gene effect | co-essentiality → response similarity | depmap.org | ~400 MB | CC BY 4.0 (unverified) | none | DepMap portal download |
| Gene priors: STRING human | PPI graph | string-db.org | ~1 GB | CC BY 4.0 (unverified) | none | direct download |
| Gene priors: ESM-2 protein embeddings | sequence prior | HF `facebook/esm2_*` | model ~2.5 GB | MIT (unverified) | none | compute on GPU (~1 h) |
| Gene priors: GO annotations, GENCODE TSS | function; CRISPRi neighbour silencing | geneontology.org, gencodegenes.org | small | CC BY 4.0 / open (unverified) | none | direct download |
| Tahoe-100M, scBaseCount | not planned | Arc Virtual Cell Atlas | huge | — | — | drug / unperturbed data don't inform CRISPRi responses directly |
| State, Stack weights | not planned | Arc | — | non-commercial code, weights and outputs [5]; State has a commercial trial [6] | — | your decision |

## Notes
- **X-Atlas/Orion would be the biggest single data upgrade** (two more genome-wide contexts, i.e. more lines to transfer from and to validate on). Its license is non-commercial and Immunome AI is a company; Xaira says it is open to commercial collaborations [3]. Ask them, or skip.
- X-Atlas/Pisces (25.6M cells, 16 contexts, used to train X-Cell [4]) — public availability unverified; assume not available.
- Technology mismatch: Replogle/Nadig are 10x 3′; the challenge (and VCC 2025 H1) is 10x Flex probe-based. H1 is the best stand-in for Flex-specific noise in local validation.

## Sources
1. [arXiv 2510.01562 (Replogle K562 coverage)](https://arxiv.org/pdf/2510.01562)
2. [Arc — VCC 2026 announcement](https://arcinstitute.org/news/virtual-cell-challenge-2026)
3. [GEN — Xaira releases X-Atlas/Orion](https://www.genengnews.com/topics/artificial-intelligence/xaira-therapeutics-releases-largest-perturb-seq-dataset-to-power-the-virtual-cell/)
4. [GEN — Xaira's X-Cell](https://www.genengnews.com/gen-edge/xairas-first-virtual-cell-model-is-largest-to-date-toward-complex-biology/)
5. [ArcInstitute/state](https://github.com/ArcInstitute/state), [ArcInstitute/stack](https://github.com/ArcInstitute/stack)
6. [State commercial trial](https://arcinstitute.org/tools/state/commercial)

## Licence decision, 15 Oct 2026
Rafid approved using **X-Atlas/Orion and X-Atlas/Pisces (CC BY-NC-SA 4.0)**. Planning flag (recorded, accepted by Rafid): NC = non-commercial and SA = share-alike, and Immunome AI is a company in a cash-prize competition. Every NC dataset is tagged `"licence"` in `loco.json`, and the final pipeline is scored with and without NC data, so the decision stays reversible.
