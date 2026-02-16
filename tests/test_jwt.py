import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from gateway.auth import AuthConfig, AuthError, JWTValidator


@pytest.fixture
def rsa_material():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    kid = "test-kid-1"
    jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    jwk["kid"] = kid
    jwks = {"keys": [jwk]}

    return private_key, kid, jwks


@pytest.mark.asyncio
async def test_validate_token_with_stub_jwks(rsa_material):
    private_key, kid, jwks = rsa_material
    config = AuthConfig(
        enabled=True,
        issuer="https://issuer.example.com",
        audience="mlflow-gateway",
        algorithms=["RS256"],
        jwks_uri=None,
        jwks_json=json.dumps(jwks),
        tenant_claim="tenant_id",
    )
    validator = JWTValidator(config)

    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "iss": "https://issuer.example.com",
            "aud": "mlflow-gateway",
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=10),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )

    claims = await validator.validate_token(token)

    assert claims["sub"] == "user-123"
    assert claims["tenant_id"] == "tenant-a"


@pytest.mark.asyncio
async def test_validate_token_rejects_bad_audience(rsa_material):
    private_key, kid, jwks = rsa_material
    config = AuthConfig(
        enabled=True,
        issuer="https://issuer.example.com",
        audience="mlflow-gateway",
        algorithms=["RS256"],
        jwks_uri=None,
        jwks_json=json.dumps(jwks),
        tenant_claim="tenant_id",
    )
    validator = JWTValidator(config)

    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "iss": "https://issuer.example.com",
            "aud": "other-audience",
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=10),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )

    with pytest.raises(AuthError, match="Invalid JWT"):
        await validator.validate_token(token)


@pytest.mark.asyncio
async def test_validate_token_refreshes_jwks_on_kid_miss(monkeypatch: pytest.MonkeyPatch):
    old_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    old_public = old_private.public_key()
    old_kid = "old-kid"
    old_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(old_public))
    old_jwk["kid"] = old_kid

    new_private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    new_public = new_private.public_key()
    new_kid = "new-kid"
    new_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(new_public))
    new_jwk["kid"] = new_kid

    config = AuthConfig(
        enabled=True,
        issuer="https://issuer.example.com",
        audience="mlflow-gateway",
        algorithms=["RS256"],
        jwks_uri="https://issuer.example.com/.well-known/jwks.json",
        jwks_json=None,
        tenant_claim="tenant_id",
    )
    validator = JWTValidator(config)
    validator._jwks_cache = {"keys": [old_jwk]}

    refresh_calls = {"count": 0}

    async def _fake_load_jwks(*, force_refresh: bool = False):
        if force_refresh:
            refresh_calls["count"] += 1
            validator._jwks_cache = {"keys": [new_jwk]}
        return validator._jwks_cache

    monkeypatch.setattr(validator, "_load_jwks", _fake_load_jwks)

    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "user-123",
            "tenant_id": "tenant-a",
            "iss": "https://issuer.example.com",
            "aud": "mlflow-gateway",
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=10),
        },
        new_private,
        algorithm="RS256",
        headers={"kid": new_kid},
    )

    claims = await validator.validate_token(token)

    assert claims["tenant_id"] == "tenant-a"
    assert refresh_calls["count"] == 1
