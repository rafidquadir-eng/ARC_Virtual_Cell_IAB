"""A2: CRISPRi neighbour silencing.

dCas9-KRAB at a target's promoter also represses genes whose TSS is close by (bidirectional and
shared promoters). The scorer excludes only the target gene itself, so silenced neighbours are scored.

Two pieces:
  build_tss(gtf)       GENCODE GTF -> per-gene canonical TSS table (gene, chrom, tss, strand)
  NeighborPrior        learns, from the public screens, how strongly neighbours at each distance
                       are knocked down (mean log2FC by distance bin), then predicts that effect for
                       any target in a new line, gated by whether the neighbour is expressed there.

  python -m vcc26.neighbors build-tss --gtf gencode.v46.basic.annotation.gtf.gz --out tss.csv
  python -m vcc26.neighbors learn --tss tss.csv --summaries pb/*.npz --out neighbor_prior.json
"""
from __future__ import annotations

import argparse
import gzip
import json

import numpy as np
import pandas as pd

BINS = [0, 500, 1000, 2000, 5000]          # bp; bin i = [BINS[i], BINS[i+1])


def build_tss(gtf: str) -> pd.DataFrame:
    """One TSS per gene symbol: the 'gene' record's 5' end (start on +, end on -)."""
    rows = []
    op = gzip.open if gtf.endswith(".gz") else open
    with op(gtf, "rt") as fh:
        for line in fh:
            if line.startswith("#"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 9 or f[2] != "gene":
                continue
            attrs = f[8]
            if 'gene_type "protein_coding"' not in attrs and 'gene_type "lncRNA"' not in attrs:
                continue
            name = attrs.split('gene_name "')[1].split('"')[0]
            tss = int(f[3]) if f[6] == "+" else int(f[4])
            rows.append((name, f[0], tss, f[6]))
    df = pd.DataFrame(rows, columns=["gene", "chrom", "tss", "strand"])
    return df.drop_duplicates("gene", keep="first").reset_index(drop=True)


def neighbor_pairs(tss: pd.DataFrame, genes_axis, max_bp: int = BINS[-1]) -> dict[str, list[tuple[str, int]]]:
    """{gene: [(neighbour, distance_bp), ...]} for neighbours on the axis within max_bp."""
    on_axis = set(genes_axis)
    t = tss[tss["gene"].isin(on_axis)].sort_values(["chrom", "tss"])
    out: dict[str, list] = {}
    for _, grp in t.groupby("chrom"):
        g, x = grp["gene"].values, grp["tss"].values
        for i in range(len(g)):
            j = i + 1
            while j < len(g) and x[j] - x[i] <= max_bp:
                d = int(x[j] - x[i])
                out.setdefault(g[i], []).append((g[j], d))
                out.setdefault(g[j], []).append((g[i], d))
                j += 1
    return out


_PAIR_CACHE: dict = {}


def load_pairs(tss_csv: str, genes_axis) -> dict:
    """Cached neighbor_pairs for a TSS csv and gene axis."""
    key = (tss_csv, len(genes_axis), str(genes_axis[0]) if len(genes_axis) else "")
    if key not in _PAIR_CACHE:
        _PAIR_CACHE[key] = neighbor_pairs(pd.read_csv(tss_csv), genes_axis)
    return _PAIR_CACHE[key]


def _bin(d: int) -> int:
    for i in range(len(BINS) - 1):
        if BINS[i] <= d < BINS[i + 1]:
            return i
    return -1


class NeighborPrior:
    """Mean neighbour log2FC per distance bin, learned from measured targets in source screens."""

    def __init__(self, bin_lfc: list[float], bin_n: list[int]):
        self.bin_lfc, self.bin_n = list(bin_lfc), list(bin_n)

    @classmethod
    def learn(cls, sources: list[dict], pairs: dict, min_ctrl_cpm: float = 5.0):
        acc = [[] for _ in range(len(BINS) - 1)]
        for s in sources:
            pos = {g: i for i, g in enumerate(s["genes"])}
            for r, t in enumerate(s["perts"]):
                for nb, d in pairs.get(t, []):
                    j = pos.get(nb)
                    b = _bin(d)
                    if j is None or b < 0 or s["ctrl_cpm"][j] < min_ctrl_cpm or not s["present"][j]:
                        continue
                    acc[b].append(float(s["lfc"][r, j]))
        lfc = [float(np.median(a)) if len(a) >= 20 else 0.0 for a in acc]   # robust; 0 if too few
        return cls(lfc, [len(a) for a in acc])

    def predict(self, targets, genes, pairs, target_ctrl_cpm=None, gate_cpm: float = 5.0,
                only_negative: bool = True) -> dict[int, list[tuple[int, float]]]:
        """{row: [(gene_index, lfc), ...]} neighbour knockdowns for each target row."""
        pos = {g: i for i, g in enumerate(genes)}
        out = {}
        for r, t in enumerate(targets):
            eff = []
            for nb, d in pairs.get(t, []):
                b = _bin(d); j = pos.get(nb)
                if b < 0 or j is None:
                    continue
                v = self.bin_lfc[b]
                if only_negative and v >= 0:
                    continue
                gate = 1.0 if target_ctrl_cpm is None else float(np.clip(target_ctrl_cpm[j] / gate_cpm, 0, 1))
                eff.append((j, v * gate))
            if eff:
                out[r] = eff
        return out

    def to_json(self, path: str):
        json.dump({"bins_bp": BINS, "bin_lfc": self.bin_lfc, "bin_n": self.bin_n}, open(path, "w"), indent=2)

    @classmethod
    def from_json(cls, path: str):
        d = json.load(open(path))
        return cls(d["bin_lfc"], d["bin_n"])


def apply_neighbors(lfc: np.ndarray, effects: dict, mode: str = "min") -> np.ndarray:
    """Add neighbour knockdowns to a predicted log2FC matrix.
    mode 'min': take the stronger repression of (existing prediction, neighbour prior), so a
    neighbour effect already present in transferred data is not double-counted."""
    out = lfc.copy()
    for r, eff in effects.items():
        for j, v in eff:
            out[r, j] = min(out[r, j], v) if mode == "min" else out[r, j] + v
    return out


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build-tss"); b.add_argument("--gtf", required=True); b.add_argument("--out", required=True)
    l = sub.add_parser("learn"); l.add_argument("--tss", required=True)
    l.add_argument("--summaries", nargs="+", required=True); l.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "build-tss":
        df = build_tss(a.gtf); df.to_csv(a.out, index=False); print(f"{a.out}: {len(df)} genes")
    else:
        from .pseudobulk import load
        srcs = [load(p) for p in a.summaries]
        tss = pd.read_csv(a.tss)
        prior = NeighborPrior.learn(srcs, neighbor_pairs(tss, srcs[0]["genes"]))
        prior.to_json(a.out)
        print(json.dumps({"bins_bp": BINS, "bin_lfc": prior.bin_lfc, "bin_n": prior.bin_n}))


if __name__ == "__main__":
    main()
