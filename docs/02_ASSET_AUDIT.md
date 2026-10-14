# iMEMORY asset audit

All Box access read-only. Confidential and collaborator folders (Shalek, Jordi-RQ, Mariana-RQ, anything marked Confidential) not opened.

## Final model
| | |
|---|---|
| Checkpoint | `OutputsV4/checkpoints/phase2_v4/phase2_v4_best.pt` (28,956,963 B, 30 Mar 2026) — **confirmed final** |
| Evidence | `OutputsV4/logs/phase2_v4_train.log`: best macro-F1 0.7391 at epoch 24, TI F1 0.875, balanced 1,200-sample val |
| Contents | `model_state_dict`, optimizer state, val metrics, module names |
| Model class | `HeteroClassificationModelV3` (`OutputsV4/scripts/hetero_encoder_v4.py`, = v3 code); torch_geometric HeteroConv(SAGEConv) ×2, hidden 256, 128-d L2-normalized graph embedding, 6-class head |
| Config | `pipeline_config.py` (now also in `ARC Virtual cell Challenge/Embedding file search (from local disk)`): NODE_INPUT_DIMS, EDGE_TYPES, label map |

## What it embeds
- **Patient/sample graphs**, one per sample. Classes: acute rejection, chronic rejection, CKD, hemodialysis, kidney transplant, trained immunity.
- 45,670 training graphs from 840 study shards (151,513 more filtered out by the clean-endotype list).
- Log warning: 10 of 13 node types are never updated by message passing (no incoming edges).
- Not cells, not perturbations. No perturbation node or perturbation objective.

## Gene features (the only part relevant to this challenge)
- `embed_nodes_v2.py`: BioLinkBERT-large (1024-d) + SPECTER2 (768-d) CLS embedding of the **bare gene symbol string**, concatenated, then `nn.Linear(1792 → 512)` with **random Xavier init, never trained, unseeded**, saved as `gene_proj_weights.pt`.
- Graph gene-node features = that 512-d vector × the sample's z-scored expression, centered by `gene_mean_embedding.npy`.
- Vocabulary: **22,880 genes** (from `rebuild_sdy997_individual_genes.py`).
- Trained gene-specific weights in the checkpoint: `encoder.input_proj.gene` (512 → 256).
- `gene_mean_embedding.npy` (4,224 B) confirmed: one 512-d float64 vector (128-byte header + 512 × 8).

## Box search for the embedding table (14 Oct)
All 12 `.npz` files on Box checked; none is the gene table:

| File | Size | What it is |
|---|---|---|
| `GSE286911.npz`, `GSE249006.npz` (OutputsV3/problematic_files) | 357 MB, 305 MB | raw study matrices (graph-builder inputs) |
| `v3_embeddings_for_umap.npz` (×2) | 1.0 MB | ~2,000 samples × 128 — sample embeddings |
| `v3_umap_coords.npz` (×2), `v3_module_activations.npz` (×2) | 138 KB, 70 KB | per-sample UMAP / module scores |
| `recovery_vector.npz` (×2), `recovery_vector_individual_genes.npz` (×2) | 5.7 KB, 1.8 KB | SDY997 disease/healthy centroids + 128-d direction |

Searches for `embedding`, `node_embeddings`, `gene_symbol_list`, `gene_proj` found only scripts and sample-level files. Also checked (14 Oct): the private GitHub repo `rafidquadir-eng/iMEMORY_V4` (130 files) mirrors Box `OutputsV4`: the same checkpoint, `stage1/embeddings_v4.npy` (45,670 samples × 128), UMAP/t-SNE coordinates and `gene_ti_correlation_rhos.npy` (256 values). No gene table. The table (~40 MB) exists only at `/mnt/nvme15tb/trained_im/node_embeddings/` on the old EC2 disk.

**It cannot be rebuilt:** the projection layer was random and unseeded, so regenerated vectors would not match what the checkpoint was trained on. Regenerating only the raw BioLinkBERT/SPECTER2 vectors is possible, but that tests public language models, not iMEMORY (it is included as one of the public gene priors in `04_APPROACHES.md`).

**To run the iMEMORY test, recover from the EC2 volume or an EBS snapshot:**
`gene_embeddings.npz`, `gene_proj_weights.pt`, `gene_symbol_list.txt`.

## Other code
- `insilico_knockout.py`: from the public showcase repo with synthetic weights; attenuates one of 128 embedding features and scores movement to a healthy centroid. No gene-level output → **not usable** for CRISPRi prediction.
- `hetgat_ops.py`, `therapeutic_signature.py`: NumPy reference ops of the showcase pipeline; nothing reusable for this task beyond the HetGAT idea.

## Training-data terms
README: production cohorts include AMP SLE (ImmPort SDY997), CHORD and kidney-transplant data under data-use agreements; most shards are GEO accessions. Your written confirmation is needed **only if** iMEMORY passes its test and goes into an entry.

## controls.zip
`ARC Virtual cell Challenge/controls.zip`, 662,118,680 B, uploaded 14 Oct 16:54 UTC. Not unpacked yet (Box connector reads text only; this workspace cannot download from Box). Runbook step E000 unzips and inventories it. Expected per the datasets page: contexts A, B, C; 18,400 control cells each; 18,533 genes; raw counts; 300-target list.
