# Prior-knowledge resources (curation D5)

Fetched 15 Oct 2026 by `scripts/fetch_priors.sh` to `$DATA/priors/<resource>/` and mirrored to
`gdrive:VCC2026/data/priors` (`rclone check` OK). Total 848 MB. Every licence was checked at its source
before download, for commercial use.

| Resource | Version | Files (size) | URL | Licence (checked at) |
|---|---|---|---|---|
| STRING human | v12.0 | `9606.protein.links.detailed.v12.0.txt.gz` (134 MB; channel scores + combined), `protein.info` (2 MB), `protein.aliases` (20 MB) | https://stringdb-downloads.org/download/ | CC BY 4.0, commercial use allowed — https://string-db.org/cgi/access |
| Gene Ontology | ontology `releases/2026-07-26`; GAF 2.2 generated 2026-05-21 | `go-basic.obo` (32 MB), `goa_human.gaf.gz` (16 MB) | http://current.geneontology.org/annotations/, http://purl.obolibrary.org/obo/go/go-basic.obo | CC BY 4.0 — https://geneontology.org/docs/go-citation-policy/ |
| UniProt human reference proteome (UP000005640) | UniProt 2026_03 (02 Sep 2026) | `UP000005640_9606.fasta.gz` (8 MB, 20,652 canonical sequences), `UP000005640_9606.idmapping.gz` (28 MB) | https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/reference_proteomes/Eukaryota/UP000005640/ | CC BY 4.0 — https://ftp.uniprot.org/pub/databases/uniprot/LICENSE |
| DepMap CRISPR gene effect (Chronos) | DepMap 24Q4 Public (confirmed 16 Oct: md5 6edf7ade09b9b34199210b559d4745d3 = figshare file 51064667 of the "DepMap 24Q4 Public" record, published 2024-12-10) | `CRISPRGeneEffect.csv` (410 MB), `Model.csv`, `README.txt` | figshare 10.25452/figshare.plus.27993248 | CC BY 4.0 (figshare record, re-checked 16 Oct) |
| DepMap expression (CCLE) | DepMap 24Q4 Public | `OmicsExpressionProteinCodingGenesTPMLogp1.csv` (507 MB, 1,673 models; md5 71794802b750ce77c422dad0720a40af), with the existing `Model.csv` | figshare 10.25452/figshare.plus.27993248 (file 51065489) | CC BY 4.0 (figshare record) |
| DepMap somatic mutations (batch 3, D14, 16 Oct) | DepMap 24Q4 Public | `OmicsSomaticMutations.csv` (339 MB; per-variant calls incl. `LikelyLoF`, hotspot flags), `OmicsSomaticMutationsMatrixDamaging.csv` (148 MB; model × gene, 0/1/2 damaging), `OmicsSomaticMutationsMatrixHotspot.csv` (4 MB; model × gene hotspot) in `$DATA/priors/depmap/`; md5 7bdba347…, cb20fdbe…, a5aeb1de… all match figshare | figshare 10.25452/figshare.plus.27993248 (files 51065732, 51065747, 51065750) | CC BY 4.0 (figshare record, checked 16 Oct). Drive copy queued for 17 Oct 08:00 UTC (daily upload limit hit 16 Oct) |
| Reactome human | database version 97 | `ReactomePathways.gmt.zip`, `ReactomePathways.txt`, `ReactomePathwaysRelation.txt`, `Ensembl2Reactome.txt` (176 MB, all species) | https://reactome.org/download/current/ | Data CC0, commercial use allowed — https://reactome.org/license (§1c) |

ESM-2 weights were not fetched: the experiment session computes embeddings from the UniProt FASTA.

## Listed, not fetched

| Resource | Why |
|---|---|
| CollecTRI TF→target network | OmniPath lists its licence as "Constituting databases carry their own licenses (Composite)" (https://omnipathdb.org/info). OmniPath's `license=commercial` filter returned the same 64,516 rows as `license=academic` (the same was true for `omnipath` and `dorothea`), so the filter can't be relied on and commercial use could not be verified. Needs a per-source licence review (https://github.com/saezlab/CollecTRI) or permission. A file downloaded during the check was deleted locally and on Drive. |
| DepMap releases newer than 24Q4 | Only on depmap.org, which serves a bot-verification page to the instance. Rafid can download a newer `CRISPRGeneEffect.csv` in a browser if wanted (same licence). |
