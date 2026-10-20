#!/usr/bin/env bash
# E051 (docs/16 §10): MSE-optimal E021/B5 blend weight, w = 0.10-0.25, on the 5-line V* and H1-R400.
#   tmux new -d -s E051 "bash scripts/run_E051.sh 2>&1 | tee logs/E051.log"
set -uo pipefail
source ~/.vcc_env; cd ~/vcc; mkdir -p results/E051 logs
H="--config loco.json --holdout H1 --mode seen --out $DATA/loco/E037 --seed 0 --holdout-tag R400 --min-target-cells 400 --umi-target 20000"
( python -m vcc26.loco $H --specs specs_E051.json --tag E051h || echo "FAILED H1 E051" ) > logs/E051h.log 2>&1 &
HPID=$!
bash scripts/vstar_par.sh specs_E051.json E051 0 results/E051 || echo "FAILED E051"
wait $HPID
cp $DATA/loco/E037/scores_H1_R400_seen_E051h.csv results/E051/ || echo "FAILED copying H1 rows"
echo "E051 runs done $(date -u)"
