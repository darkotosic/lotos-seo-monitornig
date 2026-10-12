# LOTOS SEO INTELLIGENCE v3.0.0 — ZERO-COST EDITION

> **v3 je nadogradnja postojećeg v2 projekta, a ne novi produkcioni sistem.** Postojeći Ruma/Inđija GSC i Telegram Secrets ostaju. Svi plaćeni cloud servisi su isključeni; raspolaganje GitHub besplatnom kvotom mora biti ograničeno na nivou naloga. Pogledaj [zero-cost policy](docs/ENTERPRISE_ZERO_COST_V3.md) i [migraciju v2→v3](docs/MIGRACIJA_V2_V3.md).

## v3 — nove komande

```bash
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check seo_monitor tests
python -m seo_monitor validate --config config/sites.yml --limits config/limits.yml
python -m seo_monitor run --skip-gsc --no-notify
python -m seo_monitor audit --skip-pagespeed --no-notify
python -m seo_monitor rebuild-db --output data --db local/seo_history.db
```

`audit` je stvarni, nedeljni HTTPS sitemap crawler sa kontrolom `robots.txt`, bez promene produkcionog koda. Izostavi `--skip-pagespeed` da aktiviraš ograničeni, besplatni PageSpeed (keyless) koji može vratiti N/D. Dnevni monitoring koristi postojeće GSC/Telegram tajne. Izveštaji nastaju u `reports/`, dnevna istorija ostaje u `data/{site}/`, a novi nedeljni rezultati u `data/audits/{site}/`.

### Nova dokumentacija

- [ZERO COST / ENTERPRISE V3](docs/ENTERPRISE_ZERO_COST_V3.md)
- [MIGRACIJA V2 → V3](docs/MIGRACIJA_V2_V3.md)
- [OPERATIONS V3](docs/OPERATIONS_V3.md)
- [TEST MATRIX V3](docs/TEST_MATRIX_V3.md)
- [RELEASE NOTES](RELEASE_NOTES.md)

---


**Enterprise-grade read-only SEO observability za Cvećaru Lotos** — zaseban Python repozitorijum za `cvecararuma.rs`, `cvecaraindjija.rs` i nove lokalne domene. **Nije bot za veštačke klikove**; ne menja prodajne sisteme i ne garantuje Google rangiranje.

## Šta dobijaš

| Funkcija | Kako radi | Bezbednosno ograničenje |
|---|---|---|
| Search Console API | Klikovi, prikazi, CTR, pozicija, upiti, URL stranice, search appearance | Read-only OAuth scope; finalizovani, ne live podaci |
| 28d i 7d analitika | Poređenje sa prethodnim istim periodom; 3 dana zakašnjenja podataka | `N/D` ako nema podataka; bez pozicije nula |
| URL Inspection | Index verdict, coverage, Google canonical, robots/fetch za konfigurisane URL-ove | Samo uzorak; API ne može da zahteva indeksiranje |
| HTTP/SEO | 200/4xx/5xx, canonical, `noindex`, H1, title, description, JSON-LD, robots i sitemap | HTTPS, isti host, ograničenje 2 MB, nema kupovine |
| Dnevni Telegram | Stvarni KPI za sve domene, promene, pozicije ključnih reči i indeksiranje | Bez podataka kupaca; običan tekst, do 3500 karaktera |
| Nedeljni pregled | Svakog ponedeljka u dnevnoj poruci dodaje poređenje poslednjih 7d sa ranijih 7d | Isto finalizovano GSC merenje |
| SEO upozorenja | Pad pozicije sa dovoljnim brojem prikaza, noindex, 5xx, indeksne regresije, nedostupan API | Alarm je signal za proveru, ne tvrdnja o uzroku |
| Watchdog | Nezavisan GitHub Actions workflow proverava da li je dnevni job uspeo | Ako sam GitHub Actions ne radi, potreban je nezavisan spoljašnji monitor |
| Izveštaji | JSON, HTML dashboard, Markdown i Excel CSV, istorija po domenu | Git repo ostaviti **privatnim** |

