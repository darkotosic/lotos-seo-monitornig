# LOTOS SEO — v3 Operativni priručnik

## Raspored GitHub Actions

- `SEO Daily Monitoring` — svaki dan 06:17 UTC: GSC + odabrani HTTP/indeks uzorak + Telegram.
- `SEO Weekly Technical Audit` — ponedeljkom 08:43 UTC: ograničeni sitemap crawl, PSI i nedeljni Telegram.
- `SEO Monitoring Watchdog` — svaki dan u 12:00 UTC: alarm ako nije uspešno završen dnevni workflow.
- `SEO Telegram Connection Test` — isključivo ručno pokretanje.
- `Monitor CI` — testovi na push/PR.

GitHub cron može kasniti i može biti pauziran zbog neaktivnosti; ovaj repo ne garantuje SLA. Za strogi SLA ne prelaziti na plaćeni scheduler bez nove izričite odluke.

## Folderi i istorija

- `data/{site_id}/YYYY-MM-DD.json`: dnevni GSC/HTTP snapshot (čuvati pri migraciji).
- `data/audits/{site_id}/YYYY-MM-DD.json`: nedeljni tehnički nalaz.
- `reports/{site_id}-latest.md`: dnevni izveštaj.
- `reports/{site_id}-audit.md`: poslednji nedeljni audit.
- `reports/telegram-preview.txt`: dnevna poruka.
- `reports/telegram-weekly-preview.txt`: nedeljna poruka.
- `reports/dashboard.html`, CSV: postojeći v2 izveštaji, u v3 prošireni GSC segmentima.
- `local/seo_history.db`: privremeni lokalni SQLite, obnovljiv komandom `rebuild-db`, ne ide u Git.

## Tumačenje alarma

| Simptom | Postupak |
|---|---|
| GSC unavailable 403 | Uključiti Search Console API, proveriti service account Full i `sc-domain:` property. |
| GSC 429 | Ne ponavljati agresivno; poštovati Google kvotu i kasnije probati ponovo. |
| GSC N/D | Ne tretirati kao nulu; proveriti male uzorke ili vreme finalizacije. |
| Crawler `quota` | Očekivano ograničenje; nikada ne povećavati cap bez analize GitHub budžeta. |
| Crawler `fatal_error` | Proveriti robots.txt, sitemap i HTTP dostupnost. |
| PSI 403/429 | Ostaviti N/D; ne praviti plaćeni ključ niti aktivirati billing. |
| H1 `Učitavanje...` | Proveriti SSR HTML i renderovani DOM; ne menjati odmah proizvodni sajt. |
| `wrong_delivery_city` | Proveriti da li opis za Inđiju nepravilno navodi dostavu u Rumi; fizička radnja u Rumi je legitimna. |
| Telegram nema poruke | Proveriti token (rotirati ranije otkriven token), Chat ID, dozvole bota i workflow log. |
| Git push odbijen | Proveriti branch protection i konflikte, ne koristiti force push. |

## Dodavanje domena

Tek nakon puštanja domena u rad i verifikacije Google Search Console, u `config/sites.yml` dodati:

```yaml
  - id: starapazova
    enabled: true
    name: "Cvećara Stara Pazova — Lotos"
    base_url: "https://cvecarastarpazova.rs"
    gsc_property: "sc-domain:cvecarastarpazova.rs"
    keywords:
      - "cvecara stara pazova"
      - "dostava cveca stara pazova"
    check_paths: ["/", "/proizvodi", "/dostava"]
    inspect_paths: ["/", "/proizvodi"]
```

Dodati **isti** postojeći service account kao Full korisnika u novi property, zatim `validate` i ručni run `--site starapazova`. Novi bot, nova Render instanca ili migracija baze nisu potrebni.

## Bezbednost

- Nikad ne stavljaj API ključ, privatni servisni JSON ili Telegram token u Git, `NEXT_PUBLIC_*`, frontend, logove niti chat.
- Repo držati privatnim jer SEO izveštaji mogu otkriti poslovne planove i strategije.
- Nema automatskog slanja SEO ispravki na Rumu ili Inđiju.
- Prioritet je očuvanje postojećih Google pozicija i stvarna vrednost kupcima, bez lažnih Google Business Profile adresa.
