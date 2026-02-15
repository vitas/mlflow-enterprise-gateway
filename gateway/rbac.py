from __future__ import annotations

from typing import Any

from gateway.mlflow.tenant import (
    is_model_version_create_path,
    is_model_version_get_path,
    is_registered_model_create_path,
    is_registered_model_get_path,
    is_registered_models_search_path,
    is_runs_create_path,
    is_runs_get_path,
    is_runs_search_path,
)


class RBACError(Exception):
    pass


ROLE_LEVEL = {
    "viewer": 1,
    "contributor": 2,
    "admin": 3,
}


def _parse_csv(value: str) -> list[str]:
    return [item.strip().lower() for item in value.split(",") if item.strip()]


def _build_alias_map(
    viewer_aliases: str, contributor_aliases: str, admin_aliases: str
) -> dict[str, str]:
    alias_map: dict[str, str] = {}

    for alias in ["viewer", *_parse_csv(viewer_aliases)]:
        alias_map[alias] = "viewer"
    for alias in ["contributor", *_parse_csv(contributor_aliases)]:
        alias_map[alias] = "contributor"
    for alias in ["admin", *_parse_csv(admin_aliases)]:
        alias_map[alias] = "admin"

    return alias_map


def _collect_role_candidates(claims: dict[str, Any], role_claims: list[str]) -> tuple[list[str], list[str]]:
    candidates: list[str] = []
    present_claims: list[str] = []
    for claim_key in role_claims:
        if claim_key not in claims:
            continue
        present_claims.append(claim_key)
        raw = claims.get(claim_key)
        if isinstance(raw, str):
            candidates.append(raw.strip())
        elif isinstance(raw, list):
            candidates.extend(item.strip() for item in raw if isinstance(item, str))
    return [c for c in candidates if c], present_claims


def required_role_for_request(path: str) -> str | None:
    if is_runs_create_path(path) or is_registered_model_create_path(path) or is_model_version_create_path(path):
        return "contributor"
    if is_runs_get_path(path) or is_runs_search_path(path):
        return "viewer"
    if is_registered_model_get_path(path) or is_registered_models_search_path(path) or is_model_version_get_path(path):
        return "viewer"
    return None


def extract_effective_role(
    claims: dict[str, Any],
    role_claim: str,
    viewer_aliases: str = "",
    contributor_aliases: str = "",
    admin_aliases: str = "",
) -> str:
    role_claims = _parse_csv(role_claim)
    if not role_claims:
        role_claims = ["roles"]

    candidates, present_claims = _collect_role_candidates(claims, role_claims)
    if not present_claims:
        raise RBACError(f"Missing role claim(s): {', '.join(role_claims)}")

    alias_map = _build_alias_map(viewer_aliases, contributor_aliases, admin_aliases)
    effective = None
    for candidate in candidates:
        mapped = alias_map.get(candidate.lower())
        if mapped is None:
            continue
        if effective is None or ROLE_LEVEL[mapped] > ROLE_LEVEL[effective]:
            effective = mapped

    if effective is None:
        raise RBACError(f"No recognized roles found in claim(s): {', '.join(role_claims)}")
    return effective


def enforce_rbac(
    path: str,
    claims: dict[str, Any],
    role_claim: str,
    viewer_aliases: str = "",
    contributor_aliases: str = "",
    admin_aliases: str = "",
) -> None:
    required = required_role_for_request(path)
    if required is None:
        return

    effective = extract_effective_role(
        claims,
        role_claim,
        viewer_aliases,
        contributor_aliases,
        admin_aliases,
    )

    if ROLE_LEVEL[effective] < ROLE_LEVEL[required]:
        raise RBACError(f"Insufficient role: required {required}, got {effective}")
