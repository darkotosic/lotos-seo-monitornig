"""Sanitized operator diagnostics: never persist provider payloads or credential URLs."""

from __future__ import annotations

import re
from typing import Any

# Only a fixed set of Google error reasons is safe to expose in commits and logs.
KNOWN_REASONS = {
    "accessNotConfigured", "accessNotConfiguredWithGoogleCloudProject",
    "accessNotConfiguredWithService", "forbidden", "insufficientPermissions",
    "insufficientAuthenticationScopes", "invalidCredentials", "notFound",
    "quotaExceeded", "dailyLimitExceeded", "rateLimitExceeded", "userRateLimitExceeded",
    "backendError", "internalError", "serviceUnavailable", "permissionDenied",
    "PERMISSION_DENIED", "RESOURCE_EXHAUSTED", "SERVICE_DISABLED",
}


def provider_error(exc: Exception, operation: str = "Google API") -> str:
    """Summarize HTTP status and allowlisted reason; do not echo exception text.

    Google HttpError messages sometimes include request URLs, arbitrary response
    bodies, headers or tokens. This formatter deliberately discards those fields.
    """
    response: Any = getattr(exc, "resp", None)
    status = getattr(response, "status", None)
    if isinstance(status, int) and 100 <= status <= 599:
        reason = getattr(exc, "error_reason", None)
        reason_text = reason if isinstance(reason, str) and reason in KNOWN_REASONS else None
        suffix = f" ({reason_text})" if reason_text else ""
        return f"{operation} HTTP {status}{suffix}"
    name = type(exc).__name__
    if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,60}", name):
        name = "Exception"
    return f"{operation} unavailable: {name}"
