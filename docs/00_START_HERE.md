# VCC 2026 — Immunome AI entry: start here

Updated 14 Oct 2026, 14:30 ET. Deadline: **Thu 5 Nov 2026, 23:59 UTC (18:59 ET)** — 22 days.

## Status

| Item | State |
|---|---|
| Rules, timeline, IP | Done — go. No code/weights disclosure; finalists publish a high-level method description. → `01_RULES_TIMELINE_IP.md` |
| Asset audit | Done. iMEMORY gene-embedding table is not on Box (searched all 12 `.npz`); it lives only on the old EC2 disk. → `02_ASSET_AUDIT.md` |
| Datasets | Listed; download script written. X-Atlas/Orion added (non-commercial license — needs your call). → `03_DATASETS.md` |
| Approaches | Ranked, with what to borrow from X-Cell and an honest read on LeJEPA. → `04_APPROACHES.md` |
| Compute | ~$650 of $7,000 planned. LR-1 ready. → `05_COMPUTE_AND_LAUNCH.md` |
| Schedule | Updated for 2 entries/day through 5 Nov. → `06_SCHEDULE.md` |
| Code | Written and tested end-to-end on synthetic data (`vcc26_code.tar.gz`). |
| Baselines on real data | **Not run yet — needs the instance.** → `07_RUNBOOK_INSTANCE.md` |

## Yes — I need the go-ahead, and it is these four actions on your side

I can't launch or log in to anything, so "execute" means:

1. **Launch LR-1:** 1x A100 40 GB (SXM or PCIe) + a 600 GB persistent filesystem named `vcc-data`, same region.
2. **Connect Claude Desktop to the instance** (Code tab → environment dropdown → + Add SSH connection) and let it clone this repo to `~/vcc` — exact steps in `08_CLAUDE_CODE_WEB.md`. Claude Code on the web can't SSH.
3. **In a terminal on the instance only:** `~/.local/bin/vcc login --store-plaintext` (hidden prompt; token from the challenge site's Credentials page). Never paste it in chat or any Claude setting.
4. **Tell the Desktop session** to run `07_RUNBOOK_INSTANCE.md` E000–E005. rclone Drive/Box sign-ins are optional and only needed for the log copy and the iMEMORY files.

Then the runbook produces, in order:
- **E000** controls inventory (what's actually in `controls.zip`) — ~30 min after launch
- **E001** first leaderboard entry (generic-shift baseline, pipeline check) — same day
- **E002–E005** public data, local validation anchors, baseline table B0–B3 — by Fri 16 Oct

Paste the runbook's report block back here after each stage and I'll decide the next experiments and update the log.

## Decisions still open (none blocks the baseline)

1. X-Atlas/Orion: non-commercial license. Ask Xaira for permission / legal review, or skip. (Biggest single data upgrade if allowed.)
2. State / Stack: non-commercial licenses. Recommend skip.
3. Old EC2 disk or EBS snapshot: needed only for the iMEMORY test (3 files listed in `02_ASSET_AUDIT.md`).
4. Patent counsel: only if iMEMORY ends up in the final entry; plus the possible prior disclosure noted in `01`.
5. Team registration: confirm members, all as Immunome AI employees (`vcc whoami` checks it).

## Files

| File | Contents |
|---|---|
| `00_START_HERE.md` | this page |
| `01_RULES_TIMELINE_IP.md` | rules, metrics, IP, go/no-go |
| `02_ASSET_AUDIT.md` | iMEMORY checkpoint, gene features, what's missing, Box search |
| `03_DATASETS.md` | sources, sizes, licenses, keys, commands |
| `04_APPROACHES.md` | ranked approaches, X-Cell borrowings, LeJEPA, rejected ideas |
| `05_COMPUTE_AND_LAUNCH.md` | budget, LAUNCH REQUEST LR-1, warnings |
| `06_SCHEDULE.md` | week-by-week, submission policy |
| `07_RUNBOOK_INSTANCE.md` | step-by-step for Claude Code on the Lambda instance |
| `08_CLAUDE_CODE_WEB.md` | how to connect (Mac Terminal over SSH, or Claude Desktop) |
| `09_DATA_CURATION_AGENT.md` | prompt for the data-curation agent |
| `10_PLAN_TO_TOP.md` | strategy: gap analysis, work packages, which outside ideas we use |
| `11_BUILD_PLAN.md` | **the detailed build plan**: phases D/E/B/M/C/T, owners, acceptance rules, calendar |
| `12_DIAGNOSIS.md` | **every known problem (engineering, data, biology, metric, ops) and its fix**, after E021 |
| `13_EXECUTION_PLAN.md` | **the working queue**: owners, commands, acceptance tests and dates for every fix; rclone OAuth steps |
| `EXPERIMENT_LOG.md` | running log (also mirrored as a Google Sheet) |
