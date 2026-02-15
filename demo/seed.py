#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000").rstrip("/")
OUTPUT_PATH = os.getenv("DEMO_OUTPUT_PATH", "/demo/seed-output.json")
TENANTS = ("alpha", "bravo")


def _now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def _request(
    method: str,
    path: str,
    *,
    tenant: str | None = None,
    subject: str | None = None,
    payload: dict | None = None,
    query: dict | None = None,
) -> tuple[int, dict]:
    url = f"{GATEWAY_URL}{path}"
    if query:
        url = f"{url}?{urllib.parse.urlencode(query)}"

    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if tenant:
        headers["X-Tenant"] = tenant
    if subject:
        headers["X-Subject"] = subject

    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8") or "{}"
            return resp.getcode(), json.loads(body)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") or "{}"
        try:
            parsed = json.loads(body)
        except json.JSONDecodeError:
            parsed = {"detail": body}
        return exc.code, parsed
    except urllib.error.URLError as exc:
        return 0, {"detail": str(exc)}


def wait_for_gateway_ready() -> None:
    for _ in range(120):
        code, _ = _request("GET", "/readyz")
        if code == 200:
            return
        time.sleep(1)
    raise RuntimeError(f"Gateway not ready at {GATEWAY_URL}/readyz")


def create_or_get_experiment(tenant: str, subject: str, name: str) -> str:
    code, body = _request(
        "POST",
        "/api/2.0/mlflow/experiments/create",
        tenant=tenant,
        subject=subject,
        payload={"name": name},
    )
    if code == 200:
        return str(body["experiment_id"])

    code, body = _request(
        "GET",
        "/api/2.0/mlflow/experiments/get-by-name",
        tenant=tenant,
        subject=subject,
        query={"experiment_name": name},
    )
    if code == 200 and isinstance(body.get("experiment"), dict):
        return str(body["experiment"]["experiment_id"])
    raise RuntimeError(f"Failed to create/get experiment {name}: {code} {body}")


def create_run(tenant: str, subject: str, experiment_id: str, idx: int) -> str:
    tags = [
        {"key": "tenant", "value": tenant},
        {"key": "demo_seed", "value": "true"},
        {"key": "seed_tenant", "value": tenant},
        {"key": "seed_run", "value": str(idx)},
    ]
    code, body = _request(
        "POST",
        "/api/2.0/mlflow/runs/create",
        tenant=tenant,
        subject=subject,
        payload={"experiment_id": experiment_id, "tags": tags},
    )
    if code != 200:
        raise RuntimeError(f"Failed to create run for {tenant}: {code} {body}")
    run_id = body.get("run", {}).get("info", {}).get("run_id")
    if not isinstance(run_id, str) or not run_id:
        raise RuntimeError(f"Missing run_id in response: {body}")
    return run_id


def log_run_data(tenant: str, subject: str, run_id: str, idx: int) -> None:
    payload = {
        "run_id": run_id,
        "params": [
            {"key": "learning_rate", "value": f"0.0{idx}"},
            {"key": "tenant", "value": tenant},
        ],
        "metrics": [
            {"key": "accuracy", "value": 0.8 + (idx * 0.05), "timestamp": _now_ms(), "step": idx}
        ],
        "tags": [{"key": "seed_source", "value": "docker-compose-demo"}],
    }
    code, body = _request(
        "POST",
        "/api/2.0/mlflow/runs/log-batch",
        tenant=tenant,
        subject=subject,
        payload=payload,
    )
    if code != 200:
        raise RuntimeError(f"Failed to log run data for {run_id}: {code} {body}")


def create_or_get_registered_model(tenant: str, subject: str, model_name: str) -> None:
    payload = {
        "name": model_name,
        "tags": [
            {"key": "tenant", "value": tenant},
            {"key": "demo_seed", "value": "true"},
        ],
    }
    code, body = _request(
        "POST",
        "/api/2.0/mlflow/registered-models/create",
        tenant=tenant,
        subject=subject,
        payload=payload,
    )
    if code == 200:
        return

    code, _ = _request(
        "POST",
        "/api/2.0/mlflow/registered-models/get",
        tenant=tenant,
        subject=subject,
        payload={"name": model_name},
    )
    if code != 200:
        raise RuntimeError(f"Failed to create/get registered model {model_name}: {code} {body}")


def create_model_version(
    tenant: str, subject: str, model_name: str, source_run_id: str
) -> str:
    payload = {
        "name": model_name,
        "source": f"runs:/{source_run_id}/model",
        "run_id": source_run_id,
        "tags": [
            {"key": "tenant", "value": tenant},
            {"key": "demo_seed", "value": "true"},
        ],
    }
    code, body = _request(
        "POST",
        "/api/2.0/mlflow/model-versions/create",
        tenant=tenant,
        subject=subject,
        payload=payload,
    )
    if code != 200:
        raise RuntimeError(f"Failed to create model version for {model_name}: {code} {body}")
    version = body.get("model_version", {}).get("version")
    if not isinstance(version, str):
        version = str(version)
    return version


def main() -> None:
    print(f"Seeding demo data through gateway: {GATEWAY_URL}")
    wait_for_gateway_ready()

    out: dict[str, dict] = {}
    for tenant in TENANTS:
        subject = f"{tenant}-seed"
        experiment_name = f"demo-{tenant}-exp"
        model_name = f"demo-{tenant}-model"

        experiment_id = create_or_get_experiment(tenant, subject, experiment_name)
        run_ids: list[str] = []
        for idx in (1, 2):
            run_id = create_run(tenant, subject, experiment_id, idx)
            log_run_data(tenant, subject, run_id, idx)
            run_ids.append(run_id)

        create_or_get_registered_model(tenant, subject, model_name)
        model_version = create_model_version(tenant, subject, model_name, run_ids[0])

        out[tenant] = {
            "experiment_name": experiment_name,
            "experiment_id": experiment_id,
            "run_ids": run_ids,
            "model_name": model_name,
            "model_version": model_version,
        }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    print(f"Seed complete. Output written to {OUTPUT_PATH}")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
