"""Deterministic SEO opportunities from actual GSC observations. No made-up metrics."""

from __future__ import annotations

from typing import Any


def _eligible(row: dict[str, Any], minimum: int) -> bool:
    return row.get("impressions", 0) >= minimum and isinstance(row.get("position"), (int, float)) and row["position"] > 0


def discover(snapshot: dict, *, minimum_impressions: int = 20, limit: int = 12) -> list[dict]:
    """Return evidence-backed human review tasks; numbers are not ranking forecasts."""
    gsc = snapshot.get("gsc") or {}
    items: list[dict] = []
    candidates = [(r.get("query", ""), r.get("current") or {}, "query", "")
                  for r in gsc.get("keywords", [])]
    candidates += [(r.get("query", ""), r, "query", "") for r in gsc.get("top_queries", [])]
    candidates += [(r.get("url", ""), r, "page", r.get("url", ""))
                   for r in gsc.get("top_pages", [])]
    seen = set()
    for label, value, kind, url in candidates:
        identifier = (kind, label)
        if not label or identifier in seen or not _eligible(value, minimum_impressions):
            continue
        seen.add(identifier)
        impressions = value["impressions"]
        position, ctr = float(value["position"]), float(value.get("ctr") or 0)
        if 4 <= position <= 15:
            issue = "Pozicija 4–15: proveriti nameru pretrage, sadržaj i interne linkove"
            priority = "P1" if position <= 10 else "P2"
        elif position < 4 and ctr < 0.04 and impressions >= 50:
            issue = "Visoka pozicija uz nizak CTR: proveriti stvarni SERP, naslov i snippet"
            priority = "P1"
        elif position > 15 and impressions >= 100:
            issue = "Veliki broj prikaza i daleka pozicija: proceniti relevantnost stranice"
            priority = "P2"
        else:
            continue
        # Heuristic prioritization of review, not claimed prediction of clicks or rank.
        score = round(min(impressions, 5000) ** 0.5 * (2.0 if priority == "P1" else 1.0), 2)
        items.append({"kind": kind, "target": label[:250], "url": url,
                      "impressions": impressions, "clicks": value.get("clicks", 0),
                      "position": round(position, 2), "ctr": round(ctr, 5),
                      "priority": priority, "score": score, "recommendation": issue})
    items.sort(key=lambda x: (-x["score"], x["kind"], x["target"]))
    return items[:limit]


def compare_totals(current: dict | None, previous: dict | None) -> dict:
    """Comparable 28d periods only; missing is not zero."""
    if not current or not previous:
        return {"available": False}
    return {"available": True,
            "clicks_change": current.get("clicks", 0) - previous.get("clicks", 0),
            "impressions_change": current.get("impressions", 0) - previous.get("impressions", 0),
            "position_delta": (round(current["position"] - previous["position"], 2)
                               if current.get("position") and previous.get("position") else None)}
