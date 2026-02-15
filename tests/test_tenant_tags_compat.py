import pytest

from gateway.mlflow.tenant import (
    extract_tenant_tag_from_model_version_response,
    extract_tenant_tag_from_registered_model_response,
    extract_tenant_tag_from_run_response,
    ensure_tenant_tag_for_create,
)


def test_ensure_tenant_tag_for_create_supports_dict_tags_and_outputs_list():
    payload = {"name": "model-a", "tags": {"owner": "team-1"}}

    updated = ensure_tenant_tag_for_create(payload, "tenant-a")

    assert isinstance(updated["tags"], list)
    assert {"key": "owner", "value": "team-1"} in updated["tags"]
    assert {"key": "tenant", "value": "tenant-a"} in updated["tags"]


def test_ensure_tenant_tag_for_create_denies_conflicting_tenant_in_dict_tags():
    payload = {"tags": {"tenant": "tenant-b", "owner": "team-1"}}

    with pytest.raises(PermissionError, match="Tenant tag conflict"):
        ensure_tenant_tag_for_create(payload, "tenant-a")


def test_extract_tenant_tag_from_run_response_supports_dict_tags():
    payload = {"run": {"data": {"tags": {"tenant": "tenant-a", "purpose": "demo"}}}}
    assert extract_tenant_tag_from_run_response(payload) == "tenant-a"


def test_extract_tenant_tag_from_registered_model_response_supports_dict_tags():
    payload = {"registered_model": {"tags": {"tenant": "tenant-a"}}}
    assert extract_tenant_tag_from_registered_model_response(payload) == "tenant-a"


def test_extract_tenant_tag_from_model_version_response_supports_dict_tags():
    payload = {"model_version": {"tags": {"tenant": "tenant-a"}}}
    assert extract_tenant_tag_from_model_version_response(payload) == "tenant-a"
