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
