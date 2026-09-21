#!/usr/bin/env bash
# Start MarketPulse locally: backend on :8000, frontend on :5173.
#
# If the UI shows no data, the usual cause is simply that nothing is running —
# the frontend proxies /api to :8000 and renders empty when that refuses.
#
#   ./dev.sh          start both, stream logs, Ctrl-C stops both
#
# Use venv/ and not .venv/: venv/ is the complete environment, and the console
# scripts in both carry a dead shebang from the project's former ~/Desktop path,
# so everything must go through `python -m`.
set -euo pipefail
cd "$(dirname "$0")"

for port in 8000 5173; do
  if lsof -ti:"$port" >/dev/null 2>&1; then
    echo "port $port already in use by pid(s): $(lsof -ti:"$port" | tr '\n' ' ')"
    echo "stop it first, or run: lsof -ti:$port | xargs kill"
    exit 1
  fi
done

[ -d venv ] || { echo "venv/ missing — create it, then: venv/bin/python -m pip install -r requirements.txt"; exit 1; }
[ -d frontend/node_modules ] || { echo "installing frontend deps..."; (cd frontend && npm install); }

cleanup() { echo; echo "stopping..."; kill 0 2>/dev/null; }
trap cleanup EXIT INT TERM

echo "backend  -> http://localhost:8000  (docs at /docs)"
venv/bin/python run.py 2>&1 | sed 's/^/[api] /' &

echo "frontend -> http://localhost:5173"
(cd frontend && npm run dev) 2>&1 | sed 's/^/[web] /' &

wait
