# Test matrica v3.0.0

## Lokalni, deterministički testovi

- v2 regressions: postojeći konfiguracioni, CLI, GSC, HTML, report, Telegram i watchdog testovi.
- Zero-cost guard: zabrana `pay_as_you_go`, nepoznatih konfiguracionih polja, prekoračenja kvota i odbijanje nepostojećih kategorija.
- Crawler: kontrolisani `httpx.MockTransport`, robots.txt, sitemap index, odbijanje drugog hosta, hard limit pre HTTP poziva, nadzor pogrešne dostave, slike bez alt i Product JSON-LD.
- PageSpeed: validan keyless lab odgovor, nedostajuća CrUX metrika, HTTP 429 bez fallback-a, ograničenje API broja.
- GSC: stvarni tip `image`, uređaj/zemlja/upiti; izostavljene reči nakon quota limita prikazuju N/D umesto 0.
- Storage: SQLite iz JSON-a, nedostajuće vrednosti u tabeli ostaju NULL.
- Audit: generisanje JSON/Markdown/Telegram sa lažnim (mock) servisima.
- Deploy contract: YAML workflow validnost, centralni sites/limits i nepostojanje dodatnog Render resursa.

## Komande

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check seo_monitor tests
python -m compileall -q seo_monitor
python -m seo_monitor validate --config config/sites.yml --limits config/limits.yml
```

## Šta zahteva produkcioni test (nije tvrđeno da je već prošlo)

1. `SEO Daily Monitoring`: verifikovati stvarni GSC API i URL Inspection za sve aktivne domene.
2. `SEO Weekly Technical Audit`: proveriti da li sitemap crawler nalazi sve očekivane URL-ove i da li PSI keyless vraća podatke ili kontrolisani N/D.
3. Telegram: proveriti dnevni i nedeljni izveštaj u privatnom kanalu i watchdog.
4. GitHub Billing: potvrditi **Stop usage when budget limit is reached** i dovoljno besplatnih minuta.
5. CI: `ruff` i testovi moraju proći na GitHub runneru.

Ovo nije garancija SEO pozicije. Nema stvarnih plaćenih API poziva, nema checkout pokušaja, nema produkcionih deploy-a.
