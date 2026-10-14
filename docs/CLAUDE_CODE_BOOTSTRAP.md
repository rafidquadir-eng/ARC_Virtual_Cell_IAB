# Bootstrap prompt for Claude Code on the Lambda instance

Paste everything below the line into Claude Code on the instance.

---

You are setting up and running Immunome AI's entry for the Arc Institute Virtual Cell Challenge 2026 on this Lambda instance. A separate planning session wrote the code and plan. Your job: get the code, run the runbook, and post reports to Google Drive where the planning session can read them.

## 0. Ground rules (read first)
- Box is read-only. Only ever `rclone copy box:<path> <local>`. Never write, move or delete on Box.
- Never upload iMEMORY files (`phase2_v4_best.pt`, `gene_mean_embedding.npy`, anything under `$DATA/imemory`) anywhere except `gdrive:VCC2026/checkpoints_private`.
- Secrets only in shell variables (`VCC_TOKEN`, `HF_TOKEN`). Never write them to files, logs, reports or git. If you need one, ask the user to run `read -rs VCC_TOKEN && export VCC_TOKEN` in this shell.
- Max 2 leaderboard submissions per UTC day. Say how many are used before each `vcc submit`.
- Stop and ask before anything that adds cost beyond this instance (new instances, downloads over 300 GB).

## 1. Get rclone and connect the user's Google Drive
```bash
mkdir -p ~/vcc && cd ~/vcc
command -v rclone >/dev/null || curl -s https://rclone.org/install.sh | sudo bash
rclone listremotes
```
If there is no `gdrive:` remote, create one named `gdrive` (type `drive`, scope `drive`). The instance has no browser, so ask the user to pick one of:
- (a) Reconnect their SSH session with a tunnel: `ssh -L 53682:localhost:53682 ubuntu@<instance-ip>`, then run `rclone config` here and answer **yes** to "Use web browser to automatically authenticate"; they open the printed `http://127.0.0.1:53682/...` link on their laptop.
- (b) Answer **no** to that question; rclone prints an `rclone authorize "drive" "..."` command for them to run on their laptop (needs rclone there) and paste the result back here.

Check: `rclone lsf gdrive:VCC2026/` lists `code/`.

## 2. Get the code and plan
```bash
cd ~/vcc
rclone copy gdrive:VCC2026/code/vcc26_code.tar.gz ~/vcc/
sha256sum vcc26_code.tar.gz        # report this value
tar -xf vcc26_code.tar.gz
ls docs/
```
Read, in order: `docs/00_START_HERE.md`, `docs/01_RULES_TIMELINE_IP.md`, `docs/04_APPROACHES.md`, then follow **`docs/07_RUNBOOK_INSTANCE.md`** step by step (E000 → E005). `docs/02`, `03`, `05`, `06` are reference.

Notes for this instance:
- It may be an A10 (24 GB) rather than the A100 the plan assumed; that is fine (the work is CPU/RAM-heavy). Report `nvidia-smi`, `nproc` and `free -g` in E000.
- Storage is a persistent filesystem under `/lambda/nfs/`; `setup_lambda.sh` auto-detects it and sets `DATA`. Report the path.
- The challenge controls: prefer the official `vcc` CLI download if it has one (check `vcc --help`); otherwise set up a `box:` remote the same way as step 1 and copy `box:ARC Virtual cell Challenge/controls.zip`.
- If a `box:` remote is not set up, skip the iMEMORY copy in setup step 6 (it is not needed for E000–E005).

## 3. How to report back (the planning session reads these from Drive)
After each stage, write the REPORT block to a plain-text file and upload it as a Google Doc:
```bash
mkdir -p ~/vcc/reports
# write the report to ~/vcc/reports/REPORT_E000.txt (E001, E002, ... for later stages)
rclone copy ~/vcc/reports/REPORT_E000.txt gdrive:VCC2026/reports/ --drive-import-formats txt
```
Also copy result CSVs: `rclone copy $DATA/loco gdrive:VCC2026/logs/loco --include "*.csv" --include "*.json"`.
Then tell the user in this terminal: "E00x report is in Drive VCC2026/reports".

## 4. When done or idle
Print total instance hours used and remind the user to **terminate the instance** if nothing is queued (the filesystem persists).
