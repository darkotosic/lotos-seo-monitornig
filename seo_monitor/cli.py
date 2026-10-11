"""CLI entrypoint. Offline dry run, independent sites, snapshots, and report artifacts."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from seo_monitor.checks import collect_checks
from seo_monitor.config import load_config
from seo_monitor.gsc import GoogleSearchConsole, collect_gsc
from seo_monitor.notify import send_telegram
from seo_monitor.report import assess, csv_history, csv_keywords, dashboard, markdown, overview


def previous_snapshot(folder: Path, today: str) -> dict | None:
    entries = sorted(p for p in folder.glob("????-??-??.json") if p.stem < today)
    if not entries:
        return None
    try:
        return json.loads(entries[-1].read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only multi-domain SEO Monitor")
    parser.add_argument("run", nargs="?", default="run", choices=["run"])
    parser.add_argument("--config", default="config/sites.yml")
    parser.add_argument("--output", default="data")
    parser.add_argument("--reports", default="reports")
    parser.add_argument("--site", help="Optional site ID (ruma, indjija, ...)")
    parser.add_argument("--date", help="Local date YYYY-MM-DD, optional; for deterministic replay")
    parser.add_argument("--skip-gsc", action="store_true", help="Only run HTTP/SEO checks; no credentials needed")
    parser.add_argument("--skip-inspection", action="store_true", help="Skip URL Inspection API")
    parser.add_argument("--no-notify", action="store_true", help="Disable Telegram")
    args = parser.parse_args(argv)

    settings, sites = load_config(Path(args.config))
    if args.site:
        sites = [s for s in sites if s.id == args.site]
        if not sites:
            parser.error(f"Site ID not present or disabled: {args.site}")
    today = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo("Europe/Belgrade")).date()
    root = Path(args.output)
    report_dir = Path(args.reports)
    root.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    api = None
    api_error = None
    if not args.skip_gsc:
        try:
            api = GoogleSearchConsole(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""))
        except Exception as exc:
            api_error = f"Google authentication/init failed: {type(exc).__name__}"

    snapshots: dict[str, dict] = {}
    notification_alerts: list[str] = []
    any_error = api_error is not None
    for site in sites:
        folder = root / site.id
        folder.mkdir(parents=True, exist_ok=True)
        old = previous_snapshot(folder, today.isoformat())
        same_day_file = folder / f"{today.isoformat()}.json"
        try:
            comparison = json.loads(same_day_file.read_text(encoding="utf-8")) if same_day_file.exists() else old
        except (OSError, ValueError):
            comparison = old
        snap: dict = {
            "site_id": site.id, "base_url": site.base_url,
            "created_at": datetime.now(ZoneInfo("Europe/Belgrade")).isoformat(timespec="seconds"),
            "monitor_date": today.isoformat(),
        }
        try:
            snap["checks"] = collect_checks(site, settings)
        except Exception as exc:
            snap["checks"] = {}
            snap["check_error"] = f"HTTP monitoring failed: {type(exc).__name__}"
            any_error = True
        if api:
            try:
                snap["gsc"] = collect_gsc(api, site, settings, today, inspect=not args.skip_inspection)
            except Exception as exc:
                snap["gsc_error"] = f"Search Console API failed: {type(exc).__name__}"
                any_error = True
        elif not args.skip_gsc:
            snap["gsc_error"] = api_error
        snap["alerts"] = assess(snap, settings, old)
        if snap.get("check_error"):
            snap["alerts"].append(snap["check_error"])
        old_alerts = set((comparison or {}).get("alerts", []))
        notification_alerts += [f"{site.id}: {item}" for item in snap["alerts"] if item not in old_alerts]
        if any(page.get("error") for page in snap.get("checks", {}).get("pages", [])):
            any_error = True
        if any(snap.get("checks", {}).get(key, {}).get("error") for key in ("robots", "sitemap")):
            any_error = True
        (folder / f"{today.isoformat()}.json").write_text(
            json.dumps(snap, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        (report_dir / f"{site.id}-latest.md").write_text(markdown(site, snap), encoding="utf-8")
        csv_keywords(report_dir / f"{site.id}-keywords.csv", snap)
        csv_history(folder, report_dir / f"{site.id}-history.csv", report_dir / f"{site.id}-rank-history.csv")
        snapshots[site.id] = snap
        print(f"[{site.id}] HTTP checks: {len(snap.get('checks',{}).get('pages',[]))}; "
              f"alerts: {len(snap['alerts'])}; GSC: {'OK' if 'gsc' in snap else 'unavailable'}")

    (report_dir / "overview.md").write_text(overview(sites, snapshots), encoding="utf-8")
    (report_dir / "dashboard.html").write_text(dashboard(sites, snapshots), encoding="utf-8")
    if not args.no_notify and (notification_alerts or os.environ.get("SEO_DAILY_TELEGRAM_SUMMARY") == "true"):
        message = ("Lotos SEO Monitoring · " + today.isoformat() + "\n" +
                   ("\n".join(notification_alerts[:25]) if notification_alerts else "Bez novih upozorenja."))
        if not send_telegram(message):
            print("Telegram notification not delivered or not configured", file=sys.stderr)
    return 2 if any_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
