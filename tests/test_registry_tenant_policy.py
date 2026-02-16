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


def test_registered_model_create_injects_tenant_tag():
    with respx.mock(assert_all_called=True) as mock:
        def _assert_request(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert {"key": "tenant", "value": "tenant-a"} in payload["tags"]
            assert {"key": "owner", "value": "team-1"} in payload["tags"]
            return httpx.Response(200, json={"registered_model": {"name": "model-a"}})

        mock.post("http://mlflow:5000/api/2.0/mlflow/registered-models/create").mock(
            side_effect=_assert_request
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/registered-models/create",
            json={"name": "model-a", "tags": [{"key": "owner", "value": "team-1"}]},
            headers={"X-Tenant": "tenant-a"},
        )

    assert response.status_code == 200


def test_model_version_create_denies_conflicting_tenant_tag():
    with respx.mock(assert_all_called=False) as mock:
        route = mock.post("http://mlflow:5000/api/2.0/mlflow/model-versions/create").mock(
            return_value=httpx.Response(200, json={"model_version": {"version": "1"}})
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/model-versions/create",
            json={
                "name": "model-a",
                "source": "s3://bucket/artifact",
                "tags": [{"key": "tenant", "value": "tenant-b"}],
            },
            headers={"X-Tenant": "tenant-a"},
        )

    assert response.status_code == 403
    assert route.called is False


def test_registered_models_search_appends_tenant_filter():
    with respx.mock(assert_all_called=True) as mock:
        def _assert_request(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            assert payload["filter_string"] == "(name LIKE 'model-%') and tags.tenant = 'tenant-a'"
            return httpx.Response(200, json={"registered_models": []})

        mock.post("http://mlflow:5000/api/2.0/mlflow/registered-models/search").mock(
            side_effect=_assert_request
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/registered-models/search",
            json={"filter_string": "name LIKE 'model-%'"},
            headers={"X-Tenant": "tenant-a"},
        )

    assert response.status_code == 200


def test_registered_model_get_denies_access_to_other_tenant():
    with respx.mock(assert_all_called=True) as mock:
        route = mock.post("http://mlflow:5000/api/2.0/mlflow/registered-models/get").mock(
            return_value=httpx.Response(
                200,
                json={
                    "registered_model": {
                        "name": "model-a",
                        "tags": [{"key": "tenant", "value": "tenant-b"}],
                    }
                },
            )
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/registered-models/get",
            json={"name": "model-a"},
            headers={"X-Tenant": "tenant-a"},
        )

    assert response.status_code == 403
    assert route.call_count == 1


def test_model_version_get_denies_access_to_other_tenant():
    with respx.mock(assert_all_called=True) as mock:
        route = mock.post("http://mlflow:5000/api/2.0/mlflow/model-versions/get").mock(
            return_value=httpx.Response(
                200,
                json={
                    "model_version": {
                        "name": "model-a",
                        "version": "1",
                        "tags": [{"key": "tenant", "value": "tenant-b"}],
                    }
                },
            )
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/model-versions/get",
            json={"name": "model-a", "version": "1"},
            headers={"X-Tenant": "tenant-a"},
        )

    assert response.status_code == 403
    assert route.call_count == 1


def test_registered_model_delete_denies_access_to_other_tenant():
    with respx.mock(assert_all_called=False) as mock:
        preflight = mock.post("http://mlflow:5000/api/2.0/mlflow/registered-models/get").mock(
            return_value=httpx.Response(
                200,
                json={
                    "registered_model": {
                        "name": "model-a",
                        "tags": [{"key": "tenant", "value": "tenant-b"}],
                    }
                },
            )
        )
        mutation = mock.post("http://mlflow:5000/api/2.0/mlflow/registered-models/delete").mock(
            return_value=httpx.Response(200, json={})
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/registered-models/delete",
            json={"name": "model-a"},
            headers={"X-Tenant": "tenant-a"},
        )

    assert response.status_code == 403
    assert preflight.called is True
    assert mutation.called is False


def test_model_version_transition_stage_denies_access_to_other_tenant():
    with respx.mock(assert_all_called=False) as mock:
        preflight = mock.post("http://mlflow:5000/api/2.0/mlflow/model-versions/get").mock(
            return_value=httpx.Response(
                200,
                json={
                    "model_version": {
                        "name": "model-a",
                        "version": "1",
                        "tags": [{"key": "tenant", "value": "tenant-b"}],
                    }
                },
            )
        )
        mutation = mock.post("http://mlflow:5000/api/2.0/mlflow/model-versions/transition-stage").mock(
            return_value=httpx.Response(200, json={})
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/model-versions/transition-stage",
            json={"name": "model-a", "version": "1", "stage": "Production"},
            headers={"X-Tenant": "tenant-a"},
        )

    assert response.status_code == 403
    assert preflight.called is True
    assert mutation.called is False
