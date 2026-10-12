import json
import sqlite3
from datetime import date

from seo_monitor.audit_cli import run_weekly, weekly_report, weekly_telegram
from seo_monitor.config import Site
from seo_monitor.cost_guard import Limits
from seo_monitor.opportunities import compare_totals, discover
from seo_monitor.recommendations import recommendations
from seo_monitor.storage import rebuild_sqlite

SITE=Site('ruma','Ruma','https://cvecararuma.rs','sc-domain:cvecararuma.rs',
          ('cvecara ruma',),('/',),('/',))


def test_intelligence_insufficient_data_and_scoring():
    snapshot={'gsc':{'top_queries':[{'query':'orhideja ruma','impressions':160,'clicks':1,
                                   'position':8,'ctr':.00625},
                                  {'query':'irrelevant','impressions':2,'clicks':0,
                                   'position':19,'ctr':0}],
                     'keywords':[]}}
    rows=discover(snapshot)
    assert len(rows)==1 and rows[0]['target']=='orhideja ruma'
    assert rows[0]['priority']=='P1'
    assert rows[0]['score']>0
    assert compare_totals(None,{})=={'available':False}
    assert recommendations(snapshot)[0]['manual_review_required']


def test_weekly_report_and_digest():
    audit={'audit_date':'2026-10-12','pages':[{'url':SITE.url('/'),'status':200}],
           'pages_in_sitemap':3,'http_statuses':{'200':1},'metadata_issues':[],
           'schema_issues':[],'image_issues':[], 'pagespeed':[]}
    assert 'Nedeljni SEO audit' in weekly_report(SITE,audit,None)
    assert 'preskočeno' in weekly_report(SITE,audit,None)
    assert 'Ruma' in weekly_telegram([SITE],{'ruma':audit},date(2026,10,12))


def test_sqlite_projection_preserves_null_rank(tmp_path):
    root=tmp_path/'data'/'ruma';root.mkdir(parents=True)
    snapshot={'site_id':'ruma','monitor_date':'2026-10-12','gsc':{
        'totals':{'clicks':3,'impressions':99,'ctr':.03,'position':9.4},
        'keywords':[{'query':'no data','current':None},
                    {'query':'cvecara ruma','current':{'impressions':10,'clicks':1,'position':2.1,'ctr':.1}}]}}
    (root/'2026-10-12.json').write_text(json.dumps(snapshot))
    db=tmp_path/'local'/'seo.db';counts=rebuild_sqlite(tmp_path/'data',db)
    assert counts=={'snapshots':1,'keyword_records':2}
    with sqlite3.connect(db) as connection:
        rows=connection.execute('SELECT query,position FROM keywords ORDER BY query').fetchall()
    assert rows==[('cvecara ruma',2.1),('no data',None)]


def test_weekly_command_does_not_call_live_services(tmp_path,monkeypatch):
    import seo_monitor.audit_cli as module
    monkeypatch.setattr(module,'audit_site',lambda site,guard: {
        'site_id':site.id,'pages':[{'url':site.url('/'),'status':200}],
        'pages_in_sitemap':1,'http_statuses':{'200':1},
        'metadata_issues':[],'schema_issues':[],'image_issues':[],'warnings':[]})
    monkeypatch.setattr(module,'collect_pagespeed',lambda site,guard,paths: [])
    code=run_weekly([SITE],Limits(),date(2026,10,12),tmp_path/'data',tmp_path/'reports')
    assert code==0
    assert (tmp_path/'data'/'audits'/'ruma'/'2026-10-12.json').exists()
    assert (tmp_path/'reports'/'ruma-audit.md').exists()
    assert (tmp_path/'reports'/'telegram-weekly-preview.txt').exists()
