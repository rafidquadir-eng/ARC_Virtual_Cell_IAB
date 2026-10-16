"""Song et al. 2025 (Nat Cell Biol, GEO GSE249595) Jurkat genome-wide CRISPRi CROP-seq -> pseudobulk-row h5ad.

The screen is high-MOI (median ~7 detected guides per cell), so no cell carries a single perturbation.
For one hash condition (default `untreated_1`) this writes one row per target gene holding the summed
counts of every cell that carries >= 1 guide for it (guide UMI >= --guide-min), plus one reference row
`all_cells` = all cells of that condition. Under additive effects, target-carrying cells minus all cells
estimates the target's effect (each gene is carried by < 0.1 % of cells). Feed the result to

  python -m vcc26.pseudobulk --h5ad OUT --pert-col target --control all_cells --weight-col ncells ...

Per channel (16, raw STARsolo matrices): cells = barcodes with >= --min-umi transcriptome UMI; hash
label = argmax label if it holds >= 60 % of label UMI, else unassigned.

  python scripts/convert_song.py SRC_DIR OUT.h5ad [--condition untreated_1] [--min-umi 1000] [--guide-min 5]
"""
from __future__ import annotations

import argparse
import glob
import os

import anndata as ad
import numpy as np
import pandas as pd
import scipy.io as sio
import scipy.sparse as sp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--condition", default="untreated_1")
    ap.add_argument("--min-umi", type=int, default=1000)
    ap.add_argument("--guide-min", type=int, default=5)
    ap.add_argument("--label-frac", type=float, default=0.6)
    a = ap.parse_args()
    chans = sorted(glob.glob(os.path.join(a.src, "GSM*_transcriptome_matrix.mtx.gz")))
    tot = targets = genes = None
    ncells = None; nall = 0; liball = None
    for ch in chans:
        p = ch.replace("transcriptome_matrix.mtx.gz", "")
        X = sio.mmread(ch).tocsc()                                    # genes x barcodes
        umi = np.asarray(X.sum(0)).ravel()
        keep = np.where(umi >= a.min_umi)[0]
        L = sio.mmread(p + "labels_matrix.mtx.gz").tocsc()[:, keep].toarray()
        lab = pd.read_csv(p + "labels_features.tsv.gz", sep="\t", header=None)[0].values
        frac = L.max(0) / np.maximum(L.sum(0), 1)
        cl = np.where(frac >= a.label_frac, lab[L.argmax(0)], "unassigned")
        cells = keep[cl == a.condition]
        Xc = X[:, cells].T.tocsr().astype(np.float64)                 # cells x genes
        G = sio.mmread(p + "guides_matrix.mtx.gz").tocsc()[:, cells]
        gtarget = pd.read_csv(p + "guides_features.tsv.gz", sep="\t", header=None)[0].str.rsplit("_", n=1).str[0].values
        if targets is None:
            targets = np.unique(gtarget)
            genes = pd.read_csv(p + "transcriptome_features.tsv.gz", sep="\t", header=None)[1].astype(str).values
            tot = np.zeros((len(targets), Xc.shape[1])); ncells = np.zeros(len(targets)); liball = np.zeros(Xc.shape[1])
        tidx = np.searchsorted(targets, gtarget)
        Gb = (G >= a.guide_min).astype(np.float64)                    # guides x cells
        T = sp.csr_matrix((np.ones(len(tidx)), (tidx, np.arange(len(tidx)))), shape=(len(targets), len(tidx)))
        C = (T @ Gb); C.data[:] = 1.0                                 # targets x cells, carries >= 1 guide
        tot += (C @ Xc).toarray()
        ncells += np.asarray(C.sum(1)).ravel()
        liball += np.asarray(Xc.sum(0)).ravel(); nall += len(cells)
        print(f"{os.path.basename(p)} cells>={a.min_umi}: {len(keep)}  {a.condition}: {len(cells)}", flush=True)
    rows = np.vstack([tot, liball[None, :]]).astype(np.float32)
    obs = pd.DataFrame({"target": list(targets) + ["all_cells"],
                        "ncells": np.r_[ncells, nall].astype(np.int64)})
    obs.index = obs.index.astype(str)
    out = ad.AnnData(X=sp.csr_matrix(rows), obs=obs, var=pd.DataFrame(index=pd.Index(genes).astype(str)))
    out.var_names_make_unique()
    out.write_h5ad(a.out)
    print(f"wrote {a.out}: {len(targets)} targets, {nall} {a.condition} cells, "
          f"median cells/target {np.median(ncells):.0f}")


if __name__ == "__main__":
    main()
