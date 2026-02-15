# Release Notes (v0.1.0)

## Implemented features

- FastAPI Policy Enforcement Gateway for MLflow with upstream forwarding via `httpx`.
- OIDC mode with JWT validation, tenant extraction from claims, and strict header semantics.
- Dev/demo mode (`AUTH_MODE=off`) with required `X-Tenant`, optional `X-Subject`, and stripped `Authorization` upstream.
- Tenant isolation MVP for MLflow Runs and Model Registry (create/search/get controls).
- Configurable tenant tag key via `TENANT_TAG_KEY` / `GW_TENANT_TAG_KEY`.
- Minimal RBAC (`viewer`, `contributor`, `admin`) with claim-based mapping and aliases.
- Audit logging for allowed/denied requests, including RBAC deny audit events.
- Health endpoint (`/healthz`) and pytest coverage for auth, tenant policy, RBAC, and health checks.
- Docker Compose local stack (gateway + MLflow + Postgres + MinIO) and runnable demo scripts.
- Kubernetes/OpenShift gateway-only deployment manifests and a minimal Helm chart.
- Enterprise-focused docs: integration, RBAC, Kubernetes, and OpenShift architecture guides.
