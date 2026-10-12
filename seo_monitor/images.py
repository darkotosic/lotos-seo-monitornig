"""Image metadata audit without external AI/paid Vision service."""

from __future__ import annotations


def audit_images(pages: list[dict]) -> list[dict]:
    issues = []
    for p in pages:
        if "text/html" not in p.get("content_type", ""):
            continue
        count = p.get("img_count", 0)
        if p.get("images_without_alt", 0):
            issues.append({"url": p["url"], "type": "img_alt_missing",
                           "count": p["images_without_alt"], "severity": "P2"})
        if count > 0 and not p.get("img_lazy_count", 0):
            # Informational only: eager loading may be appropriate for LCP image.
            issues.append({"url": p["url"], "type": "check_image_loading_strategy", "severity": "INFO"})
    return issues
