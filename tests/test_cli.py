import json
from pathlib import Path

from seo_monitor import cli


def test_offline_run_generates_readable_artifacts(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "collect_checks", lambda site, settings: {
        "pages": [{"url": site.url("/"), "path": "/", "status": 200}],
        "robots": {"status": 200}, "sitemap": {"status": 200},
    })
    data = tmp_path / "data"
    reports = tmp_path / "reports"
    args = ["run", "--skip-gsc", "--no-notify", "--date", "2026-10-11",
            "--output", str(data), "--reports", str(reports)]
    assert cli.main(args) == 0
    assert (reports / "dashboard.html").exists()
    assert "cvecararuma.rs" in (reports / "overview.md").read_text(encoding="utf-8")
    assert (data / "indjija" / "2026-10-11.json").exists()
    assert len(list((data / "ruma").glob("*.json"))) == 1
    assert cli.main(args) == 0
    assert len(list((data / "ruma").glob("*.json"))) == 1
    report = json.loads((data / "ruma" / "2026-10-11.json").read_text())
    assert report["checks"]["pages"][0]["status"] == 200


def test_http_failure_causes_nonzero_exit(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "collect_checks", lambda site, settings: {
        "pages": [{"url": site.url("/"), "path": "/", "status": 503, "error": "HTTP 503"}],
        "robots": {"status": 200}, "sitemap": {"status": 200},
    })
    assert cli.main(["run", "--skip-gsc", "--no-notify", "--site", "indjija",
                     "--output", str(tmp_path / "data"), "--reports", str(tmp_path / "reports")]) == 2
