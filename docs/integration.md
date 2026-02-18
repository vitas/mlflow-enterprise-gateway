# Enterprise Integration Guide

## Overview

`mlflow-enterprise-gateway` is a Policy Enforcement Gateway (PEP) in front of MLflow. It provides:

- OIDC JWT validation in production mode
- tenant-context enforcement for supported MLflow APIs
- RBAC enforcement by role
- centralized audit logging at the gateway boundary

The integration model is extension-only: MLflow is not forked or modified.

## Prerequisites

- MLflow deployment (API/UI reachable by gateway inside the network)
- backend metadata DB (for example Postgres)
- artifact store (for example MinIO/S3-compatible)
- Kubernetes or OpenShift deployment platform
- IdP with OIDC support (issuer, JWKS, audience)
- TLS for external endpoint (Ingress or Route)
- NetworkPolicy support in cluster CNI

## Supported Integration Modes

### `AUTH_MODE=oidc` (production)

- Recommended for production.
- Gateway validates JWT, extracts tenant from claim, enforces RBAC and tenant policies.
- Requests must carry `Authorization: Bearer <token>`.
- `X-Tenant` is rejected in this mode.

### `AUTH_MODE=off` (dev/demo only)

- Use only for local development or demo.
- JWT validation is bypassed.
- `X-Tenant` header is required for each request.
- `X-Subject` is optional.
- `Authorization` header is ignored and not forwarded upstream.

## Identity and platform integrations

### Supported identity integrations

The gateway supports identity integration through OIDC/OAuth2 JWT validation. Typical enterprise providers:

- Generic OIDC/OAuth2 providers (standards-compliant issuer + JWKS)
- Keycloak
- Azure AD / Entra ID
- Okta (via standard OIDC configuration)

### Optional SSO proxy pattern

If browser SSO/session handling is required, deploy an auth proxy (for example `oauth2-proxy`) in front of the gateway:

- auth proxy responsibility: login flow, session/cookie handling, IdP redirect
- gateway responsibility: tenant-aware authorization, RBAC, and audit enforcement

Reference flow:

`User -> Ingress/Route -> oauth2-proxy -> Gateway (PEP) -> MLflow`

Integration is configured with existing gateway env vars (`GW_OIDC_ISSUER`, `GW_JWKS_URI`, `GW_OIDC_AUDIENCE`, `GW_ROLE_CLAIM`, `GW_TENANT_CLAIM`, and RBAC alias settings when needed).

### LDAP / Active Directory integration model

LDAP/AD is supported indirectly through IdP federation, not by direct gateway LDAP binding. Typical patterns:

- LDAP/AD users and groups are synchronized or federated into Keycloak.
- LDAP/AD identities are represented in Azure AD / Entra ID.
- IdP issues OIDC JWTs consumed by the gateway.

Direct LDAP integration in the gateway is intentionally out of scope by design. The gateway remains focused on policy enforcement, while identity lifecycle, authentication, and directory integration stay in the IdP layer.

### Reference flow

Directory-backed identity flow in enterprise deployments:

`LDAP/AD -> IdP -> OIDC JWT -> Gateway (PEP) -> MLflow`

## Step-by-Step Integration

### 1) Deploy gateway

- Deploy gateway as an internal service in the same cluster/namespace as MLflow.
- Set labels consistently (`app=gateway`, `app=mlflow`) for NetworkPolicy selectors.

### 2) Configure `GW_TARGET_BASE_URL`

Set MLflow upstream base URL reachable from gateway, for example:

```bash
export GW_TARGET_BASE_URL=http://mlflow:5000
```

### 3) Expose only gateway externally

- Expose `gateway` via Ingress (Kubernetes) or Route (OpenShift).
- Keep `mlflow` service internal (`ClusterIP`) with no Ingress/Route.
- Apply NetworkPolicy so MLflow accepts traffic only from gateway pods.

See:
- `docs/kubernetes-architecture.md`
- `docs/openshift-architecture.md`

### 4) Configure OIDC and tenant claim

Example production env:

```bash
export GW_AUTH_ENABLED=true
export GW_AUTH_MODE=oidc
export GW_OIDC_ISSUER=https://idp.example.com/realms/ml
export GW_OIDC_AUDIENCE=mlflow-gateway
export GW_JWKS_URI=https://idp.example.com/realms/ml/protocol/openid-connect/certs
export GW_TENANT_CLAIM=tenant_id
```

Optional role settings:

```bash
export GW_ROLE_CLAIM=roles,groups
```

### 5) Verify with curl

Health:

```bash
curl -sS http://localhost:8000/healthz
```

OIDC mode request (expected `401` if token is missing/invalid):

```bash
curl -i -sS -X POST http://localhost:8000/api/2.0/mlflow/runs/search \
  -H "Content-Type: application/json" \
  -d '{"experiment_ids":["0"]}'
```

Dev mode request (expected `400` if `X-Tenant` missing in `AUTH_MODE=off`):

```bash
curl -i -sS -X POST http://localhost:8000/api/2.0/mlflow/runs/search \
  -H "Content-Type: application/json" \
  -d '{"experiment_ids":["0"]}'
```

Dev mode request with tenant (expected `200`):

```bash
curl -i -sS -X POST http://localhost:8000/api/2.0/mlflow/runs/search \
  -H "Content-Type: application/json" \
  -H "X-Tenant: team-a" \
  -d '{"experiment_ids":["0"]}'
```

## Operational Notes

- Audit/logging:
  - Denied auth and RBAC decisions are audited at the gateway.
  - Keep gateway logs centralized (for example via cluster log pipeline).
- Scaling:
  - Run multiple gateway replicas behind one Service.
  - Gateway is stateless; scale horizontally.
- Timeouts:
  - Tune `GW_REQUEST_TIMEOUT_SECONDS` based on MLflow API latency and upstream behavior.

## Related Docs

- RBAC details: `docs/rbac.md`
- Kubernetes architecture: `docs/kubernetes-architecture.md`
- OpenShift architecture: `docs/openshift-architecture.md`
