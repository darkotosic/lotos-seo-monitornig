"""Multi-domain SEO monitoring CLI; read-only services with durable local reports."""

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
from seo_monitor.cost_guard import CostGuard, QuotaExceeded, load_limits
from seo_monitor.diagnostics import provider_error
from seo_monitor.gsc import GoogleSearchConsole, collect_gsc
from seo_monitor.notify import send_telegram
from seo_monitor.report import assess, csv_history, csv_keywords, dashboard, markdown, overview
from seo_monitor.telegram_report import build_alert_message, build_daily_message

TZ = ZoneInfo("Europe/Belgrade")


def _read_snapshot(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, ValueError):
        return None


def previous_snapshot(folder: Path, today: str) -> dict | None:
    """Last known snapshot before the monitoring date, never a future run."""
    entries = sorted((p for p in folder.glob("????-??-??.json") if p.stem < today), reverse=True)
    for file in entries:
        snapshot = _read_snapshot(file)
        if snapshot is not None:
            return snapshot
    return None


def _write_json(path: Path, data: dict) -> None:
    """Atomic replacement prevents half-written daily JSON after a crash."""
    tmp = path.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                       encoding="utf-8")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only multi-domain SEO monitoring")
    parser.add_argument("command", nargs="?", default="run", choices=["run", "validate", "notify-test", "audit", "rebuild-db"])
    parser.add_argument("--config", default="config/sites.yml")
    parser.add_argument("--limits", default="config/limits.yml")
    parser.add_argument("--skip-pagespeed", action="store_true", help="Weekly crawl without PageSpeed calls")
    parser.add_argument("--db", default="local/seo_history.db", help="Rebuildable local SQLite file")
    parser.add_argument("--output", default="data")
    parser.add_argument("--reports", default="reports")
    parser.add_argument("--site", help="Optional site ID (ruma, indjija, ...)")
    parser.add_argument("--date", help="Local date YYYY-MM-DD; deterministic offline replay")
    parser.add_argument("--skip-gsc", action="store_true", help="HTTP and SEO only; no credentials")
    parser.add_argument("--skip-inspection", action="store_true", help="Skip Google URL Inspection")
    parser.add_argument("--no-notify", action="store_true", help="Do not contact Telegram")
    parser.add_argument("--preview-telegram", action="store_true", help="Print digest (no secret values)")
    args = parser.parse_args(argv)

    settings, sites = load_config(Path(args.config))
    limits = load_limits(Path(args.limits))
    if len(sites) > limits.maximum_sites:
        parser.error("Enabled sites exceed the free-only site cap")
    if args.site:
        sites = [s for s in sites if s.id == args.site]
        if not sites:
            parser.error(f"Site ID not present or disabled: {args.site}")
    if args.command == "rebuild-db":
        from seo_monitor.storage import rebuild_sqlite
        result = rebuild_sqlite(Path(args.output), Path(args.db))
        print(f"SQLite built locally: {result}")
        return 0
    if args.command == "validate":
        print(f"Configuration valid: {len(sites)} enabled domain(s): " + ", ".join(s.id for s in sites))
        return 0
    if args.command == "notify-test":
        if args.no_notify:
            parser.error("notify-test cannot be combined with --no-notify")
        success = send_telegram("Lotos SEO Monitoring: test Telegram integracije. Nema SEO merenja.")
        print("Telegram: delivered" if success else "Telegram: failed or not configured")
        return 0 if success else 2

    today = date.fromisoformat(args.date) if args.date else datetime.now(TZ).date()
    if args.command == "audit":
        from seo_monitor.audit_cli import run_weekly
        return run_weekly(sites, limits, today, Path(args.output), Path(args.reports),
                          skip_pagespeed=args.skip_pagespeed, notify=not args.no_notify)
    root, report_dir = Path(args.output), Path(args.reports)
    root.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    api = None
    api_error = None
    if not args.skip_gsc:
        try:
            api = GoogleSearchConsole(os.getenv("GOOGLE_APPLICATION_CREDENTIALS", ""))
        except Exception as exc:
            api_error = provider_error(exc, "Google authentication/init")
            print(f"[GSC] {api_error}", file=sys.stderr)

    snapshots: dict[str, dict] = {}
    new_alerts: list[str] = []
    any_error = api_error is not None
    for site in sites:
        folder = root / site.id
        folder.mkdir(parents=True, exist_ok=True)
        old = previous_snapshot(folder, today.isoformat())
        same_day_file = folder / f"{today.isoformat()}.json"
        comparison = _read_snapshot(same_day_file) or old
        snap: dict = {
            "schema_version": 2,
            "site_id": site.id, "base_url": site.base_url,
            "created_at": datetime.now(TZ).isoformat(timespec="seconds"),
            "monitor_date": today.isoformat(),
        }
        try:
            snap["checks"] = collect_checks(site, settings)
        except Exception as exc:
            snap["checks"] = {}
            snap["check_error"] = provider_error(exc, "HTTP monitoring")
            any_error = True
        if api:
            try:
                snap["gsc"] = collect_gsc(api, site, settings, today, inspect=not args.skip_inspection,
                                          guard=CostGuard(limits))
            except Exception as exc:
                snap["gsc_error"] = provider_error(exc, "Search Console API")
                if isinstance(exc, QuotaExceeded):
                    snap["gsc_error"] = "GSC free-call quota reached; skipped further requests"
                print(f"[{site.id}] {snap['gsc_error']}", file=sys.stderr)
                any_error = True
        elif not args.skip_gsc:
            snap["gsc_error"] = api_error or "Google authentication failed"
            any_error = True
        else:
            snap["gsc_skipped"] = True
        snap["alerts"] = assess(snap, settings, old)
        if snap.get("check_error"):
            snap["alerts"].append(snap["check_error"])
        snap["alerts"] = sorted(set(snap["alerts"]))
        previous_alerts = set((comparison or {}).get("alerts", []))
        new_alerts.extend(f"{site.id}: {item}" for item in snap["alerts"] if item not in previous_alerts)
        if any(page.get("error") for page in (snap.get("checks") or {}).get("pages", [])):
            any_error = True
        if any((snap.get("checks") or {}).get(kind, {}).get("error") for kind in ("robots", "sitemap")):
            any_error = True
        _write_json(same_day_file, snap)
        (report_dir / f"{site.id}-latest.md").write_text(markdown(site, snap), encoding="utf-8")
        csv_keywords(report_dir / f"{site.id}-keywords.csv", snap)
        csv_history(folder, report_dir / f"{site.id}-history.csv", report_dir / f"{site.id}-rank-history.csv")
        snapshots[site.id] = snap
        print(f"[{site.id}] HTTP checks: {len((snap.get('checks') or {}).get('pages', []))}; "
              f"alerts: {len(snap['alerts'])}; GSC: {'OK' if 'gsc' in snap else 'skipped' if args.skip_gsc else 'unavailable'}")

    (report_dir / "overview.md").write_text(overview(sites, snapshots), encoding="utf-8")
    (report_dir / "dashboard.html").write_text(dashboard(sites, snapshots), encoding="utf-8")
    message = build_daily_message(sites, snapshots, today)
    (report_dir / "telegram-preview.txt").write_text(message + "\n", encoding="utf-8")
    if args.preview_telegram:
        print("\n" + message)
    summary_enabled = os.environ.get("SEO_DAILY_TELEGRAM_SUMMARY", "false").lower() == "true"
    if not args.no_notify and (new_alerts or summary_enabled):
        notification = message if summary_enabled else build_alert_message(new_alerts, today)
        telegram_is_configured = bool(os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))
        delivered = send_telegram(notification)
        print("Telegram: delivered" if delivered else "Telegram: unavailable or delivery failed")
        # A configured integration must not be silently reported as successful.
        # Optional/unconfigured Telegram does not block pure SEO monitoring.
        if telegram_is_configured and not delivered:
            any_error = True
    return 2 if any_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
