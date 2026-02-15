import pytest

from gateway.rbac import RBACError, enforce_rbac, extract_effective_role, required_role_for_request


def test_required_role_mapping():
    assert required_role_for_request("/api/2.0/mlflow/runs/create") == "contributor"
    assert required_role_for_request("/api/2.0/mlflow/runs/get") == "viewer"
    assert required_role_for_request("/api/2.0/mlflow/registered-models/create") == "contributor"
    assert required_role_for_request("/api/2.0/mlflow/registered-models/search") == "viewer"
    assert required_role_for_request("/api/2.0/mlflow/experiments/list") is None


def test_extract_effective_role_picks_highest():
    claims = {"roles": ["viewer", "contributor"]}
    assert extract_effective_role(claims, "roles") == "contributor"


def test_extract_effective_role_uses_alias_mapping():
    claims = {"groups": ["mlflow-read", "mlflow-write"]}
    assert (
        extract_effective_role(
            claims,
            "roles,groups",
            viewer_aliases="mlflow-read",
            contributor_aliases="mlflow-write",
        )
        == "contributor"
    )


def test_extract_effective_role_supports_multiple_claim_keys():
    claims = {"groups": ["viewer"], "roles": ["admin"]}
    assert extract_effective_role(claims, "roles,groups") == "admin"


def test_extract_effective_role_missing_claims_message():
    claims = {"tenant_id": "team-a"}
    with pytest.raises(RBACError, match=r"Missing role claim\(s\): roles, groups"):
        extract_effective_role(claims, "roles,groups")


def test_extract_effective_role_unrecognized_roles_message():
    claims = {"roles": ["employee", "analyst"]}
    with pytest.raises(RBACError, match=r"No recognized roles found in claim\(s\): roles"):
        extract_effective_role(claims, "roles")


def test_enforce_rbac_allows_admin_for_contributor_action():
    claims = {"roles": ["admin"]}
    enforce_rbac("/api/2.0/mlflow/runs/create", claims, "roles")


def test_enforce_rbac_denies_viewer_for_create():
    claims = {"roles": ["viewer"]}
    with pytest.raises(RBACError, match="Insufficient role"):
        enforce_rbac("/api/2.0/mlflow/runs/create", claims, "roles")


def test_enforce_rbac_denies_missing_role_claim():
    claims = {"tenant_id": "team-a"}
    with pytest.raises(RBACError, match="Missing role claim"):
        enforce_rbac("/api/2.0/mlflow/runs/get", claims, "roles")
