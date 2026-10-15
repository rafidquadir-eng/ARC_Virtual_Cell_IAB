"""Convert Feng et al. 2025 (HipSci iPSC CRISPRi) dense gene x cell count CSVs to one h5ad.

Rows of each *_RNA-UMI-Counts.csv.gz are genes ("ENSG:SYMBOL:Gene-Expression"), columns are cells.
obs `target` = gene from Guide_Call (GENE_guideseq); NonTarget guides and cells with no assigned
guide ("unassigned", used as controls in the paper) become "non-targeting".

  python scripts/convert_feng.py <dir with figshare 27989294 files> <out.h5ad> [screen ...]
"""
import multiprocessing as mp
import shutil
import subprocess
import sys

import anndata as ad
import numpy as np
import pandas as pd
import scipy.sparse as sp


def _parse(line):
    name, _, rest = line.partition(",")
    v = np.fromstring(rest, dtype=np.int32, sep=",")
    nz = np.flatnonzero(v)
    return name, nz.astype(np.int32), v[nz]


def one(d, screen, procs=24):
    meta = pd.read_csv(f"{d}/{screen}_Cell-Metadata.tsv.gz", sep="\t").set_index("Cell_ID")
    zc = subprocess.Popen(["pigz" if shutil.which("pigz") else "gzip", "-dc", f"{d}/{screen}_RNA-UMI-Counts.csv.gz"],
                          stdout=subprocess.PIPE, text=True, bufsize=1 << 24)
    cols = pd.Index(zc.stdout.readline().rstrip("\n").split(",")[1:])
    genes, rows, data, ptr = [], [], [], [0]
    with mp.Pool(procs) as pool:
        for name, nz, v in pool.imap(_parse, (l.rstrip("\n") for l in zc.stdout), chunksize=16):
            genes.append(name); rows.append(nz); data.append(v); ptr.append(ptr[-1] + len(nz))
            if len(genes) % 2000 == 0:
                print(screen, len(genes), flush=True)
    zc.wait()
    # genes x cells CSR -> cells x genes
    G = sp.csr_matrix((np.concatenate(data).astype(np.float32), np.concatenate(rows), np.array(ptr, np.int64)),
                      shape=(len(genes), len(cols)))
    X = G.T.tocsr()  # cells x genes
    g = pd.Series(genes).str.split(":", expand=True)
    var = pd.DataFrame({"gene_ids": g[0].values, "gene_name": g[1].values}, index=g[0].values)
    obs = meta.reindex(cols)
    call = obs["Guide_Call"].astype(str)
    tgt = call.str.rsplit("_", n=1).str[0]
    tgt[(call == "unassigned") | tgt.str.startswith("NonTarget")] = "non-targeting"
    obs = pd.DataFrame({"target": tgt.values, "guide": call.values, "cell_line": obs["Cell_Line"].astype(str).values,
                        "batch": obs["Batch"].astype(str).values, "screen": screen}, index=np.asarray(cols, str))
    return ad.AnnData(X=X, obs=obs, var=var)


def main():
    d, out = sys.argv[1], sys.argv[2]
    screens = sys.argv[3:] or ["GenomeWideScreen_FitnessGenes", "GenomeWideScreen_NonFitnessGenes", "TargetedScreen"]
    parts = [one(d, s) for s in screens]
    a = ad.concat(parts, join="inner", merge="first")
    a.obs_names_make_unique()
    a.write_h5ad(out)
    vc = a.obs.target.value_counts()
    print(f"{out}: {a.shape}, {len(vc) - 1} targets, {vc.get('non-targeting', 0)} controls")


if __name__ == "__main__":
    main()