## Početak za postojeći GitHub repo

**Ne menjati** Ruma/Indjija frontend, Django/Render, Netlify, checkout, API, CORS, SEO konfiguraciju prodajnih domena. Ovaj projekat se instalira kao zaseban repozitorijum.

1. Napravi backup postojećeg repozitorijuma `darkotosic/lotos-seo-monitornig` (ili novu granu).
2. Kopiraj kompletan sadržaj ZIP-a u **root postojećeg repozitorijuma**, tako da `.github/workflows/seo-daily.yml` ostane na istom putu.
3. Sačuvaj `data/` istoriju prethodnih dana koju si eventualno već prikupio; arhiva nosi postojeći početni snapshot iz dostavljenog ZIP-a. Ne briši novije podatke iz GitHub-a.
4. Ne menjaj postojeća tri GitHub Actions Secret-a: `SEO_GSC_SERVICE_ACCOUNT_JSON`, `SEO_TELEGRAM_BOT_TOKEN`, `SEO_TELEGRAM_CHAT_ID`.
5. Postojeći `config/sites.yml` i GSC Domain properties za Rumu/Inđiju ostaju nepromenjeni.
6. Napravi PR, pusti CI, zatim merge i ručno izvrši `SEO Daily Monitoring` iz **Actions**.
7. Proveri `reports/telegram-preview.txt`, `reports/dashboard.html`, `reports/overview.md` i oba `data/{id}/YYYY-MM-DD.json`.
8. Iz **Actions → SEO Telegram Connection Test** možeš zasebno testirati Telegram; **SEO Monitoring Watchdog** nadgleda dnevni run.

### Instalacija (PowerShell / Windows)

```powershell
cd C:\projekti\lotos-seo-monitornig
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m seo_monitor validate --config config/sites.yml
python -m pytest -q
ruff check seo_monitor tests
python -m compileall -q seo_monitor
```

**Bez GSC kredencijala**, ali uz stvarne HTTP provere oba produkciona domena:

```powershell
python -m seo_monitor run --skip-gsc --no-notify --preview-telegram
```

