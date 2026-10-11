from pathlib import Path

import pytest

from seo_monitor.config import _site, load_config


def test_real_config_contains_two_independent_domains():
    settings, sites = load_config(Path("config/sites.yml"))
    assert settings.window_days == 28
    assert {s.id for s in sites} == {"ruma", "indjija"}
    assert {s.base_url for s in sites} == {"https://cvecararuma.rs", "https://cvecaraindjija.rs"}
    assert sites[0].url("/") == "https://cvecararuma.rs/"
    assert sites[1].url("/twitter-image") == "https://cvecaraindjija.rs/twitter-image"


@pytest.mark.parametrize("base,prop", [
    ("http://cvecararuma.rs", "sc-domain:cvecararuma.rs"),
    ("https://localhost", "sc-domain:localhost"),
    ("https://cvecararuma.rs:8443", "sc-domain:cvecararuma.rs"),
    ("https://cvecararuma.rs", "sc-domain:bad-site.rs"),
])
def test_reject_unsafe_base_and_property(base, prop):
    with pytest.raises(ValueError):
        _site({"id": "ruma", "name": "Ruma", "base_url": base,
               "gsc_property": prop, "keywords": ["cvecara ruma"]})


def test_reject_cross_domain_url_in_paths():
    with pytest.raises(ValueError):
        _site({"id": "ruma", "name": "Ruma", "base_url": "https://cvecararuma.rs",
               "gsc_property": "sc-domain:cvecararuma.rs", "keywords": ["cvecara ruma"],
               "check_paths": ["//evil.example/"]})
