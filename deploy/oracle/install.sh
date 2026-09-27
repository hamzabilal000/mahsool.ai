#!/usr/bin/env bash
# Installs the Mahsool AI backend on an Ubuntu ARM64 (or x86-64) VM. Run as root; cloud-init.yaml
# runs it on the first boot. Safe to run again (sudo bash install.sh): every step checks what is
# already there.
# No secrets here: setup-secrets.sh asks for them afterwards.
set -euo pipefail

REPO_URL="${REPO_URL:-https://github.com/hamzabilal000/mahsool.ai.git}"
APP=/opt/mahsool
APP_USER=mahsool
say() { echo "=== [mahsool install] $* ($(date -u +%H:%M:%S) UTC)"; }

say "1/7 system packages"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y git curl ca-certificates gnupg build-essential sqlite3 jq  # also in cloud-init

say "2/7 ngrok agent (official apt repository, has arm64)"
if ! command -v ngrok >/dev/null; then
  curl -fsSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc -o /etc/apt/trusted.gpg.d/ngrok.asc
  echo "deb https://ngrok-agent.s3.amazonaws.com buster main" > /etc/apt/sources.list.d/ngrok.list
  apt-get update -y && apt-get install -y ngrok
fi

say "3/7 app user and code in $APP"
id "$APP_USER" >/dev/null 2>&1 || useradd --system --create-home --home-dir /home/$APP_USER --shell /bin/bash "$APP_USER"
if [ ! -d "$APP/.git" ]; then
  git clone --depth 1 "$REPO_URL" "$APP"
fi
chown -R "$APP_USER:$APP_USER" "$APP"

say "4/7 Python 3.11 (uv) and dependencies, CPU-only PyTorch"
run_as() { sudo -u "$APP_USER" -H bash -c "cd $APP && $*"; }
if [ ! -x /home/$APP_USER/.local/bin/uv ]; then
  run_as "curl -LsSf https://astral.sh/uv/install.sh | sh"
fi
UV=/home/$APP_USER/.local/bin/uv
run_as "$UV venv --python 3.11 --allow-existing .venv"
run_as "$UV pip install --python .venv/bin/python torch --index-url https://download.pytorch.org/whl/cpu"
run_as "$UV pip install --python .venv/bin/python -e '.[ml]'"

say "5/7 vector index (prebuilt, no 30-minute re-index)"
run_as ".venv/bin/python scripts/get_index.py"

say "6/7 models (BGE-M3 + gte reranker, ~3 GB, downloaded once)"
run_as "HF_HOME=$APP/.cache/huggingface .venv/bin/python -c \"from huggingface_hub import snapshot_download as d; d('BAAI/bge-m3'); from backend.app.config import get_settings; from backend.app.rag.reranker import make_reranker; make_reranker(get_settings())\""

say "7/7 systemd services (backend, ngrok, health check, daily keep-alive)"
install -m 0644 "$APP"/deploy/oracle/systemd/*.service "$APP"/deploy/oracle/systemd/*.timer /etc/systemd/system/
chmod +x "$APP"/deploy/oracle/*.sh
systemctl daemon-reload
systemctl enable mahsool-backend.service mahsool-ngrok.service
systemctl enable --now mahsool-health.timer mahsool-keepalive.timer
# The backend and ngrok start once setup-secrets.sh has written the keys (they wait for the files).
if [ -f "$APP/.env" ] && [ -f "$APP/ngrok.yml" ]; then
  systemctl restart mahsool-backend.service mahsool-ngrok.service
fi

say "done. Next: sudo bash $APP/deploy/oracle/setup-secrets.sh"
