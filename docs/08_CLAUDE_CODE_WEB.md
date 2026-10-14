# Running this from Claude Code on the web

## 0. Before you start (the user does this once, outside chat)
1. In this Claude Code environment's settings, allow outbound network access to `132.145.128.143` port 22 (or "full" network access), and make the SSH private key for the `a10instance` key pair available to the session (environment secret or file). Never paste the private key into chat.
2. Add `VCC_TOKEN` (challenge site → Credentials) as an **environment secret** of this Claude Code environment, not in chat or in files.

## 1. Connect
```bash
IP=132.145.128.143
SSH="ssh -o StrictHostKeyChecking=accept-new -o ServerAliveInterval=30 ubuntu@$IP"
$SSH 'nvidia-smi --query-gpu=name,memory.total --format=csv; df -h /lambda/nfs/* ~ 2>/dev/null; uptime'
```
Record the instance start time from `uptime`; the planning session tracks spend from it ($1.99/h for `gpu_1x_a100_sxm4`, unverified against your invoice).

## 2. Sync the code to the instance
```bash
rsync -az --delete --exclude .git --exclude '__pycache__' ./ ubuntu@$IP:~/vcc/
```
Re-run after every code change (the repo is the source of truth; the instance copy is disposable).

## 3. Log the instance in to the challenge (token never printed)
```bash
printf '%s' "$VCC_TOKEN" | $SSH 'mkdir -p ~/.local/bin; cat > /tmp/.t; chmod 600 /tmp/.t'
$SSH 'cd ~/vcc && bash setup_lambda.sh' 2>&1 | tail -60        # installs env (~10 min)
$SSH '~/.local/bin/vcc login --token-stdin --store-plaintext < /tmp/.t && rm -f /tmp/.t && ~/.local/bin/vcc whoami'
```
If `setup_lambda.sh` takes longer than your command timeout, run it in tmux instead (next section).

## 4. Long jobs: always tmux + log file
```bash
run() {  # run <session-name> <command...>   (on the instance, inside ~/vcc, with ~/.vcc_env loaded)
  local name=$1; shift
  $SSH "cd ~/vcc && tmux new -d -s $name 'source ~/.vcc_env; $* 2>&1 | tee logs/$name.log; echo EXIT=\$? >> logs/$name.log'"
}
peek() { $SSH "tail -n ${2:-40} ~/vcc/logs/$1.log"; }
done_() { $SSH "grep -q '^EXIT=' ~/vcc/logs/$1.log && grep '^EXIT=' ~/vcc/logs/$1.log"; }
```
Example: `run E002 bash fetch_public_data.sh`, then poll `peek E002` every few minutes until `done_ E002` prints `EXIT=0`.

## 5. Execute the runbook
Follow `docs/07_RUNBOOK_INSTANCE.md` stage by stage (E000 → E005). Commands there run **on the instance** inside `~/vcc` after `source ~/.vcc_env` (wrap them with `run`, or `$SSH 'source ~/.vcc_env; cd ~/vcc; ...'`). Stop at each **CHECK**; print each **REPORT** block in chat for the user to paste back to the planning session.

Challenge data: if `controls/` is not on the instance after setup, use the vcc CLI's data-download subcommand (see `reports/vcc_help.txt` on the instance) to fetch the validation bundle into `$DATA/challenge/controls`. Box is only a fallback and needs an rclone `box` remote the user configures themselves.

## 6. Bring results back
```bash
mkdir -p results/reports results/scores
rsync -az ubuntu@$IP:~/vcc/reports/ results/reports/
$SSH 'source ~/.vcc_env; find "$DATA/loco" -name "scores_*.csv"' | while read -r f; do
  rsync -az "ubuntu@$IP:$f" "results/scores/$(basename "$(dirname "$f")")_$(basename "$f")"; done
```
Commit only small CSV/JSON score tables and reports (no h5ad, no .vcc, no tokens) under `results/`, and update `docs/EXPERIMENT_LOG.md`.

## 7. Cost discipline
- When a stage finishes and nothing is queued, tell the user: **terminate the instance in the Lambda console** (the filesystem keeps the data). You cannot terminate it yourself.
- Storage is billed per GB-month: skip the K562 genome-wide download (`WITH_GWPS=0`, the default) unless the planning session asks for it.
