import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from gateway.config import settings
from gateway.main import app


@pytest.fixture(autouse=True)
def _configure_gateway(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "target_base_url", "http://mlflow:5000")


def test_authorization_ignored_in_auth_mode_off(monkeypatch: pytest.MonkeyPatch, caplog):
    monkeypatch.setattr(settings, "auth_enabled", False)
    monkeypatch.setattr(settings, "auth_mode", "off")

    with respx.mock(assert_all_called=True) as mock:
        def _assert_request(request: httpx.Request) -> httpx.Response:
            assert "authorization" not in request.headers
            return httpx.Response(200, json={"runs": []})

        mock.post("http://mlflow:5000/api/2.0/mlflow/runs/search").mock(side_effect=_assert_request)
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/search",
            json={"experiment_ids": ["0"]},
            headers={"Authorization": "Bearer invalid-token", "X-Tenant": "tenant-a"},
        )

    assert response.status_code == 200
    assert "Authorization header ignored because AUTH_MODE=off" in caplog.text


def test_auth_mode_off_missing_x_tenant_returns_400(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "auth_enabled", False)
    monkeypatch.setattr(settings, "auth_mode", "off")

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post("http://mlflow:5000/api/2.0/mlflow/runs/search").mock(
            return_value=httpx.Response(200, json={"runs": []})
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/search",
            json={"experiment_ids": ["0"]},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing X-Tenant header"
    assert route.called is False


def test_oidc_mode_rejects_x_tenant_header(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "auth_mode", "oidc")

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post("http://mlflow:5000/api/2.0/mlflow/runs/search").mock(
            return_value=httpx.Response(200, json={"runs": []})
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/search",
            json={"experiment_ids": ["0"]},
            headers={"X-Tenant": "tenant-a", "Authorization": "Bearer token"},
        )

    assert response.status_code == 400
    assert response.json()["detail"] == "X-Tenant header is not allowed when AUTH_MODE=oidc"
    assert route.called is False
