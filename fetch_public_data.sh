#!/usr/bin/env bash
# Download public CRISPRi Perturb-seq data and build per-context summaries on the challenge gene axis.
# Run on the instance after setup_lambda.sh.  Disk: ~150-250 GB peak with K562 genome-wide.
# Every source below is verified in the plan's dataset table except where marked UNVERIFIED --
# the script prints file lists first so we can confirm names/sizes before the big pulls.
set -euo pipefail
WORK=${WORK:-$(cd "$(dirname "$0")" && pwd)}
source "$WORK/.venv/bin/activate"; export PYTHONPATH="$WORK/src"; export PATH="$HOME/.local/bin:$PATH"
FS=$(ls -d /lambda/nfs/*/ 2>/dev/null | head -1 || true)
DATA=${DATA:-${FS:+${FS%/}/vcc-data}}; DATA=${DATA:-$HOME/vcc-data}
RAW=$DATA/raw; PB=$DATA/pb; mkdir -p "$RAW" "$PB"
AXIS=$(find "$DATA/challenge/controls" -name 'gene_names*.csv' 2>/dev/null | head -1 || true)
[ -n "$AXIS" ] || { echo "gene_names.csv not found under challenge/controls -- run setup first"; exit 1; }

echo "== Replogle et al. 2022 (Cell) -- figshare article 20029387, CC BY 4.0"
curl -s https://api.figshare.com/v2/articles/20029387/files | jq -r '.[] | "\(.size)\t\(.name)\t\(.download_url)"' \
  | tee "$RAW/replogle_files.tsv"
# Raw single-cell files for essential-scale K562 and RPE1 (genome-wide K562 is optional, ~10x larger):
for pat in "K562_essential_raw_singlecell" "rpe1_raw_singlecell"; do
  url=$(grep -i "$pat" "$RAW/replogle_files.tsv" | grep -i h5ad | head -1 | cut -f3)
  name=$(grep -i "$pat" "$RAW/replogle_files.tsv" | grep -i h5ad | head -1 | cut -f2)
  [ -n "$url" ] && [ ! -f "$RAW/$name" ] && aria2c -x8 -s8 -d "$RAW" -o "$name" "$url"
done
if [ "${WITH_GWPS:-0}" = "1" ]; then   # K562 genome-wide: covers ~9.8k expressed targets
  url=$(grep -i "K562_gwps_raw_singlecell" "$RAW/replogle_files.tsv" | grep -i h5ad | head -1 | cut -f3)
  name=$(grep -i "K562_gwps_raw_singlecell" "$RAW/replogle_files.tsv" | grep -i h5ad | head -1 | cut -f2)
  [ -n "$url" ] && [ ! -f "$RAW/$name" ] && aria2c -x8 -s8 -d "$RAW" -o "$name" "$url"
fi

echo "== Nadig et al. 2025 HepG2 + Jurkat (+ Replogle lines) -- HF arcinstitute/Replogle-Nadig (UNVERIFIED: file list, license, raw vs HVG)"
python - <<'EOF'
from huggingface_hub import list_repo_files
try:
    for f in list_repo_files("arcinstitute/Replogle-Nadig", repo_type="dataset"): print(f)
except Exception as e: print("HF listing failed:", e)
EOF
echo "   -> pick the raw-count, full-gene HepG2 and Jurkat files from the list above, then e.g.:"
echo "   huggingface-cli download arcinstitute/Replogle-Nadig <file> --repo-type dataset --local-dir $RAW/nadig"
echo "   If HF only has HVG-filtered matrices, use GEO GSE264667 raw counts instead (UNVERIFIED accession)."

echo "== VCC 2025 H1 (train+val+test, now public via Arc Virtual Cell Atlas) -- UNVERIFIED download path"
echo "   Get the link from https://arcinstitute.org/tools/virtualcellatlas and save under $RAW/h1_2025/"

echo "== Summaries (only for files present). Adjust --pert-col / --symbol-col after a quick look:"
echo "   python -c \"import anndata as ad;a=ad.read_h5ad('<file>',backed='r');print(a.obs.columns.tolist(), a.var.columns.tolist())\""
summ () {  # name file pert_col control [symbol_col]
  [ -f "$2" ] || { echo "skip $1 (missing $2)"; return; }
  [ -f "$PB/$1.npz" ] && { echo "have $PB/$1.npz"; return; }
  python -m vcc26.pseudobulk --h5ad "$2" --pert-col "$3" --control "$4" --gene-axis "$AXIS" \
     ${5:+--symbol-col $5} --max-kd 0.7 --out "$PB/$1.npz"
}
# Replogle raw files: obs 'gene' holds the target symbol, controls are 'non-targeting',
# var 'gene_name' holds symbols (var_names are Ensembl IDs) -- confirm with the one-liner above.
summ K562 "$(find "$RAW" -maxdepth 1 -iname 'K562_essential_raw_singlecell*.h5ad' | head -1)" gene non-targeting gene_name
summ RPE1 "$(find "$RAW" -maxdepth 1 -iname 'rpe1_raw_singlecell*.h5ad' | head -1)" gene non-targeting gene_name
rclone listremotes 2>/dev/null | grep -q "^gdrive:" && rclone copy "$PB" gdrive:VCC2026/summaries/ --include "*.npz" || true
echo "== GENCODE TSS table for A2 neighbour silencing (GENCODE v46 basic; release number unverified on this mirror)"
if [ ! -f "$DATA/tss.csv" ]; then
  aria2c -x4 -d "$RAW" -o gencode.basic.gtf.gz \
    https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/release_46/gencode.v46.basic.annotation.gtf.gz \
    && python -m vcc26.neighbors build-tss --gtf "$RAW/gencode.basic.gtf.gz" --out "$DATA/tss.csv" \
    || echo "!! GENCODE download failed: check the release folder at https://ftp.ebi.ac.uk/pub/databases/gencode/Gencode_human/"
fi
echo "== done"; du -sh "$RAW" "$PB"
