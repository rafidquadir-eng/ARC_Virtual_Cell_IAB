"""iMEMORY go/no-go probe: do iMEMORY gene representations carry perturbation-response signal?

What iMEMORY can offer here (from the Box audit):
  * gene node INPUT features: BioLinkBERT+SPECTER2 embeddings of the gene SYMBOL, projected to
    512-d by an untrained (random xavier) Linear layer -> node_embeddings/gene_embeddings.npz
    (on the old EC2 disk, NOT on Box)
  * the trained encoder's gene input projection: encoder.input_proj['gene'] (512 -> 256), applied
    after subtracting gene_mean_embedding.npy (on Box). This is the only TRAINED, gene-specific
    part of phase2_v4_best.pt that can be read without building patient graphs.

The probe writes two embedding files usable by loco.py as kNN fallbacks:
  imemory_raw.npz   {symbol: 512-d}   text features as fed to the model
  imemory_proj.npz  {symbol: 256-d}   after the trained gene projection

Then run loco.py in --mode unseen with specs comparing knn:imemory_raw / knn:imemory_proj against
the same kNN on (a) a shuffled copy of the same vectors and (b) the linear fallback.
GO only if an iMEMORY arm beats BOTH the shuffle null and the linear fallback on the mean context
score in >= 2 of 3 held-out contexts, by more than the replicate seed noise (anchors.json
replicate_sd, scaled). Otherwise NO-GO and iMEMORY stays out of the entry.

  python -m vcc26.imemory_probe --ckpt phase2_v4_best.pt --gene-emb gene_embeddings.npz \
      --gene-mean gene_mean_embedding.npy --out emb/
"""
from __future__ import annotations

import argparse
import os

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ckpt", required=True)
    ap.add_argument("--gene-emb", required=True, help="gene_embeddings.npz {symbol: 512-d}")
    ap.add_argument("--gene-mean", required=True, help="gene_mean_embedding.npy (512,)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import torch
    os.makedirs(a.out, exist_ok=True)
    z = np.load(a.gene_emb, allow_pickle=True)
    emb = {k: z[k].astype(np.float32) for k in z.files}
    np.savez(f"{a.out}/imemory_raw.npz", **emb)

    ck = torch.load(a.ckpt, map_location="cpu", weights_only=False)
    sd = ck.get("model_state_dict", ck)
    W = sd["encoder.input_proj.gene.weight"].numpy()      # (256, 512)
    b = sd["encoder.input_proj.gene.bias"].numpy()
    mean = np.load(a.gene_mean).astype(np.float32)
    proj = {k: (W @ (v - mean) + b).astype(np.float32) for k, v in emb.items()}
    np.savez(f"{a.out}/imemory_proj.npz", **proj)
    nz = sum(np.abs(v).sum() == 0 for v in emb.values())
    print(f"{len(emb)} genes; {nz} all-zero (failed embeds); checkpoint epoch={ck.get('epoch')} "
          f"val_macro_f1={ck.get('val_macro_f1')}")


if __name__ == "__main__":
    main()
