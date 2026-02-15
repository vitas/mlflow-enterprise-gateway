from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="GW_", extra="ignore")

    app_name: str = "mlflow-policy-enforcement-gateway"
    log_level: str = "INFO"

    listen_host: str = "0.0.0.0"
    listen_port: int = 8000

    target_base_url: str = "http://mlflow:5000"
    request_timeout_seconds: float = 30.0

    auth_enabled: bool = True
    auth_mode: str = Field(
        default="oidc",
        validation_alias=AliasChoices("GW_AUTH_MODE", "AUTH_MODE"),
    )
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_algorithms: list[str] = Field(default_factory=lambda: ["RS256"])
    jwks_uri: str | None = None
    jwks_json: str | None = None
    tenant_claim: str = "tenant_id"
    role_claim: str = Field(
        default="roles",
        validation_alias=AliasChoices("GW_ROLE_CLAIM", "ROLE_CLAIM"),
    )
    rbac_viewer_aliases: str = Field(
        default="",
        validation_alias=AliasChoices("GW_RBAC_VIEWER_ALIASES", "RBAC_VIEWER_ALIASES"),
    )
    rbac_contributor_aliases: str = Field(
        default="",
        validation_alias=AliasChoices("GW_RBAC_CONTRIBUTOR_ALIASES", "RBAC_CONTRIBUTOR_ALIASES"),
    )
    rbac_admin_aliases: str = Field(
        default="",
        validation_alias=AliasChoices("GW_RBAC_ADMIN_ALIASES", "RBAC_ADMIN_ALIASES"),
    )
    tenant_tag_key: str = Field(
        default="tenant",
        validation_alias=AliasChoices("GW_TENANT_TAG_KEY", "TENANT_TAG_KEY"),
    )


settings = Settings()
