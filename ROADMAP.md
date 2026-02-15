# Roadmap (Next Release)

## Next Release Goal: v0.1.0 Public Open Source Release

Deliver a functionally complete, usable first public release that platform teams can deploy, validate, and operate without modifying MLflow.

### v0.1 functional scope (must be complete)

- Tenant isolation for MLflow Runs and Model Registry paths currently covered by gateway policies.
- Minimal RBAC with tenant-scoped roles: `viewer`, `contributor`, `admin`.
- Audit logging for allowed and denied requests at the gateway enforcement boundary.
- Helm chart for Kubernetes deployment of the gateway.
- Enterprise documentation: integration guide and RBAC guide.
- Runnable demo that proves tenant isolation in a local environment.

## Operational readiness for v0.1

- Compatibility matrix for supported MLflow and Python versions.
- Explicit list of supported and unsupported MLflow endpoints.
- Operational runbook for health/readiness checks and common failure modes.
- Production logging guidance (audit usage, correlation patterns, retention expectations).
- Backward-compatibility policy for configuration and behavior changes.
- Test hardening for policy edge cases and regression stability.

## Out of scope for v0.1

- External policy engine integration (for example OPA).
- Direct LDAP integration in the gateway.
- Multi-cluster control plane or centralized management plane.
- Dedicated gateway UI.

## Scope notes

- Focus remains on reliability, security, and operator usability.
- No major architecture changes or control-plane expansion in this release.
