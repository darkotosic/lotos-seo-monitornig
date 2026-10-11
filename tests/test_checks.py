import httpx
import pytest

from seo_monitor.checks import _document, _get, _sitemap_urls, collect_checks
from seo_monitor.config import Settings, Site


@pytest.fixture
def site():
    return Site("ruma", "Ruma", "https://cvecararuma.rs", "sc-domain:cvecararuma.rs",
                ("cvecara ruma",), ("/", "/proizvodi", "/twitter-image"), ("/",))


def fake_transport(request):
    path = request.url.path
    if path == "/bad":
        return httpx.Response(301, headers={"location": "https://evil.example/phishing"})
    if path == "/unavailable":
        return httpx.Response(503, text="Service unavailable")
    if path == "/robots.txt":
        return httpx.Response(200, text="User-agent: *\nAllow: /\n", headers={"content-type": "text/plain"})
    if path == "/sitemap.xml":
        return httpx.Response(200, text='''<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://cvecararuma.rs/</loc></url></urlset>''', headers={"content-type": "application/xml"})
    if path == "/twitter-image":
        return httpx.Response(200, content=b"PNG", headers={"content-type": "image/png"})
    return httpx.Response(200, text='''<html><head><title>Cvećara Ruma</title>
<meta name="description" content="Dostava cveća Ruma"><link rel="canonical" href="https://cvecararuma.rs/">
<script type="application/ld+json">{"@type":"Product","name":"Buket"}</script></head>
<body><h1>Buketi Ruma</h1></body></html>''', headers={"content-type": "text/html"})


def test_html_analysis(site):
    with httpx.Client(transport=httpx.MockTransport(fake_transport)) as client:
        response, content = _get(client, site, site.url("/"))
        data = _document(site, response, content)
    assert data["status"] == 200
    assert data["h1"] == "Buketi Ruma"
    assert "Product" in data["jsonld_types"]
    assert data["canonical"] == "https://cvecararuma.rs/"
    assert "error" not in data


def test_reject_cross_domain_redirect(site):
    with httpx.Client(transport=httpx.MockTransport(fake_transport)) as client:
        with pytest.raises(ValueError, match="outside configured HTTPS host"):
            _get(client, site, site.url("/bad"))


def test_image_is_not_interpreted_as_html(site):
    with httpx.Client(transport=httpx.MockTransport(fake_transport)) as client:
        response, content = _get(client, site, site.url("/twitter-image"))
        data = _document(site, response, content)
    assert data["status"] == 200
    assert "warning" not in data


def test_collect_checks(site, monkeypatch):
    original_client = httpx.Client

    def configured_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(fake_transport)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "Client", configured_client)
    result = collect_checks(site, Settings())
    assert result["robots"]["allows_home_googlebot"] is True
    assert result["sitemap"]["loc_count"] == 1
    assert len(result["pages"]) == 3
    assert not any("error" in page for page in result["pages"])


def test_noindex_detection(site):
    resp = httpx.Response(200, text='<html><head><meta name="robots" content="noindex"></head></html>',
                          headers={"content-type": "text/html"}, request=httpx.Request("GET", site.url("/")))
    result = _document(site, resp, resp.content)
    assert "noindex" in result["error"]


def test_sitemap_parse():
    assert _sitemap_urls(b'<urlset><url><loc>https://example.com/</loc>'
                         b'<image><loc>https://example.com/image.jpg</loc></image>'
                         b'</url></urlset>') == ["https://example.com/"]
