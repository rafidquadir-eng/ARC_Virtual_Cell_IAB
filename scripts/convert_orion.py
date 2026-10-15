"""X-Atlas/Orion parquet (HF Xaira-Therapeutics/X-Atlas-Orion) -> one backed-readable CSR h5ad per cell line.

Each parquet file is one GEM batch (`sample`); a row is a cell with sparse raw counts
(`gene_token_id`, `gene_expression`) indexed by metadata/gene_metadata.parquet. Keeps cells with
pass_guide_filter == 1 and genes whose symbol is on the challenge gene axis (first token per symbol).
Worker processes build one CSR block per file; the main process appends blocks to the h5ad on disk,
so memory stays at a few files' worth.

  python scripts/convert_orion.py --parquet-dir data --line HCT116 --gene-meta gene_metadata.parquet \
      --gene-axis gene_axis.csv --out HCT116.h5ad [--workers 12]
"""
import argparse
import glob
import os
from concurrent.futures import ProcessPoolExecutor

import anndata as ad
import h5py
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

OBS = ["cell_barcode", "sample", "gene_target", "guide_target", "num_features", "total_counts", "pct_counts_mt"]
TOK2COL = None


def _init(tok2col):
    global TOK2COL
    TOK2COL = tok2col


def block(path):
    t = pq.read_table(path, columns=OBS + ["gene_token_id", "gene_expression", "pass_guide_filter"])
    keep = np.asarray(t.column("pass_guide_filter").to_numpy(zero_copy_only=False)) == 1
    t = t.filter(keep)
    tok = t.column("gene_token_id").combine_chunks()
    val = t.column("gene_expression").combine_chunks()
    off = tok.offsets.to_numpy(); off = off - off[0]
    flat_t = tok.flatten().to_numpy()
    flat_v = val.flatten().to_numpy().astype(np.float32)
    col = TOK2COL[flat_t]
    m = col >= 0
    cm = np.concatenate([[0], np.cumsum(m)])
    indptr = cm[off].astype(np.int64)             # kept entries per row (rows are contiguous)
    col, v = col[m], flat_v[m]
    d = np.diff(col)
    if (d <= 0).any():                            # columns follow token order; re-sort only if unsorted
        row_end = indptr[1:-1]
        bad = np.ones(len(d), bool); bad[row_end[(row_end > 0) & (row_end < len(col))] - 1] = False
        if (d[bad] <= 0).any():
            row = np.repeat(np.arange(len(off) - 1), np.diff(indptr))
            o = np.lexsort((col, row)); col, v = col[o], v[o]
    obs = t.select(OBS).to_pandas()
    return path, obs, v, col.astype(np.int32), indptr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet-dir", required=True); ap.add_argument("--line", required=True)
    ap.add_argument("--gene-meta", required=True); ap.add_argument("--gene-axis", required=True)
    ap.add_argument("--out", required=True); ap.add_argument("--workers", type=int, default=12)
    a = ap.parse_args()
    files = sorted(glob.glob(f"{a.parquet_dir}/{a.line}_Batch*.parquet"),
                   key=lambda p: int(os.path.basename(p).split("Batch")[1].split(".")[0]))
    gm = pd.read_parquet(a.gene_meta)
    axis = pd.read_csv(a.gene_axis, header=None).iloc[:, 0].astype(str).values
    gm = gm[gm.gene_name.isin(set(axis))].sort_values("gene_token_id").drop_duplicates("gene_name")
    # column order = token order, so per-cell token lists (sorted) map to sorted CSR columns
    tok2col = np.full(int(pd.read_parquet(a.gene_meta).gene_token_id.max()) + 1, -1, np.int64)
    tok2col[gm.gene_token_id.values] = np.arange(len(gm))
    G = len(gm)
    print(f"{a.line}: {len(files)} files, {G} genes on the axis", flush=True)
    tmp = a.out + ".part"
    obs_parts, n, nnz = [], 0, 0
    with h5py.File(tmp, "w") as f:
        X = f.create_group("X")
        X.attrs["encoding-type"] = "csr_matrix"; X.attrs["encoding-version"] = "0.1.0"
        d = X.create_dataset("data", (0,), np.float32, maxshape=(None,), chunks=(1 << 20,))
        ix = X.create_dataset("indices", (0,), np.int32, maxshape=(None,), chunks=(1 << 20,))
        ip = X.create_dataset("indptr", (1,), np.int64, maxshape=(None,), chunks=(1 << 16,))
        ip[0] = 0
        with ProcessPoolExecutor(a.workers, initializer=_init, initargs=(tok2col,)) as ex:
            for i, (path, obs, v, col, indptr) in enumerate(ex.map(block, files)):
                k = len(v)
                d.resize((nnz + k,)); d[nnz:] = v
                ix.resize((nnz + k,)); ix[nnz:] = col
                ip.resize((n + len(obs) + 1,)); ip[n + 1:] = indptr[1:] + nnz
                nnz += k; n += len(obs)
                obs_parts.append(obs)
                if i % 10 == 0 or i == len(files) - 1:
                    print(f"  {i + 1}/{len(files)} {os.path.basename(path)}: cells {n:,} nnz {nnz:,}", flush=True)
        X.attrs["shape"] = np.array([n, G])
        obs = pd.concat(obs_parts, ignore_index=True)
        obs.index = obs.pop("cell_barcode").astype(str).values
        for c in ["sample", "gene_target", "guide_target"]:
            obs[c] = obs[c].astype("category")
        obs["line"] = a.line
        var = pd.DataFrame({"gene_name": gm.gene_name.values, "ensembl_id": gm.ensembl_id.values},
                           index=gm.gene_name.values)
        ad.io.write_elem(f, "obs", obs); ad.io.write_elem(f, "var", var)
        for k in ["uns", "obsm", "varm", "layers", "obsp", "varp"]:
            ad.io.write_elem(f, k, {})
        f.attrs["encoding-type"] = "anndata"; f.attrs["encoding-version"] = "0.1.0"
    os.replace(tmp, a.out)
    print(f"wrote {a.out}: {n:,} cells x {G} genes, nnz {nnz:,}", flush=True)


if __name__ == "__main__":
    main()
