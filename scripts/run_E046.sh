#!/usr/bin/env bash
# E046 (docs/07, docs/16 §4): lever sweep on the 5-line V* and H1-R400, renorm variants, same-line proxy.
#   tmux new -d -s E046 "bash scripts/run_E046.sh [b3] 2>&1 | tee logs/E046.log"
# Pass "b3" if E045 adopted balanced3 (uses specs_E046b3.json, specs_E046rb3.json, specs_E046sameb3.json).
set -uo pipefail
source ~/.vcc_env; cd ~/vcc; mkdir -p results/E046 logs
SUF=${1:-}
for f in specs_E046$SUF.json specs_E046r$SUF.json specs_E046same$SUF.json; do [ -f $f ] || { echo "missing $f"; exit 2; }; done
H="--config loco.json --holdout H1 --mode seen --out $DATA/loco/E037 --seed 0 --holdout-tag R400 --min-target-cells 400 --umi-target 20000"
(
  python -m vcc26.loco $H --specs specs_E046$SUF.json --tag E046h || echo "FAILED H1 E046"
  VCC_RENORM_AXIS=1 python -m vcc26.loco $H --specs specs_E046r$SUF.json --tag E046hr || echo "FAILED H1 E046r"
) > logs/E046h.log 2>&1 &
HPID=$!
bash scripts/vstar_par.sh specs_E046$SUF.json E046 0 results/E046 || echo "FAILED E046"
VCC_RENORM_AXIS=1 bash scripts/vstar_par.sh specs_E046r$SUF.json E046r 0 results/E046 || echo "FAILED E046r"
VSTAR_LINES=CD4T_Stim8hr bash scripts/vstar_par.sh specs_E046same$SUF.json E046same 0 results/E046 \
  --allow-same-line CD4T_Stim48hr,CD4T_Rest || echo "FAILED E046same"
wait $HPID
cp $DATA/loco/E037/scores_H1_R400_seen_E046h.csv $DATA/loco/E037/scores_H1_R400_seen_E046hr.csv results/E046/ || echo "FAILED copying H1 rows"
grep FAILED logs/E046h.log || true
echo "E046 runs done $(date -u)"
