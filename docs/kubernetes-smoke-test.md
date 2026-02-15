# Kubernetes Smoke Test (Local)

This guide validates gateway tenant isolation end-to-end in a local cluster using:

- a minimal single-pod MLflow deployment (internal service only)
- gateway deployment via the existing Helm chart
- `AUTH_MODE=off` for quick local testing

Target runtime: under 10 minutes on a typical laptop.

## Prerequisites

- Docker
- `kubectl`
- `helm`
- one local cluster runtime:
  - `kind` (recommended), or
  - `k3d`

## 1) Start a local cluster

### Option A: kind

```bash
kind create cluster --name mlflow-gw
```

### Option B: k3d

```bash
k3d cluster create mlflow-gw --agents 1
```

## 2) Build local images

```bash
docker build -t mlflow-gateway:smoke .
docker build -f docker/mlflow.Dockerfile -t mlflow-smoke:smoke .
```

## 3) Load images into cluster

### kind

```bash
kind load docker-image mlflow-gateway:smoke --name mlflow-gw
kind load docker-image mlflow-smoke:smoke --name mlflow-gw
```

### k3d

```bash
k3d image import mlflow-gateway:smoke -c mlflow-gw
k3d image import mlflow-smoke:smoke -c mlflow-gw
```

## 4) Deploy MLflow (internal only)

```bash
kubectl create namespace mlflow-gw-smoke
kubectl -n mlflow-gw-smoke apply -f deploy/k8s/smoke/mlflow-smoke.yaml
kubectl -n mlflow-gw-smoke rollout status deploy/mlflow
```

`deploy/k8s/smoke/mlflow-smoke.yaml` creates:

- `Deployment/mlflow` (single pod)
- `Service/mlflow` (`ClusterIP`, no external exposure)

## 5) Deploy gateway via Helm

```bash
helm upgrade --install gateway deploy/helm \
  -n mlflow-gw-smoke \
  -f deploy/helm/values-smoke.yaml

kubectl -n mlflow-gw-smoke rollout status deploy/gateway-gateway
```

This smoke setup uses:

- `GW_TARGET_BASE_URL=http://mlflow:5000`
- `AUTH_MODE=off` (`GW_AUTH_ENABLED=false`)
- gateway service as `ClusterIP`
- no Ingress required

## 6) Verify exposure model

Only gateway should be used for external access in this smoke test:

```bash
kubectl -n mlflow-gw-smoke get svc
kubectl -n mlflow-gw-smoke get ingress
```

Expected:

- `mlflow` service is `ClusterIP` only
- no MLflow ingress/route
- gateway is accessed via port-forward for local test

## 7) Run smoke test

```bash
demo/k8s_smoke_test.sh
```

The script:

- creates a run in tenant `team-a`
- searches runs in tenant `team-a`
- attempts cross-tenant read from tenant `team-b` and expects `403`

If needed, override defaults:

```bash
NAMESPACE=mlflow-gw-smoke RELEASE=gateway LOCAL_PORT=8000 demo/k8s_smoke_test.sh
```

## 8) Cleanup

### kind

```bash
kind delete cluster --name mlflow-gw
```

### k3d

```bash
k3d cluster delete mlflow-gw
```
