# Running the runbook on the Lambda instance

**Claude Code on the web cannot do this.** Web sessions run behind an HTTP/HTTPS proxy that carries all their outbound traffic [1], so they cannot open an SSH connection to the instance, whatever the network-access level. Their environment variables are also not a secret store: anyone who uses the environment can read them [1].

**Run Claude Code on the instance instead**, either from your Mac Terminal over SSH (1a) or from the Claude Desktop app's SSH session (1b) [2]. Claude Code then runs *on the instance*, your private key never leaves your laptop, and nothing secret goes into any Claude setting.

## 1a. Connect from the Mac Terminal (works on any macOS; use this if Desktop won't install)
Claude Code itself needs macOS 13+ [3], but nothing has to be installed on the Mac: Claude Code runs on the instance (Ubuntu), and the Mac only needs its built-in Terminal and `ssh`.
```bash
# on the Mac (Terminal.app). Use the path of the a10instance private key you downloaded from Lambda.
chmod 600 ~/.ssh/a10instance            # ssh refuses keys other users can read
ssh -i ~/.ssh/a10instance ubuntu@132.145.128.143

# now on the instance
sudo apt-get install -y tmux
curl -fsSL https://claude.ai/install.sh | bash      # native installer [3]
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
claude --version
tmux new -s cc                                      # keeps Claude running if the SSH connection drops
claude                                              # first run: login (below)
```
**Login over SSH:** Claude prints a login URL (press `c` to copy it). Open it in the Mac's browser, sign in, and if the browser shows a code, paste it into the terminal at `Paste code here if prompted` [4]. That code goes only into the terminal, never into chat.

**Reconnecting later:** `ssh -i ~/.ssh/a10instance ubuntu@132.145.128.143` then `tmux attach -t cc`. Detach without stopping Claude with `Ctrl-b` then `d`.

Then continue with steps 2–4 below inside that Claude session (start it from `~` before the repo exists; after the clone, quit with `/exit` and restart it from `~/vcc` with `cd ~/vcc && claude` so it reads `CLAUDE.md`).

## 1b. Connect from Claude Desktop (macOS 13+ only)
1. Install the Claude Desktop app (macOS, Windows, or Linux beta) and open the **Code** tab.
2. Before starting a session, open the environment dropdown → **+ Add SSH connection**:
   - **Name:** `lambda-vcc`
   - **SSH Host:** `ubuntu@132.145.128.143`
   - **SSH Port:** leave empty (22)
   - **Identity File:** the path on your laptop to the private key of the `a10instance` key pair (for example `~/.ssh/a10instance` or wherever you saved it when you created the key in Lambda)
3. Select `lambda-vcc` and start a session. Desktop installs Claude Code on the instance the first time [2].

## 2. Get the code onto the instance (no secrets in chat)
In that session, ask Claude to run, on the instance:
```bash
sudo apt-get install -y gh 2>/dev/null || (type -p curl >/dev/null && curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg && echo "deb [signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list && sudo apt-get update -qq && sudo apt-get install -y gh)
gh auth login --hostname github.com --git-protocol https --web     # prints a one-time code; YOU open github.com/login/device and enter it
gh repo clone rafidquadir-eng/ARC_Virtual_Cell_IAB ~/vcc
```
The device-code flow is the only step that needs you: you type the code into GitHub in your browser. Nothing is pasted into chat.

## 3. Install, then log in to the challenge yourself
```bash
cd ~/vcc && bash setup_lambda.sh 2>&1 | tee logs/E000_setup.log     # non-interactive, ~10 min
```
Then open a terminal on the instance (Desktop's integrated terminal in the SSH session, or your own `ssh -i <key> ubuntu@132.145.128.143`) and type:
```bash
~/.local/bin/vcc login --store-plaintext      # prompts for the token with hidden input; stored 0600 on the instance
~/.local/bin/vcc whoami
```
The token comes from the challenge site's Credentials page. It is typed only into that hidden prompt, never into chat or any Claude setting.

## 4. Run the runbook
Tell the Desktop session:
> Follow CLAUDE.md: run docs/07_RUNBOOK_INSTANCE.md stages E000–E005 here on the instance and print each REPORT block.

Rules for long jobs: run each stage in `tmux` with a log file (`tmux new -d -s E002 'source ~/.vcc_env; cd ~/vcc; bash fetch_public_data.sh 2>&1 | tee logs/E002.log'`) and poll the log, so a dropped connection or a sleeping laptop doesn't kill the job. Desktop can keep a task running while disconnected [2], but tmux is the safer default for multi-hour downloads.

## 5. Bring results back
Commit small CSV/JSON score tables and reports under `results/` and push (`git push` works through the `gh` login). Never commit data, predictions, `.vcc` files or tokens. Paste the REPORT blocks to the planning session.

## 6. Cost discipline
When a stage finishes and nothing is queued, terminate the instance in the Lambda console (the filesystem keeps the data). Storage is billed per GB-month: keep `WITH_GWPS=0` unless the planning session asks for it.

## Sources
1. [Configure cloud environments (Claude Code docs)](https://code.claude.com/docs/en/cloud-environments)
2. [Desktop app — SSH sessions (Claude Code docs)](https://code.claude.com/docs/en/desktop)
3. [Advanced setup — system requirements and install (Claude Code docs)](https://code.claude.com/docs/en/setup)
4. [Authentication — login over SSH (Claude Code docs)](https://code.claude.com/docs/en/authentication)
