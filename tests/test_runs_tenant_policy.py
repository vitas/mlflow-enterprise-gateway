import json

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from gateway.config import settings
from gateway.main import app


@pytest.fixture(autouse=True)
def _configure_gateway(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "auth_enabled", False)
    monkeypatch.setattr(settings, "auth_mode", "oidc")
    monkeypatch.setattr(settings, "target_base_url", "http://mlflow:5000")
    monkeypatch.setattr(settings, "tenant_tag_key", "tenant")


def test_create_injects_tenant_tag():

    with respx.mock(assert_all_called=True) as mock:
        def _assert_request(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert {"key": "tenant", "value": "tenant-a"} in payload["tags"]
            assert {"key": "project", "value": "demo"} in payload["tags"]
            return httpx.Response(200, json={"run": {"info": {"run_id": "r-1"}}})

        mock.post("http://mlflow:5000/api/2.0/mlflow/runs/create").mock(side_effect=_assert_request)
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/create",
            json={"experiment_id": "1", "tags": [{"key": "project", "value": "demo"}]},
            headers={"X-Tenant": "tenant-a"},
        )

    assert response.status_code == 200


def test_create_denies_conflicting_tenant_tag():
    with respx.mock(assert_all_called=False) as mock:
        route = mock.post("http://mlflow:5000/api/2.0/mlflow/runs/create").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/create",
            json={"tags": [{"key": "tenant", "value": "other-tenant"}]},
            headers={"X-Tenant": "tenant-a"},
        )

    assert response.status_code == 403
    assert route.called is False


def test_search_appends_tenant_filter():
    with respx.mock(assert_all_called=True) as mock:
        def _assert_request(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert payload["filter"] == "(attributes.status = 'RUNNING') and tags.tenant = 'tenant-a'"
            return httpx.Response(200, json={"runs": []})

        mock.post("http://mlflow:5000/api/2.0/mlflow/runs/search").mock(side_effect=_assert_request)
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/search",
            json={"experiment_ids": ["1"], "filter": "attributes.status = 'RUNNING'"},
            headers={"X-Tenant": "tenant-a"},
        )

    assert response.status_code == 200


def test_get_denies_access_to_other_tenant():
    with respx.mock(assert_all_called=True) as mock:
        route = mock.post("http://mlflow:5000/api/2.0/mlflow/runs/get").mock(
            return_value=httpx.Response(
                200,
                json={
                    "run": {
                        "data": {
                            "tags": [
                                {"key": "tenant", "value": "tenant-b"},
                            ]
                        }
                    }
                },
            )
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/get",
            json={"run_id": "r-1"},
            headers={"X-Tenant": "tenant-a"},
        )

    assert response.status_code == 403
    assert route.call_count == 1


def test_create_injects_tenant_tag_with_auth_enabled(monkeypatch: pytest.MonkeyPatch):
    from gateway.main import _validator

    async def _fake_validate_token(token: str):
        assert token == "token-1"
        return {"tenant_id": "tenant-a", "roles": ["contributor"], "sub": "alice"}

    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "auth_mode", "oidc")
    monkeypatch.setattr(_validator, "validate_token", _fake_validate_token)

    with respx.mock(assert_all_called=True) as mock:
        def _assert_request(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert {"key": "tenant", "value": "tenant-a"} in payload["tags"]
            return httpx.Response(200, json={"run": {"info": {"run_id": "r-2"}}})

        mock.post("http://mlflow:5000/api/2.0/mlflow/runs/create").mock(side_effect=_assert_request)
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/create",
            json={"experiment_id": "1"},
            headers={"Authorization": "Bearer token-1"},
        )

    assert response.status_code == 200


def test_create_uses_configured_tenant_tag_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "tenant_tag_key", "workspace")

    with respx.mock(assert_all_called=True) as mock:
        def _assert_request(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert {"key": "workspace", "value": "tenant-a"} in payload["tags"]
            assert {"key": "tenant", "value": "tenant-a"} not in payload["tags"]
            return httpx.Response(200, json={"run": {"info": {"run_id": "r-3"}}})

        mock.post("http://mlflow:5000/api/2.0/mlflow/runs/create").mock(side_effect=_assert_request)
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/create",
            json={"experiment_id": "1"},
            headers={"X-Tenant": "tenant-a"},
        )

    assert response.status_code == 200


def test_log_batch_denies_access_to_other_tenant():
    with respx.mock(assert_all_called=False) as mock:
        preflight = mock.post("http://mlflow:5000/api/2.0/mlflow/runs/get").mock(
            return_value=httpx.Response(
                200,
                json={
                    "run": {
                        "data": {
                            "tags": [
                                {"key": "tenant", "value": "tenant-b"},
                            ]
                        }
                    }
                },
            )
        )
        mutation = mock.post("http://mlflow:5000/api/2.0/mlflow/runs/log-batch").mock(
            return_value=httpx.Response(200, json={})
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/log-batch",
            json={"run_id": "r-1", "metrics": []},
            headers={"X-Tenant": "tenant-a"},
        )

    assert response.status_code == 403
    assert preflight.called is True
    assert mutation.called is False
