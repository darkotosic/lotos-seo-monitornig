"""Optional read-only aggregated GA4 Data API using existing Google auth package.

Not enabled by default. No visitor/client identifiers or customer data. No new billing service.
"""

from __future__ import annotations

from datetime import date


def read_organic_overview(credentials_file: str, property_id: str, start: date, end: date) -> dict:
    if not property_id.isascii() or not property_id.isdigit():
        raise ValueError("GA4 property ID must be numeric")
    if start > end:
        raise ValueError("Invalid date range")
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/analytics.readonly"]
    credentials = service_account.Credentials.from_service_account_file(credentials_file, scopes=scopes)
    api = build("analyticsdata", "v1beta", credentials=credentials, cache_discovery=False)
    payload = {"dateRanges": [{"startDate": start.isoformat(), "endDate": end.isoformat()}],
               "metrics": [{"name": "sessions"}, {"name": "keyEvents"}],
               "dimensionFilter": {"filter": {"fieldName": "sessionDefaultChannelGroup",
                                              "stringFilter": {"value": "Organic Search", "matchType": "EXACT"}}},
               "limit": 1}
    result = api.properties().runReport(property=f"properties/{property_id}", body=payload).execute(num_retries=1)
    metric_values = (result.get("rows") or [{}])[0].get("metricValues") or []
    def value(index: int) -> float | None:
        try:
            return float(metric_values[index]["value"])
        except (IndexError, KeyError, TypeError, ValueError):
            return None
    return {"start": start.isoformat(), "end": end.isoformat(),
            "organic_sessions": value(0), "key_events": value(1),
            "warning": "keyEvents uključuje sve konfigurisane key events; ne predstavlja potvrđene uplate."}
