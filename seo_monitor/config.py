"""Strict config validation keeps network checks within owned HTTPS domains."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

import yaml


@dataclass(frozen=True)
class Settings:
    window_days: int = 28
    reporting_lag_days: int = 3
    request_timeout_seconds: int = 15
    min_impressions_for_rank_alert: int = 20
    rank_drop_alert_positions: float = 3.0


@dataclass(frozen=True)
class Site:
    id: str
    name: str
    base_url: str
    gsc_property: str
    keywords: tuple[str, ...]
    check_paths: tuple[str, ...]
    inspect_paths: tuple[str, ...]

    def url(self, path: str) -> str:
        return self.base_url + ("" if path == "/" else path) + ("/" if path == "/" else "")


def _path(value: str) -> str:
    if not isinstance(value, str) or not value.startswith("/") or value.startswith("//"):
        raise ValueError(f"Path must start with a single '/': {value!r}")
    parsed = urlsplit(value)
    if parsed.netloc or parsed.scheme or parsed.fragment or "\\" in value:
        raise ValueError(f"Unsafe URL path: {value!r}")
    return value


def _site(raw: dict) -> Site:
    import re

    site_id = str(raw["id"])
    if not re.fullmatch(r"[a-z][a-z0-9_-]{1,30}", site_id):
        raise ValueError(f"Invalid site id: {site_id}")
    base = str(raw["base_url"]).rstrip("/")
    parsed = urlsplit(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.port:
        raise ValueError(f"Only clean HTTPS base URLs are supported: {base}")
    if parsed.path or parsed.query or parsed.fragment or parsed.hostname == "localhost":
        raise ValueError(f"Base URL must contain only the host: {base}")
    prop = str(raw["gsc_property"])
    if not (prop == f"sc-domain:{parsed.hostname}" or prop in (base + "/", base)):
        raise ValueError(f"GSC property must belong to {base}: {prop}")
    checks = tuple(_path(p) for p in raw.get("check_paths", ["/"]))
    inspections = tuple(_path(p) for p in raw.get("inspect_paths", ["/"]))
    if len(checks) > 30 or len(inspections) > 20:
        raise ValueError("Limit check_paths to 30 and inspect_paths to 20 per site")
    keywords = tuple(str(k).strip() for k in raw.get("keywords", []))
    if not keywords or len(keywords) > 50 or any(not k or len(k) > 120 for k in keywords):
        raise ValueError("Provide 1–50 short keywords per site")
    return Site(
        id=site_id, name=str(raw["name"]), base_url=base, gsc_property=prop,
        keywords=keywords, check_paths=checks, inspect_paths=inspections,
    )


def load_config(path: Path) -> tuple[Settings, list[Site]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("sites"), list):
        raise ValueError("Config needs a 'sites' list")
    settings = Settings(**raw.get("settings", {}))
    if not 7 <= settings.window_days <= 90:
        raise ValueError("window_days must be in 7..90")
    if not 2 <= settings.reporting_lag_days <= 14:
        raise ValueError("reporting_lag_days must be in 2..14")
    if not 5 <= settings.request_timeout_seconds <= 60:
        raise ValueError("request_timeout_seconds must be in 5..60")
    if settings.min_impressions_for_rank_alert < 1 or settings.rank_drop_alert_positions < 1:
        raise ValueError("Alert thresholds must be positive")
    sites = [_site(s) for s in raw["sites"] if s.get("enabled", True)]
    if not sites or len(sites) > 30 or len({s.id for s in sites}) != len(sites):
        raise ValueError("Expected 1..30 unique enabled site IDs")
    return settings, sites
