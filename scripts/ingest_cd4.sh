#!/usr/bin/env bash
# CD4+ T cell genome-scale CRISPRi (Zhu, Dann et al., Cell 2026). Run inside tmux.
#   ingest_cd4.sh pb      per-condition summaries from the all-donor pseudobulk file
#   ingest_cd4.sh subset  holdout subsets from donor D4's single-cell files (needs the cells download)
# Logs: logs/ingest_CD4T_<step>.log
source ~/.vcc_env; cd ~/vcc
R=$DATA/scratch/CD4T_Marson2026; C=$DATA/scratch/CD4T_Marson2026_cells
AX=$DATA/challenge/controls/gene_axis.csv; PF=$DATA/challenge/controls/pert_counts.csv
step=$1; log=logs/ingest_CD4T_$step.log
exec >> $log 2>&1
echo "== $step start $(date -u +%FT%TZ)"
if [ "$step" = pb ]; then
  for c in Rest Stim8hr Stim48hr; do
    python -m vcc26.pseudobulk --h5ad $R/GWCD4i.pseudobulk_merged.h5ad --pert-col perturbed_gene_name \
      --control NTC --gene-axis $AX --symbol-col gene_name --weight-col n_cells \
      --where culture_condition=$c --out $DATA/pb/CD4T_$c.npz --min-cells 25 --max-kd 0.7 || exit 1
  done
elif [ "$step" = subset ]; then
  # guide -> curated target label (authors curate targets post hoc; cell files carry pre-curation names)
  python - <<'EOF' || exit 1
import anndata as ad, os, pandas as pd
R = os.environ['DATA'] + "/scratch/CD4T_Marson2026"
o = ad.read_h5ad(f"{R}/GWCD4i.pseudobulk_merged.h5ad", backed="r").obs[["guide_id", "perturbed_gene_name", "guide_type"]]
o = o.drop_duplicates("guide_id").set_index("guide_id")
lab = o.perturbed_gene_name.astype(str).where(o.guide_type != "non-targeting", "non-targeting")
lab.rename("label").to_csv(f"{R}/guide_to_target.csv")
print("guides", len(lab), "NTC", (lab == "non-targeting").sum())
EOF
  for c in Rest Stim8hr Stim48hr; do
    python scripts/make_subset.py --h5ad $C/cells/D4_$c.assigned_guide.h5ad --pert-col perturbed_gene_name \
      --control non-targeting --gene-axis $AX --panel-file $PF --symbol-col gene_name \
      --label-map $R/guide_to_target.csv --map-col guide_id --where low_quality=False \
      --keep-obs guide_id,lane_id,total_counts --out $DATA/subsets/CD4T_$c.h5ad || exit 1
  done
fi
echo "== $step exit 0 $(date -u +%FT%TZ)"
