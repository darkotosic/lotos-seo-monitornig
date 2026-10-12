"""Human-readable reports, safe alerts, and deterministic comparisons."""

from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path
from typing import Any

from seo_monitor.config import Settings, Site
from seo_monitor.opportunities import discover


def safe(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def metric(value: dict | None, name: str) -> str:
    if value is None:
        return "N/D"
    v = value.get(name)
    if v is None:
        return "N/D"
    if name == "ctr":
        return f"{100 * v:.1f}%"
    if name == "position":
        if value.get("impressions", 0) == 0:
            return "N/D"
        return f"{v:.1f}"
    return str(v)


def assess(snapshot: dict, settings: Settings, previous_snapshot: dict | None = None) -> list[str]:
    alerts: list[str] = []
    checks = snapshot.get("checks") or {}
    for page in checks.get("pages", []):
        if page.get("error"):
            alerts.append(f"HTTP/on-page: {page['path']}: {page['error']}")
        elif page.get("warning"):
            alerts.append(f"SEO warning: {page['path']}: {page['warning']}")
    for key in ("sitemap", "robots"):
        if checks.get(key, {}).get("error"):
            alerts.append(f"{key}: {checks[key]['error']}")
    if snapshot.get("gsc_error"):
        alerts.append(f"GSC unavailable: {snapshot['gsc_error']}")
    for inspection in (snapshot.get("gsc") or {}).get("inspections", []):
        if inspection.get("error"):
            alerts.append(f"Index inspection: {inspection['url']}: {inspection['error']}")
        elif inspection.get("verdict") in ("NEUTRAL", "FAIL"):
            alerts.append(f"Index review: {inspection['url']}: {inspection.get('coverageState') or inspection['verdict']}")
    gsc = snapshot.get("gsc") or {}
    for kw in gsc.get("keywords", []):
        current, previous = kw.get("current"), kw.get("previous")
        if not current or not previous:
            continue  # Privacy-filtered, new keywords, or no measured impressions.
        if (current["impressions"] < settings.min_impressions_for_rank_alert
                or previous["impressions"] < settings.min_impressions_for_rank_alert
                or current.get("position") is None or previous.get("position") is None):
            continue
        delta = current["position"] - previous["position"]
        if delta >= settings.rank_drop_alert_positions:
            alerts.append(f"Position down: {kw['query']}: {previous['position']:.1f} → {current['position']:.1f}")
    if previous_snapshot:
        old_pages = {p["path"]: p for p in (previous_snapshot.get("checks") or {}).get("pages", [])}
        for page in checks.get("pages", []):
            old = old_pages.get(page["path"])
            if old and not old.get("error") and page.get("error"):
                alerts.append(f"NEW outage: {page['path']}")
        old_inspections = {p["url"]: p for p in (previous_snapshot.get("gsc") or {}).get("inspections", [])}
        for inspection in gsc.get("inspections", []):
            old = old_inspections.get(inspection["url"])
            if old and old.get("verdict") == "PASS" and inspection.get("verdict") not in ("PASS", None):
                alerts.append(f"Index regression: {inspection['url']}: {inspection.get('coverageState')}")
    return sorted(set(alerts))


def opportunities(snapshot: dict) -> list[str]:
    """Rank evidence-backed review candidates from tracked and discovered GSC queries."""
    return [f"{item['priority']} — {item['target']} | pozicija {item['position']:.1f}, "
            f"prikazi {item['impressions']}: {item['recommendation']}"
            for item in discover(snapshot, minimum_impressions=20, limit=15)]


def markdown(site: Site, snapshot: dict) -> str:
    gsc = snapshot.get("gsc") or {}
    totals = gsc.get("totals")
    previous_totals = gsc.get("previous_totals")
    lines = [
        f"# SEO izveštaj — {safe(site.name)}",
        "",
        f"Generisano: {snapshot['created_at']}  |  Domen: {site.base_url}",
        "",
        "## Google Search Console — Web pretraga",
        f"Period: {gsc.get('current_window', {}).get('start','N/D')} do {gsc.get('current_window', {}).get('end','N/D')} (finalizovani podaci)",
        "",
        "| Pokazatelj | Tekući period | Prethodni period |",
        "|---|---:|---:|",
    ]
    for name, label in (("clicks", "Klikovi"), ("impressions", "Prikazi"), ("ctr", "CTR"), ("position", "Prosečna pozicija")):
        lines.append(f"| {label} | {metric(totals, name)} | {metric(previous_totals, name)} |")
    if gsc.get("weekly_window"):
        week = gsc.get("weekly_totals")
        previous_week = gsc.get("previous_weekly_totals")
        lines += ["", "## Nedeljno poređenje — 7 + 7 dana", "",
                  f"Period: {gsc['weekly_window'].get('start')} do {gsc['weekly_window'].get('end')}", "",
                  "| Pokazatelj | Poslednjih 7 dana | Prethodnih 7 dana |",
                  "|---|---:|---:|",
                  f"| Klikovi | {metric(week, 'clicks')} | {metric(previous_week, 'clicks')} |",
                  f"| Prikazi | {metric(week, 'impressions')} | {metric(previous_week, 'impressions')} |",
                  f"| Pozicija | {metric(week, 'position')} | {metric(previous_week, 'position')} |"]
    lines += ["", "## Ključne reči", "", "| Upit | Klikovi | Prikazi | CTR | Pozicija | Prethodna pozicija |",
              "|---|---:|---:|---:|---:|---:|"]
    for kw in gsc.get("keywords", []):
        c, p = kw.get("current"), kw.get("previous")
        lines.append(f"| {safe(kw['query'])} | {metric(c,'clicks')} | {metric(c,'impressions')} | "
                     f"{metric(c,'ctr')} | {metric(c,'position')} | {metric(p,'position')} |")
    lines += ["", "## Najposećenije stranice", "", "| URL | Klikovi | Prikazi | Pozicija |",
              "|---|---:|---:|---:|"]
    for row in gsc.get("top_pages", [])[:15]:
        lines.append(f"| {safe(row['url'])} | {metric(row,'clicks')} | "
                     f"{metric(row,'impressions')} | {metric(row,'position')} |")
    if gsc.get("top_queries"):
        lines += ["", "## Dodatni upiti iz Search Console (uzorak do 250)", "",
                  "| Upit | Klikovi | Prikazi | Pozicija |", "|---|---:|---:|---:|"]
        for row in gsc["top_queries"][:25]:
            lines.append(f"| {safe(row['query'])} | {metric(row,'clicks')} | "
                         f"{metric(row,'impressions')} | {metric(row,'position')} |")
    if gsc.get("image_search_totals"):
        lines += ["", "## Google Image Search", "",
                  f"- Klikovi: {metric(gsc['image_search_totals'], 'clicks')}",
                  f"- Prikazi: {metric(gsc['image_search_totals'], 'impressions')}",
                  f"- Prosečna pozicija: {metric(gsc['image_search_totals'], 'position')}"]
    for label, title, key in (("devices", "Uređaji", "device"),
                               ("countries", "Zemlje", "country")):
        if gsc.get(label):
            lines += ["", f"## {title}", "", "| Segment | Klikovi | Prikazi | Pozicija |",
                      "|---|---:|---:|---:|"]
            for row in gsc[label][:12]:
                lines.append(f"| {safe(row[key])} | {metric(row,'clicks')} | "
                             f"{metric(row,'impressions')} | {metric(row,'position')} |")
    lines += ["", "## Search appearance", "", "| Tip | Klikovi | Prikazi |",
              "|---|---:|---:|"]
    for row in gsc.get("search_appearances", []):
        lines.append(f"| {safe(row['appearance'])} | {metric(row,'clicks')} | {metric(row,'impressions')} |")
    lines += ["", "## Google indeks (URL Inspection API)", "", "| URL | Status | Coverage | Google canonical |",
              "|---|---|---|---|"]
    for item in gsc.get("inspections", []):
        lines.append(f"| {safe(item['url'])} | {safe(item.get('verdict',item.get('error','N/D')))} | "
                     f"{safe(item.get('coverageState','N/D'))} | {safe(item.get('googleCanonical','N/D'))} |")
    lines += ["", "## Tehničko zdravlje", "", "| URL | HTTP | SEO problem |",
              "|---|---:|---|"]
    for page in snapshot.get("checks", {}).get("pages", []):
        lines.append(f"| {safe(page['url'])} | {page.get('status','N/D')} | "
                     f"{safe(page.get('error') or page.get('warning') or ('H1 u početnom HTML-u je placeholder' if page.get('ssr_h1_placeholder') else '—'))} |")
    for kind in ("sitemap", "robots"):
        item = snapshot.get("checks", {}).get(kind, {})
        lines.append(f"- **{kind}:** HTTP {item.get('status','N/D')}; "
                     f"{safe(item.get('error') or 'bez uočenih HTTP problema')}")
    lines += ["", "## SEO mogućnosti (heuristika, nije prognoza)", ""]
    lines += [f"- {safe(item)}" for item in opportunities(snapshot)] or ["Nema dovoljno podataka za preporuke."]
    lines += ["", "## Upozorenja", ""]
    lines += [f"- {safe(alert)}" for alert in snapshot.get("alerts", [])] or ["Nema aktiviranih upozorenja."]
    if snapshot.get("gsc_error"):
        lines += ["", f"**GSC greška:** {safe(snapshot['gsc_error'])}"]
    lines += ["", "*N/D znači da podaci nisu dostupni ili Google nije prijavio podatke; nije isto što i 0.*",
              "*URL Inspection prikazuje stanje iz Google indeksa, ne trenutni live test stranice.*", ""]
    return "\n".join(lines)


def spreadsheet_text(value: str) -> str:
    """Avoid spreadsheet formula interpretation when opening generated CSV in Excel."""
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) else value


