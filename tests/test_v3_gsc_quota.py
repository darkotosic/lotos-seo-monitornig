from dataclasses import replace
from datetime import date

from seo_monitor.config import Settings, Site
from seo_monitor.cost_guard import CostGuard, Limits
from seo_monitor.gsc import collect_gsc


class Api:
    def __init__(self):
        self.queries=[]
        self.inspections=[]

    def query(self, prop, start, end, dimensions=None, query=None, limit=1000, search_type='web'):
        self.queries.append((prop, start, end, dimensions, query, limit, search_type))
        if dimensions:
            name = 'mobile' if dimensions==['device'] else 'sr' if dimensions==['country'] else 'cvecara ruma'
            return {'rows':[{'keys':[name], 'clicks':4,'impressions':60,'ctr':.06,'position':3.0}]}
        return {'rows':[{'clicks':4,'impressions':60,'ctr':.06,'position':3.0}]}

    def inspect(self, prop, url):
        self.inspections.append(url)
        return {'verdict':'PASS'}


def test_gsc_budget_caps_before_each_call():
    site=Site('ruma','Lotos','https://cvecararuma.rs','sc-domain:cvecararuma.rs',
              tuple(f'kw{i}' for i in range(40)),('/',),('/',))
    limit=replace(Limits(),maximum_daily_gsc_calls_per_site=15,
                  maximum_daily_inspections_per_site=1)
    api=Api();guard=CostGuard(limit)
    out=collect_gsc(api,site,Settings(),date(2026,10,12),guard=guard)
    assert len(api.queries)<=15
    assert len(api.inspections)<=1
    assert sum(k.get('status')=='quota_skipped' for k in out['keywords'])>0
    assert any(k['current'] is None for k in out['keywords'])


def test_gsc_image_search_is_optional_and_real_type():
    site=Site('ruma','Lotos','https://cvecararuma.rs','sc-domain:cvecararuma.rs',
              ('cvecara ruma',),('/',),('/',))
    api=Api()
    out=collect_gsc(api,site,Settings(),date(2026,10,12),guard=CostGuard(Limits()))
    assert any(item[-1]=='image' for item in api.queries)
    assert out['image_search_totals']['impressions']==60
    assert len(out['devices'])==1
    assert len(out['top_queries'])==1
