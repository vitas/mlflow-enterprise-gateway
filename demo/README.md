# Demo: Seeded Multi-Tenant MLflow (AUTH_MODE=off)

This demo seeds reproducible data through the gateway so MLflow UI is non-empty and tenant isolation can be validated immediately.

## One-command seed

```bash
docker compose --profile demo up --build demo-seed
```

This starts `postgres`, `minio`, `mlflow`, `gateway`, and runs one-shot `demo-seed`.

## What gets created

- Tenants: `alpha`, `bravo`
- Per tenant:
  - 1 experiment
  - 2 runs with params/metrics/tags (including tenant tag)
  - 1 registered model + 1 model version (tenant-tagged)

All writes go through the gateway using `X-Tenant` and `X-Subject`.

## Run smoke test

```bash
./demo/smoke_test.sh
```

Checks:

- `alpha` can search its runs
- `bravo` cannot read an `alpha` run (`403`)

## Useful URLs

- Gateway (governed access): `http://localhost:8000/`
- MLflow UI direct (local debug): `http://localhost:5001/`
