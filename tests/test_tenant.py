import pytest

from gateway.auth import AuthError, extract_tenant


def test_extract_tenant_success():
    claims = {"tenant_id": "tenant-01", "sub": "alice"}
    assert extract_tenant(claims, "tenant_id") == "tenant-01"


def test_extract_tenant_missing_claim():
    claims = {"sub": "alice"}
    with pytest.raises(AuthError, match="tenant claim"):
        extract_tenant(claims, "tenant_id")


def test_extract_tenant_empty_claim():
    claims = {"tenant_id": "   "}
    with pytest.raises(AuthError, match="tenant claim"):
        extract_tenant(claims, "tenant_id")
