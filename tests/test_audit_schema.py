import json
from datetime import datetime

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from gateway.config import settings
from gateway.main import app


@pytest.fixture(autouse=True)
def _configure_gateway(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "auth_enabled", False)
    monkeypatch.setattr(settings, "auth_mode", "off")
    monkeypatch.setattr(settings, "target_base_url", "http://mlflow:5000")
    monkeypatch.setattr(settings, "tenant_tag_key", "tenant")


def _parse_last_audit_event(caplog: pytest.LogCaptureFixture) -> dict:
    records = [r for r in caplog.records if r.name == "gateway.audit"]
    assert records, "expected at least one audit log record"
    return json.loads(records[-1].message)


def test_audit_schema_v1_on_allow(caplog: pytest.LogCaptureFixture):
    caplog.set_level("INFO", logger="gateway.audit")

    with respx.mock(assert_all_called=True) as mock:
        mock.post("http://mlflow:5000/api/2.0/mlflow/runs/search").mock(
            return_value=httpx.Response(200, json={"runs": []})
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/search",
            headers={"X-Tenant": "team-a"},
            json={"experiment_ids": ["0"]},
        )

    assert response.status_code == 200
    event = _parse_last_audit_event(caplog)

    required = {
        "schema_version",
        "timestamp",
        "request_id",
        "tenant",
        "subject",
        "method",
        "path",
        "status_code",
        "upstream",
        "decision",
    }
    assert required.issubset(event.keys())
    assert event["schema_version"] == "1"
    datetime.fromisoformat(event["timestamp"])
    assert event["request_id"] == response.headers["x-request-id"]
    assert event["tenant"] == "team-a"
    assert event["subject"] is None
    assert event["method"] == "POST"
    assert event["path"] == "/api/2.0/mlflow/runs/search"
    assert event["status_code"] == 200
    assert event["decision"] == "allow"


def test_audit_schema_v1_on_payload_400(caplog: pytest.LogCaptureFixture):
    caplog.set_level("INFO", logger="gateway.audit")

    client = TestClient(app)
    response = client.post(
        "/api/2.0/mlflow/runs/search",
        headers={"X-Tenant": "team-a"},
        json={"experiment_ids": ["0"], "filter": 123},
    )

    assert response.status_code == 400
    event = _parse_last_audit_event(caplog)

    assert event["schema_version"] == "1"
    assert event["status_code"] == 400
    assert event["decision"] == "deny"
    assert "Invalid MLflow payload" in event.get("reason", "")
