"""Weekly zero-cost technical audit orchestration and Markdown output."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from seo_monitor.config import Site
from seo_monitor.cost_guard import CostGuard, Limits
from seo_monitor.crawler import audit_site
from seo_monitor.performance import collect_pagespeed
from seo_monitor.recommendations import recommendations
from seo_monitor.report import safe


def weekly_report(site: Site, audit: dict, snapshot: dict | None) -> str:
    pages = audit.get("pages") or []
    issues = (audit.get("metadata_issues") or []) + (audit.get("schema_issues") or [])
    issues += (audit.get("image_issues") or [])
    p = [f"# Nedeljni SEO audit — {safe(site.name)}", "",
         f"Domen: {site.base_url}  |  Datum: {audit.get('audit_date', 'N/D')}", "",
         "## Obuhvat", "",
         f"- Sitemap URL-ova: {audit.get('pages_in_sitemap', 'N/D')}",
         f"- Posećenih URL-ova: {len(pages)}",
         f"- Statusi: {safe(audit.get('http_statuses', {}))}",
         f"- Delimična provera (kvote): {'da' if audit.get('partial') else 'ne'}", "",
         "## Content, schema, image audit", "",
         "| Prioritet | Provera | URL |", "|---|---|---|"]
    for issue in issues[:50]:
        p.append(f"| {safe(issue.get('severity', 'P2'))} | {safe(issue.get('type'))} | {safe(issue.get('url'))} |")
    if not issues:
        p.append("| — | Bez detektovanih problema u uzorku | — |")
    p += ["", "## Unutrašnji linkovi", "",
          f"- Kandidati bez ulaznih linkova u uzorku: "
          f"{len((audit.get('link_audit') or {}).get('candidate_orphans_in_crawled_sample', []))}",
          "- Ovo nije dokaz o stvarno orphan URL-ovima bez potpunog crawl-a.", "",
          "## PageSpeed (opciono, keyless)", "",
          "| URL | Uređaj | Status | Lab score | LCP ms (lab) | CLS (lab) | INP p75 (field) |",
          "|---|---|---|---:|---:|---:|---:|"]
    for row in audit.get("pagespeed", []):
        p.append(f"| {safe(row.get('url'))} | {safe(row.get('strategy'))} | "
                 f"{safe(row.get('status'))} | {row.get('lab_performance_score') or 'N/D'} | "
                 f"{row.get('lab_lcp_ms') if row.get('lab_lcp_ms') is not None else 'N/D'} | "
                 f"{row.get('lab_cls') if row.get('lab_cls') is not None else 'N/D'} | "
                 f"{row.get('field_inp_ms_p75') if row.get('field_inp_ms_p75') is not None else 'N/D'} |")
    if not audit.get("pagespeed"):
        p.append("| — | — | preskočeno | — | — | — | — |")
    p += ["", "## Predlog ručnih SEO zadataka", ""]
    tasks = recommendations(snapshot or {}, audit)
    p += [f"- **{safe(t['priority'])}** — {safe(t['target'])}: {safe(t['action'])}"
          for t in tasks] or ["Nema novih zadataka sa dovoljno dokaza."]
    p += ["", "## Tehnička upozorenja", ""]
    p += [f"- {safe(item)}" for item in audit.get("warnings", [])] or ["Nema upozorenja."]
    p += ["", "*Bot ne vrši izmene na sajtu; zadatke mora potvrditi čovek.*",
          "*PageSpeed rezultat nije garancija Google pozicije; CrUX može biti N/D.*", ""]
    return "\n".join(p)


def weekly_telegram(sites: list[Site], audits: dict[str, dict], today: date) -> str:
    lines = [f"LOTOS SEO | NEDELJNI AUDIT | {today.isoformat()}",
             "Stvarni tehnički nalazi; preporuke zahtevaju ljudsku proveru.", ""]
    for site in sites:
        audit = audits.get(site.id) or {}
        pages = audit.get("pages") or []
        issues = sum(len(audit.get(k) or []) for k in ("metadata_issues", "schema_issues", "image_issues"))
        checks_ok = sum(p.get("status") == 200 for p in pages)
        lines.extend([f"{site.name}",
                      f"Sitemap: {audit.get('pages_in_sitemap', 'N/D')} URL-ova",
                      f"Crawler: {checks_ok}/{len(pages)} HTTP 200",
                      f"Content/schema/image nalaza: {issues}",
                      f"PageSpeed: {sum(p.get('status') == 'ok' for p in audit.get('pagespeed', []))} uspešnih merenja",
                      ""])
    lines += ["Kompletna analiza: GitHub / reports/*-audit.md", "Nema plaćenih API-ja."]
    return "\n".join(lines)[:3500]


def run_weekly(sites: list[Site], limits: Limits, today: date, root: Path, reports: Path,
               *, skip_pagespeed: bool = False, notify: bool = False) -> int:
    """Partial/free API failures are recorded, without fabricating a successful metric."""
    from seo_monitor.notify import send_telegram

    results: dict[str, dict] = {}
    any_critical = False
    for site in sites:
        guard = CostGuard(limits)
        try:
            audit = audit_site(site, guard)
        except Exception as exc:
            audit = {"site_id": site.id, "base_url": site.base_url, "pages": [],
                     "warnings": [f"Crawler failed: {type(exc).__name__}"], "partial": True}
            any_critical = True
        if audit.get("fatal_error"):
            any_critical = True
        audit["audit_date"] = today.isoformat()
        audit["generated_at"] = datetime.now(ZoneInfo("Europe/Belgrade")).isoformat(timespec="seconds")
        if not skip_pagespeed:
            audit["pagespeed"] = collect_pagespeed(site, guard, paths=("/", "/proizvodi"))
        else:
            audit["pagespeed"] = []
        audit["quota_used"] = dict(guard.used)
        folder = root / "audits" / site.id
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / f"{today.isoformat()}.json"
        temp = target.with_suffix(".json.tmp")
        try:
            temp.write_text(json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                            encoding="utf-8")
            temp.replace(target)
        finally:
            temp.unlink(missing_ok=True)
        latest = root / site.id / f"{today.isoformat()}.json"
        previous = None
        if not latest.exists():
            latest = max((root / site.id).glob("????-??-??.json"), default=None)
        if latest:
            try:
                previous = json.loads(latest.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                previous = None
        reports.mkdir(parents=True, exist_ok=True)
        (reports / f"{site.id}-audit.md").write_text(weekly_report(site, audit, previous), encoding="utf-8")
        results[site.id] = audit
        print(f"[{site.id}] weekly: {len(audit.get('pages', []))} pages, "
              f"{len(audit.get('metadata_issues', []))} metadata issues, "
              f"{len(audit.get('pagespeed', []))} PSI checks")
    msg = weekly_telegram(sites, results, today)
    (reports / "telegram-weekly-preview.txt").write_text(msg + "\n", encoding="utf-8")
    if notify:
        import os
        if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
            if not send_telegram(msg):
                print("Telegram weekly report delivery failed")
                any_critical = True
    return 2 if any_critical else 0
