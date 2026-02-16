import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from gateway.config import settings
from gateway.main import app


def test_healthz_returns_ok():
    client = TestClient(app)
    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.fixture(autouse=True)
def _configure_gateway(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "target_base_url", "http://mlflow:5000")


def test_readyz_returns_ok_when_upstream_reachable():
    with respx.mock(assert_all_called=True) as mock:
        mock.get("http://mlflow:5000/").mock(return_value=httpx.Response(200, text="ok"))
        client = TestClient(app)
        response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_readyz_returns_503_when_upstream_unavailable():
    with respx.mock(assert_all_called=True) as mock:
        mock.get("http://mlflow:5000/").mock(side_effect=httpx.ConnectError("boom"))
        client = TestClient(app)
        response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["detail"] == "Upstream MLflow is unavailable"


def test_readyz_returns_503_when_upstream_returns_500():
    with respx.mock(assert_all_called=True) as mock:
        mock.get("http://mlflow:5000/").mock(return_value=httpx.Response(500, text="error"))
        client = TestClient(app)
        response = client.get("/readyz")

    assert response.status_code == 503
    assert response.json()["detail"] == "Upstream MLflow is unavailable"
