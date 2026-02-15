#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

GW_URL="http://localhost:8000"
CREATE_ENDPOINT="$GW_URL/api/2.0/mlflow/runs/create"
GET_ENDPOINT="$GW_URL/api/2.0/mlflow/runs/get"
SEARCH_ENDPOINT="$GW_URL/api/2.0/mlflow/runs/search"

ensure_compose_running() {
  if docker compose -f "$REPO_ROOT/docker-compose.yml" ps --services --filter status=running | grep -q '^gateway$'; then
    return 0
  fi
  echo "Gateway is not running. Starting stack with docker compose up -d --build ..."
  docker compose -f "$REPO_ROOT/docker-compose.yml" up -d --build
}

wait_for_gateway() {
  echo "Waiting for gateway at $GW_URL/healthz ..."
  i=0
  while [ "$i" -lt 60 ]; do
    if curl -fsS "$GW_URL/healthz" >/dev/null 2>&1; then
      return 0
    fi
    i=$((i + 1))
    sleep 1
  done
  echo "FAIL: gateway did not become ready in time"
  return 1
}

extract_run_id() {
  body="$1"
  if command -v jq >/dev/null 2>&1; then
    printf '%s' "$body" | jq -r '.run.info.run_id // empty'
  else
    printf '%s' "$body" | python3 -c 'import json,sys; d=json.load(sys.stdin); print((d.get("run",{}).get("info",{}).get("run_id","")))'
  fi
}

ensure_compose_running
wait_for_gateway

create_body='{"experiment_id":"0","tags":[{"key":"demo_case","value":"multi-tenant"}]}'
create_resp=$(curl -sS -w '\n%{http_code}' -X POST "$CREATE_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "X-Tenant: team-a" \
  -H "X-Subject: alice" \
  -d "$create_body")
create_code=$(printf '%s' "$create_resp" | tail -n1)
create_json=$(printf '%s' "$create_resp" | sed '$d')

if [ "$create_code" != "200" ]; then
  echo "FAIL: run creation returned HTTP $create_code"
  echo "$create_json"
  exit 1
fi

RUN_ID=$(extract_run_id "$create_json")
if [ -z "$RUN_ID" ]; then
  echo "FAIL: could not extract RUN_ID"
  echo "$create_json"
  exit 1
fi

echo "✔ run created ($RUN_ID)"

same_resp=$(curl -sS -w '\n%{http_code}' -X POST "$GET_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "X-Tenant: team-a" \
  -H "X-Subject: alice" \
  -d "{\"run_id\":\"$RUN_ID\"}")
same_code=$(printf '%s' "$same_resp" | tail -n1)
if [ "$same_code" != "200" ]; then
  echo "FAIL: same-tenant get returned HTTP $same_code"
  exit 1
fi

echo "✔ same-tenant access allowed"

other_resp=$(curl -sS -w '\n%{http_code}' -X POST "$GET_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "X-Tenant: team-b" \
  -H "X-Subject: bob" \
  -d "{\"run_id\":\"$RUN_ID\"}")
other_code=$(printf '%s' "$other_resp" | tail -n1)
if [ "$other_code" != "403" ]; then
  echo "FAIL: cross-tenant get expected 403, got $other_code"
  exit 1
fi

echo "✔ cross-tenant access denied"

search_resp=$(curl -sS -w '\n%{http_code}' -X POST "$SEARCH_ENDPOINT" \
  -H "Content-Type: application/json" \
  -H "X-Tenant: team-b" \
  -H "X-Subject: bob" \
  -d '{"experiment_ids":["0"],"filter":"tags.demo_case = '\''multi-tenant'\''"}')
search_code=$(printf '%s' "$search_resp" | tail -n1)
search_json=$(printf '%s' "$search_resp" | sed '$d')
if [ "$search_code" != "200" ]; then
  echo "FAIL: cross-tenant search returned HTTP $search_code"
  exit 1
fi

if command -v jq >/dev/null 2>&1; then
  empty_search=$(printf '%s' "$search_json" | jq -e '.runs | length == 0' >/dev/null 2>&1; echo $?)
else
  empty_search=$(printf '%s' "$search_json" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(0 if len(d.get("runs", []))==0 else 1)')
fi

if [ "$empty_search" != "0" ]; then
  echo "FAIL: cross-tenant search was not empty"
  echo "$search_json"
  exit 1
fi

echo "✔ cross-tenant search empty"

echo "SUCCESS: tenant isolation demo passed"
