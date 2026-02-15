#!/usr/bin/env bash
set -euo pipefail

curl -sS -X POST "http://localhost:8000/api/2.0/mlflow/runs/create" \
  -H "Content-Type: application/json" \
  -H "X-Tenant: team-a" \
  -H "X-Subject: alice" \
  -d '{"experiment_id":"0","tags":[{"key":"demo_case","value":"multi-tenant"}]}'
