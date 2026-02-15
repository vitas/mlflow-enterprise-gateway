from __future__ import annotations

import json
import logging
from datetime import UTC, datetime


audit_logger = logging.getLogger("gateway.audit")


def log_audit_event(
    *,
    method: str,
    path: str,
    status_code: int,
    request_id: str | None,
    tenant: str | None,
    subject: str | None,
    upstream: str,
    decision: str,
    reason: str | None = None,
) -> None:
    event = {
        "schema_version": "1",
        "timestamp": datetime.now(UTC).isoformat(),
        "request_id": request_id,
        "tenant": tenant,
        "subject": subject,
        "method": method,
        "path": path,
        "status_code": status_code,
        "upstream": upstream,
        "decision": decision,
    }
    if reason:
        event["reason"] = reason
    audit_logger.info(json.dumps(event, separators=(",", ":")))
