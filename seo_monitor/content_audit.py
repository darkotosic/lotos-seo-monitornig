"""Non-generative content review; differentiates wrong DELIVERY city from business address."""

from __future__ import annotations

import re
from urllib.parse import urlsplit


def audit_metadata(pages: list[dict], site_id: str) -> list[dict]:
    warnings = []
    values: dict[tuple[str, str], list[str]] = {}
    for page in pages:
        url = page.get("url", "")
        if page.get("status") != 200 or "text/html" not in page.get("content_type", ""):
            continue
        for field in ("title", "description"):
            text = (page.get(field) or "").strip()
            if not text:
                warnings.append({"url": url, "type": f"missing_{field}", "severity": "P1"})
            elif len(text) < 8:
                warnings.append({"url": url, "type": f"short_{field}", "severity": "P2"})
            else:
                values.setdefault((field, text.casefold()), []).append(url)
        if page.get("ssr_h1_placeholder"):
            warnings.append({"url": url, "type": "ssr_h1_placeholder", "severity": "P2",
                             "details": "Početni HTML ima placeholder; proveriti renderovani H1 u browseru"})
        if page.get("h1_count", 0) == 0:
            warnings.append({"url": url, "type": "missing_ssr_h1", "severity": "P2"})
        if site_id == "indjija":
            text = " ".join((page.get("description") or "", page.get("title") or ""))
            if re.search(r"\bdostav[au]\s+(?:cveća\s+)?(?:u|za)\s+Rumi\b", text, flags=re.I):
                warnings.append({"url": url, "type": "wrong_delivery_city", "severity": "P1",
                                 "details": "Opis isporuke pominje Rumu; proveriti kontekst Inđije"})
    for (field, _), urls in values.items():
        if len(urls) > 1:
            warnings.append({"url": urls[0], "type": f"duplicate_{field}",
                             "severity": "P2", "affected_urls": urls[:12]})
    return warnings[:100]


def internal_link_audit(pages: list[dict], sitemap_urls: list[str]) -> dict:
    """Sitemap URLs with no link from crawled pages are *candidates*, not proven orphans."""
    crawled = {p.get("url", "").rstrip("/") for p in pages if p.get("status") == 200}
    linked = {link.rstrip("/") for p in pages for link in p.get("internal_links", [])}
    host = next((urlsplit(u).hostname for u in sitemap_urls if urlsplit(u).hostname), None)
    candidates = sorted({u.rstrip("/") for u in sitemap_urls
                         if urlsplit(u).hostname == host and u.rstrip("/") in crawled and
                         u.rstrip("/") not in linked})
    return {"crawled_pages": len(crawled), "candidate_orphans_in_crawled_sample": candidates[:30],
            "note": "Delimičan crawl: kandidat nije dokaz da stranica nema ulazne linkove."}
