#!/usr/bin/env bash
# Final-test pipeline (dress rehearsal on A,B,C; real run on D,E,F once released). Does NOT submit.
#   bash scripts/final_pipeline.sh <controls_dir> <contexts> <specs.json> <spec name> <tag> [nc=on|off]
# Writes $DATA/preds/<tag>_nc<on|off>.h5ad / .vcc, reports/<tag>_nc<on|off>_context_id.json and logs/<tag>_nc<on|off>_*.log; prints timings.
set -euo pipefail
source ~/.vcc_env; cd ~/vcc
CTRL=$1; CTX=$2; SPECS=$3; SPEC=$4; TAG=$5; NC=${6:-on}
AXIS=$DATA/challenge/controls/gene_axis.csv
PANEL=$(find $(dirname $CTRL) $CTRL -maxdepth 2 -name pert_counts.csv | head -1)
SUMS=$(python -c "import json;print(' '.join(c['summary'] for c in json.load(open('loco.json'))['contexts']))")
EXCL=""; [ "$NC" = off ] && EXCL="--exclude-licence NC"
RUN=${TAG}_nc${NC}          # every output of this run carries the NC suffix (E036: two runs with one tag overwrote logs)
t0=$(date +%s)
python -m vcc26.context_id --controls-dir $CTRL --contexts $CTX --gene-axis $AXIS --summaries $SUMS --out reports/${RUN}_context_id.json > logs/${RUN}_context_id.log
t1=$(date +%s)
python -m vcc26.predict_challenge --controls-dir $CTRL --contexts $CTX --perts $PANEL --gene-names $AXIS \
  --registry loco.json $EXCL --summaries $SUMS --spec-file $SPECS --spec "$SPEC" --n-control 0 \
  --out $DATA/preds/${TAG}_nc${NC}.h5ad 2>&1 | tee logs/${RUN}_predict.log
t2=$(date +%s)
vcc prep $DATA/preds/${TAG}_nc${NC}.h5ad -g $AXIS --perts $PANEL --contexts $CTX -o $DATA/preds/${TAG}_nc${NC}.vcc 2>&1 | tee logs/${RUN}_prep.log
t3=$(date +%s)
echo "context_id $((t1-t0)) s | predict $((t2-t1)) s | prep $((t3-t2)) s | total $((t3-t0)) s"
echo "ready: $DATA/preds/${TAG}_nc${NC}.vcc   (submit only per the runbook rules)"
