from __future__ import annotations

"""Policy Enforcement Gateway (PEP) request handling for MLflow extension layer."""

import json
import logging
from typing import Any
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from gateway.audit import log_audit_event
from gateway.auth import AuthConfig, AuthError, JWTValidator, extract_bearer_token, extract_tenant
from gateway.config import settings
from gateway.mlflow.tenant import (
    TenantPayloadError,
    ensure_tenant_filter_for_search,
    ensure_tenant_filter_for_registered_models_search,
    ensure_tenant_tag_for_create,
    extract_tenant_tag_from_model_version_response,
    extract_tenant_tag_from_registered_model_response,
    extract_tenant_tag_from_run_response,
    is_model_version_create_path,
    is_model_version_get_path,
    is_registered_model_create_path,
    is_registered_model_get_path,
    is_registered_models_search_path,
    is_runs_create_path,
    is_runs_get_path,
    is_runs_search_path,
)
from gateway.rbac import RBACError, enforce_rbac


logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))
logger = logging.getLogger(__name__)

app = FastAPI(title=settings.app_name)

_validator = JWTValidator(
    AuthConfig(
        enabled=settings.auth_enabled,
        issuer=settings.oidc_issuer,
        audience=settings.oidc_audience,
        algorithms=settings.oidc_algorithms,
        jwks_uri=settings.jwks_uri,
        jwks_json=settings.jwks_json,
        tenant_claim=settings.tenant_claim,
    )
)


@app.get("/healthz")
async def healthz(request: Request) -> dict[str, str]:
    request.state.audit_upstream = "policy"
    _log_request_audit(request, status_code=200)
    return {"status": "ok"}


@app.get("/readyz")
async def readyz(request: Request) -> dict[str, str]:
    probe_url = f"{settings.target_base_url.rstrip('/')}/"
    request.state.audit_upstream = probe_url
    timeout = httpx.Timeout(min(settings.request_timeout_seconds, 2.0))
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            probe_response = await client.get(probe_url)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="Upstream MLflow is unavailable") from exc
    if probe_response.status_code == 500:
        raise HTTPException(status_code=503, detail="Upstream MLflow is unavailable")
    _log_request_audit(request, status_code=200, upstream=probe_url)
    return {"status": "ready"}


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


def _decision_for_status(status_code: int) -> str:
    if status_code >= 500:
        return "error"
    if status_code >= 400:
        return "deny"
    return "allow"


def _log_request_audit(
    request: Request,
    *,
    status_code: int,
    reason: str | None = None,
    upstream: str | None = None,
) -> None:
    request_id = getattr(request.state, "request_id", None)
    tenant = getattr(request.state, "audit_tenant", None)
    subject = getattr(request.state, "audit_subject", None)
    resolved_upstream = upstream or getattr(request.state, "audit_upstream", "policy")
    log_audit_event(
        method=request.method,
        path=request.url.path,
        status_code=status_code,
        request_id=request_id if isinstance(request_id, str) else None,
        tenant=tenant if isinstance(tenant, str) else None,
        subject=subject if isinstance(subject, str) else None,
        upstream=resolved_upstream if isinstance(resolved_upstream, str) else "policy",
        decision=_decision_for_status(status_code),
        reason=reason,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    _log_request_audit(request, status_code=exc.status_code, reason=str(exc.detail))
    headers = dict(exc.headers or {})
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str):
        headers["X-Request-ID"] = request_id
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=headers)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled gateway exception", exc_info=exc)
    _log_request_audit(request, status_code=500, reason="internal_error")
    request_id = getattr(request.state, "request_id", None)
    headers = {"X-Request-ID": request_id} if isinstance(request_id, str) else {}
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error"},
        headers=headers,
    )


def _require_tenant_from_headers(request: Request) -> str:
    header = request.headers.get("x-tenant")
    if not header or not header.strip():
        raise HTTPException(status_code=400, detail="Missing X-Tenant header")
    return header.strip()


def _optional_subject_from_headers(request: Request) -> str | None:
    subject = request.headers.get("x-subject")
    if subject and subject.strip():
        return subject.strip()
    return None


def _has_authorization_header(request: Request) -> bool:
    return bool(request.headers.get("authorization"))


def _load_json_payload(raw_body: bytes) -> dict[str, Any]:
    if not raw_body:
        return {}
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON payload must be an object")
    return payload


