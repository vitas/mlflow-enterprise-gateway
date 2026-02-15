# Kubernetes Architecture: Gateway-Only MLflow Access

This deployment model enforces that users access MLflow UI and API only through the Policy Enforcement Gateway (PEP).

## Diagram

```mermaid
flowchart LR
    U[User / Browser / SDK]
    I[Ingress]
    G[Gateway (PEP)]
    M[MLflow Service (ClusterIP)]
    DB[(Backend DB - Postgres)]
    OBJ[(Artifact Store - S3/MinIO)]

    U --> I --> G --> M
    M --> DB
    M --> OBJ
```

## Components

- Ingress: public entrypoint that routes traffic only to `gateway` Service.
- Gateway (PEP): FastAPI service that performs authn/authz checks and forwards requests to MLflow.
- MLflow server: private backend service (no Ingress).
- Postgres: MLflow backend metadata store.
- Object storage (MinIO/S3-compatible): MLflow artifact store.

## Request Flow (UI + API)

1. User sends browser/API request to Ingress host/path.
2. Ingress forwards request to `gateway` Service.
3. Gateway validates identity/policy and applies tenant controls.
4. Gateway forwards allowed traffic to MLflow `ClusterIP` service.
5. MLflow reads/writes metadata to Postgres and artifacts to object storage.
6. Response returns to user through Gateway and Ingress.

## Security Controls

- `gateway` is exposed via Ingress; `gateway` Service remains `ClusterIP`.
- `mlflow` Service is `ClusterIP` only and has **no Ingress**.
- NetworkPolicy allows ingress to MLflow pods only from Gateway pods on TCP 5000.
- No public endpoint is defined for MLflow directly.

## Why Gateway-Only

- Tenant isolation and RBAC policies are enforced in one place (the PEP).
- Audit logging and request controls are centralized at the gateway.
- MLflow is kept private to reduce accidental bypass of policy checks.

## Verification

1. Confirm only gateway is externally exposed:
   - `kubectl get ingress`
   - Expect ingress entries only for `gateway`; no ingress for `mlflow`.
2. Confirm services are internal:
   - `kubectl get svc gateway mlflow -o wide`
   - Expect both as `ClusterIP`.
3. Confirm MLflow has no external route/path:
   - `kubectl get ingress | grep -i mlflow` should return nothing for direct MLflow exposure.
4. Confirm NetworkPolicy exists and is enforced:
   - `kubectl get networkpolicy mlflow-only-from-gateway -o yaml`
   - Check `podSelector: app=mlflow` and ingress `from` selector `app=gateway` on port `5000`.

## Operational Notes

- Ensure pod labels match selectors:
  - Gateway pods: `app=gateway`
  - MLflow pods: `app=mlflow`
- Apply manifests in your namespace (examples assume `default`).
