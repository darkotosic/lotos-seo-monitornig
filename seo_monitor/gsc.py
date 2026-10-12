"""Read-only Google Search Console Search Analytics and URL Inspection calls."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from seo_monitor.config import Settings, Site
from seo_monitor.diagnostics import provider_error

SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"


def metrics(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    # Google may report an empty row. A position of 0 is not a ranking.
    if int(row.get("impressions", 0)) <= 0:
        return None
    return {
        "clicks": int(row.get("clicks", 0)),
        "impressions": int(row.get("impressions", 0)),
        "ctr": round(float(row.get("ctr", 0)), 5),
        "position": (round(float(row["position"]), 2)
                     if row.get("position") is not None and float(row["position"]) > 0 else None),
    }


def _first(response: dict[str, Any]) -> dict[str, Any] | None:
    return metrics(next(iter(response.get("rows", [])), None))


class GoogleSearchConsole:
    def __init__(self, credentials_file: str):
        if not credentials_file:
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is required for GSC")
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds = service_account.Credentials.from_service_account_file(credentials_file, scopes=[SCOPE])
        self.webmasters = build("webmasters", "v3", credentials=creds, cache_discovery=False)
        self.inspection = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    def query(self, prop: str, start: date, end: date, dimensions: list[str] | None = None,
              query: str | None = None, limit: int = 1000) -> dict[str, Any]:
        body: dict[str, Any] = {
            "startDate": start.isoformat(), "endDate": end.isoformat(),
            "type": "web", "dataState": "final", "rowLimit": limit,
        }
        if dimensions:
            body["dimensions"] = dimensions
        if query is not None:
            body["dimensionFilterGroups"] = [{"groupType": "and", "filters": [{
                "dimension": "query", "operator": "equals", "expression": query,
            }]}]
        return self.webmasters.searchanalytics().query(siteUrl=prop, body=body).execute(num_retries=2)

    def inspect(self, prop: str, url: str) -> dict[str, Any]:
        result = self.inspection.urlInspection().index().inspect(body={
            "inspectionUrl": url, "siteUrl": prop, "languageCode": "sr-RS",
        }).execute(num_retries=2)
        index = result.get("inspectionResult", {}).get("indexStatusResult", {})
        return {k: index.get(k) for k in (
            "verdict", "coverageState", "robotsTxtState", "indexingState", "lastCrawlTime",
            "pageFetchState", "googleCanonical", "userCanonical", "sitemap",
        )}


def collect_gsc(api: GoogleSearchConsole, site: Site, settings: Settings, today: date,
                inspect: bool = True) -> dict[str, Any]:
    end = today - timedelta(days=settings.reporting_lag_days)
    start = end - timedelta(days=settings.window_days - 1)
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=settings.window_days - 1)

    prop = site.gsc_property
    result: dict[str, Any] = {
        "current_window": {"start": start.isoformat(), "end": end.isoformat()},
        "previous_window": {"start": previous_start.isoformat(), "end": previous_end.isoformat()},
        "source": "Google Search Console API; finalized data; Web search",
    }
    # No dimensions gives site-level totals, not a sum of privacy-filtered query rows.
    result["totals"] = _first(api.query(prop, start, end))
    result["previous_totals"] = _first(api.query(prop, previous_start, previous_end))
    # Comparable seven-day windows, useful for weekly executive reporting.
    week_start = end - timedelta(days=6)
    preceding_week_end = week_start - timedelta(days=1)
    preceding_week_start = preceding_week_end - timedelta(days=6)
    result["weekly_window"] = {"start": week_start.isoformat(), "end": end.isoformat()}
    result["weekly_totals"] = _first(api.query(prop, week_start, end))
    result["previous_weekly_totals"] = _first(api.query(prop, preceding_week_start,
                                                           preceding_week_end))
    pages = api.query(prop, start, end, ["page"], limit=200)
    result["top_pages"] = [
        {"url": r["keys"][0], **metrics(r)} for r in pages.get("rows", [])
        if r.get("keys") and metrics(r) is not None
    ]
    appearances = api.query(prop, start, end, ["searchAppearance"], limit=100)
    result["search_appearances"] = [
        {"appearance": r["keys"][0], **metrics(r)} for r in appearances.get("rows", [])
        if r.get("keys") and metrics(r) is not None
    ]
    result["keywords"] = []
    for keyword in site.keywords:
        current = _first(api.query(prop, start, end, query=keyword))
        previous = _first(api.query(prop, previous_start, previous_end, query=keyword))
        result["keywords"].append({"query": keyword, "current": current, "previous": previous})

    result["inspections"] = []
    if inspect:
        for path in site.inspect_paths:
            url = site.url(path)
            try:
                result["inspections"].append({"url": url, **api.inspect(prop, url)})
            except Exception as exc:
                result["inspections"].append({
                    "url": url, "error": provider_error(exc, "URL Inspection"),
                })
    return result
