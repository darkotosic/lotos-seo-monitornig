"""Reliable, plain-text, human-readable Telegram digest from verified snapshots.

No synthetic rank, no unverified business claim, no HTML/Markdown injection,
no customer's data and no access to Telegram message contents.
"""

from __future__ import annotations

from datetime import date

from seo_monitor.config import Site

TELEGRAM_SAFE_LIMIT = 3500


def _fmt(value: dict | None, key: str) -> str:
    if not value or value.get(key) is None or (key == "position" and value.get("impressions", 0) == 0):
        return "N/D"
    number = value[key]
    if key == "ctr":
        return f"{100 * number:.1f}%"
    if key == "position":
        return f"{number:.1f}"
    return f"{number:,}".replace(",", ".")


def _delta(current: dict | None, previous: dict | None, key: str) -> str:
    if not current or not previous or current.get(key) is None or previous.get(key) is None:
        return ""
    if key == "position" and (current.get("impressions", 0) < 1 or previous.get("impressions", 0) < 1):
        return ""
    before, after = previous[key], current[key]
    if key == "position":
        shift = after - before
        if abs(shift) < 0.05:
            return " (stabilno)"
        return f" ({'bolje' if shift < 0 else 'lošije'} {abs(shift):.1f})"
    if before == 0:
        return " (novo)" if after > 0 else ""
    pct = (after - before) / before * 100
    if abs(pct) < 0.05:
        return " (0%)"
    return f" ({pct:+.0f}%)"


def _index_counts(snapshot: dict) -> tuple[int, int, int]:
    inspections = (snapshot.get("gsc") or {}).get("inspections", [])
    passed = sum(1 for item in inspections if item.get("verdict") == "PASS")
    issues = sum(1 for item in inspections if item.get("verdict") in ("FAIL", "NEUTRAL"))
    unknown = sum(1 for item in inspections if item.get("error") or
                  item.get("verdict") not in ("PASS", "FAIL", "NEUTRAL"))
    return passed, issues, unknown


def build_daily_message(sites: list[Site], snapshots: dict[str, dict], today: date,
                        *, max_keywords: int = 3) -> str:
    """Build one bounded daily report for all enabled sites. Multiple domains scale."""
    lines = [f"LOTOS SEO MONITORING | {today.isoformat()}",
             "Google Search Console · Web · poslednjih 28 dana (sa zakašnjenjem)", ""]
    all_alerts = []
    for site in sites:
        snap = snapshots.get(site.id, {})
        gsc = snap.get("gsc") or {}
        current, previous = gsc.get("totals"), gsc.get("previous_totals")
        lines.append(f"{site.name} | {site.base_url}")
        if not gsc:
            lines.append("GSC: NEDOSTUPAN — podaci se ne prikazuju kao nula")
        else:
            period = gsc.get("current_window") or {}
            if period.get("start") and period.get("end"):
                lines.append(f"Period: {period['start']} — {period['end']}")
            lines.extend([
                f"Klikovi: {_fmt(current, 'clicks')}{_delta(current, previous, 'clicks')}",
                f"Prikazi: {_fmt(current, 'impressions')}{_delta(current, previous, 'impressions')}",
                f"CTR: {_fmt(current, 'ctr')}",
                f"Prosečna pozicija: {_fmt(current, 'position')}{_delta(current, previous, 'position')}",
            ])
            valid_keywords = sorted(
                (k for k in gsc.get("keywords", []) if k.get("current")
                 and k["current"].get("impressions", 0) > 0),
                key=lambda k: -k["current"]["impressions"],
            )[:max_keywords]
            if valid_keywords:
                lines.append("Upiti (prosečne pozicije):")
                for keyword in valid_keywords:
                    kw_current, kw_previous = keyword["current"], keyword.get("previous")
                    lines.append(f"- {keyword['query'][:72]}: {_fmt(kw_current, 'position')}"
                                 f"{_delta(kw_current, kw_previous, 'position')}"
                                 f" · {kw_current['impressions']} prikaza")
            indexed, issues, unknown = _index_counts(snap)
            if gsc.get("inspections"):
                lines.append(f"URL Inspection uzorak: {indexed} indeksirano, {issues} problem, "
                             f"{unknown} nepoznato")
        checks = (snap.get("checks") or {}).get("pages") or []
        ok = sum(1 for item in checks if item.get("status") == 200 and not item.get("error"))
        lines.append(f"HTTP: {ok}/{len(checks)} odgovora 200")
        if today.weekday() == 0 and gsc and (gsc.get("weekly_totals") or gsc.get("previous_weekly_totals")):
            week, prior_week = gsc.get("weekly_totals"), gsc.get("previous_weekly_totals")
            lines.append("Nedeljni pregled (7d naspram prethodnih 7d):")
            lines.append(f"- Klikovi: {_fmt(week, 'clicks')}{_delta(week, prior_week, 'clicks')}")
            lines.append(f"- Prikazi: {_fmt(week, 'impressions')}{_delta(week, prior_week, 'impressions')}")
        all_alerts.extend(f"{site.id}: {a}" for a in snap.get("alerts", []))
        lines.append("")
    lines.append(f"Upozorenja: {len(all_alerts)}")
    if all_alerts:
        lines += [f"- {a[:140]}" for a in all_alerts[:5]]
        if len(all_alerts) > 5:
            lines.append(f"... još {len(all_alerts) - 5} u izveštaju")
    else:
        lines.append("Bez aktivnih upozorenja.")
    lines += ["", "N/D = nema pouzdanih podataka; nije pozicija 0.",
              "Pozicije su GSC proseci, ne trenutni Google rezultati."]
    message = "\n".join(lines)
    if len(message) > TELEGRAM_SAFE_LIMIT:
        message = message[:TELEGRAM_SAFE_LIMIT - 55].rstrip() + "\n... nastavak u GitHub izveštajima."
    return message


def build_alert_message(new_alerts: list[str], today: date) -> str:
    header = f"LOTOS SEO UPOZORENJE | {today.isoformat()}\n"
    content = "\n".join(f"- {item[:170]}" for item in new_alerts[:15])
    if len(new_alerts) > 15:
        content += f"\n... još {len(new_alerts) - 15} novih upozorenja"
    return (header + content)[:TELEGRAM_SAFE_LIMIT]
