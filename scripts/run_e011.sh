#!/usr/bin/env bash
# usage: run_e011.sh <job>   job = a (K562_GWPS panel holdout, seen+unseen) | RPE1 | HepG2 | Jurkat | H1 (testlike + all)
source ~/.vcc_env; cd ~/vcc; job=$1; O=$DATA/loco/E011; mkdir -p $O
PANEL=$(find $DATA/challenge -name pert_counts.csv | head -1)
if [ "$job" = a ]; then
  for mode in seen unseen; do
    log=logs/E011_K562_GWPS_$mode.log; echo "== E011 K562_GWPS $mode start $(date -u +%T)" >> $log
    python -m vcc26.loco --config loco.json --holdout K562_GWPS --mode $mode --out $O \
      --panel-file $PANEL --specs specs_E011.json >> $log 2>&1
    echo "== E011 K562_GWPS $mode exit $?" >> $log
  done
else
  c=$job; [ -d $O/holdout_$c ] || cp -r $DATA/loco/E003/holdout_$c $O/
  for t in testlike all; do
    log=logs/E011_${c}_$t.log; echo "== E011 $c $t start $(date -u +%T)" >> $log
    if [ $t = testlike ]; then src="--sources K562_GWPS,H1"; else src=""; fi
    python -m vcc26.loco --config loco.json --holdout $c --mode seen --out $O \
      --specs specs_E011.json $src --tag $t >> $log 2>&1
    echo "== E011 $c $t exit $?" >> $log
  done
fi