@app.api_route("/", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def policy_enforcement_gateway_handler(full_path: str, request: Request) -> Response:
    tenant = None
    subject = None
    claims: dict[str, Any] | None = None
    auth_is_enabled = settings.auth_enabled and settings.auth_mode.lower() != "off"
    request.state.audit_upstream = "policy"

    if auth_is_enabled:
        if request.headers.get("x-tenant"):
            request.state.audit_upstream = "auth"
            raise HTTPException(
                status_code=400,
                detail="X-Tenant header is not allowed when AUTH_MODE=oidc",
            )
        try:
            token = extract_bearer_token(request.headers.get("authorization"))
            claims = await _validator.validate_token(token)
            tenant = extract_tenant(claims, settings.tenant_claim)
            subject = claims.get("sub") if isinstance(claims.get("sub"), str) else None
            request.state.audit_tenant = tenant
            request.state.audit_subject = subject
            try:
                enforce_rbac(
                    request.url.path,
                    claims,
                    settings.role_claim,
                    settings.rbac_viewer_aliases,
                    settings.rbac_contributor_aliases,
                    settings.rbac_admin_aliases,
                    settings.rbac_default_deny,
                )
            except RBACError as exc:
                request.state.audit_upstream = "policy"
                raise HTTPException(status_code=403, detail=str(exc)) from exc
        except AuthError as exc:
            request.state.audit_upstream = "auth"
            raise HTTPException(status_code=401, detail=str(exc)) from exc
    else:
        if _has_authorization_header(request):
            logger.warning("Authorization header ignored because AUTH_MODE=off")
        tenant = _require_tenant_from_headers(request)
        subject = _optional_subject_from_headers(request)
        request.state.audit_tenant = tenant
        request.state.audit_subject = subject

    upstream_url = f"{settings.target_base_url.rstrip('/')}/{full_path}"
    request.state.audit_upstream = upstream_url

    forward_headers = dict(request.headers)
    forward_headers.pop("host", None)
    forward_headers.pop("content-length", None)
    if not auth_is_enabled:
        forward_headers.pop("authorization", None)

    body = await request.body()
    request_path = request.url.path

    if (
        is_runs_create_path(request_path)
        or is_registered_model_create_path(request_path)
        or is_model_version_create_path(request_path)
    ):
        payload = _load_json_payload(body)
        try:
            payload = ensure_tenant_tag_for_create(payload, tenant, settings.tenant_tag_key)
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except TenantPayloadError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        body = json.dumps(payload).encode()
    elif is_runs_search_path(request_path):
        payload = _load_json_payload(body)
        try:
            payload = ensure_tenant_filter_for_search(payload, tenant, settings.tenant_tag_key)
        except TenantPayloadError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        body = json.dumps(payload).encode()
    elif is_registered_models_search_path(request_path):
        payload = _load_json_payload(body)
        try:
            payload = ensure_tenant_filter_for_registered_models_search(
                payload, tenant, settings.tenant_tag_key
            )
        except TenantPayloadError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        body = json.dumps(payload).encode()

    timeout = httpx.Timeout(settings.request_timeout_seconds)

    async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
        response_tenant_extractor = None
        if is_runs_get_path(request_path):
            response_tenant_extractor = lambda payload: extract_tenant_tag_from_run_response(
                payload, settings.tenant_tag_key
            )
        elif is_registered_model_get_path(request_path):
            response_tenant_extractor = lambda payload: extract_tenant_tag_from_registered_model_response(
                payload, settings.tenant_tag_key
            )
        elif is_model_version_get_path(request_path):
            response_tenant_extractor = lambda payload: extract_tenant_tag_from_model_version_response(
                payload, settings.tenant_tag_key
            )

        if response_tenant_extractor is not None:
            preflight_response = await client.request(
                method=request.method,
                url=upstream_url,
                params=request.query_params,
                headers=forward_headers,
                content=body,
            )
            if preflight_response.status_code == 200:
                try:
                    run_payload = preflight_response.json()
                except ValueError as exc:
                    raise HTTPException(status_code=502, detail="Invalid upstream response") from exc
                resource_tenant = response_tenant_extractor(run_payload)
                if resource_tenant != tenant:
                    raise HTTPException(status_code=403, detail="Resource is not accessible for tenant")
            upstream_response = preflight_response
        else:
            upstream_response = await client.request(
                method=request.method,
                url=upstream_url,
                params=request.query_params,
                headers=forward_headers,
                content=body,
            )

    excluded = {"content-encoding", "transfer-encoding", "connection", "content-length"}
    response_headers = {
        k: v for k, v in upstream_response.headers.items() if k.lower() not in excluded
    }

    _log_request_audit(
        request,
        status_code=upstream_response.status_code,
        reason="upstream_server_error" if upstream_response.status_code >= 500 else None,
        upstream=upstream_url,
    )

    return Response(
        content=upstream_response.content,
        status_code=upstream_response.status_code,
        headers=response_headers,
        media_type=upstream_response.headers.get("content-type"),
    )
