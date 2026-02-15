# Release Notes

## v0.2.0

- Added `/readyz` endpoint for readiness checks against MLflow upstream reachability.
- `/healthz` remains a simple liveness endpoint.
- Added readiness unit tests for reachable and unavailable upstream scenarios.
- Updated README with `/healthz` vs `/readyz` behavior and Kubernetes probe example.
- Bumped project and Helm chart version to `0.2.0`.
- Introduced structured audit schema v1 (`schema_version`, `request_id`, `decision`, optional `reason`) for SIEM-friendly logs.
- Added optional `GW_RBAC_DEFAULT_DENY` mode to deny unknown API paths with `403`.
- Added audit schema and default-deny test coverage.
- Added audit documentation in `docs/audit.md` and updated RBAC docs for default-deny behavior.

## v0.1.0

- FastAPI Policy Enforcement Gateway for MLflow with upstream forwarding via `httpx`.
- OIDC mode with JWT validation, tenant extraction from claims, and strict header semantics.
- Dev/demo mode (`AUTH_MODE=off`) with required `X-Tenant`, optional `X-Subject`, and stripped `Authorization` upstream.
- Tenant isolation MVP for MLflow Runs and Model Registry (create/search/get controls).
- Configurable tenant tag key via `TENANT_TAG_KEY` / `GW_TENANT_TAG_KEY`.
- Minimal RBAC (`viewer`, `contributor`, `admin`) with claim-based mapping and aliases.
- Audit logging for allowed/denied requests, including RBAC deny audit events.
- Request correlation IDs (`X-Request-ID`) in responses and audit events.
- Health endpoint (`/healthz`) and pytest coverage for auth, tenant policy, RBAC, and health checks.
- Docker Compose local stack (gateway + MLflow + Postgres + MinIO) and runnable demo scripts.
- Kubernetes/OpenShift gateway-only deployment manifests and a minimal Helm chart.
- Minimal Kubernetes smoke-test workflow (kind/k3d + Helm + tenant-isolation script).
- Enterprise-focused docs: integration, RBAC, Kubernetes/OpenShift architecture, and Kubernetes smoke-test guide.
