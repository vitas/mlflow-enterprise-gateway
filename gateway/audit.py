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
) -> None:
    event = {
        "ts": datetime.now(UTC).isoformat(),
        "method": method,
        "path": path,
        "status_code": status_code,
        "request_id": request_id,
        "tenant": tenant,
        "subject": subject,
        "upstream": upstream,
    }
    audit_logger.info(json.dumps(event, separators=(",", ":")))