def csv_history(folder: Path, path: Path, rank_path: Path) -> None:
    """Export daily aggregate and keyword trends from local snapshots (no database)."""
    with path.open("w", encoding="utf-8-sig", newline="") as fh, rank_path.open(
        "w", encoding="utf-8-sig", newline=""
    ) as rank_fh:
        overall = csv.writer(fh)
        positions = csv.writer(rank_fh)
        overall.writerow(["date", "period_start", "period_end", "clicks", "impressions", "ctr_percent",
                          "average_position", "alerts_count", "gsc_status"])
        positions.writerow(["date", "query", "clicks", "impressions", "ctr_percent", "average_position"])
        for file in sorted(folder.glob("????-??-??.json")):
            try:
                snapshot = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, ValueError, TypeError):
                continue
            gsc = snapshot.get("gsc") or {}
            totals = gsc.get("totals") or {}
            overall.writerow([
                snapshot.get("monitor_date", file.stem),
                gsc.get("current_window", {}).get("start", ""),
                gsc.get("current_window", {}).get("end", ""),
                totals.get("clicks", ""), totals.get("impressions", ""),
                round(totals["ctr"] * 100, 2) if totals.get("ctr") is not None else "",
                totals.get("position", ""), len(snapshot.get("alerts", [])),
                "ok" if "gsc" in snapshot else "unavailable",
            ])
            for item in gsc.get("keywords", []):
                value = item.get("current") or {}
                positions.writerow([
                    snapshot.get("monitor_date", file.stem), spreadsheet_text(item["query"]),
                    value.get("clicks", ""), value.get("impressions", ""),
                    round(value["ctr"] * 100, 2) if value.get("ctr") is not None else "",
                    value.get("position", ""),
                ])


