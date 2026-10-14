#!/usr/bin/env bash
# Rerun E003 RPE1 when <3 loco jobs are on the GPU, wait for all E003, check anchors, then E004/E005 two contexts at a time.
source ~/.vcc_env; cd ~/vcc; Q=logs/queue.log
while [ $(pgrep -fc "[p]ython -m vcc26.loco") -ge 3 ]; do sleep 15; done
echo "== queue: E003 RPE1 rerun $(date -u +%T)" >> $Q; bash scripts/run_e003.sh RPE1
while pgrep -f "[p]ython -m vcc26.loco" >/dev/null; do sleep 15; done
echo "== queue: E003 check $(date -u +%T)" >> $Q
python scripts/check_e003.py K562 RPE1 HepG2 Jurkat H1 >> $Q 2>&1 || { echo "== queue: E003 CHECK FAILED, stopping" >> $Q; exit 1; }
echo "== queue: E004 start $(date -u +%T)" >> $Q
printf "%s\n" K562 RPE1 HepG2 Jurkat H1 | xargs -P 2 -I{} bash scripts/run_e004.sh {}
echo "== queue: E004 ALL DONE $(date -u +%T)" >> $Q
