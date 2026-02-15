#!/usr/bin/env bash
set -euo pipefail

RUN_ID="${1:-}"
if [ -z "$RUN_ID" ]; then
  echo "Usage: $0 <RUN_ID>"
  exit 1
fi

curl -sS -i -X POST "http://localhost:8000/api/2.0/mlflow/runs/get" \
  -H "Content-Type: application/json" \
  -H "X-Tenant: team-b" \
  -H "X-Subject: bob" \
  -d "{\"run_id\":\"$RUN_ID\"}"
