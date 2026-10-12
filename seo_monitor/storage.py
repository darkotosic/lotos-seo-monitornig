"""Rebuildable local SQLite projection of tracked JSON snapshots; no cloud database."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


def rebuild_sqlite(data_root: Path, destination: Path) -> dict:
    """Build in a local DB for offline SQL; never commit *.db to Git."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    stats = {"snapshots": 0, "keyword_records": 0}
    with sqlite3.connect(destination) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS snapshots (
              site_id TEXT NOT NULL, monitor_date TEXT NOT NULL,
              clicks INTEGER, impressions INTEGER, ctr REAL, position REAL,
              PRIMARY KEY(site_id, monitor_date));
            CREATE TABLE IF NOT EXISTS keywords (
              site_id TEXT NOT NULL, monitor_date TEXT NOT NULL,
              query TEXT NOT NULL, clicks INTEGER, impressions INTEGER,
              ctr REAL, position REAL, PRIMARY KEY(site_id, monitor_date, query));
        """)
        db.execute("DELETE FROM keywords")
        db.execute("DELETE FROM snapshots")
        for file in sorted(data_root.glob("*/????-??-??.json")):
            try:
                snap = json.loads(file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if not isinstance(snap, dict):
                continue
            site = snap.get("site_id")
            monitor_date = snap.get("monitor_date")
            if site != file.parent.name or monitor_date != file.stem:
                continue
            totals = (snap.get("gsc") or {}).get("totals") or {}
            db.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?)",
                       (site, monitor_date, totals.get("clicks"), totals.get("impressions"),
                        totals.get("ctr"), totals.get("position")))
            stats["snapshots"] += 1
            for row in (snap.get("gsc") or {}).get("keywords", []):
                values = row.get("current") or {}
                if not row.get("query"):
                    continue
                db.execute("INSERT OR REPLACE INTO keywords VALUES (?,?,?,?,?,?,?)",
                           (site, monitor_date, row["query"], values.get("clicks"),
                            values.get("impressions"), values.get("ctr"), values.get("position")))
                stats["keyword_records"] += 1
    return stats
