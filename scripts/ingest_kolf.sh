#!/usr/bin/env bash
# KOLF2.1J hiPSC genome-scale CRISPRi (Nourreddine, Doctor et al., Nat Biotechnol 2026). Run inside tmux.
# X holds raw counts (identical to layers/counts), stored CSC. Log: logs/ingest_KOLF2.1J_iPSC.log
source ~/.vcc_env; cd ~/vcc
F=$DATA/scratch/KOLF2.1J_iPSC/KOLF_Pan_Genome_QC_Filtered.h5ad
AX=$DATA/challenge/controls/gene_axis.csv; PF=$DATA/challenge/controls/pert_counts.csv
exec >> logs/ingest_KOLF2.1J_iPSC.log 2>&1
echo "== start $(date -u +%FT%TZ)"
python -m vcc26.pseudobulk --h5ad $F --pert-col gene_target --control NTC --gene-axis $AX \
  --out $DATA/pb/KOLF2.1J.npz --min-cells 25 --max-kd 0.7 || exit 1
python scripts/make_subset.py --h5ad $F --pert-col gene_target --control NTC --gene-axis $AX \
  --panel-file $PF --keep-obs gRNA,channel,batch,total_counts --out $DATA/subsets/KOLF2.1J.h5ad || exit 1
echo "== exit 0 $(date -u +%FT%TZ)"
