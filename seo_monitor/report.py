"""Human-readable reports, safe alerts, and deterministic comparisons."""

from __future__ import annotations

import csv
import json
from html import escape
from pathlib import Path
from typing import Any

from seo_monitor.config import Settings, Site


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
                or previous["impressions"] < settings.min_impressions_for_rank_alert):
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
    """Conservative decision support; never a promise of a Google rank."""
    output: list[str] = []
    for kw in (snapshot.get("gsc") or {}).get("keywords", []):
        c = kw.get("current")
        if not c or c["impressions"] < 20:
            continue
        if 4 <= c["position"] <= 15:
            output.append(f"Quick win candidate — '{kw['query']}' at avg. {c['position']:.1f} "
                          f"({c['impressions']} impressions); review landing page relevance and intent")
        elif c["position"] < 4 and c["ctr"] < 0.05:
            output.append(f"CTR review — '{kw['query']}' position {c['position']:.1f} "
                          f"with {c['ctr'] * 100:.1f}% CTR; inspect actual SERP and snippet")
    return output[:15]


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
                     f"{safe(page.get('error') or page.get('warning') or '—')} |")
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
    cards = []
    for site in sites:
        snap = snapshots.get(site.id, {})
        totals = (snap.get("gsc") or {}).get("totals")
        link = escape(site.base_url, quote=True)
        alerts = len(snap.get("alerts", []))
        cards.append(f'''<article><h2><a href="{link}" rel="noopener noreferrer">{escape(site.name)}</a></h2>
<p class="domain">{link}</p><div class="stats"><div><b>{metric(totals,'clicks')}</b><span>Klikovi</span></div>
<div><b>{metric(totals,'impressions')}</b><span>Prikazi</span></div>
<div><b>{metric(totals,'ctr')}</b><span>CTR</span></div>
<div><b>{metric(totals,'position')}</b><span>Pozicija</span></div></div>
<p class="{'bad' if alerts else 'good'}">{alerts} upozorenja</p>
<p><a href="{escape(site.id)}-latest.md">Detaljan izveštaj</a> · <a href="{escape(site.id)}-keywords.csv">Ključne reči</a> · <a href="{escape(site.id)}-history.csv">Istorija</a> · <a href="{escape(site.id)}-rank-history.csv">Pozicije</a></p></article>''')
    return '''<!doctype html><html lang="sr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Lotos SEO Monitoring</title><style>body{font:16px system-ui;background:#f8fafc;color:#1f2937;margin:0 auto;padding:28px;max-width:1100px}
h1{font-size:1.8rem}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:18px}
article{background:white;border:1px solid #e5e7eb;border-radius:14px;padding:22px}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:15px}.stats div{display:flex;flex-direction:column}
.stats b{font-size:1.7rem}.stats span,.domain{color:#64748b;font-size:.85rem}
a{color:#126b4a}.bad{color:#b45309}.good{color:#166534}</style></head><body>
<h1>Lotos SEO Monitoring</h1><p>Zvanični Search Console podaci i tehničke provere · nije live Google ranking.</p><main>''' + "\n".join(cards) + "</main></body></html>"
