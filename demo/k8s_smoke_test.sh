#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-mlflow-gw-smoke}"
RELEASE="${RELEASE:-gateway}"
LOCAL_PORT="${LOCAL_PORT:-8000}"
GATEWAY_SERVICE="${GATEWAY_SERVICE:-${RELEASE}-gateway}"
GW_URL="${GW_URL:-http://127.0.0.1:${LOCAL_PORT}}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

extract_run_id() {
  if command -v jq >/dev/null 2>&1; then
    jq -r '.run.info.run_id // empty'
  else
    python3 -c 'import json,sys; print(json.load(sys.stdin).get("run",{}).get("info",{}).get("run_id",""))'
  fi
}

need_cmd kubectl
need_cmd curl
need_cmd python3

echo "Checking gateway service..."
kubectl -n "${NAMESPACE}" get svc "${GATEWAY_SERVICE}" >/dev/null

echo "Starting port-forward ${GATEWAY_SERVICE}:${LOCAL_PORT}..."
kubectl -n "${NAMESPACE}" port-forward "svc/${GATEWAY_SERVICE}" "${LOCAL_PORT}:80" >/tmp/gw-port-forward.log 2>&1 &
PF_PID=$!
cleanup() {
  kill "${PF_PID}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "Waiting for gateway health..."
for _ in $(seq 1 60); do
  if curl -fsS "${GW_URL}/healthz" >/dev/null; then
    break
  fi
  sleep 1
done
curl -fsS "${GW_URL}/healthz" >/dev/null

echo "Creating run as tenant team-a..."
CREATE_BODY='{"experiment_id":"0","tags":[{"key":"smoke","value":"k8s"}]}'
CREATE_RESP="$(curl -sS -X POST "${GW_URL}/api/2.0/mlflow/runs/create" \
  -H "Content-Type: application/json" \
  -H "X-Tenant: team-a" \
  -H "X-Subject: smoke-a" \
  -d "${CREATE_BODY}")"

RUN_ID="$(printf '%s' "${CREATE_RESP}" | extract_run_id)"
if [ -z "${RUN_ID}" ]; then
  echo "FAIL: run_id not found in create response" >&2
  echo "${CREATE_RESP}" >&2
  exit 1
fi
echo "✔ run created (${RUN_ID})"

echo "Searching runs as tenant team-a..."
SEARCH_A_CODE="$(curl -sS -o /tmp/search-a.json -w '%{http_code}' -X POST "${GW_URL}/api/2.0/mlflow/runs/search" \
  -H "Content-Type: application/json" \
  -H "X-Tenant: team-a" \
  -d '{"experiment_ids":["0"],"filter":"tags.smoke = '\''k8s'\''"}')"
if [ "${SEARCH_A_CODE}" != "200" ]; then
  echo "FAIL: expected 200 for team-a search, got ${SEARCH_A_CODE}" >&2
  cat /tmp/search-a.json >&2
  exit 1
fi
if ! grep -q "${RUN_ID}" /tmp/search-a.json; then
  echo "FAIL: team-a search did not include created run" >&2
  cat /tmp/search-a.json >&2
  exit 1
fi
echo "✔ tenant-a search returned created run"

echo "Attempting cross-tenant get as team-b..."
GET_B_CODE="$(curl -sS -o /tmp/get-b.json -w '%{http_code}' -X POST "${GW_URL}/api/2.0/mlflow/runs/get" \
  -H "Content-Type: application/json" \
  -H "X-Tenant: team-b" \
  -H "X-Subject: smoke-b" \
  -d "{\"run_id\":\"${RUN_ID}\"}")"
if [ "${GET_B_CODE}" != "403" ]; then
  echo "FAIL: expected 403 for cross-tenant get, got ${GET_B_CODE}" >&2
  cat /tmp/get-b.json >&2
  exit 1
fi
echo "✔ cross-tenant access denied (403)"

echo "Smoke test passed."