**Sa Google API kredencijalima** (van Git-a):

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\secure\lotos\gsc.json"
python -m seo_monitor run --config config/sites.yml --output data --reports reports --no-notify
```

**Test Telegram poruke**, samo nakon unosa novih/rotiranih tajni u env:

```powershell
$env:TELEGRAM_BOT_TOKEN="NOVI_TOKEN_POSTAVLJEN_LOKALNO"
$env:TELEGRAM_CHAT_ID="-100..."
python -m seo_monitor notify-test
```

Nijedan pravi token ne sme biti u skripti, README-u, Git-u, javnom logu ili `NEXT_PUBLIC_*`. Za GitHub koristi Repository Secrets. Nalog u GSC mora biti dodat za oba domena, a `searchconsole.googleapis.com` uključen u Google Cloud projektu.

## GitHub Actions

| Workflow | Okidač | Dozvole |
|---|---|---|
| `.github/workflows/ci.yml` | Push/promene koda i Pull Request | `contents: read` |
| `.github/workflows/seo-daily.yml` | Svakog dana `06:17 UTC`, ručno | `contents: write` (samo za snapshot commit) |
| `.github/workflows/telegram-test.yml` | Ručno | `contents: read` |
| `.github/workflows/seo-watchdog.yml` | Svakog dana `12:00 UTC`, ručno | `actions: read`, `contents: read` |

**Bez izmene podrazumevanih repository workflow permissions:** dnevni workflow već eksplicitno traži `contents: write`. Podrazumevano repo podešavanje može ostati **read-only**. Ako je `main` zaštićen od direktnog push-a, potrebno je dizajnirati PR/data granu; nemoj uklanjati branch zaštitu samo zbog monitora.

`seo-daily.yml` trenutno postavlja `SEO_DAILY_TELEGRAM_SUMMARY: 'true'`, pa šalje pun dnevni izveštaj i bez alarma. Svako ručno ponovno izvršavanje može ponovo poslati dnevnu poruku. Watchdog može javiti lažan alarm ako GitHub značajno odloži dnevni run.

## Konfiguracija novih gradova

Dovoljno je dodati konfiguraciju u `config/sites.yml`, objaviti stvarnu prodajnu stranicu i dodati postojeći GSC service account u **novi** Search Console Domain property. Nisu potrebni novi Python bot, Render servis ili Django migracija.

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

Ostali planirani domeni: `cvecarasremskamitrovica.rs`, `cvecarasabac.rs`, opcionalno `cvecaranovapazova.rs`, `cvecaravrdnik.rs`. Ove adrese u dokumentaciji **nisu tvrdnja da su kupljene, dostupne ili aktivne**. Ne predstavljati Rumu kao fizičku poslovnicu u drugim gradovima.

## Najvažnije komande

```bash
python -m seo_monitor validate                     # Proveri YAML bez API-ja
python -m seo_monitor run --no-notify             # Pun GSC + HTTP/SEO test
python -m seo_monitor run --site indjija --skip-inspection --no-notify
python -m seo_monitor run --skip-gsc --no-notify --preview-telegram
python -m seo_monitor notify-test                  # Samo Telegram test
python -m pytest -q
ruff check seo_monitor tests
python -m compileall -q seo_monitor
```

## Gde su rezultati

- `reports/dashboard.html` — pregled svih domena, trendova i ključnih reči, bez JavaScript zavisnosti.
- `reports/telegram-preview.txt` — tačan tekst poslednjeg dnevnog Telegram izveštaja, bez tokena.
- `reports/{id}-latest.md` — GSC metrike 28d i 7d, top strane, keyword podaci, URL Inspection i tehničke provere.
- `reports/{id}-history.csv` i `{id}-rank-history.csv` — Excel-kompatibilna istorija.
- `data/{id}/YYYY-MM-DD.json` — snapshot za svaki dan, sa kontrolom integriteta pri upisu.

**Ograničenja:** GSC podaci kasne, podaci za retke upite mogu izostati, prosečna pozicija nije trenutno #1, URL Inspection nije kompletan Page indexing izveštaj, HTTP status 200 ne potvrđuje sve klijentske funkcije, HTML HTTP-check nije JS renderer. Nema automatskog SEO pisanja niti podataka o narudžbinama/konverzijama. Za pravi 24/7 SLA potrebna je nezavisna infrastruktura izvan GitHub Actions.

## Dokumentacija

- [`docs/OPERATIVNI_PRIRUCNIK_V2.md`](docs/OPERATIVNI_PRIRUCNIK_V2.md) — koraci, upozorenja i provere.
- [`docs/MIGRACIJA_V1_V2.md`](docs/MIGRACIJA_V1_V2.md) — bezbedno ažuriranje postojećeg repozitorijuma.
- [`docs/SECURITY.md`](docs/SECURITY.md) — poverljivost, token rotacija, GitHub privilegije i rizici.
- [`docs/TELEGRAM_IZVESTAJ.md`](docs/TELEGRAM_IZVESTAJ.md) — format i značenje metrika.
- [`docs/KOMPLETNO_UPUTSTVO.md`](docs/KOMPLETNO_UPUTSTVO.md) — originalna v1 dokumentacija (arhiva).
- [`docs/STRUKTURA_I_TEHNICKA_DOKUMENTACIJA.md`](docs/STRUKTURA_I_TEHNICKA_DOKUMENTACIJA.md) — izvorni opis.
- [`docs/SEO_STRATEGIJA_I_KPI.md`](docs/SEO_STRATEGIJA_I_KPI.md) — poslovni SEO KPI.

Pripremljena arhiva zasniva se na stvarno dostavljenom `lotos-seo-monitornig-main.zip`. **Nijedna produkciona integracija nije pozvana sa stvarnim tajnama tokom izrade ove verzije.**
