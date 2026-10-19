#!/usr/bin/env bash
# 5-line V* as parallel per-holdout loco processes (round 4; vstar.py runs lines serially and one rows file
# per tag, so parallel vstar calls with one tag would overwrite each other).
#
#   bash scripts/vstar_par.sh <specs.json> <tag> <seed> <results dir> [extra loco args ...]
#
# Env:
#   VSTAR_PAR    concurrent holdouts (default 2; RPE1-sized jobs went OOM at 4-5)
#   VSTAR_LINES  space-separated holdouts (default: the 5 standard V* lines)
#   VCC_RENORM_AXIS=1 is passed through to loco (review C-06)
#
# Writes $DATA/loco/E020/scores_<line>_seen_<tag>.csv + pertarget parquet (loco never overwrites; a rerun
# gets a timestamp suffix), logs/<tag>_<line>.log, and <results dir>/vstar_rows_<tag>.csv (all lines).
# Exit status is non-zero if any holdout failed; the failed lines are printed.
set -uo pipefail
source ~/.vcc_env; cd ~/vcc
SPECS=$1; TAG=$2; SEED=$3; RES=$4; shift 4
PANEL=$(find $DATA/challenge -name pert_counts.csv | head -1)
LINES=${VSTAR_LINES:-"CD4T_Stim8hr KOLF2.1J Orion_HCT116 Orion_HEK293T K562_GWPS"}
PAR=${VSTAR_PAR:-2}
mkdir -p "$RES" logs
declare -A PID
for h in $LINES; do
  python -m vcc26.loco --config loco.json --holdout $h --mode seen --out $DATA/loco/E020 --panel-file $PANEL \
    --specs $SPECS --tag $TAG --seed $SEED "$@" > logs/${TAG}_${h}.log 2>&1 &
  PID[$h]=$!
  echo "$(date -u +%H:%M:%S) started $h (pid ${PID[$h]}, renorm=${VCC_RENORM_AXIS:-0}, seed $SEED)"
  while [ "$(jobs -rp | wc -l)" -ge "$PAR" ]; do sleep 15; done
done
FAIL=""
for h in $LINES; do
  wait ${PID[$h]} || FAIL="$FAIL $h"
done
python - "$TAG" "$RES" "$DATA" $LINES <<'EOF'
import glob, os, sys
import pandas as pd
tag, res, data, lines = sys.argv[1], sys.argv[2], sys.argv[3] + "/loco/E020", sys.argv[4:]
fs = []
for h in lines:
    c = sorted(glob.glob(f"{data}/scores_{h}_seen_{tag}*.csv"), key=os.path.getmtime)
    if c: fs.append(c[-1])          # newest file for this line and tag
if fs:
    df = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    df.to_csv(f"{res}/vstar_rows_{tag}.csv", index=False)
    print(f"wrote {res}/vstar_rows_{tag}.csv ({len(df)} rows from {len(fs)} lines)")
EOF
if [ -n "$FAIL" ]; then echo "FAILED holdouts:$FAIL (see logs/${TAG}_<line>.log)"; exit 1; fi
echo "$(date -u +%H:%M:%S) done: $TAG"
