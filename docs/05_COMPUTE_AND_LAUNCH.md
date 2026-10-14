# Compute, budget and launch requests

Budget $7,000 Lambda credits. **LR-1: first instance launched 14 Oct ~18:40 UTC (132.145.128.143, unverified, replaced); second instance 150.136.70.112 (key A10) up by ~20:20 UTC, both `gpu_1x_a100_sxm4`, us-east-1.** Spend accrues at ~$1.99/h per running instance, plus filesystem storage per GB-month. Warnings at $3,500 (50%), $5,250 (75%), $6,300 (90%).

| Request | Instance | Hours | Cost |
|---|---|---|---|
| LR-1, 14–21 Oct | 1x A100 40 GB, 30 vCPU, 220 GiB RAM, $1.99/h [1][2] | ~70 | ~$139 |
| LR-2, 22 Oct–5 Nov | same | ~112 | ~$223 |
| LR-3, optional (A5) | 1x H100 SXM 80 GB, $4.29/h [1][2] | ~40 | ~$172 |
| Persistent filesystem | 600 GB | 1 month | ~$120 (rate unverified) |
| **Total** | | | **~$654 (9.3%)** |

GPU is not the bottleneck: data preparation and DE scoring are CPU- and RAM-heavy, and the A100 is the cheapest Lambda instance with enough RAM (220 GiB) for 360k-cell × 18.5k-gene matrices; its GPU runs cell-eval2's GPU DE. Avoid GH200 (ARM64; some wheels are x86-only). Lambda billing granularity (per minute vs per hour) unverified — check the console.

## LAUNCH REQUEST LR-1

- **Purpose / experiments:** E000 controls inventory; E001 pipeline-check leaderboard entry; E002 public data + summaries; E003 LOCO anchors; E004–E005 baselines B0–B3 (seen, unseen); then A1/A2 work (E007–E009); E006 iMEMORY test only if EC2 files arrive.
- **Instance:** 1x A100 40 GB SXM (fallback: 1x A100 40 GB PCIe, same price).
- **Estimate:** ~10 h/day × 7 days ≈ 70 h ≈ **$139**. After LR-1: ~$6,860 left before storage.
- **Storage:** 600 GB persistent filesystem `vcc-data`, same region (mounts at `/lambda/nfs/vcc-data`).
- **Setup after launch:**
  ```bash
  mkdir -p ~/vcc && cd ~/vcc            # copy vcc26_code.tar.gz here first (scp or Drive VCC2026/code)
  tar -xf vcc26_code.tar.gz
  read -rs VCC_TOKEN && export VCC_TOKEN
  bash setup_lambda.sh                   # prompts once for rclone Drive + Box sign-in
  bash fetch_public_data.sh
  ```
  Then hand `docs/07_RUNBOOK_INSTANCE.md` to Claude Code on the instance.
- **Stop condition:** terminate when idle > 1 h and every night unless a job is queued (keep the filesystem). LR-1 ends at the earlier of 21 Oct 23:00 UTC or E000–E009 complete.

**Reminder: terminate idle instances.** I'll repeat this in every round report, with spend to date.

## Sources
1. [Lambda pricing](https://lambda.ai/pricing)
2. [Lambda pricing snapshot, Sept 2026 (synpixcloud)](https://www.synpixcloud.com/blog/lambda-labs-gpu-pricing-2026)
