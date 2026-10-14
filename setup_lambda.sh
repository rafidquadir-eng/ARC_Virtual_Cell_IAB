#!/usr/bin/env bash
# Immunome AI x VCC 2026 -- Lambda instance setup (Ubuntu 22.04 / Lambda Stack image)
# Run on the instance, from the code folder:   bash setup_lambda.sh
# NON-INTERACTIVE (safe to run over ssh / tmux) and idempotent (safe to re-run).
#
# Secrets never go in this file, in git, or in chat:
#   VCC_TOKEN  challenge token  -> log in once with:  printf '%s' "$VCC_TOKEN" | ~/.local/bin/vcc login --token-stdin --store-plaintext
#   HF_TOKEN   only if a Hugging Face dataset turns out to be gated
# rclone (Drive / Box) is OPTIONAL: used only if remotes named 'gdrive' / 'box' already exist.
set -euo pipefail

WORK=${WORK:-$(cd "$(dirname "$0")" && pwd)}          # this code checkout
# Persistent filesystem: first mount under /lambda/nfs (Lambda attaches them there); else home disk.
FS=$(ls -d /lambda/nfs/*/ 2>/dev/null | head -1 || true)
DATA=${DATA:-${FS:+${FS%/}/vcc-data}}; DATA=${DATA:-$HOME/vcc-data}
DRIVE=${DRIVE:-gdrive:VCC2026}
mkdir -p "$DATA"/{raw,pb,loco,preds,challenge,imemory} "$WORK"/{reports,logs}
echo "WORK=$WORK  DATA=$DATA"

echo "== 1. system packages"
sudo DEBIAN_FRONTEND=noninteractive apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq rclone unzip pigz tmux htop jq aria2 >/dev/null
# Some images ship without the NVIDIA driver: torch then installs as CPU-only and cell-eval2 falls back
# to the slow scanpy DE backend. Install the driver and stop: a reboot is needed before step 2.
if lspci | grep -qi nvidia && ! command -v nvidia-smi >/dev/null; then
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "linux-headers-$(uname -r)" \
      nvidia-driver-595-server nvidia-utils-595-server >/dev/null
  echo "!! NVIDIA driver installed: run 'sudo reboot', then re-run setup_lambda.sh"; exit 1
fi

echo "== 2. python env (uv, Python 3.12)"
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
cd "$WORK"
[ -d .venv ] || uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -q --torch-backend=auto "cell-eval2[gpu,gpudge]==0.18.0" \
    anndata scanpy polars pandas scipy numpy pyarrow huggingface_hub "torch>=2.2"
uv tool install -q vcc-cli 2>/dev/null || uv tool upgrade -q vcc-cli
# Env file sourced explicitly by every job (Ubuntu's .bashrc returns early in non-interactive shells)
cat > ~/.vcc_env <<EOF
export WORK=$WORK DATA=$DATA PYTHONPATH=$WORK/src PATH="\$HOME/.local/bin:\$PATH"
source $WORK/.venv/bin/activate
EOF
grep -q 'vcc_env' ~/.bashrc || echo '[ -f ~/.vcc_env ] && source ~/.vcc_env' >> ~/.bashrc
export PYTHONPATH="$WORK/src"
python - <<'EOF'
import importlib.metadata as m
print("cell-eval2", m.version("cell-eval2"))
try:
    import torch; print("torch", torch.__version__, "cuda", torch.cuda.is_available())
except Exception as e: print("torch:", e)
EOF
# cell-eval2's de.backend="auto" RAISES if a GPU is visible but gpudge is broken -- check now:
python -c "import gpudge; print('gpudge ok')" || echo "!! gpudge import failed: pass --de-backend pdex to loco/local_eval"

echo "== 3. optional rclone remotes"
HAVE_GDRIVE=0; HAVE_BOX=0
rclone listremotes 2>/dev/null | grep -q '^gdrive:' && HAVE_GDRIVE=1
rclone listremotes 2>/dev/null | grep -q '^box:' && HAVE_BOX=1
echo "gdrive remote: $HAVE_GDRIVE   box remote: $HAVE_BOX   (0 = not configured; that's fine)"
if [ "$HAVE_GDRIVE" = 1 ]; then
  for d in logs summaries reports plan; do rclone mkdir "$DRIVE/$d" || true; done
  rclone copy "$WORK/docs" "$DRIVE/plan" --include "*.md" || true
fi

echo "== 4. challenge login + data"
VCC="$HOME/.local/bin/vcc"
if "$VCC" whoami >/dev/null 2>&1; then
  echo "vcc: already logged in"; "$VCC" whoami
elif [ -n "${VCC_TOKEN:-}" ]; then
  printf '%s' "$VCC_TOKEN" | "$VCC" login --token-stdin --store-plaintext && "$VCC" whoami
else
  echo "!! vcc not logged in and VCC_TOKEN not set (see header). Continuing without it."
fi
"$VCC" --help > "$WORK/reports/vcc_help.txt" 2>&1 || true
echo "vcc CLI help saved to reports/vcc_help.txt (find the data-download subcommand there)"
if [ ! -d "$DATA/challenge/controls" ]; then
  if [ -f "$DATA/challenge/controls.zip" ]; then :
  elif [ "$HAVE_BOX" = 1 ]; then rclone copy "box:ARC Virtual cell Challenge/controls.zip" "$DATA/challenge/"
  fi
  if [ -f "$DATA/challenge/controls.zip" ]; then
    unzip -q "$DATA/challenge/controls.zip" -d "$DATA/challenge/controls"
  else
    echo "!! controls not present yet: download them with the vcc CLI into $DATA/challenge/controls (see reports/vcc_help.txt)"
  fi
fi
if [ -d "$DATA/challenge/controls" ]; then
  python -m vcc26.inspect_controls --dir "$DATA/challenge/controls" --out "$WORK/reports/controls_inventory.json" | head -120
fi

echo "== 5. iMEMORY files (only if the Box remote exists; never re-shared)"
if [ "$HAVE_BOX" = 1 ]; then
  rclone copy "box:OutputsV4/checkpoints/phase2_v4/phase2_v4_best.pt" "$DATA/imemory/" || true
  rclone copy "box:scripts/scripts_EC2/gene_mean_embedding.npy" "$DATA/imemory/" || true
fi
echo "   gene_embeddings.npz is NOT on Box; the iMEMORY test (E006) stays blocked until it is recovered from EC2."

echo "== done"
nvidia-smi --query-gpu=name,memory.total --format=csv || true
df -h "$DATA" | tail -1
