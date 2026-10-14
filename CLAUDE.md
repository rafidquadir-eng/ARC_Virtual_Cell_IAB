# CLAUDE.md — Immunome AI × Virtual Cell Challenge 2026 (execution repo)

You are Claude Code running **on the Lambda GPU instance** (started over SSH from the Mac Terminal, or from a Claude Desktop SSH session). This repo, cloned at `~/vcc`, holds the code and plan. A separate planning session decides experiments; you execute them and report back.

**Start with `docs/08_CLAUDE_CODE_WEB.md`** (how this session was connected, the challenge login the user does themselves, long-job rules). The step-by-step task list is `docs/07_RUNBOOK_INSTANCE.md`.

## Instance
- Lambda `gpu_1x_a100_sxm4`, us-east-1. Code at `~/vcc`; data under the persistent filesystem (`/lambda/nfs/<fs>/vcc-data`, auto-detected) or `~/vcc-data`. `source ~/.vcc_env` before any command.

## Hard rules
- Secrets (challenge token, `HF_TOKEN`, rclone tokens, SSH keys) never go into files you write, commits, logs or chat output. The user logs in to `vcc` themselves; never ask them to paste a token into chat.
- Box is read-only. Never write to `box:`.
- Never upload iMEMORY weights or data anywhere except the private `gdrive:VCC2026/checkpoints_private`.
- Max **2 challenge submissions per UTC day**. Leaderboard entries only where the runbook says; never tune on the leaderboard.
- Run anything longer than ~2 minutes inside `tmux` on the instance and poll its log; SSH sessions drop.
- Ask before launching extra instances, downloading > 300 GB, or anything else that costs money beyond the runbook.
- Commit code changes to this repo (small, described commits). Never commit data, predictions, tokens or `.vcc` files.
