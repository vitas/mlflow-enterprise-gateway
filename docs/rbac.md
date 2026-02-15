# RBAC Guide

## RBAC Overview

RBAC is tenant-scoped and uses three internal roles:

- `viewer`
- `contributor`
- `admin`

Role strength order:

`viewer` < `contributor` < `admin`

`contributor` and `admin` satisfy `viewer` permissions. `admin` satisfies `contributor` permissions.

## Permission matrix

| API path | Minimum role |
|---|---|
| `/api/2.0/mlflow/runs/create` | `contributor` |
| `/api/2.1/mlflow/runs/create` | `contributor` |
| `/api/2.0/mlflow/runs/get` | `viewer` |
| `/api/2.1/mlflow/runs/get` | `viewer` |
| `/api/2.0/mlflow/runs/search` | `viewer` |
| `/api/2.1/mlflow/runs/search` | `viewer` |
| `/api/2.0/mlflow/registered-models/create` | `contributor` |
| `/api/2.1/mlflow/registered-models/create` | `contributor` |
| `/api/2.0/mlflow/registered-models/get` | `viewer` |
| `/api/2.1/mlflow/registered-models/get` | `viewer` |
| `/api/2.0/mlflow/registered-models/search` | `viewer` |
| `/api/2.1/mlflow/registered-models/search` | `viewer` |
| `/api/2.0/mlflow/model-versions/create` | `contributor` |
| `/api/2.1/mlflow/model-versions/create` | `contributor` |
| `/api/2.0/mlflow/model-versions/get` | `viewer` |
| `/api/2.1/mlflow/model-versions/get` | `viewer` |

### Notes

- RBAC is enforced in OIDC mode (`GW_AUTH_ENABLED=true` and `AUTH_MODE`/`GW_AUTH_MODE` not `off`) using validated JWT claims.
- In `AUTH_MODE=off`, JWT-based RBAC is not enforced by current code path; this mode is intended for demo/dev.
- Tenant isolation is enforced independently of RBAC for supported tenant policy endpoints. Cross-tenant access is denied (for example, run/model get preflight checks return `403` on tenant mismatch).

Source of truth: gateway/rbac.py::required_role_for_request()

## Role Claim Configuration

Configure claim keys with:

- `GW_ROLE_CLAIM` (or `ROLE_CLAIM`)

It supports a single claim key or CSV list, for example:

- `GW_ROLE_CLAIM=roles`
- `GW_ROLE_CLAIM=roles,groups`

Gateway reads all configured claims and computes the strongest recognized role.

## Role Alias Mapping

Map IdP role/group names to internal roles using CSV aliases:

- `GW_RBAC_VIEWER_ALIASES` (or `RBAC_VIEWER_ALIASES`)
- `GW_RBAC_CONTRIBUTOR_ALIASES` (or `RBAC_CONTRIBUTOR_ALIASES`)
- `GW_RBAC_ADMIN_ALIASES` (or `RBAC_ADMIN_ALIASES`)

### Keycloak example (`groups`)

```bash
export GW_ROLE_CLAIM=groups
export GW_RBAC_VIEWER_ALIASES=mlflow-view,ml-readonly
export GW_RBAC_CONTRIBUTOR_ALIASES=mlflow-write,ml-contrib
export GW_RBAC_ADMIN_ALIASES=mlflow-admin
```

### Azure AD example (`roles,groups`)

```bash
export GW_ROLE_CLAIM=roles,groups
export GW_RBAC_VIEWER_ALIASES=MLflow.Viewer,mlflow-readers
export GW_RBAC_CONTRIBUTOR_ALIASES=MLflow.Contributor,mlflow-contributors
export GW_RBAC_ADMIN_ALIASES=MLflow.Admin,mlflow-admins
```

## JWT Claim Mapping Examples

Example A:

```json
{
  "sub": "alice",
  "tenant_id": "team-a",
  "roles": ["MLflow.Contributor"]
}
```

With `GW_RBAC_CONTRIBUTOR_ALIASES=MLflow.Contributor`, effective role is `contributor`.

Example B:

```json
{
  "sub": "bob",
  "tenant_id": "team-a",
  "groups": ["mlflow-admins", "engineering"]
}
```

With `GW_RBAC_ADMIN_ALIASES=mlflow-admins`, effective role is `admin`.

Example C (multiple claims):

```json
{
  "sub": "carol",
  "tenant_id": "team-a",
  "roles": ["viewer"],
  "groups": ["mlflow-contributors"]
}
```

With `GW_ROLE_CLAIM=roles,groups` and contributor alias mapping, effective role becomes `contributor`.

## Troubleshooting

Common misconfigurations:

- Role claim key mismatch:
  - Gateway expects `GW_ROLE_CLAIM`, but token stores role in another claim.
- Alias mismatch:
  - Token role values do not match configured alias lists.
- Missing claim content:
  - Claim exists but values are empty/non-string.

Common error messages:

- `Missing role claim(s): roles, groups`
  - None of the configured claim keys existed in JWT.
- `No recognized roles found in claim(s): roles, groups`
  - Claim keys existed, but values did not map to `viewer`/`contributor`/`admin`.
- `Insufficient role: required contributor, got viewer`
  - Caller role resolved correctly but is too weak for endpoint.
