#!/usr/bin/env bash
# usage: run_e004.sh <ctx>   (E004 seen + E005 unseen baselines for one held-out context, reusing E003 anchors)
source ~/.vcc_env; cd ~/vcc; ctx=$1
mkdir -p $DATA/loco/E004
[ -d $DATA/loco/E004/holdout_$ctx ] || cp -r $DATA/loco/E003/holdout_$ctx $DATA/loco/E004/
for mode in seen unseen; do
  log=logs/E004_${ctx}_${mode}.log
  echo "== E004 $ctx $mode start $(date -u +%T)" >> $log
  python -m vcc26.loco --config loco.json --holdout $ctx --mode $mode --out $DATA/loco/E004 \
    --specs specs_baselines.json >> $log 2>&1
  echo "== E004 $ctx $mode exit $?" >> $log
done
