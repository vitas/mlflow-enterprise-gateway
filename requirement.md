# Requirements Prompts Log

## 1) Project Skeleton

- Goal: Create project skeleton for "mlflow-enterprise-gateway" (FastAPI reverse proxy + OIDC JWT validation + audit logging).
- Constraints:
  - Python 3.11+
  - Use FastAPI + httpx
  - Config via env vars
  - Add unit tests (pytest) for JWT parsing and tenant extraction (stub JWKS)
  - Provide Dockerfile and docker-compose for local demo (mlflow + postgres + minio + gateway)
- Definition of Done:
  - `pytest -q` passes
  - `docker compose up` starts gateway and mlflow
  - README contains quickstart

## 2) Repository Review + Health Endpoint

- Review the current repository and:
  1. Explain architecture in 10 bullet points
  2. List missing pieces for MVP
  3. Add minimal health endpoint `/healthz`
  4. Add pytest that checks the endpoint
  5. Ensure `docker compose up` starts successfully
- Constraint: Do not add new features beyond MVP.

## 3) Positioning Rewrite (Docs/Naming)

- Update repository positioning from "reverse proxy" to "MLflow Multi-Tenancy & RBAC Extension".
- Tasks:
  1. Rename README title/description accordingly; use "Policy Enforcement Gateway" or "Extension layer".
  2. Add short "Why" section (tenant isolation, RBAC, audit, IAM gap).
  3. Add "Architecture" section using PEP/PDP terminology.
  4. Ensure current code/comments reflect naming (variables/module docstrings).
  5. Do not change functionality beyond naming/docs.
- Definition of done: README reads like enterprise multi-tenancy extension project.

## 4) Runs Tenant Isolation MVP

- Implement MVP tenant isolation for MLflow RUNS only, without forking MLflow.
- Existing behavior:
  - If `auth_enabled`, validate OIDC JWT and extract tenant via `extract_tenant(claims, tenant_claim)`.
  - Forward request to upstream and return response.
  - Audit logging already exists.
- Requirements:
  1. `AUTH_MODE=off`: use `X-Tenant` (required, else 400); `X-Subject` optional.
  2. Enforce tenant tag on `/api/2.0|2.1/mlflow/runs/create`; merge tags; conflicting tenant tag -> 403.
  3. Enforce tenant filter on `/api/2.0/mlflow/runs/search`; append `and tags.tenant = '<tenant_id>'` safely.
  4. Enforce access on `/api/2.0/mlflow/runs/get` via preflight; mismatch/missing tenant tag -> 403.
  5. Add pytest+respx tests:
     - create injects tenant tag
     - create denies conflicting tag
     - search appends tenant filter
     - get denies other tenant
  6. Keep changes localized:
     - helpers in `gateway/mlflow/tenant.py`
     - handler integration in `gateway/main.py`
  7. Minimal README update only if needed.
- Definition of done:
  - `pytest -q` passes
  - behavior works for `auth_enabled` true and false

## 5) README Demo (AUTH_MODE=off)

- Add README demo section for tenant isolation in `AUTH_MODE=off`.
- Requirements:
  - 4-6 exact curl commands using `X-Tenant` and `X-Subject`
  - show run create + other tenant cannot read it (403) and cannot see it in search
  - short and copy-paste runnable
- Constraint: no code changes.

## 6) Model Registry Tenant Isolation MVP

- Extend tenant isolation to MLflow Model Registry:
  - enforce tenant tagging on create registered model/model version (inject, deny conflicts)
  - enforce tenant filtering on list registered models
  - enforce access control on get registered model/model version via preflight
- Add respx tests similar to runs policy tests.
- Keep changes localized to `gateway/mlflow/tenant.py` and `gateway/main.py`.

## 7) Auth Mode Semantics Hardening

- Requirements:
  1. `AUTH_MODE=off`:
     - ignore `Authorization` header if present
     - log warning and audit event when `Authorization` provided
     - require `X-Tenant` (400 if missing)
     - `X-Subject` optional
  2. `AUTH_MODE=oidc` (`auth_enabled=true`):
     - reject requests containing `X-Tenant` with 400
     - tenant must come only from validated JWT claims
  3. Keep changes minimal/localized in `gateway/main.py`.
  4. Add pytest for:
     - Authorization ignored in off mode
     - missing `X-Tenant` -> 400
     - `X-Tenant` present in OIDC mode -> 400
