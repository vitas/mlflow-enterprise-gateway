# Demo: MLflow Runs Multi-Tenancy (AUTH_MODE=off)

This demo proves tenant isolation for MLflow runs through the Policy Enforcement Gateway at `http://localhost:8000`.

Prerequisite:

```bash
docker compose up --build
```

Run the demo:

```bash
./demo/run_demo.sh
```

Optional direct curl helpers:

```bash
./demo/curl/create_run.sh
./demo/curl/get_run_same_tenant.sh <RUN_ID>
./demo/curl/get_run_other_tenant.sh <RUN_ID>
./demo/curl/search_other_tenant.sh
```

Expected results:

- create run: `200`
- get as same tenant (`team-a`): `200`
- get as other tenant (`team-b`): `403`
- search as other tenant (`team-b`): empty run list
