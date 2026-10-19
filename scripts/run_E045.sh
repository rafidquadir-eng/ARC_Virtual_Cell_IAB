#!/usr/bin/env bash
# E045 (docs/07, docs/16): seed variance and emitter choice on the 5-line V*, plus the H1-R400 bracket, in parallel.
#   tmux new -d -s E045 "bash scripts/run_E045.sh 2>&1 | tee logs/E045.log"
# GPU processes at once: VSTAR_PAR (default 2) V* holdouts + 1 H1-R400 job.
set -uo pipefail
source ~/.vcc_env; cd ~/vcc; mkdir -p results/E045 logs
(
  for f in E045ref E045b3; do
    python -m vcc26.loco --config loco.json --holdout H1 --mode seen --out $DATA/loco/E037 --specs specs_$f.json \
      --tag ${f}h --seed 0 --holdout-tag R400 --min-target-cells 400 --umi-target 20000 || echo "FAILED H1 $f"
  done
) > logs/E045h.log 2>&1 &
HPID=$!
for s in 0 1 2; do bash scripts/vstar_par.sh specs_E045ref.json E045s$s $s results/E045 || echo "FAILED E045s$s"; done
for s in 0 1; do bash scripts/vstar_par.sh specs_E045b3.json E045b3s$s $s results/E045 || echo "FAILED E045b3s$s"; done
wait $HPID
cp $DATA/loco/E037/scores_H1_R400_seen_E045refh.csv $DATA/loco/E037/scores_H1_R400_seen_E045b3h.csv results/E045/ || echo "FAILED copying H1 rows"
grep FAILED logs/E045h.log || true
echo "E045 runs done $(date -u)"
