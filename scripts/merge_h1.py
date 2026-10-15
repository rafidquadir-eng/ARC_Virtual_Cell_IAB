"""Merge the VCC 2025 H1 train, validation and test h5ads into one (all ~300 perturbations).

The splits share their non-targeting cells; duplicates (same obs name) are kept once.

  python scripts/merge_h1.py <train.h5ad> <validation.h5ad> <test.h5ad> <out.h5ad>
"""
import sys

import anndata as ad
import numpy as np

parts = []
seen = set()
for path, split in zip(sys.argv[1:4], ["train", "validation", "test"]):
    a = ad.read_h5ad(path)
    a.obs = a.obs[["target_gene", "guide_id", "batch"]].copy()
    a.obs["split"] = split
    keep = ~np.isin(a.obs_names, list(seen))
    print(f"{split}: {a.n_obs} cells, {keep.sum()} new, {a.obs.target_gene.nunique()} labels")
    seen.update(a.obs_names)
    parts.append(a[keep].copy())
m = ad.concat(parts, join="inner", merge="same")
assert m.obs_names.is_unique
m.write_h5ad(sys.argv[4])
vc = m.obs.target_gene.value_counts()
print(f"{sys.argv[4]}: {m.shape}, {len(vc) - 1} perturbations, {vc.get('non-targeting', 0)} controls")
