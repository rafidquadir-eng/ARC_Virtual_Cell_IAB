"""Read remote HDF5 / h5ad files over HTTP byte ranges (h5py on a file-like object).

Used for headers and obs of large public h5ad files (S3, figshare) without downloading them, and
for pulling selected CSR rows (cells) out of them.
"""
import io
import urllib.request
from concurrent.futures import ThreadPoolExecutor

import h5py
import numpy as np

UA = {"User-Agent": "Mozilla/5.0"}


def _get(url, a, b, timeout=120):
    req = urllib.request.Request(url, headers={"Range": f"bytes={a}-{b}", **UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.geturl(), r.headers.get("Content-Range"), r.read()


class RangeFile(io.RawIOBase):
    def __init__(self, url, block=4 << 20, max_blocks=512):
        self.orig = url
        self._resolve()
        self.pos, self.block, self.max_blocks, self.cache, self.nbytes = 0, block, max_blocks, {}, 0

    def _resolve(self):  # follows redirects; presigned targets (figshare) expire, so re-resolve on error
        self.url, cr, _ = _get(self.orig, 0, 0)
        self.size = int(cr.split("/")[1])

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.size + off)
        return self.pos

    def fetch(self, a, b):
        """Bytes [a, b] inclusive, with retries."""
        for t in range(6):
            try:
                c = _get(self.url, a, b)[2]
                self.nbytes += len(c)
                return c
            except Exception:
                if t == 5:
                    raise
                self._resolve()

    def _blk(self, i):
        if i not in self.cache:
            a = i * self.block
            self.cache[i] = self.fetch(a, min(self.size, a + self.block) - 1)
            if len(self.cache) > self.max_blocks:
                self.cache.pop(next(iter(self.cache)))
        return self.cache[i]

    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        out = bytearray()
        while len(out) < n:
            p = self.pos + len(out)
            i, o = divmod(p, self.block)
            out += self._blk(i)[o:o + n - len(out)]
        b[:n] = out
        self.pos += n
        return n


def open_remote(url):
    f = RangeFile(url)
    return f, h5py.File(f, "r")


def read_cat(g):
    """An obs/var column (categorical group or plain dataset) as an object array of str."""
    if isinstance(g, h5py.Group):
        cats = np.array([c.decode() if isinstance(c, bytes) else c for c in g["categories"][:]], dtype=object)
        return cats[g["codes"][:]]
    v = g[:]
    return np.array([x.decode() if isinstance(x, bytes) else x for x in v], dtype=object)


def dataset_ranges(f, ds, items):
    """Contiguous-dataset element runs [(start, stop)] -> list of numpy arrays, fetched in parallel."""
    off, dt = ds.id.get_offset(), ds.dtype
    if off is None:
        raise ValueError(f"{ds.name} is chunked/compressed; byte-range row reads need contiguous storage")
    def one(r):
        s, e = r
        if e <= s:
            return np.zeros(0, dt)
        return np.frombuffer(f.fetch(off + s * dt.itemsize, off + e * dt.itemsize - 1), dtype=dt)
    with ThreadPoolExecutor(16) as ex:
        return list(ex.map(one, items))


def csr_rows(f, h, rows, max_gap=64):
    """Selected rows of a CSR X as (data, indices, indptr) in the order of sorted rows."""
    rows = np.sort(np.asarray(rows))
    indptr = h["X/indptr"][:]
    # merge nearby rows into runs to cut request count
    runs, s = [], rows[0]
    prev = s
    for r in rows[1:]:
        if r - prev > max_gap:
            runs.append((s, prev + 1)); s = r
        prev = r
    runs.append((s, prev + 1))
    spans = [(int(indptr[a]), int(indptr[b])) for a, b in runs]
    data = dataset_ranges(f, h["X/data"], spans)
    idx = dataset_ranges(f, h["X/indices"], spans)
    want = set(rows.tolist())
    D, I, P = [], [], [0]
    for (a, b), (s0, _), d, ix in zip(runs, spans, data, idx):
        for r in range(a, b):
            if r in want:
                lo, hi = int(indptr[r]) - s0, int(indptr[r + 1]) - s0
                D.append(d[lo:hi]); I.append(ix[lo:hi]); P.append(P[-1] + hi - lo)
    return rows, np.concatenate(D), np.concatenate(I), np.array(P)
