from datetime import date

from seo_monitor.config import Settings, Site
from seo_monitor.gsc import collect_gsc, metrics
from seo_monitor.report import assess, markdown


class FakeApi:
    def __init__(self):
        self.requests = []

    def query(self, prop, start, end, dimensions=None, query=None, limit=1000):
        self.requests.append((prop, start, end, dimensions, query, limit))
        if dimensions == ["page"]:
            return {"rows": [{"keys": ["https://cvecararuma.rs/"], "clicks": 4,
                              "impressions": 100, "ctr": 0.04, "position": 4.0}]}
        if dimensions == ["searchAppearance"]:
            return {"rows": [{"keys": ["PRODUCT_SNIPPETS"], "clicks": 1,
                              "impressions": 30, "ctr": 0.033, "position": 3.1}]}
        if query == "no data":
            return {"rows": []}
        if query:
            position = 8.0 if len(self.requests) % 2 == 0 else 3.0
            return {"rows": [{"clicks": 4, "impressions": 60, "ctr": 0.067, "position": position}]}
        return {"rows": [{"clicks": 10, "impressions": 100, "ctr": 0.1, "position": 5.0}]}

    def inspect(self, prop, url):
        return {"verdict": "PASS", "coverageState": "Submitted and indexed"}


def test_collect_gsc_and_finalized_dates():
    api = FakeApi()
    site = Site("ruma", "Ruma", "https://cvecararuma.rs", "sc-domain:cvecararuma.rs",
                ("cvecara ruma", "no data"), ("/",), ("/",))
    result = collect_gsc(api, site, Settings(), date(2026, 10, 11))
    assert result["current_window"] == {"start": "2026-09-11", "end": "2026-10-08"}
    assert result["keywords"][1]["current"] is None
    assert result["inspections"][0]["verdict"] == "PASS"
    assert all(q[0] == site.gsc_property for q in api.requests)
    assert result["search_appearances"][0]["appearance"] == "PRODUCT_SNIPPETS"


def test_rank_alert_requires_enough_impressions():
    snapshot = {"checks": {"pages": []}, "gsc": {"keywords": [
        {"query": "cvecara ruma", "current": {"impressions": 100, "position": 9.0},
         "previous": {"impressions": 100, "position": 3.0}},
        {"query": "rare", "current": {"impressions": 1, "position": 20.0},
         "previous": {"impressions": 100, "position": 1.0}},
    ]}}
    alerts = assess(snapshot, Settings())
    assert len(alerts) == 1
    assert "cvecara ruma" in alerts[0]


def test_no_data_is_not_zero():
    assert metrics(None) is None
    assert metrics({"clicks": 0, "impressions": 20, "position": 11.27}) == {
        "clicks": 0, "impressions": 20, "ctr": 0.0, "position": 11.27,
    }


def test_markdown_report():
    site = Site("ruma", "Ruma", "https://cvecararuma.rs", "sc-domain:cvecararuma.rs",
                ("cvecara ruma",), ("/",), ("/",))
    report = markdown(site, {"created_at": "now", "gsc": {}, "checks": {}, "alerts": []})
    assert "N/D" in report
    assert "Google indeks" in report


def test_history_csv_and_excel_safety(tmp_path):
    import csv
    import json

    from seo_monitor.report import csv_history, csv_keywords

    folder = tmp_path / "snapshots"
    folder.mkdir()
    snapshot = {
        "monitor_date": "2026-10-11",
        "alerts": ["test"],
        "gsc": {
            "current_window": {"start": "2026-09-11", "end": "2026-10-08"},
            "totals": {"clicks": 8, "impressions": 88, "ctr": 0.0909, "position": 7.1},
            "keywords": [{"query": '=HYPERLINK("http://evil.example")', "current": {
                "clicks": 1, "impressions": 8, "ctr": 0.125, "position": 3.8}, "previous": None}],
        },
    }
    (folder / "2026-10-11.json").write_text(json.dumps(snapshot))
    csv_history(folder, tmp_path / "all.csv", tmp_path / "rank.csv")
    with (tmp_path / "all.csv").open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["impressions"] == "88"
    assert rows[0]["average_position"] == "7.1"
    assert rows[0]["gsc_status"] == "ok"
    with (tmp_path / "rank.csv").open(encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))
    assert rows[0]["query"].startswith("'=")
    csv_keywords(tmp_path / "keywords.csv", snapshot)
    assert "'=HYPERLINK" in (tmp_path / "keywords.csv").read_text(encoding="utf-8-sig")


def test_history_csv_skips_invalid_snapshots(tmp_path):
    from seo_monitor.report import csv_history

    (tmp_path / "2026-10-10.json").write_text("invalid")
    csv_history(tmp_path, tmp_path / "all.csv", tmp_path / "rank.csv")
    assert len((tmp_path / "all.csv").read_text(encoding="utf-8-sig").splitlines()) == 1
