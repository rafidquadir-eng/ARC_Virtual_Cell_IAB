#!/usr/bin/env bash
# CD4+ T cell holdout subsets, one condition at a time on LOCAL disk (the network filesystem is too
# slow for concurrent 100+ GB writes): download donor D4's cell file from the public S3 bucket ->
# subset -> archive the raw file to gdrive:VCC2026/data/raw/CD4T_Marson2026_cells/cells -> check -> delete.
# ARCHIVE=0 skips the Drive copy (files stay re-pullable from the authors' public S3 bucket).
# Needs $DATA/scratch/CD4T_Marson2026/guide_to_target.csv (scripts/ingest_cd4.sh subset writes it) or
# the pseudobulk file to build it. Run inside tmux. Log: logs/data_CD4T_Marson2026_cells.log
source ~/.vcc_env; cd ~/vcc
L=${LOCAL_SCRATCH:-$HOME/scratch_local}/CD4T_cells; mkdir -p $L
B=https://genome-scale-tcell-perturb-seq.s3.amazonaws.com/marson2025_data
AX=$DATA/challenge/controls/gene_axis.csv; PF=$DATA/challenge/controls/pert_counts.csv
MAP=$DATA/pb/CD4T_guide_to_target.csv; log=logs/data_CD4T_Marson2026_cells.log
say() { echo "[$(date -u +%FT%TZ)] $*" | tee -a $log; }
if [ ! -s $MAP ]; then
  python - $MAP <<'EOF' >> $log 2>&1 || { echo "FAILED guide map" >> $log; exit 1; }
import anndata as ad, os, sys
o = ad.read_h5ad(os.environ['DATA'] + "/scratch/CD4T_Marson2026/GWCD4i.pseudobulk_merged.h5ad", backed="r").obs
o = o[["guide_id", "perturbed_gene_name", "guide_type"]].drop_duplicates("guide_id").set_index("guide_id")
lab = o.perturbed_gene_name.astype(str).where(o.guide_type != "non-targeting", "non-targeting")
lab.rename("label").to_csv(sys.argv[1]); print("guides", len(lab), "NTC", (lab == "non-targeting").sum())
EOF
fi
for c in ${CONDS:-Rest Stim8hr Stim48hr}; do
  f=D4_$c.assigned_guide.h5ad; t0=$(date +%s)
  if [ ! -s $DATA/subsets/CD4T_$c.h5ad ]; then
    aria2c -c -x16 -s16 -k16M --auto-file-renaming=false --console-log-level=warn --show-console-readout=false \
      -d $L -o $f $B/$f >> $log 2>&1 || { say "FAILED download $f"; exit 1; }
    say "got $f $(du -h $L/$f | cut -f1) in $(( ($(date +%s)-t0)/60 )) min"
    python scripts/make_subset.py --h5ad $L/$f --pert-col perturbed_gene_name --control non-targeting \
      --gene-axis $AX --panel-file $PF --symbol-col gene_name --label-map $MAP --map-col guide_id \
      --where low_quality=False --keep-obs guide_id,lane_id,total_counts --out $DATA/subsets/CD4T_$c.h5ad >> $log 2>&1 \
      || { say "FAILED subset $c"; exit 1; }
    say "subset $c done"
  fi
  if [ -s $L/$f ] && [ "${ARCHIVE:-1}" = 0 ]; then
    say "not archived (ARCHIVE=0; source of record: $B/$f)"; rm -f $L/$f
  elif [ -s $L/$f ]; then
    rclone copy --stats 300s --stats-one-line -v --drive-chunk-size 256M $L/$f gdrive:VCC2026/data/raw/CD4T_Marson2026_cells/cells >> $log 2>&1 \
      && rclone check --size-only $L gdrive:VCC2026/data/raw/CD4T_Marson2026_cells/cells --include $f >> $log 2>&1 \
      && { say "rclone check OK $f"; rm -f $L/$f; } || { say "FAILED archive $f"; exit 3; }
  fi
  say "done $c in $(( ($(date +%s)-t0)/60 )) min"
done
say "ALL DONE"
