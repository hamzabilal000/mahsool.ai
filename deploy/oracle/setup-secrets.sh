#!/usr/bin/env bash
# Run ONCE on the VM after the install finished:  sudo bash /opt/mahsool/deploy/oracle/setup-secrets.sh
# Asks for your Groq API key and your ngrok authtoken, stores them only on this VM, starts the app.
set -euo pipefail
APP=/opt/mahsool
APP_USER=mahsool

[ "$(id -u)" = 0 ] || { echo "Please run with sudo."; exit 1; }
if ! grep -q "=== \[mahsool install\] done" /var/log/mahsool-install.log 2>/dev/null; then
  echo "The install is not finished yet. Watch it with:  tail -f /var/log/mahsool-install.log"
  echo "(It takes about 15-25 minutes after the VM starts.) Then run this script again."
  exit 1
fi

read -r -s -p "Paste your GROQ_API_KEY (starts with gsk_), then Enter: " GROQ; echo
read -r -s -p "Paste your ngrok authtoken, then Enter: " NGROK; echo
[ -n "$GROQ" ] && [ -n "$NGROK" ] || { echo "Both values are needed."; exit 1; }

umask 077
cat > "$APP/.env" <<ENV
GROQ_API_KEY=$GROQ
# Question log and feedback in local SQLite (no DATABASE_URL on this server).
MAHSOOL_SQLITE_PATH=$APP/data/mahsool.db
ENV
cat > "$APP/ngrok.yml" <<YML
version: "3"
agent:
  authtoken: $NGROK
YML
chown "$APP_USER:$APP_USER" "$APP/.env" "$APP/ngrok.yml"
chmod 600 "$APP/.env" "$APP/ngrok.yml"

systemctl restart mahsool-backend.service
systemctl restart mahsool-ngrok.service
. /etc/mahsool/ngrok.env
echo "Saved. The backend is starting (loading the models takes 1-2 minutes)."
echo "Check it:  bash $APP/deploy/oracle/healthcheck.sh"
echo "Public address: https://$NGROK_DOMAIN/health"
