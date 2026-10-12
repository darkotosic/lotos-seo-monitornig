from dataclasses import replace

import httpx

from seo_monitor.config import Site
from seo_monitor.cost_guard import CostGuard, Limits
from seo_monitor.performance import collect_pagespeed, parse_pagespeed

SITE = Site('ruma','Ruma','https://cvecararuma.rs','sc-domain:cvecararuma.rs',
            ('cvecara ruma',),('/',),('/',))


def test_pagespeed_field_missing_does_not_become_zero():
    result = parse_pagespeed({'lighthouseResult': {'categories': {'performance': {'score': .96}},
                                                'audits': {'largest-contentful-paint': {'numericValue': 2000}}}})
    assert result['lab_performance_score']==96
    assert result['lab_lcp_ms']==2000
    assert result['field_inp_ms_p75'] is None
    assert not result['field_data_available']


def test_pagespeed_both_devices_keyless():
    requests=[]
    def handler(request):
        requests.append(dict(request.url.params))
        return httpx.Response(200,json={'lighthouseResult':{'categories':{'performance':{'score':.91}}}})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result=collect_pagespeed(SITE,CostGuard(Limits()),client=client)
    assert len(result)==2
    assert all(x['status']=='ok' for x in result)
    assert {x['strategy'] for x in result}=={'mobile','desktop'}
    assert not any('key' in item for x in requests for item in x)


def test_pagespeed_429_stops_without_paid_fallback():
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(429)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result=collect_pagespeed(SITE,CostGuard(Limits()),client=client)
    assert len(calls)==1 and result[0]['http_status']==429


def test_pagespeed_quota_stops_before_second_request():
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json={'lighthouseResult':{}})
    guard=CostGuard(replace(Limits(),maximum_weekly_pagespeed_calls_per_site=1))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result=collect_pagespeed(SITE,guard,client=client)
    assert len(calls)==1
    assert result[-1]['status']=='quota_skipped'
