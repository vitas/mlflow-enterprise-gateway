from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from jwt import InvalidTokenError


class AuthError(Exception):
    pass


@dataclass
class AuthConfig:
    enabled: bool
    issuer: str | None
    audience: str | None
    algorithms: list[str]
    jwks_uri: str | None
    jwks_json: str | None
    tenant_claim: str


class JWTValidator:
    def __init__(self, config: AuthConfig, timeout_seconds: float = 10.0):
        self.config = config
        self.timeout_seconds = timeout_seconds
        self._jwks_cache: dict[str, Any] | None = None

    async def _load_jwks(self) -> dict[str, Any]:
        if self._jwks_cache is not None:
            return self._jwks_cache

        if self.config.jwks_json:
            try:
                self._jwks_cache = json.loads(self.config.jwks_json)
                return self._jwks_cache
            except json.JSONDecodeError as exc:
                raise AuthError("Invalid GW_JWKS_JSON") from exc

        if not self.config.jwks_uri:
            raise AuthError("JWKS source is not configured")

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            resp = await client.get(self.config.jwks_uri)
            resp.raise_for_status()
            self._jwks_cache = resp.json()
            return self._jwks_cache

    async def _get_key(self, token: str):
        try:
            header = jwt.get_unverified_header(token)
        except InvalidTokenError as exc:
            raise AuthError("Invalid JWT header") from exc

        kid = header.get("kid")
        if not kid:
            raise AuthError("JWT header missing kid")

        jwks = await self._load_jwks()
        keys = jwks.get("keys", [])
        for jwk in keys:
            if jwk.get("kid") == kid:
                return jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))

        raise AuthError("Signing key not found for token kid")

    async def validate_token(self, token: str) -> dict[str, Any]:
        key = await self._get_key(token)
        options = {
            "verify_signature": True,
            "verify_exp": True,
            "verify_nbf": True,
            "verify_iat": True,
            "verify_iss": bool(self.config.issuer),
            "verify_aud": bool(self.config.audience),
        }

        try:
            claims = jwt.decode(
                token,
                key=key,
                algorithms=self.config.algorithms,
                issuer=self.config.issuer,
                audience=self.config.audience,
                options=options,
            )
        except InvalidTokenError as exc:
            raise AuthError(f"Invalid JWT: {exc}") from exc

        return claims


def extract_bearer_token(authorization_header: str | None) -> str:
    if not authorization_header:
        raise AuthError("Missing Authorization header")

    scheme, _, token = authorization_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthError("Authorization header must use Bearer token")
    return token


def extract_tenant(claims: dict[str, Any], tenant_claim: str) -> str:
    tenant = claims.get(tenant_claim)
    if not isinstance(tenant, str) or not tenant.strip():
        raise AuthError(f"Missing or invalid tenant claim: {tenant_claim}")
    return tenant
