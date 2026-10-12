"""V2 regressions: truthful metrics, safe diagnostics, digest, CLI, resilience."""

from __future__ import annotations

import json
from datetime import date
from types import SimpleNamespace

import pytest

from seo_monitor import cli
from seo_monitor.config import Settings, Site
from seo_monitor.diagnostics import provider_error
from seo_monitor.gsc import collect_gsc, metrics
from seo_monitor.report import dashboard, markdown, metric
from seo_monitor.telegram_report import build_alert_message, build_daily_message

SITE = Site("ruma", "Lotos Ruma", "https://cvecararuma.rs", "sc-domain:cvecararuma.rs",
            ("cvecara ruma",), ("/",), ("/",))


def _gsc():
    return {
        "current_window": {"start": "2026-09-12", "end": "2026-10-09"},
        "totals": {"clicks": 148, "impressions": 3765, "ctr": .03931, "position": 5.87},
        "previous_totals": {"clicks": 133, "impressions": 3263, "ctr": .04076, "position": 6.09},
        "weekly_totals": {"clicks": 40, "impressions": 900, "ctr": .04, "position": 5.6},
        "weekly_window": {"start": "2026-10-03", "end": "2026-10-09"},
        "previous_weekly_totals": {"clicks": 30, "impressions": 810, "ctr": .03, "position": 6.2},
        "keywords": [
            {"query": "cvecara ruma", "current": {"clicks": 22, "impressions": 331,
              "ctr": .066, "position": 1.54}, "previous": {"impressions": 319, "position": 2.61}},
            {"query": "dostava cveca ruma", "current": None, "previous": None},
        ],
        "inspections": [{"url": "https://cvecararuma.rs/", "verdict": "PASS"}],
    }


def _snapshot(gsc=None, alerts=None):
    return {"site_id": "ruma", "created_at": "2026-10-12T10:00:00+02:00",
            "gsc": _gsc() if gsc is None else gsc,
            "checks": {"pages": [{"url": SITE.url("/"), "path": "/", "status": 200}],
                       "robots": {"status": 200}, "sitemap": {"status": 200}},
            "alerts": alerts or []}


def test_telegram_full_digest_contains_verified_data():
    text = build_daily_message([SITE], {"ruma": _snapshot()}, date(2026, 10, 12))
    assert "148" in text and "3.765" in text
    assert "5.9" in text and "Upiti" in text
    assert "1.5" in text and "Nedeljni pregled" in text
    assert "HTTP: 1/1" in text and "1 indeksirano" in text
    assert "N/D =" in text
    assert "pozicija 0" in text.lower()
    assert len(text) <= 3500


def test_telegram_warning_when_gsc_unavailable():
    text = build_daily_message([SITE], {"ruma": _snapshot(gsc={})}, date(2026, 10, 11))
    assert "NEDOSTUPAN" in text
    assert "0 klikova" not in text


def test_telegram_large_report_is_bounded():
    many_sites = [Site(f"site{i}", "Flower "+str(i), f"https://flowers{i}.rs",
                       f"sc-domain:flowers{i}.rs", ("flowers",), ("/",), ("/",))
                  for i in range(30)]
    data = {s.id: _snapshot(alerts=["long error " + "x" * 300]) for s in many_sites}
    text = build_daily_message(many_sites, data, date(2026, 10, 12))
    assert len(text) <= 3500
    assert "nastavak" in text
    assert "Upozorenja: 30" not in text or len(text) <= 3500


def test_telegram_no_untrusted_markup_needed():
    snap = _snapshot()
    snap["gsc"]["keywords"][0]["query"] = "test & <fake>"
    text = build_daily_message([SITE], {"ruma": snap}, date(2026, 10, 11))
    assert "test & <fake>" in text  # Telegram uses plain text, not parse_mode.


def test_new_alert_message_is_concise():
    text = build_alert_message(["ruma: HTTP 503", "indjija: indexing failed"], date(2026, 10, 12))
    assert "HTTP 503" in text and "2026-10-12" in text


def test_google_error_status_without_secrets():
    class DummyHttpError(Exception):
        resp = SimpleNamespace(status=403)
        error_reason = "accessNotConfigured"

        def __str__(self):
            return "access_token=SECRET123 and URL https://private.googleapis.example"

    message = provider_error(DummyHttpError(), "Search Console API")
    assert message == "Search Console API HTTP 403 (accessNotConfigured)"
    assert "SECRET123" not in message and "private.googleapis" not in message


def test_google_unknown_reason_redacted():
    class DummyHttpError(Exception):
        resp = SimpleNamespace(status=401)
        error_reason = "secret-should-not-appear"

    message = provider_error(DummyHttpError())
    assert message == "Google API HTTP 401"


@pytest.mark.parametrize("value", [None, {"clicks": 0, "impressions": 0, "position": 0}])
def test_zero_impressions_are_not_position_zero(value):
    assert metrics(value) is None


