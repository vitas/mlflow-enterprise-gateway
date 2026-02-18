# Roadmap (Next Release)

## Current Baseline: v0.2.0

Current release baseline is `v0.2.0`, with gateway policy enforcement, readiness/liveness probes, structured audit schema v1, and expanded tenant/RBAC coverage for runs and model registry mutation paths.

## Next Release Goal

Deliver a production-ready hardening increment on top of `v0.2.0` focused on safe operations, stricter deployment defaults, and release discipline.

## Priorities

- Provide a production profile that exposes only gateway and keeps MLflow internal.
- Default docs and examples to OIDC mode for production paths.
- Keep demo/dev profile explicit and separate.
- Close highest-risk uncovered API paths based on real usage patterns.
- Publish compatibility matrix (MLflow/Python/Kubernetes targets).
- Add operator runbook for startup failures, probe behavior, and incident handling.


## Out of scope (unchanged)

- External policy engine integration (for example OPA).
- Direct LDAP integration in the gateway.
- Multi-cluster control plane or centralized management plane.
- Dedicated gateway UI.

## Scope notes

- Focus remains on reliability, security, and operator usability.
- No major architecture changes or control-plane expansion in this release.
