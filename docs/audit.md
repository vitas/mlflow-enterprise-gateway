# Audit Logging (Schema v1)

Gateway audit logs are emitted as single-line JSON suitable for SIEM ingestion.

## Schema version

- `schema_version`: `"1"`

## Fields

- `schema_version` (string): fixed schema version (`"1"`).
- `timestamp` (string): ISO8601 UTC timestamp.
- `request_id` (string|null): request correlation ID (`X-Request-ID`).
- `tenant` (string|null): resolved tenant context.
- `subject` (string|null): caller subject (for example JWT `sub`).
- `method` (string): HTTP method.
- `path` (string): gateway request path.
- `status_code` (number): response status code.
- `upstream` (string): upstream URL or policy/auth label.
- `decision` (string): `allow`, `deny`, or `error`.
- `reason` (string, optional): short reason for deny/error.

## Decision semantics

- `allow`: successful request (`2xx`/`3xx`).
- `deny`: policy/auth/input denial (`4xx`).
- `error`: internal or upstream server error (`5xx`).

## Example events

Allow:

```json
{"schema_version":"1","timestamp":"2026-02-15T12:00:00+00:00","request_id":"8fca3f9a-5f6d-4f7b-a530-4d68a57f5642","tenant":"team-a","subject":"alice","method":"POST","path":"/api/2.0/mlflow/runs/search","status_code":200,"upstream":"http://mlflow:5000/api/2.0/mlflow/runs/search","decision":"allow"}
```

Deny:

```json
{"schema_version":"1","timestamp":"2026-02-15T12:01:00+00:00","request_id":"d29b5bce-ec53-4e2f-a6d1-20af17dd8067","tenant":"team-a","subject":"alice","method":"POST","path":"/api/2.0/mlflow/runs/create","status_code":403,"upstream":"policy","decision":"deny","reason":"Insufficient role: required contributor, got viewer"}
```

Error:

```json
{"schema_version":"1","timestamp":"2026-02-15T12:02:00+00:00","request_id":"3c4dc398-45e0-43ee-a00a-6d8e6dcf9f9c","tenant":"team-a","subject":"alice","method":"POST","path":"/api/2.0/mlflow/runs/search","status_code":502,"upstream":"http://mlflow:5000/api/2.0/mlflow/runs/search","decision":"error","reason":"upstream_server_error"}
```
