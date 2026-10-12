# Lotos SEO — Operativni priručnik v2

## Dnevni raspored

- **06:17 UTC**: `SEO Daily Monitoring` proverava oba domena, uzima finalizovani GSC sa `reporting_lag_days: 3`, čuva JSON snapshot i Markdown/CSV/HTML rezultate; šalje Telegram dnevni KPI.
- **12:00 UTC**: `SEO Monitoring Watchdog` preko GitHub Actions API-ja (read-only) proverava uspešan dnevni run za poslednjih 27 h; ako ga nema šalje alarm. Ako nema Telegram dozvolu, prijavljuje neuspeh.
- **Ponedeljak**: dnevni Telegram digest sadrži dodatno poređenje finalizovanih 7+7 dana (bez zasebnog duplog postovanja).
- **Ručno**: `SEO Telegram Connection Test` šalje jednu probnu poruku i ne zahteva Google JSON.

## Operativna kontrolna lista

1. GitHub Actions dnevni monitor zelen.
2. U logu vidi se `GSC: OK` za Rumu i Inđiju.
3. `reports/overview.md` i `reports/dashboard.html` imaju 28d metrike, ne `N/D`.
4. `reports/telegram-preview.txt` odgovara očekivanoj poruci na kanalu.
5. Za svaki domen kod `HTTP` svi konfigurisani URL-ovi očekivano vraćaju 200 (ili objašnjeno odstupanje).
6. URL Inspection uzorak treba da pokazuje očekivane verdicts, Google canonical i index allow stanje.
7. Ako je `SEO Monitoring Watchdog` crven, odmah proveri `SEO Daily Monitoring` i GitHub schedule kašnjenja.

## Incidenti

| Signal | Provera | Bezbedna akcija |
|---|---|---|
| GSC HTTP 403 | Enable API, Domain property pristup, service account Full, quota | Ne menjati Google Secrets napamet; proveriti Cloud logove |
| GSC HTTP 404 | GSC property ID i domen | Proveri `sc-domain:...`; ne menjaj canonical |
| GSC 429 | API quota ili stopa poziva | Sačekati, smanjiti broj praćenih URL-ova i upita samo ako je potrebno |
| GSC 5xx | Google API privremeni kvar | Ponoviti run nakon pauze; ne skrivati grešku |
| HTTP 5xx | Netlify/Render funkcije, zavisni API | Pregled logova; ciljano otkloniti problem, bez SEO refaktora |
| `noindex` | Meta robots u HTML-u / headers | Proveriti da li je namerno; ne skidati sa administrativnih ruta |
| Canonical pogrešan | Konkretan URL i metadata | Proveriti lokalnu i Ruma konfiguraciju posebno |
| „Učitavanje...“ u H1 | SSR HTML vs hydrated browser | Ovo je informativno upozorenje; tek nakon robots-render testa zaključiti |
| Telegram nema poruke | Da li bot ima admin prava, rotiran token, ispravan `-100...` Chat ID | Pokreni odvojeni `SEO Telegram Connection Test` |
| Watchdog alarm | Dnevni job nije uspeo u 27h, GitHub schedule delay | Proveri workflow log; obnovi bez maskiranja error koda |
| Git push blocked | Branch protection, token scope | Data grana/PR ili odobrenje; ne ukidati protection |

## Poređenje SEO pozicija

- `cvecara ruma`, `cvecara indjija` i slični upiti su **tačni upiti** iz GSC API-ja, ne dokaz trenutnog #1.
- Pad pozicije se prijavljuje samo ako oba perioda imaju minimum 20 prikaza i pad >=3 pozicije (podesivo).
- `0` prikaza u Google upitima može značiti privatno filtrirane/nedostupne podatke; `N/D` ne treba tumačiti kao rang 0.
- Rast SEO klikova ne meri broj porudžbina. Za konverzije je potrebna zasebna privatno-bezbedna integracija.

## Dodavanje novog domena

1. Kupiti domen i objaviti stvaran lokalni storefront koji zaista pruža dostavu.
2. Potvrditi Google Search Console Domain property i dodati postojeći service account.
3. Dodati YAML entry sa novim jedinstvenim `id`, `base_url`, `gsc_property`, `keywords`, `check_paths`, `inspect_paths`.
4. `python -m seo_monitor validate` i test `--site NOVI_ID --no-notify`.
5. Proveriti SEO canonical, stvarnu ponudu/dostavu i da domen ne glumi fizičku radnju koja ne postoji.
6. PR → GitHub CI → merge; pri sledećem run-u domen se automatski pojavljuje u dashboard/Telegram poruci.

## Plan testiranja

```bash
python -m pip install -e '.[dev]'
ruff check seo_monitor tests
python -m pytest -q
python -m compileall -q seo_monitor
python -m seo_monitor validate
python -m seo_monitor run --skip-gsc --no-notify --preview-telegram
```

Poslednja komanda **radi stvarne HTTP provere** (nije mrežno offline), samo preskače Google API. Za pravi Google test ukloniti `--skip-gsc` i postaviti kredencijale isključivo kroz privatno okruženje.

## Ograničenja u planiranju SLA-a

Sam GitHub Actions nije garantovani 24/7 uptime monitor; kada GitHub potpuno prestane da radi, ni Watchdog neće poslati obaveštenje. Za enterprise SLA treba dodatni **spoljni nezavisni watchdog** (npr. sa drugog provajdera). HTTP proveru HTML-a ne treba proglašavati kompletnim PageSpeed, Lighthouse, mobilnim UX ili checkout testom. Nema automatizovanih Google pretraga, falsifikovanih klikova ni AI ranking obećanja.
