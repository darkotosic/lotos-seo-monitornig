from datetime import datetime, timezone

import httpx
import pytest

from seo_monitor.watchdog import check_github, recent_success

NOW = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)


def run(status, conclusion, updated_at):
    return {"status": status, "conclusion": conclusion, "updated_at": updated_at}


def test_recent_success_is_valid():
    assert recent_success([run("completed", "success", "2026-10-12T06:22:00Z")], NOW)


def test_previous_day_success_is_stale():
    assert not recent_success([run("completed", "success", "2026-10-11T06:23:00Z")], NOW)


def test_failed_and_in_progress_are_not_success():
    assert not recent_success([run("completed", "failure", "2026-10-12T06:20:00Z"),
                               run("in_progress", None, "2026-10-12T06:25:00Z")], NOW)


def test_future_or_invalid_timestamp_rejected():
    assert not recent_success([run("completed", "success", "2026-10-14T00:00:00Z"),
                               run("completed", "success", "not-date")], NOW)


def test_github_request_scoped_to_repo():
    def handler(request):
        assert request.url.host == "api.github.com"
        assert request.url.path.endswith("/actions/workflows/seo-daily.yml/runs")
        assert request.headers["Authorization"] == "Bearer TEST_TOKEN"
        return httpx.Response(200, json={"workflow_runs": [run("completed", "success", "2026-10-12T07:00:00Z")]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = check_github("darkotosic/lotos-seo-monitornig", "TEST_TOKEN", client=client)
    assert len(result) == 1


@pytest.mark.parametrize("repo", ["http://169.254.169.254/", "../bad", "org/repo/extra", "", "org/../repo"])
def test_no_arbitrary_github_repositories(repo):
    with pytest.raises(ValueError):
        check_github(repo, "TOKEN")
