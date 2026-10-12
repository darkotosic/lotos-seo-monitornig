from pathlib import Path

import yaml

from seo_monitor.config import load_config
from seo_monitor.cost_guard import load_limits


def test_deployment_contracts_and_no_paid_cloud():
    root=Path('.')
    settings,sites=load_config(root/'config/sites.yml')
    limits=load_limits(root/'config/limits.yml')
    assert len(sites)==2
    assert all(s.gsc_property.startswith('sc-domain:') for s in sites)
    assert len(sites)<=limits.maximum_sites
    assert (root/'.github/workflows/seo-weekly.yml').exists()
    for workflow in (root/'.github/workflows').glob('*.yml'):
        data=yaml.safe_load(workflow.read_text(encoding='utf-8'))
        assert isinstance(data,dict) and 'jobs' in data
        assert 'permissions' in data
    # No deployment of paid GCP resources from this repository.
    assert not (root/'terraform').exists()
    assert not (root/'render.yaml').exists()


def test_crawler_fatal_is_marked(tmp_path,monkeypatch):
    import httpx
    from seo_monitor.crawler import audit_site
    from seo_monitor.cost_guard import CostGuard
    site=load_config(Path('config/sites.yml'))[1][0]
    with httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(503))) as client:
        out=audit_site(site,CostGuard(load_limits(Path('config/limits.yml'))),client=client)
    assert out['fatal_error']
    assert out['pages']==[]
