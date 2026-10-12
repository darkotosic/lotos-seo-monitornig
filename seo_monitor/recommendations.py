"""Evidence-backed action queue. Never changes production sites automatically."""

from __future__ import annotations

from seo_monitor.opportunities import discover


def recommendations(snapshot: dict, audit: dict | None = None, limit: int = 15) -> list[dict]:
    tasks: list[dict] = []
    for item in discover(snapshot):
        tasks.append({"priority": item["priority"], "source": "GSC", "target": item["target"],
                      "action": item["recommendation"], "evidence": {
                          "impressions": item["impressions"], "position": item["position"],
                          "ctr": item["ctr"]}, "manual_review_required": True})
    for page in (audit or {}).get("pages", []):
        if page.get("error") or (page.get("status") or 0) >= 400:
            tasks.append({"priority": "P0", "source": "crawler", "target": page.get("url", ""),
                          "action": page.get("error") or f"HTTP {page.get('status')}",
                          "manual_review_required": True})
    for item in (audit or {}).get("metadata_issues", []):
        tasks.append({"priority": item["severity"], "source": "crawler", "target": item["url"],
                      "action": item["type"], "manual_review_required": True})
    for item in (audit or {}).get("schema_issues", []):
        tasks.append({"priority": item["severity"], "source": "crawler", "target": item["url"],
                      "action": item["type"], "manual_review_required": True})
    for item in (audit or {}).get("image_issues", []):
        if item.get("severity") != "INFO":
            tasks.append({"priority": item["severity"], "source": "crawler", "target": item["url"],
                          "action": item["type"], "manual_review_required": True})
    order = {"P0": 0, "P1": 1, "P2": 2, "INFO": 3}
    tasks.sort(key=lambda r: (order.get(r["priority"], 9), r["source"], r["target"]))
    return tasks[:limit]