- Definition of done:
  - pytest passes
  - behavior documented in README auth section

## 8) Tighten AUTH_MODE=off Forwarding

- Requirements:
  1. In `AUTH_MODE=off`, strip `authorization` from `forward_headers` (never forward upstream).
  2. Replace audit `status_code=0` for ignored Authorization with valid status, or remove that audit event (keep warning log).
  3. Add/adjust tests to ensure authorization is not forwarded in off mode.
- Keep changes minimal/localized in `gateway/main.py` and tests.

## 9) Tenant Tag Compatibility (First Request)

- Improve compatibility in `gateway/mlflow/tenant.py`:
  1. Support `tags` as dict and list-of-objects in:
     - `ensure_tenant_tag_for_create`
     - `extract_tenant_tag_from_run_response`
     - `extract_tenant_tag_from_registered_model_response`
     - `extract_tenant_tag_from_model_version_response`
  2. Keep list-of-objects output format when mutating payload.
  3. Add pytest cases for dict-tag create and extract paths.
- Constraint: do not change endpoint logic in `gateway/main.py`.

## 10) Configurable Tenant Tag Key

- Requirements:
  - add setting `tenant_tag_key` (env: `TENANT_TAG_KEY`, also `GW_TENANT_TAG_KEY`), default `"tenant"`
  - use this key everywhere tenant tag is read/written:
    - `ensure_tenant_tag_for_create`
    - `tenant_filter_clause`
    - `ensure_tenant_filter_for_search`
    - `ensure_tenant_filter_for_registered_models_search`
    - all `extract_tenant_tag_from_*`
  - update `gateway/main.py` to pass/use `tenant_tag_key`
  - update README with one line documenting `TENANT_TAG_KEY`
  - add/adjust tests
- Definition of done:
  - `pytest -q` passes
  - default behavior unchanged (`tenant`)

## 11) Tenant Tag Compatibility (Second Request)

- Improve compatibility in `gateway/mlflow/tenant.py`:
  - accept tags as list-of-objects or dict
  - for create mutation:
    - if dict: validate/merge tenant in dict, then convert to list-of-objects
    - if list: keep current behavior
  - for extract functions:
    - list: current logic
    - dict: return `tags.get(tenant_tag_key)` if str
  - add pytest cases:
    - dict create injects and returns list output
    - dict create conflicting tenant -> 403/PermissionError
    - extract from dict returns tenant
- Definition of done:
  - `pytest -q` passes
  - no behavior changes for list-based tags

## 12) README Multi-Tenancy Demo (team-a/team-b)

- Add README demo section for `AUTH_MODE=off` showing multi-tenancy.
- Requirements:
  - exact copy/paste curl commands
  - use `X-Tenant` for `team-a` and `team-b`
  - optional `X-Subject`
  - show run create + run get denial (403) for other tenant
  - show runs/search returns only own tenant runs
  - keep short (10-15 lines)
- Constraint: do not change code.

## 13) Runnable Demo Package in `demo/`

- Create a self-contained demo proving MLflow run tenant isolation with `AUTH_MODE=off` via gateway `http://localhost:8000`.
- Add folder and files:
  - `demo/README.md`
  - `demo/run_demo.sh`
  - `demo/curl/create_run.sh`
  - `demo/curl/get_run_same_tenant.sh`
  - `demo/curl/get_run_other_tenant.sh`
  - `demo/curl/search_other_tenant.sh`
- `demo/README.md` must include:
  - short explanation
  - prerequisite `docker compose up --build`
  - script-based steps
  - expected results (`200`, `403`, empty search)
- `demo/run_demo.sh` must:
  - wait for `/healthz`
  - create run as `team-a`
  - extract `RUN_ID` using `jq` or Python fallback
  - verify same-tenant get `200`
  - verify cross-tenant get `403`
  - verify cross-tenant search is empty
  - print clear SUCCESS/FAIL and exit non-zero on failure
- Curl helper scripts must be minimal and use `http://localhost:8000` with `X-Tenant` headers.
- Script constraints:
  - POSIX-compatible bash
  - `set -euo pipefail`
  - executable (`chmod +x`)
- Constraint: do not modify application code; only add demo assets.
- Definition of done:
  - `docker compose up --build` + `demo/run_demo.sh` demonstrates:
    - ✔ run created
    - ✔ same-tenant access allowed
    - ✔ cross-tenant access denied
    - ✔ cross-tenant search empty
  - all files under `demo/`.
