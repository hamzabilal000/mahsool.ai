#!/usr/bin/env bash
# Is Mahsool AI up?  bash /opt/mahsool/deploy/oracle/healthcheck.sh
# With --repair (the 5-minute timer uses it): restart the backend after 3 failed local checks.
. /etc/mahsool/ngrok.env 2>/dev/null || true
STATE=/run/mahsool-health-failures
ok=0
if curl -fsS -m 10 http://127.0.0.1:8000/health >/dev/null; then
  echo "backend (local):  OK"; ok=1
else
  echo "backend (local):  NOT ANSWERING  -> logs: journalctl -u mahsool-backend -n 50"
fi
if [ -n "${NGROK_DOMAIN:-}" ]; then
  if curl -fsS -m 15 -H "ngrok-skip-browser-warning: true" "https://$NGROK_DOMAIN/health" >/dev/null; then
    echo "public (ngrok):   OK  https://$NGROK_DOMAIN"
  else
    echo "public (ngrok):   NOT ANSWERING  -> logs: journalctl -u mahsool-ngrok -n 50"
  fi
fi
echo "memory: $(free -g | awk '/Mem:/ {print $3 " GB used of " $2 " GB"}')"

if [ "${1:-}" = "--repair" ]; then
  if [ "$ok" = 1 ]; then echo 0 > "$STATE"; exit 0; fi
  # A backend that is still loading its models is not broken.
  systemctl is-active --quiet mahsool-backend.service || exit 0
  n=$(( $(cat "$STATE" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$STATE"
  if [ "$n" -ge 3 ]; then
    echo "3 failed checks in a row: restarting the backend"; echo 0 > "$STATE"
    systemctl restart mahsool-backend.service
  fi
fi
