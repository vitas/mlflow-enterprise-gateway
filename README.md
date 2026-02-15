# MLflow Multi-Tenancy & Governance Gateway

Policy Enforcement Gateway (PEP) for self-hosted MLflow. It adds tenant isolation, RBAC, audit logging, and OIDC-based IAM integration without modifying MLflow itself. The gateway sits in front of MLflow API/UI traffic and enforces policy before requests reach MLflow.

Self-hosted MLflow is strong for experiment tracking, but it does not provide enterprise multi-tenancy boundaries, built-in RBAC enforcement, centralized audit control, or robust IAM integration patterns out of the box. This project addresses that gap with an extension-layer gateway.

## Why this exists

- Problem:
  - no tenant isolation control point
  - no role-based authorization boundary
  - no centralized audit decision logs
  - weak IAM integration for enterprise SSO/JWT flows
- Solution:
  - place a dedicated PEP in front of MLflow
  - enforce authn/authz/tenant policy at request time
  - keep MLflow upstream intact (no fork, no MLflow code patching)

## Key features

- Tenant isolation for MLflow Runs and Model Registry MVP endpoints.
- Minimal RBAC (`viewer`, `contributor`, `admin`) enforced in OIDC mode.
- OIDC JWT validation with configurable tenant and role claim mapping.
- Structured audit logging, including deny events.
- Configurable tenant tag key (`TENANT_TAG_KEY` / `GW_TENANT_TAG_KEY`).
- Kubernetes/OpenShift gateway-only deployment manifests and minimal Helm chart.

## Quickstart

### 1) Clone and install

```bash
git clone https://github.com/<your-org>/mlflow-enterprise-gateway.git
cd mlflow-enterprise-gateway
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

### 2) Run tests

```bash
pytest -q
```

### 3) Start local stack

```bash
docker compose up --build
```

### 4) Smoke check

```bash
curl -sS http://localhost:8000/healthz
```

## Authentication modes

- `AUTH_MODE=oidc` (production):
  - validates JWTs via OIDC/JWKS
  - tenant is extracted from JWT claim (`GW_TENANT_CLAIM`)
  - RBAC enforced from claims (`GW_ROLE_CLAIM` and aliases)
  - `X-Tenant` header is rejected
- `AUTH_MODE=off` (dev/demo):
  - JWT validation bypassed
  - `X-Tenant` required, `X-Subject` optional
  - `Authorization` ignored and not forwarded upstream
  - useful for local tenant-isolation demos only

## Architecture snapshot

```mermaid
flowchart LR
  U[User / SDK / Browser] --> E[Ingress or Route]
  E --> G[Gateway (PEP)]
  G --> M[MLflow Service]
  M --> DB[(Backend DB)]
  M --> OBJ[(Artifact Store)]
```

## Supported MLflow endpoints (implemented)

Tenant policy and RBAC are currently enforced for:

- Runs:
  - `/api/2.0/mlflow/runs/create` and `/api/2.1/mlflow/runs/create`
  - `/api/2.0/mlflow/runs/get` and `/api/2.1/mlflow/runs/get`
  - `/api/2.0/mlflow/runs/search` and `/api/2.1/mlflow/runs/search`
- Model Registry:
  - `/api/2.0/mlflow/registered-models/create` and `/api/2.1/mlflow/registered-models/create`
  - `/api/2.0/mlflow/registered-models/get` and `/api/2.1/mlflow/registered-models/get`
  - `/api/2.0/mlflow/registered-models/search` and `/api/2.1/mlflow/registered-models/search`
  - `/api/2.0/mlflow/model-versions/create` and `/api/2.1/mlflow/model-versions/create`
  - `/api/2.0/mlflow/model-versions/get` and `/api/2.1/mlflow/model-versions/get`

## Docs

- Integration guide: `docs/integration.md`
- RBAC guide: `docs/rbac.md`
- Kubernetes architecture: `docs/kubernetes-architecture.md`
- OpenShift architecture: `docs/openshift-architecture.md`

## Roadmap

See `ROADMAP.md` for next-release scope and v0.1 completion criteria.

## Support and community

Issues and PRs are welcome. For bug reports, feature requests, and security guidance, use:

- `CONTRIBUTING.md`
- `SECURITY.md`
