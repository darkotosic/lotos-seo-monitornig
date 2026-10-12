"""Low-volume HTTP and on-page checks; requests remain on the configured host."""

from __future__ import annotations

import json
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup
from defusedxml import ElementTree

from seo_monitor.config import Settings, Site

MAX_BYTES = 2_000_000


def _get(client: httpx.Client, site: Site, url: str) -> tuple[httpx.Response, bytes]:
    """Fetch at most 2 MB, rejecting non-HTTPS/cross-host redirects at every hop."""
    target = url
    for _ in range(6):
        parsed = urlsplit(target)
        if parsed.hostname != urlsplit(site.base_url).hostname or parsed.scheme != "https":
            raise ValueError("URL outside configured HTTPS host")
        with client.stream("GET", target, follow_redirects=False) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    raise ValueError("HTTP redirect with no location")
                target = str(response.url.join(location))
                continue
            return response, _read_limited(response)
    raise ValueError("More than 5 HTTP redirects")


def _read_limited(response: httpx.Response) -> bytes:
    content = bytearray()
    for chunk in response.iter_bytes():
        content.extend(chunk)
        if len(content) > MAX_BYTES:
            raise ValueError("Response exceeded 2 MB monitoring limit")
    return bytes(content)


def _document(site: Site, response: httpx.Response, content: bytes) -> dict:
    status = response.status_code
    final_url = str(response.url)
    result = {"url": final_url, "status": status, "content_type": response.headers.get("content-type", "")}
    if status >= 400:
        result["error"] = f"HTTP {status}"
        return result
    if "text/html" not in result["content_type"].lower():
        return result

    soup = BeautifulSoup(content, "html.parser")
    robots = " ".join(m.get("content", "") for m in soup.find_all("meta")
                      if m.get("name", "").lower() in ("robots", "googlebot"))
    robots += " " + response.headers.get("x-robots-tag", "")
    canonical = soup.find("link", rel=lambda v: v and "canonical" in v)
    desc = soup.find("meta", attrs={"name": "description"})
    h1 = soup.find("h1")
    ld_errors = 0
    ld_types: set[str] = set()
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        if not script.string:
            continue
        try:
            obj = json.loads(script.string)
        except (ValueError, TypeError):
            ld_errors += 1
            continue
        def walk(value):
            if isinstance(value, dict):
                t = value.get("@type")
                if isinstance(t, str):
                    ld_types.add(t)
                elif isinstance(t, list):
                    ld_types.update(s for s in t if isinstance(s, str))
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(obj)
    # Capture link/image metadata from the first HTML response only. No browser rendering.
    host = urlsplit(site.base_url).hostname
    internal_links = set()
    for anchor in soup.find_all("a", href=True):
        href = urljoin(final_url, anchor["href"])
        parsed = urlsplit(href)
        if (parsed.scheme == "https" and parsed.hostname == host and not parsed.port
                and not parsed.query and not parsed.username and not parsed.password):
            internal_links.add(parsed._replace(fragment="").geturl())
    imgs = soup.find_all("img")
    result.update({
        "internal_links": sorted(internal_links)[:300],
        "img_count": len(imgs),
        "images_without_alt": sum(1 for img in imgs if not img.has_attr("alt")),
        "img_lazy_count": sum(1 for img in imgs if img.get("loading") == "lazy"),
        "h1_count": len(soup.find_all("h1")),
        "title": (soup.title.get_text(" ", strip=True) if soup.title else "")[:200],
        "description": (desc.get("content", "") if desc else "")[:300],
        "h1": (h1.get_text(" ", strip=True) if h1 else "")[:200],
        # Informational; hydration may later replace this heading. Not a hard SEO error.
        "ssr_h1_placeholder": bool(h1 and h1.get_text(" ", strip=True).casefold()
                                   in {"učitavanje...", "loading...", "loading"}),
        "canonical": canonical.get("href") if canonical else None,
        "noindex": "noindex" in robots.lower(),
        "jsonld_types": sorted(ld_types), "jsonld_parse_errors": ld_errors,
    })
    if result["noindex"]:
        result["error"] = "Indexing blocked by robots noindex"
    elif ld_errors:
        result["warning"] = "Invalid JSON-LD block"
    elif not result["canonical"]:
        result["warning"] = "Canonical link not present in SSR HTML"
    elif urlsplit(str(result["canonical"])).hostname not in (None, urlsplit(site.base_url).hostname):
        result["warning"] = "Canonical points to a different domain"
    elif result["canonical"]:
        canonical_url = urlsplit(urljoin(final_url, str(result["canonical"])))
        actual_url = urlsplit(final_url)
        if (canonical_url.hostname != actual_url.hostname
                or canonical_url.path.rstrip("/") != actual_url.path.rstrip("/")):
            result["warning"] = "Canonical points to a different page"
    return result


def _sitemap_urls(content: bytes) -> list[str]:
    """Read page URLs (or sitemap index URLs), never nested image:loc values."""
    root = ElementTree.fromstring(content)
    urls = []
    for node in root:
        if node.tag.rsplit("}", 1)[-1] not in ("url", "sitemap"):
            continue
        for field in node:
            if field.tag.rsplit("}", 1)[-1] == "loc" and field.text:
                urls.append(field.text.strip())
    return urls


def collect_checks(site: Site, settings: Settings) -> dict:
    result: dict = {"pages": [], "sitemap": {}, "robots": {}}
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    with httpx.Client(timeout=timeout, headers={
        "User-Agent": "LotosSEOHealthMonitor/1.0 (+contact via cvecararuma.rs; low-volume bot)"
    }) as client:
        for path in dict.fromkeys(("/", *site.check_paths)):
            url = site.url(path)
            try:
                response, content = _get(client, site, url)
                result["pages"].append({"path": path, **_document(site, response, content)})
            except (httpx.HTTPError, ValueError) as exc:
                result["pages"].append({"path": path, "url": url, "error": type(exc).__name__})

        for name, url in (("sitemap", site.url("/sitemap.xml")), ("robots", site.url("/robots.txt"))):
            try:
                response, content = _get(client, site, url)
                value: dict = {"url": str(response.url), "status": response.status_code}
                if response.status_code != 200:
                    value["error"] = f"HTTP {response.status_code}"
                elif name == "sitemap":
                    try:
                        urls = _sitemap_urls(content)
                        value["loc_count"] = len(urls)
                        value["sample_urls"] = urls[:5]
                        value["is_sitemap_index"] = b"sitemapindex" in content[:1500]
                        if not urls:
                            value["error"] = "Sitemap XML contains no loc entries"
                        # No recursive fetching: site controls each sitemap, and parent locs may be child sitemaps.
                    except ElementTree.ParseError:
                        value["error"] = "Invalid sitemap XML"
                else:
                    parser = RobotFileParser()
                    parser.parse(content.decode("utf-8", errors="replace").splitlines())
                    value["allows_home_googlebot"] = parser.can_fetch("Googlebot", site.url("/"))
                    value["allows_sample_googlebot"] = {
                        path: parser.can_fetch("Googlebot", site.url(path)) for path in site.check_paths
                    }
                    if not value["allows_home_googlebot"]:
                        value["error"] = "robots.txt disallows Googlebot at homepage"
                result[name] = value
            except (httpx.HTTPError, ValueError) as exc:
                result[name] = {"url": url, "error": type(exc).__name__}
    return result
