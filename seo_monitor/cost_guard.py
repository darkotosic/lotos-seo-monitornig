"""Hard zero-cost execution caps. No paid provider or pay-as-you-go fallback."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


class QuotaExceeded(RuntimeError):
    """Optional check was skipped before any additional provider request."""


@dataclass(frozen=True)
class Limits:
    cost_mode: str = "free_only"
    maximum_sites: int = 20
    maximum_daily_gsc_calls_per_site: int = 40
    maximum_daily_inspections_per_site: int = 8
    maximum_weekly_crawl_pages_per_site: int = 80
    maximum_weekly_sitemaps_per_site: int = 3
    maximum_weekly_pagespeed_calls_per_site: int = 4
    maximum_weekly_image_checks_per_site: int = 12
    maximum_http_response_bytes: int = 2_000_000
    weekly_audit_timeout_seconds: int = 25


_BOUNDS = {
    "maximum_sites": (1, 30),
    "maximum_daily_gsc_calls_per_site": (1, 60),
    "maximum_daily_inspections_per_site": (0, 15),
    "maximum_weekly_crawl_pages_per_site": (1, 150),
    "maximum_weekly_sitemaps_per_site": (1, 5),
    "maximum_weekly_pagespeed_calls_per_site": (0, 8),
    "maximum_weekly_image_checks_per_site": (0, 25),
    "maximum_http_response_bytes": (1024, 2_000_000),
    "weekly_audit_timeout_seconds": (5, 40),
}


def load_limits(path: Path) -> Limits:
    """Reject unknown/unsafe configuration instead of silently enabling paid services."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("version") != 1:
        raise ValueError("Invalid limits file or version")
    unknown = set(raw) - {"version", *Limits.__dataclass_fields__}
    if unknown:
        raise ValueError(f"Unknown zero-cost limits: {', '.join(sorted(unknown))}")
    if raw.get("cost_mode") != "free_only":
        raise ValueError("Only free_only cost mode is allowed")
    values = {k: v for k, v in raw.items() if k != "version"}
    for name, (low, high) in _BOUNDS.items():
        val = values.get(name, getattr(Limits(), name))
        if type(val) is not int or not low <= val <= high:
            raise ValueError(f"Unsafe zero-cost quota {name}: expected integer {low}..{high}")
    return Limits(**values)


@dataclass
class CostGuard:
    limits: Limits
    used: dict[str, int] = field(default_factory=dict)

    def consume(self, category: str, amount: int = 1) -> None:
        bound = {
            "gsc": self.limits.maximum_daily_gsc_calls_per_site,
            "inspection": self.limits.maximum_daily_inspections_per_site,
            "crawl": self.limits.maximum_weekly_crawl_pages_per_site,
            "sitemaps": self.limits.maximum_weekly_sitemaps_per_site,
            "pagespeed": self.limits.maximum_weekly_pagespeed_calls_per_site,
            "image": self.limits.maximum_weekly_image_checks_per_site,
        }.get(category)
        if bound is None or type(amount) is not int or amount < 1:
            raise ValueError("Unknown quota category or invalid requested amount")
        next_used = self.used.get(category, 0) + amount
        if next_used > bound:
            raise QuotaExceeded(f"Free quota '{category}' reached ({bound}); request NOT sent")
        self.used[category] = next_used

    def remaining(self, category: str) -> int:
        maxima = {
            "gsc": self.limits.maximum_daily_gsc_calls_per_site,
            "inspection": self.limits.maximum_daily_inspections_per_site,
            "crawl": self.limits.maximum_weekly_crawl_pages_per_site,
            "sitemaps": self.limits.maximum_weekly_sitemaps_per_site,
            "pagespeed": self.limits.maximum_weekly_pagespeed_calls_per_site,
            "image": self.limits.maximum_weekly_image_checks_per_site,
        }
        return max(0, maxima[category] - self.used.get(category, 0))
