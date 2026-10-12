"""Read-only JSON-LD audit; never invent ratings, shipping or return policies."""

from __future__ import annotations


def audit_schema(pages: list[dict]) -> list[dict]:
    issues = []
    for p in pages:
        if p.get("status") != 200 or "text/html" not in p.get("content_type", ""):
            continue
        types = p.get("jsonld_types") or []
        path = p.get("path", "")
        if p.get("jsonld_parse_errors", 0) > 0:
            issues.append({"url": p["url"], "type": "jsonld_syntax", "severity": "P1"})
        if path.startswith("/proizvodi/") and "Product" not in types:
            issues.append({"url": p["url"], "type": "product_schema_missing", "severity": "P2"})
        # Missing review/aggregateRating are optional enhancements; don't manufacture them.
    return issues
