#!/usr/bin/env bash
# usage: data_fetch.sh <name> <url> [<url> ...]
# Downloads each URL (resumable) to $DATA/scratch/<name>/, archives the folder to
# gdrive:VCC2026/data/raw/<name> and verifies it with rclone check. Run inside tmux;
# log: logs/data_<name>.log. A URL may be written as <url>::<relative/out/path>.
source ~/.vcc_env; cd ~/vcc
name=$1; shift; D=$DATA/scratch/$name; log=logs/data_$name.log; mkdir -p $D logs
say() { echo "[$(date -u +%FT%TZ)] $*" | tee -a $log; }
t0=$(date +%s); say "start $name ($# files)"
for spec in "$@"; do
  url=${spec%%::*}; out=$(basename "${url%%\?*}"); [[ $spec == *::* ]] && out=${spec#*::}
  mkdir -p "$D/$(dirname "$out")"
  aria2c -c -x8 -s8 --auto-file-renaming=false --summary-interval=60 --console-log-level=warn \
    -d "$D/$(dirname "$out")" -o "$(basename "$out")" "$url" >> $log 2>&1 || { say "FAILED download $url"; exit 1; }
  say "got $out $(du -h "$D/$out" | cut -f1)"
done
gb=$(du -sb $D | awk '{printf "%.1f", $1/1e9}'); free=$(rclone about gdrive: --json | python3 -c "import json,sys; print(round(json.load(sys.stdin)['free']/1e9,1))")
say "downloaded ${gb} GB; drive free ${free} GB"
python3 -c "import sys; sys.exit(0 if $gb < $free - 50 else 1)" || { say "STOP: would exceed Drive capacity"; exit 2; }
rclone copy --stats 120s --stats-one-line -v --drive-chunk-size 256M $D gdrive:VCC2026/data/raw/$name >> $log 2>&1 || { say "FAILED rclone copy"; exit 3; }
rclone check --size-only $D gdrive:VCC2026/data/raw/$name >> $log 2>&1 && say "rclone check OK" || { say "FAILED rclone check"; exit 4; }
say "done $name ${gb} GB in $(( ($(date +%s)-t0)/60 )) min"
