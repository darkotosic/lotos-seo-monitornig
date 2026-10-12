from dataclasses import replace

import httpx

from seo_monitor.config import Site
from seo_monitor.content_audit import audit_metadata
from seo_monitor.cost_guard import CostGuard, Limits
from seo_monitor.crawler import audit_site
from seo_monitor.images import audit_images
from seo_monitor.schema_audit import audit_schema

SITE = Site('indjija', 'Inđija', 'https://cvecaraindjija.rs', 'sc-domain:cvecaraindjija.rs',
            ('cvecara indjija',), ('/',), ('/',))

ROBOTS = 'User-agent: *\nAllow: /\nDisallow: /privatno\n'
INDEX = '''<?xml version="1.0"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<sitemap><loc>https://cvecaraindjija.rs/products.xml</loc></sitemap>
<sitemap><loc>https://bad.example/evil.xml</loc></sitemap>
</sitemapindex>'''
SUB = '''<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
<url><loc>https://cvecaraindjija.rs/</loc></url>
<url><loc>https://cvecaraindjija.rs/proizvodi/buket-uspomena</loc></url>
<url><loc>https://bad.example/target</loc></url>
<url><loc>https://cvecaraindjija.rs/privatno</loc></url>
</urlset>'''
HTML = '''<!doctype html><html><head><title>Cvećara Inđija</title>
<meta name="description" content="Dostava u Rumi i okolini"/>
<link rel="canonical" href="https://cvecaraindjija.rs/"/></head><body>
<h1>Cveće za Inđiju</h1><a href="/proizvodi/buket-uspomena">Buket</a>
<a href="https://evil.example">Spoljni</a><img src="/a.webp"/></body></html>'''
PRODUCT = '''<html><head><title>Buket Uspomena | Lotos</title>
<meta name="description" content="Buket iz Rume dostavljamo u Inđiju"/>
<link rel="canonical" href="https://cvecaraindjija.rs/proizvodi/buket-uspomena"/></head>
<body><h1>Buket Uspomena</h1><script type="application/ld+json">
{"@context":"https://schema.org","@type":"Product","name":"Buket"}</script>
<img src="/p.webp" alt="Buket uspomena" loading="lazy" /></body></html>'''


def test_crawler_same_host_robots_and_sitemap_index():
    seen = []

    def handler(request):
        seen.append(str(request.url))
        p = request.url.path
        if p == '/robots.txt':
            return httpx.Response(200, text=ROBOTS)
        if p == '/sitemap.xml':
            return httpx.Response(200, content=INDEX.encode())
        if p == '/products.xml':
            return httpx.Response(200, content=SUB.encode())
        if p == '/':
            return httpx.Response(200, text=HTML, headers={'content-type':'text/html'})
        if p == '/proizvodi/buket-uspomena':
            return httpx.Response(200, text=PRODUCT, headers={'content-type':'text/html'})
        return httpx.Response(404)

    guard = CostGuard(Limits())
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = audit_site(SITE, guard, client=client)
    assert len(result['pages']) == 2
    assert result['sitemaps_fetched'] == 2
    assert all('evil.example' not in u for u in seen)
    assert all('/privatno' not in u for u in seen)
    assert any(x['type']=='wrong_delivery_city' for x in result['metadata_issues'])
    assert any(x['type']=='img_alt_missing' for x in result['image_issues'])
    assert not result['schema_issues']
    assert result['quota_used']['crawl'] == 2
    assert result['link_audit']['candidate_orphans_in_crawled_sample'] == ['https://cvecaraindjija.rs']


def test_crawler_quota_skips_pages_before_request():
    requests=[]
    def handler(request):
        requests.append(request.url.path)
        if request.url.path == '/robots.txt':
            return httpx.Response(200, text=ROBOTS)
        if request.url.path == '/sitemap.xml':
            return httpx.Response(200, content=SUB.encode())
        return httpx.Response(200,text=HTML,headers={'content-type':'text/html'})
    guard=CostGuard(replace(Limits(),maximum_weekly_crawl_pages_per_site=1))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result=audit_site(SITE,guard,client=client)
    assert result['partial']
    assert len(result['pages'])==1
    assert requests.count('/proizvodi/buket-uspomena')==0


def test_local_business_ruma_reference_is_not_mistaken_delivery():
    pages=[{'url':'https://cvecaraindjija.rs/test','content_type':'text/html', 'status':200,
            'title':'Cvećara Lotos Ruma - Dostava za Inđiju',
            'description':'Fizička cvećara u Rumi; isporuka u Inđiju', 'h1_count':1}]
    assert not any(x['type']=='wrong_delivery_city' for x in audit_metadata(pages,'indjija'))


def test_schema_warns_without_inventing_ratings():
    issues=audit_schema([{'url':'https://cvecaraindjija.rs/proizvodi/p','path':'/proizvodi/p',
                          'status':200,'content_type':'text/html','jsonld_types':[]}])
    assert issues[0]['type']=='product_schema_missing'
    assert all('aggregateRating' not in str(x) for x in issues)
    assert audit_images([])==[]
