"""Bounded same-origin sitemap crawler. No paid APIs, browser automation or SERP scraping."""

from __future__ import annotations

from collections import Counter
from urllib.parse import urlsplit, urlunsplit

import httpx
from defusedxml import ElementTree

from seo_monitor.checks import _document, _get, _sitemap_urls
from seo_monitor.config import Site
from seo_monitor.content_audit import audit_metadata, internal_link_audit
from seo_monitor.cost_guard import CostGuard, QuotaExceeded
from seo_monitor.images import audit_images
from seo_monitor.schema_audit import audit_schema


def _same_host(url: str, site: Site) -> bool:
    parsed = urlsplit(url)
    origin = urlsplit(site.base_url)
    return (parsed.scheme == "https" and parsed.hostname == origin.hostname
            and parsed.port is None and not parsed.username and not parsed.password)


def _clean_url(url: str, site: Site) -> str | None:
    if not _same_host(url, site):
        return None
    parsed = urlsplit(url)
    if parsed.query or parsed.fragment or not parsed.path.startswith("/"):
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path or "/", "", ""))


def _locations(xml: bytes) -> tuple[str, list[str]]:
    """Extract only direct sitemap/url locs; XML entities disabled by defusedxml."""
    root = ElementTree.fromstring(xml)
    kind = root.tag.rsplit("}", 1)[-1]
    if kind not in ("sitemapindex", "urlset"):
        raise ValueError("Unknown sitemap root")
    return kind, _sitemap_urls(xml)


def _robots_allowed(robots_txt: str, path: str, agent: str = "LotosSEOAudit") -> bool:
    """Conservative longest-prefix allow/disallow check for owned crawler URLs.

    We follow the most specific matching robots group, then longest matching path.
    For complex wildcard rules the caller additionally uses a standard parser.
    """
    from urllib.robotparser import RobotFileParser

    parser = RobotFileParser()
    parser.parse(robots_txt.splitlines())
    # RobotFileParser does not consistently prioritize longest matching path across all versions.
    if not parser.can_fetch(agent, path) or not parser.can_fetch("Googlebot", path):
        return False
    groups: list[tuple[list[str], list[tuple[str, str]]]] = []
    names: list[str] = []
    rules: list[tuple[str, str]] = []
    in_rules = False
    for raw in robots_txt.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = (part.strip() for part in line.split(":", 1))
        key = key.lower()
        if key == "user-agent":
            if in_rules:
                groups.append((names, rules))
                names, rules, in_rules = [], [], False
            names.append(value.lower())
        elif key in ("allow", "disallow") and names:
            in_rules = True
            rules.append((key, value))
    if names:
        groups.append((names, rules))
    best = -1
    matching_rules: list[tuple[str, str]] = []
    for agents, choices in groups:
        scores = [len(x) for x in agents if x != "*" and x in agent.lower()]
        score = max(scores) if scores else (0 if "*" in agents else -1)
        if score > best:
            best, matching_rules = score, list(choices)
        elif score == best and score >= 0:
            matching_rules.extend(choices)
    matches = [(len(value), 1 if typ == "allow" else 0, typ)
               for typ, value in matching_rules if value and path.startswith(value)]
    if not matches:
        return True
    return max(matches)[2] == "allow"


def audit_site(site: Site, guard: CostGuard, *, client: httpx.Client | None = None) -> dict:
    """Cost-capped breadth-first audit of only owned public HTTPS URLs."""
    result: dict = {"site_id": site.id, "base_url": site.base_url, "pages": [],
                    "sitemap_urls": [], "sitemaps_fetched": 0, "warnings": [],
                    "quota_used": {}, "partial": False, "fatal_error": False}
    own = client is None
    if own:
        client = httpx.Client(timeout=httpx.Timeout(guard.limits.weekly_audit_timeout_seconds),
                              headers={"User-Agent": "LotosSEOAudit/3.0 (low-volume read-only)"})
    try:
        try:
            # robots is a lightweight metadata fetch; if unavailable, do not claim robots are permissive.
            response, body = _get(client, site, site.url("/robots.txt"))
            if response.status_code != 200:
                result["warnings"].append("robots.txt unavailable; audit aborted safely")
                result["fatal_error"] = True
                return result
            robots_txt = body.decode("utf-8", errors="replace")
        except (httpx.HTTPError, ValueError) as exc:
            result["warnings"].append(f"robots check failed: {type(exc).__name__}")
            result["fatal_error"] = True
            return result
        queue = [site.url("/sitemap.xml")]
        seen_sitemaps: set[str] = set()
        page_urls: list[str] = []
        while queue:
            sitemap = queue.pop(0)
            if sitemap in seen_sitemaps or not _same_host(sitemap, site):
                continue
            try:
                guard.consume("sitemaps")
            except QuotaExceeded:
                result["partial"] = True
                result["warnings"].append("Sitemap fetch quota reached")
                break
            seen_sitemaps.add(sitemap)
            try:
                response, content = _get(client, site, sitemap)
                if response.status_code != 200:
                    result["warnings"].append(f"Sitemap HTTP {response.status_code}")
                    continue
                kind, locations = _locations(content)
                if kind == "sitemapindex":
                    for location in locations:
                        location = _clean_url(location, site)
                        if location and location not in seen_sitemaps:
                            queue.append(location)
                else:
                    page_urls.extend(filter(None, (_clean_url(x, site) for x in locations)))
            except (httpx.HTTPError, ValueError, ElementTree.ParseError) as exc:
                result["warnings"].append(f"Sitemap parse/fetch: {type(exc).__name__}")
        result["sitemaps_fetched"] = len(seen_sitemaps)
        urls = list(dict.fromkeys(page_urls))
        if not urls:
            result["warnings"].append("No URL entries available in sitemap crawl")
            result["fatal_error"] = True
        result["sitemap_urls"] = urls[:150]
        for url in urls:
            if not _robots_allowed(robots_txt, urlsplit(url).path):
                result["warnings"].append(f"robots disallows {url}")
                continue
            try:
                guard.consume("crawl")
            except QuotaExceeded:
                result["partial"] = True
                result["warnings"].append("Page crawl quota reached; remaining URLs not requested")
                break
            try:
                response, content = _get(client, site, url)
                page = _document(site, response, content)
                page["path"] = urlsplit(url).path
                if url != page.get("url"):
                    page["requested_url"] = url
                # _document never reads any links outside actual HTML; no extra requests.
                result["pages"].append(page)
            except (httpx.HTTPError, ValueError) as exc:
                result["pages"].append({"url": url, "path": urlsplit(url).path,
                                        "error": type(exc).__name__})
        pages = result["pages"]
        result["metadata_issues"] = audit_metadata(pages, site.id)
        result["schema_issues"] = audit_schema(pages)
        result["image_issues"] = audit_images(pages)
        result["link_audit"] = internal_link_audit(pages, urls)
        result["http_statuses"] = dict(Counter(str(p.get("status", "ERR")) for p in pages))
        result["quota_used"] = dict(guard.used)
        result["pages_in_sitemap"] = len(urls)
        return result
    finally:
        if own:
            client.close()