def test_zero_position_with_impressions_is_na():
    result = metrics({"clicks": 0, "impressions": 10, "position": 0})
    assert result["position"] is None
    assert metric(result, "position") == "N/D"


def test_dashboard_escapes_provider_data():
    snap = _snapshot()
    snap["gsc"]["keywords"][0]["query"] = '<img src=x onerror="alert(1)">'
    result = dashboard([SITE], {"ruma": snap})
    assert "<img src=x" not in result
    assert "&lt;img src=x" in result
    assert "Prosečna pozicija" in result
    assert "meta name=\"robots\" content=\"noindex\"" in result


def test_markdown_weekly_summary():
    report = markdown(SITE, _snapshot())
    assert "Nedeljno poređenje" in report
    assert "40" in report and "30" in report


def test_cli_validate_offline(capsys):
    assert cli.main(["validate", "--config", "config/sites.yml"]) == 0
    assert "2 enabled" in capsys.readouterr().out


def test_cli_notify_test_is_a_separate_operation(monkeypatch, tmp_path):
    called = []
    monkeypatch.setattr(cli, "send_telegram", lambda message: called.append(message) or True)
    assert cli.main(["notify-test", "--output", str(tmp_path / "data")]) == 0
    assert len(called) == 1 and "test Telegram" in called[0]
    assert not (tmp_path / "data").exists()


def test_cli_notify_test_fails_if_unavailable(monkeypatch):
    monkeypatch.setattr(cli, "send_telegram", lambda _: False)
    assert cli.main(["notify-test"]) == 2


def test_previous_snapshot_skips_corrupt_file(tmp_path):
    folder = tmp_path / "ruma"
    folder.mkdir()
    (folder / "2026-10-10.json").write_text(json.dumps({"alerts": ["ok"]}))
    (folder / "2026-10-11.json").write_text("invalid JSON")
    assert cli.previous_snapshot(folder, "2026-10-12")["alerts"] == ["ok"]


def test_atomic_json_replacement(tmp_path):
    path = tmp_path / "2026-10-12.json"
    path.write_text("old")
    cli._write_json(path, {"status": "success"})
    assert json.loads(path.read_text()) == {"status": "success"}
    assert not (tmp_path / "2026-10-12.json.tmp").exists()


def test_telegram_failure_nonzero_only_when_configured(monkeypatch, tmp_path):
    monkeypatch.setattr(cli, "collect_checks", lambda s, _: {
        "pages": [{"url": s.url("/"), "path": "/", "status": 200}],
        "robots": {"status": 200}, "sitemap": {"status": 200},
    })
    monkeypatch.setattr(cli, "send_telegram", lambda _: False)
    monkeypatch.setenv("SEO_DAILY_TELEGRAM_SUMMARY", "true")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "not-a-real-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "-100123")
    result = cli.main(["run", "--skip-gsc", "--site", "ruma", "--date", "2026-10-11",
                       "--output", str(tmp_path / "data"), "--reports", str(tmp_path / "reports")])
    assert result == 2
    assert "GSC: NEDOSTUPAN" in (tmp_path / "reports" / "telegram-preview.txt").read_text()


def test_cli_offline_preview_generates_report(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "collect_checks", lambda s, _: {
        "pages": [{"url": s.url("/"), "path": "/", "status": 200}],
        "robots": {"status": 200}, "sitemap": {"status": 200},
    })
    assert cli.main(["run", "--skip-gsc", "--no-notify", "--preview-telegram",
                     "--date", "2026-10-12", "--site", "indjija",
                     "--output", str(tmp_path / "data"), "--reports", str(tmp_path / "reports")]) == 0
    assert "LOTOS SEO MONITORING" in capsys.readouterr().out
    assert (tmp_path / "reports" / "dashboard.html").exists()


class FakeWeeklyGsc:
    def __init__(self):
        self.calls = []

    def query(self, prop, start, end, dimensions=None, query=None, limit=1000):
        self.calls.append((prop, start, end, dimensions, query))
        if dimensions:
            return {"rows": []}
        return {"rows": [{"clicks": 1, "impressions": 20, "position": 2.1, "ctr": 0.05}]}

    def inspect(self, prop, url):
        return {"verdict": "PASS"}


def test_weekly_windows_follow_finalized_lag():
    api = FakeWeeklyGsc()
    gsc = collect_gsc(api, SITE, Settings(), date(2026, 10, 12), inspect=False)
    assert gsc["weekly_window"] == {"start": "2026-10-03", "end": "2026-10-09"}
    assert gsc["weekly_totals"]["impressions"] == 20
    assert gsc["inspections"] == []
    assert any(start.isoformat() == "2026-09-26" and end.isoformat() == "2026-10-02"
               for _, start, end, _, _ in api.calls)
