from __future__ import annotations

from typing import Any


class TenantPayloadError(Exception):
    pass


def _v_path(version: str, suffix: str) -> str:
    return f"/api/{version}/mlflow/{suffix}"


RUNS_MUTATION_SUFFIXES = {
    "runs/update",
    "runs/delete",
    "runs/restore",
    "runs/log-batch",
    "runs/log-metric",
    "runs/log-parameter",
    "runs/set-tag",
    "runs/delete-tag",
}

REGISTERED_MODEL_MUTATION_SUFFIXES = {
    "registered-models/delete",
    "registered-models/rename",
    "registered-models/set-tag",
    "registered-models/delete-tag",
    "registered-models/set-alias",
    "registered-models/delete-alias",
}

MODEL_VERSION_MUTATION_SUFFIXES = {
    "model-versions/update",
    "model-versions/delete",
    "model-versions/transition-stage",
    "model-versions/set-tag",
    "model-versions/delete-tag",
}


def _normalize_tags_to_list(tags: Any) -> list[dict[str, Any]]:
    if tags is None:
        return []
    if isinstance(tags, list):
        normalized: list[dict[str, Any]] = []
        for tag in tags:
            if not isinstance(tag, dict):
                raise TenantPayloadError("Invalid MLflow payload: tag entries must be objects")
            normalized.append(tag)
        return normalized
    if isinstance(tags, dict):
        return [{"key": str(key), "value": value} for key, value in tags.items()]
    raise TenantPayloadError("Invalid MLflow payload: tags must be a list or object")


def _extract_tenant_from_tags(tags: Any, tenant_tag_key: str = "tenant") -> str | None:
    if isinstance(tags, list):
        for tag in tags:
            if isinstance(tag, dict) and tag.get("key") == tenant_tag_key:
                value = tag.get("value")
                if isinstance(value, str):
                    return value
        return None
    if isinstance(tags, dict):
        value = tags.get(tenant_tag_key)
        if isinstance(value, str):
            return value
        return None
    return None


def is_runs_create_path(path: str) -> bool:
    return path in {"/api/2.0/mlflow/runs/create", "/api/2.1/mlflow/runs/create"}


def is_runs_search_path(path: str) -> bool:
    return path in {"/api/2.0/mlflow/runs/search", "/api/2.1/mlflow/runs/search"}


def is_runs_get_path(path: str) -> bool:
    return path in {"/api/2.0/mlflow/runs/get", "/api/2.1/mlflow/runs/get"}


def is_runs_mutation_path(path: str) -> bool:
    return path in {
        *(_v_path("2.0", suffix) for suffix in RUNS_MUTATION_SUFFIXES),
        *(_v_path("2.1", suffix) for suffix in RUNS_MUTATION_SUFFIXES),
    }


def is_registered_model_create_path(path: str) -> bool:
    return path in {
        "/api/2.0/mlflow/registered-models/create",
        "/api/2.1/mlflow/registered-models/create",
    }


def is_model_version_create_path(path: str) -> bool:
    return path in {
        "/api/2.0/mlflow/model-versions/create",
        "/api/2.1/mlflow/model-versions/create",
    }


def is_registered_models_search_path(path: str) -> bool:
    return path in {
        "/api/2.0/mlflow/registered-models/search",
        "/api/2.1/mlflow/registered-models/search",
    }


def is_registered_model_get_path(path: str) -> bool:
    return path in {
        "/api/2.0/mlflow/registered-models/get",
        "/api/2.1/mlflow/registered-models/get",
    }


def is_registered_model_mutation_path(path: str) -> bool:
    return path in {
        *(_v_path("2.0", suffix) for suffix in REGISTERED_MODEL_MUTATION_SUFFIXES),
        *(_v_path("2.1", suffix) for suffix in REGISTERED_MODEL_MUTATION_SUFFIXES),
    }


