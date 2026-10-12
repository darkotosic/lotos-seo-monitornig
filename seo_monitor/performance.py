"""Opt-in bounded PageSpeed Insights checks, keyless endpoint (no Cloud billing)."""

from __future__ import annotations

import json
from urllib.parse import urlsplit

import httpx

from seo_monitor.config import Site
from seo_monitor.cost_guard import CostGuard, QuotaExceeded

PSI_ENDPOINT = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def _value(audits: dict, key: str) -> float | None:
    score = (audits.get(key) or {}).get("numericValue")
    return round(float(score), 2) if isinstance(score, (int, float)) else None


def parse_pagespeed(payload: dict) -> dict:
    """Field CWV and lab metrics kept separate; never invent unavailable CrUX."""
    lighthouse = payload.get("lighthouseResult") or {}
    audits = lighthouse.get("audits") or {}
    categories = lighthouse.get("categories") or {}
    perf = (categories.get("performance") or {}).get("score")
    experience = payload.get("loadingExperience") or {}
    field_metrics = experience.get("metrics") or {}
    return {
        "lab_performance_score": round(perf * 100) if isinstance(perf, (int, float)) else None,
        "lab_lcp_ms": _value(audits, "largest-contentful-paint"),
        "lab_cls": _value(audits, "cumulative-layout-shift"),
        "lab_tbt_ms": _value(audits, "total-blocking-time"),
        "field_data_available": bool(field_metrics),
        "field_lcp_ms_p75": (field_metrics.get("LARGEST_CONTENTFUL_PAINT_MS") or {}).get("percentile"),
        "field_cls_p75": (field_metrics.get("CUMULATIVE_LAYOUT_SHIFT_SCORE") or {}).get("percentile"),
        "field_inp_ms_p75": (field_metrics.get("INTERACTION_TO_NEXT_PAINT") or {}).get("percentile"),
        "note": "Lab PSI nije isti kao CrUX field data; nedostajući field podaci = N/D.",
    }


def collect_pagespeed(site: Site, guard: CostGuard, paths: tuple[str, ...] = ("/",),
                      *, client: httpx.Client | None = None) -> list[dict]:
    """Fail-safe to API quota/errors; never use a paid fallback or API key."""
    results: list[dict] = []
    own = client is None
    if own:
        client = httpx.Client(timeout=httpx.Timeout(guard.limits.weekly_audit_timeout_seconds))
    try:
        for path in paths:
            url = site.url(path)
            if urlsplit(url).hostname != urlsplit(site.base_url).hostname:
                continue
            for strategy in ("mobile", "desktop"):
                try:
                    guard.consume("pagespeed")
                except QuotaExceeded as exc:
                    results.append({"url": url, "strategy": strategy, "status": "quota_skipped",
                                    "reason": str(exc)})
                    return results
                try:
                    # Streaming prevents unbounded PSI responses from exhausting memory.
                    with client.stream("GET", PSI_ENDPOINT,
                                       params={"url": url, "strategy": strategy,
                                               "category": "performance"},
                                       follow_redirects=False) as response:
                        if response.status_code in (403, 429):
                            results.append({"url": url, "strategy": strategy,
                                            "status": "quota_or_service_unavailable",
                                            "http_status": response.status_code})
                            return results
                        if response.status_code != 200:
                            results.append({"url": url, "strategy": strategy,
                                            "status": "api_unavailable",
                                            "http_status": response.status_code})
                            continue
                        buffer = bytearray()
                        oversized = False
                        for chunk in response.iter_bytes():
                            buffer.extend(chunk)
                            if len(buffer) > guard.limits.maximum_http_response_bytes:
                                oversized = True
                                break
                    if oversized:
                        results.append({"url": url, "strategy": strategy, "status": "response_too_large"})
                        continue
                    parsed = parse_pagespeed(json.loads(buffer))
                    results.append({"url": url, "strategy": strategy, "status": "ok", **parsed})
                except (httpx.HTTPError, ValueError) as exc:
                    results.append({"url": url, "strategy": strategy,
                                    "status": "api_unavailable", "error_type": type(exc).__name__})
        return results
    finally:
        if own:
            client.close()
