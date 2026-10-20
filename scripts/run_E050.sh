#!/usr/bin/env bash
# E050 (docs/07, docs/16 §9): blend+budget combinations (V* + H1-R400), apples-to-apples NC-off references,
# and two same-line proxies (K562_GWPS with K562 essential allowed; CD4T at higher weights).
#   tmux new -d -s E050 "bash scripts/run_E050.sh 2>&1 | tee logs/E050.log"
set -uo pipefail
source ~/.vcc_env; cd ~/vcc; mkdir -p results/E050 logs
H="--config loco.json --holdout H1 --mode seen --out $DATA/loco/E037 --seed 0 --holdout-tag R400 --min-target-cells 400 --umi-target 20000"
( python -m vcc26.loco $H --specs specs_E050.json --tag E050h || echo "FAILED H1 E050" ) > logs/E050h.log 2>&1 &
HPID=$!
bash scripts/vstar_par.sh specs_E050.json E050 0 results/E050 || echo "FAILED E050"
bash scripts/vstar_par.sh specs_E045ref.json E050nc0 0 results/E050 --exclude-licence NC || echo "FAILED E050nc0"
VSTAR_LINES=K562_GWPS bash scripts/vstar_par.sh specs_E050sameK562.json E050sameK562 0 results/E050 --allow-same-line K562 || echo "FAILED E050sameK562"
VSTAR_LINES=CD4T_Stim8hr bash scripts/vstar_par.sh specs_E050sameCD4T.json E050sameCD4T 0 results/E050 \
  --allow-same-line CD4T_Stim48hr,CD4T_Rest || echo "FAILED E050sameCD4T"
wait $HPID
cp $DATA/loco/E037/scores_H1_R400_seen_E050h.csv results/E050/ || echo "FAILED copying H1 rows"
grep FAILED logs/E050h.log || true
echo "E050 runs done $(date -u)"
