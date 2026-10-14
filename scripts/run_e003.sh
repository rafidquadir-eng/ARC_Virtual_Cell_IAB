#!/usr/bin/env bash
# usage: run_e003.sh <ctx>   (E003 anchors for one held-out context)
source ~/.vcc_env; cd ~/vcc; ctx=$1; log=logs/E003_${ctx}.log
echo "== E003 $ctx start $(date -u +%T)" > $log
/usr/bin/time -f "== E003 $ctx wall %e s" python -m vcc26.loco --config loco.json --holdout $ctx --mode seen \
  --out $DATA/loco/E003 --specs specs_B0.json >> $log 2>&1
echo "== E003 $ctx exit $?" >> $log