def csv_keywords(path: Path, snapshot: dict) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["query", "clicks", "impressions", "ctr_percent", "average_position", "previous_position"])
        for row in (snapshot.get("gsc") or {}).get("keywords", []):
            c, p = row.get("current"), row.get("previous")
            writer.writerow([
                spreadsheet_text(row["query"]), c["clicks"] if c else "", c["impressions"] if c else "",
                round(c["ctr"] * 100, 2) if c else "", c["position"] if c else "",
                p["position"] if p else "",
            ])


def overview(sites: list[Site], snapshots: dict[str, dict]) -> str:
    lines = ["# SEO Monitoring — svi domeni", "", "| Domen | Klikovi (28d) | Prikazi (28d) | CTR | Pozicija | Upozorenja |",
             "|---|---:|---:|---:|---:|---:|"]
    for site in sites:
        snap = snapshots.get(site.id, {})
        gsc = snap.get("gsc") or {}
        totals = gsc.get("totals")
        lines.append(f"| {site.base_url} | {metric(totals,'clicks')} | {metric(totals,'impressions')} | "
                     f"{metric(totals,'ctr')} | {metric(totals,'position')} | "
                     f"{len(snap.get('alerts',[]))} |")
    lines += ["", "Period: poslednjih 28 finalizovanih dana zaključno sa datumom prikazanim u pojedinačnim izveštajima.", ""]
    return "\n".join(lines)


