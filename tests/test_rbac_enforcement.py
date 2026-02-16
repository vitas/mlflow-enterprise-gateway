import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from gateway.config import settings
from gateway.main import app


@pytest.fixture(autouse=True)
def _configure_gateway(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "auth_mode", "oidc")
    monkeypatch.setattr(settings, "target_base_url", "http://mlflow:5000")
    monkeypatch.setattr(settings, "tenant_tag_key", "tenant")
    monkeypatch.setattr(settings, "tenant_claim", "tenant_id")
    monkeypatch.setattr(settings, "role_claim", "roles")
    monkeypatch.setattr(settings, "rbac_viewer_aliases", "")
    monkeypatch.setattr(settings, "rbac_contributor_aliases", "")
    monkeypatch.setattr(settings, "rbac_admin_aliases", "")
    monkeypatch.setattr(settings, "rbac_default_deny", False)


def test_rbac_allows_contributor_create(monkeypatch: pytest.MonkeyPatch):
    from gateway.main import _validator

    async def _fake_validate_token(token: str):
        return {"tenant_id": "team-a", "roles": ["contributor"], "sub": "alice"}

    monkeypatch.setattr(_validator, "validate_token", _fake_validate_token)

    with respx.mock(assert_all_called=True) as mock:
        mock.post("http://mlflow:5000/api/2.0/mlflow/runs/create").mock(
            return_value=httpx.Response(200, json={"run": {"info": {"run_id": "r-1"}}})
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/create",
            json={"experiment_id": "1"},
            headers={"Authorization": "Bearer token-1"},
        )

    assert response.status_code == 200


def test_rbac_denies_viewer_create(monkeypatch: pytest.MonkeyPatch):
    from gateway.main import _validator

    async def _fake_validate_token(token: str):
        return {"tenant_id": "team-a", "roles": ["viewer"], "sub": "alice"}

    monkeypatch.setattr(_validator, "validate_token", _fake_validate_token)

    with respx.mock(assert_all_called=False) as mock:
        route = mock.post("http://mlflow:5000/api/2.0/mlflow/runs/create").mock(
            return_value=httpx.Response(200, json={"ok": True})
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/create",
            json={"experiment_id": "1"},
            headers={"Authorization": "Bearer token-1"},
        )

    assert response.status_code == 403
    assert route.called is False


def test_rbac_deny_emits_audit_event(monkeypatch: pytest.MonkeyPatch):
    from gateway.main import _validator

    async def _fake_validate_token(token: str):
        return {"tenant_id": "team-a", "roles": ["viewer"], "sub": "alice"}

    audit_calls = []

    def _fake_audit(**kwargs):
        audit_calls.append(kwargs)

    monkeypatch.setattr(_validator, "validate_token", _fake_validate_token)
    monkeypatch.setattr("gateway.main.log_audit_event", _fake_audit)

    client = TestClient(app)
    response = client.post(
        "/api/2.0/mlflow/runs/create",
        json={"experiment_id": "1"},
        headers={"Authorization": "Bearer token-1"},
    )

    assert response.status_code == 403
    assert isinstance(response.headers.get("x-request-id"), str)
    assert response.headers["x-request-id"]
    assert len(audit_calls) == 1
    assert audit_calls[0]["status_code"] == 403
    assert audit_calls[0]["tenant"] == "team-a"
    assert audit_calls[0]["subject"] == "alice"
    assert audit_calls[0]["upstream"] == "policy"
    assert audit_calls[0]["request_id"] == response.headers["x-request-id"]
    assert audit_calls[0]["decision"] == "deny"


def test_rbac_uses_configured_role_claim(monkeypatch: pytest.MonkeyPatch):
    from gateway.main import _validator

    monkeypatch.setattr(settings, "role_claim", "groups")

    async def _fake_validate_token(token: str):
        return {"tenant_id": "team-a", "groups": ["viewer"], "sub": "alice"}

    monkeypatch.setattr(_validator, "validate_token", _fake_validate_token)

    with respx.mock(assert_all_called=True) as mock:
        mock.post("http://mlflow:5000/api/2.0/mlflow/runs/search").mock(
            return_value=httpx.Response(200, json={"runs": []})
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/search",
            json={"experiment_ids": ["0"]},
            headers={"Authorization": "Bearer token-1"},
        )

    assert response.status_code == 200


def test_rbac_uses_aliases_for_groups(monkeypatch: pytest.MonkeyPatch):
    from gateway.main import _validator

    monkeypatch.setattr(settings, "role_claim", "roles,groups")
    monkeypatch.setattr(settings, "rbac_viewer_aliases", "mlflow-read")
    monkeypatch.setattr(settings, "rbac_contributor_aliases", "mlflow-write")

    async def _fake_validate_token(token: str):
        return {"tenant_id": "team-a", "groups": ["mlflow-write"], "sub": "alice"}

    monkeypatch.setattr(_validator, "validate_token", _fake_validate_token)

    with respx.mock(assert_all_called=True) as mock:
        mock.post("http://mlflow:5000/api/2.0/mlflow/runs/create").mock(
            return_value=httpx.Response(200, json={"run": {"info": {"run_id": "r-1"}}})
        )
        client = TestClient(app)
        response = client.post(
            "/api/2.0/mlflow/runs/create",
            json={"experiment_id": "1"},
            headers={"Authorization": "Bearer token-1"},
        )

    assert response.status_code == 200


def test_unknown_endpoint_allowed_when_default_deny_disabled(monkeypatch: pytest.MonkeyPatch):
    from gateway.main import _validator

    monkeypatch.setattr(settings, "rbac_default_deny", False)

    async def _fake_validate_token(token: str):
        return {"tenant_id": "team-a", "roles": ["viewer"], "sub": "alice"}

    monkeypatch.setattr(_validator, "validate_token", _fake_validate_token)

    with respx.mock(assert_all_called=True) as mock:
        mock.get("http://mlflow:5000/api/2.0/mlflow/experiments/list").mock(
            return_value=httpx.Response(200, json={"experiments": []})
        )
        client = TestClient(app)
        response = client.get(
            "/api/2.0/mlflow/experiments/list",
            headers={"Authorization": "Bearer token-1"},
        )

    assert response.status_code == 200


def test_unknown_endpoint_denied_when_default_deny_enabled(monkeypatch: pytest.MonkeyPatch):
    from gateway.main import _validator

    monkeypatch.setattr(settings, "rbac_default_deny", True)

    async def _fake_validate_token(token: str):
        return {"tenant_id": "team-a", "roles": ["admin"], "sub": "alice"}

    monkeypatch.setattr(_validator, "validate_token", _fake_validate_token)

    with respx.mock(assert_all_called=False) as mock:
        route = mock.get("http://mlflow:5000/api/2.0/mlflow/experiments/list").mock(
            return_value=httpx.Response(200, json={"experiments": []})
        )
        client = TestClient(app)
        response = client.get(
            "/api/2.0/mlflow/experiments/list",
            headers={"Authorization": "Bearer token-1"},
        )

    assert response.status_code == 403
    assert "default deny" in response.json()["detail"]
    assert route.called is False
