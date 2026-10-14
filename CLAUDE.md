# CLAUDE.md — Immunome AI × Virtual Cell Challenge 2026 (execution repo)

You are Claude Code on the web. This repo holds the code and plan; the work runs on a Lambda GPU instance you reach over SSH. A separate planning session decides experiments; you execute them and report back.

**Start with `docs/08_CLAUDE_CODE_WEB.md`** (how to connect, sync code, run long jobs). The step-by-step task list is `docs/07_RUNBOOK_INSTANCE.md`.

## Instance
- `ssh ubuntu@132.145.128.143` (Lambda `gpu_1x_a100_sxm4`, us-east-1). Code lives at `~/vcc` on the instance; data under the persistent filesystem (`/lambda/nfs/<fs>/vcc-data`, auto-detected) or `~/vcc-data`.

## Hard rules
- Secrets (`VCC_TOKEN`, `HF_TOKEN`, rclone tokens, SSH private keys) never go into files, commits, logs or chat output.
- Box is read-only. Never write to `box:`.
- Never upload iMEMORY weights or data anywhere except the private `gdrive:VCC2026/checkpoints_private`.
- Max **2 challenge submissions per UTC day**. Leaderboard entries only where the runbook says; never tune on the leaderboard.
- Run anything longer than ~2 minutes inside `tmux` on the instance and poll its log; SSH sessions drop.
- Ask before launching extra instances, downloading > 300 GB, or anything else that costs money beyond the runbook.
- Commit code changes to this repo (small, described commits). Never commit data, predictions, tokens or `.vcc` files.
