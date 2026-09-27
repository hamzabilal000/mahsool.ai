#!/usr/bin/env bash
# Daily keep-alive (mahsool-keepalive.timer). Oracle may reclaim an Always Free VM that looks idle
# for 7 days: CPU (95th percentile), network AND, for Ampere A1, memory all under 20%. The
# backend keeps its models in memory (~5 GB, about 20% of 24 GB); this adds a little work every
# day: the health check and a few minutes of low-priority CPU. It never calls Groq. The sure way
# to avoid reclamation is a Pay As You Go account (Always Free resources stay free), see
# docs/DEPLOY_ORACLE.md.
set -u
curl -fsS -m 30 http://127.0.0.1:8000/health >/dev/null && echo "health OK" || echo "health FAILED"
# ~3 minutes of compression work on 2 cores (nice, so real visitors always come first).
for i in 1 2; do
  nice -n 19 timeout 180 sh -c 'head -c 4000000000 /dev/urandom | gzip -1 > /dev/null' &
done
wait
echo "keep-alive done $(date -u)"
