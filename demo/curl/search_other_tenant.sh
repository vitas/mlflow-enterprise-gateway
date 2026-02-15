#!/usr/bin/env bash
set -euo pipefail

curl -sS -X POST "http://localhost:8000/api/2.0/mlflow/runs/search" \
  -H "Content-Type: application/json" \
  -H "X-Tenant: team-b" \
  -H "X-Subject: bob" \
  -d '{"experiment_ids":["0"],"filter":"tags.demo_case = '\''multi-tenant'\''"}'
