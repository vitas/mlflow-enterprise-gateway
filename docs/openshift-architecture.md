# OpenShift Architecture: Gateway-Only MLflow Access

This deployment model enforces that MLflow UI and API are reachable only through the Policy Enforcement Gateway (PEP).

## Components

- OpenShift Route: external entrypoint to the `gateway` Service.
- Gateway (PEP): enforces auth/policy and forwards requests to MLflow.
- MLflow server: internal service only (no Route).
- Postgres: backend metadata database for MLflow.
- Object storage (MinIO/S3-compatible): artifact storage.

## Request Flow (UI and API)

1. User/browser/API client calls the gateway Route hostname.
2. OpenShift router terminates/routes traffic to `gateway` Service.
3. Gateway validates identity/policy and applies tenant controls.
4. Gateway forwards allowed traffic to internal `mlflow` Service (`ClusterIP`).
5. MLflow persists metadata to Postgres and artifacts to object storage.
6. Response returns to client through Gateway and Route.

## OpenShift-Specific Controls

- Route exists only for `gateway`; do not create a Route for `mlflow`.
- Both `gateway` and `mlflow` Services are `ClusterIP`.
- NetworkPolicy restricts ingress to `mlflow` pods to only `gateway` pods on TCP 5000.
- Resources are namespaced per OpenShift project; apply manifests in the target project/namespace.

## Access Pattern

- UI: `https://<gateway-route-host>/`
- API: `https://<gateway-route-host>/api/2.0/mlflow/...`

All user access to MLflow must go through the gateway Route.
