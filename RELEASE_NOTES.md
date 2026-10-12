# LOTOS SEO INTELLIGENCE — v3.0.0 (Zero-Cost Edition)

## Nova funkcionalnost

- Hard limiti `config/limits.yml`, `seo_monitor/cost_guard.py` — samo free-only režim, fail-closed kvote.
- Nedeljni bezbedni sitemap crawler sa zaštitom od cross-host i robots blokiranih putanja.
- Detaljna provera HTML title/description/H1, canonical, unutrašnjih linkova, alt atributa i JSON-LD.
- Read-only PageSpeed keyless mobile/desktop; 429/403/preteran odgovor ne aktivira druge servise.
- Napredni GSC upiti, segmentacija po uređaju/zemlji, dodatni Google Images agregat kada je dostupan.
- Heuristički SEO Opportunity Engine sa dokazima, bez automatskih izmena sajta.
- Neobavezni read-only GA4 modul (nije zakazan niti aktiviran).
- SQLite offline rebuild iz JSON istorije; baza ostaje izvan Git-a.
- Novi `seo-weekly.yml` sa zasebnim tehničkim i Telegram izveštajem.
- Novi dokumenti v3 o migraciji, nultom trošku, operacijama i testovima.

## Kompatibilnost

- U potpunosti zadržani `sites.yml`, service-account, Telegram Secret nazivi, dnevni JSON/CSV, scheduler i watchdog v2.
- Nema izmena Ruma/Inđija produkcionih sajtova, Render/Netlify env, baze porudžbina i checkout-a.
- Ništa ne koristi Google Indexing API za e-commerce proizvode.

## Verifikacija

Pokrenuti lokalni testovi i sintaksne provere su dokumentovani u odgovoru pri isporuci; produkcioni GSC/Telegram/PageSpeed nakon deploy-a nisu testirani u ovom okruženju. GitHub CI radi Ruff lint.