def is_model_version_get_path(path: str) -> bool:
    return path in {
        "/api/2.0/mlflow/model-versions/get",
        "/api/2.1/mlflow/model-versions/get",
    }


def is_model_versions_search_path(path: str) -> bool:
    return path in {
        "/api/2.0/mlflow/model-versions/search",
        "/api/2.1/mlflow/model-versions/search",
    }


def is_model_version_mutation_path(path: str) -> bool:
    return path in {
        *(_v_path("2.0", suffix) for suffix in MODEL_VERSION_MUTATION_SUFFIXES),
        *(_v_path("2.1", suffix) for suffix in MODEL_VERSION_MUTATION_SUFFIXES),
    }


def ensure_tenant_tag_for_create(
    payload: dict[str, Any], tenant: str, tenant_tag_key: str = "tenant"
) -> dict[str, Any]:
    tags = _normalize_tags_to_list(payload.get("tags"))

    tenant_tag_found = False
    for tag in tags:
        if tag.get("key") == tenant_tag_key:
            tenant_tag_found = True
            if tag.get("value") != tenant:
                raise PermissionError("Tenant tag conflict")

    if not tenant_tag_found:
        tags.append({"key": tenant_tag_key, "value": tenant})

    payload["tags"] = tags
    return payload


def tenant_filter_clause(tenant: str, tenant_tag_key: str = "tenant") -> str:
    safe_tenant = tenant.replace("'", "''")
    return f"tags.{tenant_tag_key} = '{safe_tenant}'"


def ensure_tenant_filter_for_search(
    payload: dict[str, Any], tenant: str, tenant_tag_key: str = "tenant"
) -> dict[str, Any]:
    clause = tenant_filter_clause(tenant, tenant_tag_key)
    raw_filter = payload.get("filter")

    if raw_filter is None:
        payload["filter"] = clause
        return payload

    if not isinstance(raw_filter, str):
        raise TenantPayloadError("Invalid MLflow payload: filter must be a string")

    existing = raw_filter.strip()
    if not existing:
        payload["filter"] = clause
        return payload

    if clause in existing:
        payload["filter"] = existing
        return payload

    payload["filter"] = f"({existing}) and {clause}"
    return payload


def ensure_tenant_filter_for_registered_models_search(
    payload: dict[str, Any], tenant: str, tenant_tag_key: str = "tenant"
) -> dict[str, Any]:
    clause = tenant_filter_clause(tenant, tenant_tag_key)
    raw_filter = payload.get("filter_string")

    if raw_filter is None:
        payload["filter_string"] = clause
        return payload

    if not isinstance(raw_filter, str):
        raise TenantPayloadError("Invalid MLflow payload: filter_string must be a string")

    existing = raw_filter.strip()
    if not existing:
        payload["filter_string"] = clause
        return payload

    if clause in existing:
        payload["filter_string"] = existing
        return payload

    payload["filter_string"] = f"({existing}) and {clause}"
    return payload


def extract_tenant_tag_from_run_response(
    payload: dict[str, Any], tenant_tag_key: str = "tenant"
) -> str | None:
    run = payload.get("run")
    if not isinstance(run, dict):
        return None
    data = run.get("data")
    if not isinstance(data, dict):
        return None
    return _extract_tenant_from_tags(data.get("tags"), tenant_tag_key)


def extract_tenant_tag_from_registered_model_response(
    payload: dict[str, Any], tenant_tag_key: str = "tenant"
) -> str | None:
    registered_model = payload.get("registered_model")
    if not isinstance(registered_model, dict):
        return None
    return _extract_tenant_from_tags(registered_model.get("tags"), tenant_tag_key)


def extract_tenant_tag_from_model_version_response(
    payload: dict[str, Any], tenant_tag_key: str = "tenant"
) -> str | None:
    model_version = payload.get("model_version")
    if not isinstance(model_version, dict):
        return None
    return _extract_tenant_from_tags(model_version.get("tags"), tenant_tag_key)
