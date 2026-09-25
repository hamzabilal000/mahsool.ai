#!/bin/sh
# Install the repo's git hooks. Run once per clone: sh scripts/setup-hooks.sh
set -e
root="$(git rev-parse --show-toplevel)"
hooks="$(git rev-parse --git-path hooks)"
mkdir -p "$hooks"
cp "$root/scripts/commit-msg" "$hooks/commit-msg"
chmod +x "$hooks/commit-msg"
echo "Installed commit-msg hook in $hooks"
