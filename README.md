# MLflow Multi-Tenancy & Governance Gateway

This project is a Policy Enforcement Gateway (PEP) for self-hosted MLflow. It sits in front of MLflow UI/API traffic and applies centralized identity, tenant, and governance controls before requests reach MLflow.

## Enterprise Gap In Self-Hosted MLflow

Out of the box, self-hosted MLflow typically provides:

- no multi-tenancy isolation controls
- no built-in RBAC enforcement boundary
- no centralized audit policy layer
- limited IAM integration patterns for enterprise SSO/JWT workflows

## How This Project Addresses The Gap

- Enforces access policy at a dedicated gateway (PEP), without forking MLflow.
- Applies tenant-aware request controls for API operations.
- Adds structured audit logging at the control point.
- Integrates with OIDC/JWT-based identity flows.

## Key Benefits

- DB-agnostic: works as an extension layer regardless of MLflow backend store.
- Kubernetes-native: designed for gateway-only exposure patterns in K8s/OpenShift.
- No MLflow fork: keeps upstream MLflow intact and upgrade-friendly.

## Requirements

- Python 3.11+
- Docker + Docker Compose plugin

## Quickstart

### 1. Run unit tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
pytest -q
```

### 2. Start local demo stack

```bash
docker compose up --build
```

Services:

- Gateway: `http://localhost:8000`
- MLflow UI/API (direct): `http://localhost:5001`
- MinIO console: `http://localhost:9001`

Example via gateway:

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/api/2.0/mlflow/experiments/list
```

### AUTH_MODE=off tenant isolation demo (runs)

Start gateway with auth disabled (`GW_AUTH_ENABLED=false` or `AUTH_MODE=off`), then run:

```bash
export GW=http://localhost:8000
RUN_A=$(curl -sS -X POST "$GW/api/2.0/mlflow/runs/create" -H "Content-Type: application/json" -H "X-Tenant: team-a" -H "X-Subject: alice" -d '{"experiment_id":"0","tags":[{"key":"demo_case","value":"multi-tenant"}]}' | python3 -c "import sys,json; print(json.load(sys.stdin)['run']['info']['run_id'])")
RUN_B=$(curl -sS -X POST "$GW/api/2.0/mlflow/runs/create" -H "Content-Type: application/json" -H "X-Tenant: team-b" -H "X-Subject: bob" -d '{"experiment_id":"0","tags":[{"key":"demo_case","value":"multi-tenant"}]}' | python3 -c "import sys,json; print(json.load(sys.stdin)['run']['info']['run_id'])")
curl -sS -X POST "$GW/api/2.0/mlflow/runs/get" -H "Content-Type: application/json" -H "X-Tenant: team-a" -H "X-Subject: alice" -d "{\"run_id\":\"$RUN_A\"}"
curl -i -sS -X POST "$GW/api/2.0/mlflow/runs/get" -H "Content-Type: application/json" -H "X-Tenant: team-b" -H "X-Subject: bob" -d "{\"run_id\":\"$RUN_A\"}"
curl -sS -X POST "$GW/api/2.0/mlflow/runs/search" -H "Content-Type: application/json" -H "X-Tenant: team-a" -d '{"experiment_ids":["0"],"filter":"tags.demo_case = '\''multi-tenant'\''"}'
curl -sS -X POST "$GW/api/2.0/mlflow/runs/search" -H "Content-Type: application/json" -H "X-Tenant: team-b" -d '{"experiment_ids":["0"],"filter":"tags.demo_case = '\''multi-tenant'\''"}'
```

## Architecture

- `gateway` is the Policy Enforcement Point (PEP): it authenticates JWTs, extracts tenant context, and records audit events.
- MLflow remains the control/data plane service behind the extension layer.
- Optional OPA (or another policy engine) can be introduced as the Policy Decision Point (PDP) for externalized authorization decisions.
- In the current MVP, authorization logic is local to the gateway process; PDP integration is an extension point.

## Docs

- Integration guide: `docs/integration.md`
- RBAC guide: `docs/rbac.md`
- Kubernetes architecture: `docs/kubernetes-architecture.md`
- OpenShift architecture: `docs/openshift-architecture.md`

## Kubernetes: gateway-only access

Use `docs/kubernetes-architecture.md` and `deploy/k8s/` to expose only the gateway via Ingress while keeping MLflow private (`ClusterIP` + NetworkPolicy).

## OpenShift deployment: enforce gateway-only access

Use the OpenShift architecture and manifests in `docs/openshift-architecture.md` and `deploy/openshift/` to expose only the gateway via Route while keeping MLflow private (`ClusterIP` + NetworkPolicy).

## Configuration (env vars)

All gateway settings use `GW_` prefix.

- `GW_TARGET_BASE_URL` (default: `http://mlflow:5000`)
- `GW_AUTH_ENABLED` (`true`/`false`, default: `true`)
- `GW_AUTH_MODE` / `AUTH_MODE` (`off` disables JWT validation for local development)
- `GW_OIDC_ISSUER` (optional)
- `GW_OIDC_AUDIENCE` (optional)
- `GW_OIDC_ALGORITHMS` (default: `["RS256"]`)
- `GW_JWKS_URI` (optional if `GW_JWKS_JSON` set)
- `GW_JWKS_JSON` (inline JWKS JSON; useful for tests)
- `GW_TENANT_CLAIM` (default: `tenant_id`)
- `TENANT_TAG_KEY` / `GW_TENANT_TAG_KEY` (default: `tenant`)
- `GW_LOG_LEVEL` (default: `INFO`)

Auth mode behavior:
- `AUTH_MODE=off` (or `GW_AUTH_ENABLED=false`): JWT auth is bypassed, `Authorization` header is ignored, `X-Tenant` is required, and `X-Subject` is optional.
- `AUTH_MODE=oidc` with `GW_AUTH_ENABLED=true`: tenant is derived only from validated JWT claims; `X-Tenant` header is rejected with `400`.

## OIDC mode example

Set these when enabling auth:

```bash
export GW_AUTH_ENABLED=true
export GW_OIDC_ISSUER=https://issuer.example.com/
export GW_OIDC_AUDIENCE=mlflow-gateway
export GW_JWKS_URI=https://issuer.example.com/.well-known/jwks.json
```

Then run:

```bash
uvicorn gateway.main:app --host 0.0.0.0 --port 8000
```

## Project layout

```text
gateway/
  config.py
  auth.py
  audit.py
  main.py
tests/
  test_jwt.py
  test_tenant.py
Dockerfile
docker-compose.yml
docker/mlflow.Dockerfile
```
