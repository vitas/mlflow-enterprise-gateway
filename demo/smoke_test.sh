#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

GW_URL="${GW_URL:-http://localhost:8000}"
SEED_OUTPUT="${SEED_OUTPUT:-${REPO_ROOT}/demo/seed-output.json}"
RUN_SEARCH_PATH="/api/2.0/mlflow/runs/search"
RUN_GET_PATH="/api/2.0/mlflow/runs/get"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

extract_first_run_id() {
  if command -v jq >/dev/null 2>&1; then
    jq -r '.runs[0].info.run_id // empty'
  else
    python3 -c 'import json,sys; d=json.load(sys.stdin); runs=d.get("runs",[]); print(runs[0].get("info",{}).get("run_id","") if runs else "")'
  fi
}

extract_alpha_experiment_id() {
  if command -v jq >/dev/null 2>&1; then
    jq -r '.alpha.experiment_id // empty'
  else
    python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("alpha",{}).get("experiment_id",""))'
  fi
}

need_cmd curl
need_cmd python3

echo "Waiting for gateway readiness at ${GW_URL}/readyz ..."
for _ in $(seq 1 90); do
  if curl -fsS "${GW_URL}/readyz" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -fsS "${GW_URL}/readyz" >/dev/null

if [ ! -f "${SEED_OUTPUT}" ]; then
  echo "Seed output not found. Running demo seeding first ..."
  if ! command -v docker >/dev/null 2>&1; then
    echo "FAIL: docker not found and ${SEED_OUTPUT} is missing." >&2
    exit 1
  fi
  docker compose -f "${REPO_ROOT}/docker-compose.yml" --profile demo up --build demo-seed
fi

ALPHA_EXP_ID="$(extract_alpha_experiment_id < "${SEED_OUTPUT}")"
if [ -z "${ALPHA_EXP_ID}" ]; then
  echo "FAIL: could not read alpha experiment_id from ${SEED_OUTPUT}" >&2
  exit 1
fi

echo "Searching runs for tenant alpha ..."
ALPHA_SEARCH="$(curl -sS -w '\n%{http_code}' -X POST "${GW_URL}${RUN_SEARCH_PATH}" \
  -H "Content-Type: application/json" \
  -H "X-Tenant: alpha" \
  -H "X-Subject: alpha-check" \
  -d "{\"experiment_ids\":[\"${ALPHA_EXP_ID}\"]}")"
ALPHA_CODE="$(printf '%s' "${ALPHA_SEARCH}" | tail -n1)"
ALPHA_JSON="$(printf '%s' "${ALPHA_SEARCH}" | sed '$d')"

if [ "${ALPHA_CODE}" != "200" ]; then
  echo "FAIL: alpha search returned ${ALPHA_CODE}" >&2
  echo "${ALPHA_JSON}" >&2
  exit 1
fi

RUN_ID="$(printf '%s' "${ALPHA_JSON}" | extract_first_run_id)"
if [ -z "${RUN_ID}" ]; then
  echo "FAIL: no seeded alpha run found (run demo/seed.py first)." >&2
  exit 1
fi
echo "✔ alpha can search its runs (${RUN_ID})"

echo "Checking cross-tenant denial (bravo reading alpha run) ..."
BRAVO_GET_CODE="$(curl -sS -o /tmp/demo-bravo-get.json -w '%{http_code}' -G "${GW_URL}${RUN_GET_PATH}" \
  -H "X-Tenant: bravo" \
  -H "X-Subject: bravo-check" \
  --data-urlencode "run_id=${RUN_ID}")"
if [ "${BRAVO_GET_CODE}" != "403" ]; then
  echo "FAIL: expected 403 for cross-tenant read, got ${BRAVO_GET_CODE}" >&2
  cat /tmp/demo-bravo-get.json >&2
  exit 1
fi
echo "✔ bravo cannot access alpha run (403)"

echo
echo "MLflow UI (via gateway): ${GW_URL}/"
echo "Direct MLflow UI (local debug only): http://localhost:5001/"
echo "Use gateway URL for governed access."
