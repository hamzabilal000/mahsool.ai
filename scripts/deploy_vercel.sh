#!/usr/bin/env sh
# Deploy the frontend to Vercel (project "mahsool-ai") from the command line:
#   VERCEL_TOKEN=... sh scripts/deploy_vercel.sh
# The API address comes from frontend/.env.production. Prints the production URL at the end.
# Without a token: vercel.com -> Add New -> Project -> import this GitHub repo, Root Directory
# "frontend", Deploy (README "Deploy").
set -eu
: "${VERCEL_TOKEN:?set VERCEL_TOKEN (vercel.com -> Account Settings -> Tokens)}"
cd "$(dirname "$0")/../frontend"
npx --yes vercel@latest link --yes --project mahsool-ai --token "$VERCEL_TOKEN"
npx --yes vercel@latest deploy --prod --yes --token "$VERCEL_TOKEN"
