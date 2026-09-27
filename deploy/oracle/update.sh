#!/usr/bin/env bash
# Get the latest code and restart:  sudo bash /opt/mahsool/deploy/oracle/update.sh
set -euo pipefail
APP=/opt/mahsool
APP_USER=mahsool
run_as() { sudo -u "$APP_USER" -H bash -c "cd $APP && $*"; }

old=$(run_as "git rev-parse HEAD")
run_as "git pull --ff-only"
new=$(run_as "git rev-parse HEAD")
if [ "$old" = "$new" ]; then echo "Already up to date ($new)."; exit 0; fi
changed=$(run_as "git diff --name-only $old $new")

if echo "$changed" | grep -qx "pyproject.toml"; then
  echo "Dependencies changed: reinstalling."
  run_as "/home/$APP_USER/.local/bin/uv pip install --python .venv/bin/python -e '.[ml]'"
fi
if echo "$changed" | grep -q "^deploy/oracle/systemd/"; then
  install -m 0644 "$APP"/deploy/oracle/systemd/*.service "$APP"/deploy/oracle/systemd/*.timer /etc/systemd/system/
  systemctl daemon-reload
fi
# The index is replaced only when the committed one changed; the backend holds it open, so stop.
systemctl stop mahsool-backend.service
run_as ".venv/bin/python scripts/get_index.py"
systemctl start mahsool-backend.service
systemctl restart mahsool-ngrok.service
echo "Updated $old -> $new. Check in 2 minutes:  bash $APP/deploy/oracle/healthcheck.sh"
