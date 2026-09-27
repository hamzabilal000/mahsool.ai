#!/usr/bin/env bash
# Mahsool AI backend on an Ubuntu laptop, public through ngrok (the Linux twin of run_local.ps1).
#   bash scripts/run_local.sh          # first time installs everything; later just starts
#   bash scripts/run_local.sh --check  # is it working?
# Needs: python3.11 (+ python3.11-venv), git, ngrok with "ngrok config add-authtoken" done.
# Stop: Ctrl+C (stops the backend and ngrok).
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
touch .env && chmod 600 .env
getenv() { grep -E "^$1=" .env | tail -n 1 | cut -d= -f2- || true; }
DOMAIN="${NGROK_DOMAIN:-$(getenv NGROK_DOMAIN)}"
DOMAIN="${DOMAIN:-resident-coil-delusion.ngrok-free.dev}"

if [ "${1:-}" = "--check" ]; then
  curl -fsS -m 10 http://127.0.0.1:8000/health >/dev/null && echo "backend (local): OK" || echo "backend (local): NOT ANSWERING"
  curl -fsS -m 20 -H "ngrok-skip-browser-warning: true" "https://$DOMAIN/health" >/dev/null \
    && echo "public (ngrok):  OK  https://$DOMAIN" || echo "public (ngrok):  NOT ANSWERING"
  exit 0
fi

command -v ngrok >/dev/null || { echo "ngrok is not installed (docs/RUN_ON_MY_LAPTOP.md)"; exit 1; }
[ -x "$PY" ] || python3.11 -m venv .venv
want=$(sha256sum pyproject.toml | cut -d' ' -f1)
if [ "$(cat .venv/installed.txt 2>/dev/null)" != "$want" ]; then
  echo "== installing dependencies (first time: 10-20 minutes)"
  $PY -m pip install --upgrade pip
  $PY -m pip install torch --index-url https://download.pytorch.org/whl/cpu
  $PY -m pip install -e ".[ml]"
  echo "$want" > .venv/installed.txt
fi
$PY scripts/get_index.py

if [ -z "$(getenv GROQ_API_KEY)" ]; then
  read -r -s -p "Paste your GROQ_API_KEY, then Enter: " KEY; echo
  echo "GROQ_API_KEY=$KEY" >> .env
fi
[ -n "$(getenv NGROK_DOMAIN)" ] || echo "NGROK_DOMAIN=$DOMAIN" >> .env
[ -n "$(getenv MAHSOOL_SQLITE_PATH)" ] || echo "MAHSOOL_SQLITE_PATH=data/mahsool.db" >> .env

ngrok http 127.0.0.1:8000 --url="https://$DOMAIN" --log=stdout > data/ngrok.log 2>&1 &
NGROK_PID=$!
trap 'kill $NGROK_PID 2>/dev/null' EXIT
echo "Public address: https://$DOMAIN (ngrok log: data/ngrok.log). Stop: Ctrl+C."
env -u DATABASE_URL $PY -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 \
  --proxy-headers --forwarded-allow-ips 127.0.0.1
