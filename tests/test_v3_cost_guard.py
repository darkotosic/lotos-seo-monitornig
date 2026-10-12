from dataclasses import replace

import pytest

from seo_monitor.cost_guard import CostGuard, Limits, QuotaExceeded, load_limits


def test_real_limits_file():
    limits = load_limits(__import__('pathlib').Path('config/limits.yml'))
    assert limits.cost_mode == 'free_only'
    assert limits.maximum_weekly_pagespeed_calls_per_site <= 8


def test_rejects_paid_mode(tmp_path):
    path = tmp_path / 'limits.yml'
    path.write_text('version: 1\ncost_mode: pay_as_you_go\n')
    with pytest.raises(ValueError, match='free_only'):
        load_limits(path)


def test_rejects_excessive_limits_or_unknown_provider(tmp_path):
    path = tmp_path / 'limits.yml'
    path.write_text('version: 1\ncost_mode: free_only\nmaximum_weekly_crawl_pages_per_site: 9999\n')
    with pytest.raises(ValueError):
        load_limits(path)
    path.write_text('version: 1\ncost_mode: free_only\npaid_fallback: true\n')
    with pytest.raises(ValueError):
        load_limits(path)


def test_fail_closed_quota():
    guard = CostGuard(replace(Limits(), maximum_weekly_pagespeed_calls_per_site=2))
    guard.consume('pagespeed')
    guard.consume('pagespeed')
    assert guard.remaining('pagespeed') == 0
    with pytest.raises(QuotaExceeded, match='NOT sent'):
        guard.consume('pagespeed')
    assert guard.used['pagespeed'] == 2
    with pytest.raises(ValueError):
        guard.consume('bigquery')
    with pytest.raises(ValueError):
        guard.consume('gsc', -2)


def test_no_api_calls_when_zero_quota():
    guard = CostGuard(replace(Limits(), maximum_daily_inspections_per_site=0))
    with pytest.raises(QuotaExceeded):
        guard.consume('inspection')