def dashboard(sites: list[Site], snapshots: dict[str, dict]) -> str:
    """Static accessible dashboard, with escaped untrusted GSC strings."""
    cards = []
    for site in sites:
        snap = snapshots.get(site.id, {})
        gsc = snap.get("gsc") or {}
        current, previous = gsc.get("totals"), gsc.get("previous_totals")
        link = escape(site.base_url, quote=True)
        alerts = len(snap.get("alerts", []))
        keys = [item for item in gsc.get("keywords", [])
                if item.get("current") and item["current"].get("impressions", 0) > 0]
        keys.sort(key=lambda item: -item["current"]["impressions"])
        key_rows = "".join(
            f"<tr><th scope='row'>{escape(str(k['query']))}</th>"
            f"<td>{metric(k['current'], 'position')}</td>"
            f"<td>{metric(k['current'], 'impressions')}</td></tr>"
            for k in keys[:5]
        ) or "<tr><td colspan='3'>Nema dovoljno podataka za praćene upite</td></tr>"
        checks = (snap.get("checks") or {}).get("pages") or []
        healthy = sum(1 for page in checks if page.get("status") == 200 and not page.get("error"))
        inspections = gsc.get("inspections", [])
        indexed = sum(1 for row in inspections if row.get("verdict") == "PASS")
        index_label = f"{indexed}/{len(inspections)} PASS (uzorak)" if inspections else "N/D"
        period = gsc.get("current_window") or {}
        period_label = (f"{escape(str(period['start']))} — {escape(str(period['end']))}"
                        if period.get("start") and period.get("end") else "GSC nije dostupan")
        linkid = escape(site.id, quote=True)
        cards.append(f"""<article><h2><a href="{link}" rel="noopener noreferrer">{escape(site.name)}</a></h2>
<p class="domain">{link}</p><p class="period">GSC: {period_label}</p>
<div class="stats"><div><b>{metric(current,'clicks')}</b><span>Klikovi / 28d</span></div>
<div><b>{metric(current,'impressions')}</b><span>Prikazi / 28d</span></div>
<div><b>{metric(current,'ctr')}</b><span>CTR / 28d</span></div>
<div><b>{metric(current,'position')}</b><span>Prosečna pozicija / 28d</span></div></div>
<p class="detail">Prethodnih 28d: {metric(previous, 'clicks')} klikova / {metric(previous, 'impressions')} prikaza</p>
<p class="detail">HTTP 200: {healthy}/{len(checks)} · Google indeks: {index_label}</p>
<p class="{'bad' if alerts else 'good'}">{'Upozorenja: ' + str(alerts) if alerts else 'Nema aktivnih upozorenja'}</p>
<table><caption>Glavne praćene ključne reči</caption><thead><tr><th>Upit</th><th>Pozicija</th><th>Prikazi</th></tr></thead>
<tbody>{key_rows}</tbody></table>
<p class="links"><a href="{linkid}-latest.md">Izveštaj</a> ·
<a href="{linkid}-keywords.csv">Upiti CSV</a> ·
<a href="{linkid}-history.csv">Istorija</a> ·
<a href="{linkid}-rank-history.csv">Pozicije</a></p></article>""")
    head = """<!doctype html><html lang="sr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>Lotos SEO Monitoring</title><style>
:root{color-scheme:light;font-family:system-ui,sans-serif}*{box-sizing:border-box}
body{background:#f5f8f7;color:#1d2930;margin:auto;padding:24px;max-width:1320px}
h1{font-size:clamp(1.5rem,3vw,2.2rem)}p{line-height:1.5}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,430px),1fr));gap:18px}
article{background:#fff;border:1px solid #d7e2dc;border-radius:16px;padding:24px;box-shadow:0 4px 20px #153c2910}
a{color:#145a3e}a:focus-visible{outline:3px solid #b38825;outline-offset:3px}
article h2{font-size:1.25rem;margin:0}.domain,.period,.detail{color:#50655a;font-size:.85rem}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:8px 0}
.stats div{background:#f6faf7;border:1px solid #dfebe4;padding:12px;border-radius:10px}
.stats b{display:block;font-size:1.7rem;font-variant-numeric:tabular-nums}
.stats span{display:block;color:#466052;font-size:.78rem}
.good{color:#147249;font-weight:700}.bad{color:#ac5218;font-weight:700}
table{border-collapse:collapse;width:100%;font-size:.85rem}caption{text-align:left;font-weight:700;margin:10px 0}
th,td{border-bottom:1px solid #e3ebe6;text-align:left;padding:8px 6px}
th:nth-child(n+2),td:nth-child(n+2){text-align:right}
.links{font-size:.85rem}.notice{max-width:850px;color:#466052}
</style></head><body><header><h1>Lotos SEO Monitoring</h1>
<p class="notice">Zvanični Search Console podaci (finalizovani, nisu live Google rezultati).
Pozicija je prosek, a URL Inspection prikazuje samo odabrani uzorak stranica.
N/D znači da podaci nisu dostupni, ne poziciju nula.</p></header><main>"""
    return head + "\n".join(cards) + "</main></body></html>"
