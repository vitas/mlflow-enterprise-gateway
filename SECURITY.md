# Security Policy

## Security overview

This project provides a Policy Enforcement Point (PEP) in front of MLflow.  
It enforces authentication, tenant-aware authorization, and audit controls at the API boundary.

Security outcomes depend on correct deployment. In particular, MLflow should not be publicly exposed; user and client traffic should reach MLflow through the gateway.

## Supported versions

Security updates are provided for:

- the latest release on the main branch
- the latest maintained minor release line (if separate from main)

Older versions may not receive security fixes.

## Threat model (high level)

- OIDC/JWT authentication is used to validate caller identity in production mode.
- Tenant isolation is enforced at the gateway API boundary for supported endpoints.
- RBAC is evaluated per request based on configured role claims/aliases.
- Audit logs provide traceability for allowed and denied decisions.
- Direct access to MLflow can bypass gateway policy enforcement and weakens isolation/governance guarantees.

## Reporting a vulnerability

Please report vulnerabilities privately. Do not open public issues for security reports.

Preferred channels:

- GitHub Security Advisory (preferred)
- Email: `security@your-org.example` (placeholder; replace with project address)

Please include:

- affected component(s) and version
- reproduction steps or proof of concept
- potential impact
- any suggested mitigation

Responsible disclosure is requested to protect users while fixes are prepared.

Expected response time:

- initial acknowledgement within 3-5 business days

Validated issues will be fixed in a release, and reporter acknowledgement will be provided where appropriate.

## Security best practices for operators

- Expose only the gateway externally; keep MLflow internal.
- Enable OIDC mode in production.
- Use TLS at ingress/route entry points.
- Restrict network paths with NetworkPolicy.
- Monitor and retain audit logs for incident response.
