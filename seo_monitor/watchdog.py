"""Independent monitor-of-monitor for a missing/failed scheduled SEO workflow.

Runs in its own GitHub Actions job. Requires only `actions: read` plus Telegram
secrets; never commits snapshots, mutates websites or executes paid providers.
"""

from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone

import httpx

from seo_monitor.notify import send_telegram

REPO_PATTERN = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


def recent_success(runs: list[dict], now: datetime, *, max_age_hours: int = 27) -> bool:
    """True when a completed successful daily monitoring run is recent enough."""
    cutoff = now.astimezone(timezone.utc) - timedelta(hours=max_age_hours)
    for run in runs:
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            continue
        when = run.get("updated_at") or run.get("run_started_at")
        if not isinstance(when, str):
            continue
        try:
            completed = datetime.fromisoformat(when.replace("Z", "+00:00"))
        except ValueError:
            continue
        if completed.tzinfo is not None and cutoff <= completed.astimezone(timezone.utc) <= now:
            return True
    return False


def check_github(repo: str, token: str, *, client: httpx.Client | None = None) -> list[dict]:
    if not REPO_PATTERN.fullmatch(repo) or repo.startswith(".") or not token:
        raise ValueError("Valid GITHUB_REPOSITORY and GH_MONITOR_TOKEN are required")
    url = f"https://api.github.com/repos/{repo}/actions/workflows/seo-daily.yml/runs"
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "LotosSEOWatchdog/2.0"}
    if client is None:
        with httpx.Client(timeout=15) as temporary:
            return check_github(repo, token, client=temporary)
    response = client.get(url, params={"per_page": 20}, headers=headers)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, dict) or not isinstance(data.get("workflow_runs"), list):
        raise ValueError("Unexpected GitHub Actions API response")
    return data["workflow_runs"]


def main() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    token = os.environ.get("GH_MONITOR_TOKEN", "")
    try:
        runs = check_github(repo, token)
    except (httpx.HTTPError, ValueError) as exc:
        # Provider responses and authorization headers must not be logged.
        print(f"Watchdog: GitHub API unavailable ({type(exc).__name__})")
        return 2
    if recent_success(runs, datetime.now(timezone.utc)):
        print("Watchdog: recent successful SEO monitoring run found")
        return 0
    message = ("LOTOS SEO — ALARM\n"
               "SEO Daily Monitoring nema uspešno završeno izvršavanje u poslednjih 27 sati.\n"
               "Proveri GitHub → Actions → SEO Daily Monitoring.\n"
               "Napomena: GitHub raspored može kasniti; proveri da li je pokrenut.")
    if not send_telegram(message):
        print("Watchdog: monitor missed; Telegram alert NOT delivered")
        return 2
    print("Watchdog: monitor missed; Telegram alert delivered")
    return 1  # Red status is intentional for missing scheduled monitoring.


if __name__ == "__main__":
    raise SystemExit(main())
