# Lotos SEO Monitoring Bot (enterprise-ready foundation)

Zasebna Python aplikacija za **cvecararuma.rs** i **cvecaraindjija.rs**, uz podršku za dodatne domene. Ne menja frontend, backend, Django Admin, checkout, Netlify ili postojeći katalog.

## Šta meri

- **Google Search Console API** (zvanični podaci): Web klikovi, prikazi, CTR i prosečna pozicija, tekućih i prethodnih 28 dana; izabrane ključne reči, najposećenije stranice i Search Appearance.
- **URL Inspection API**: poslednje poznato stanje odabranih URL-ova u Google indeksu; pokrivenost, robots, canonical i datum Googlebot posete (ako Google vrati podatke).
- **HTTP & SEO**: HTTPS odgovor sajtova, 5xx/4xx, homepage, izabrani putevi, `robots.txt`, `sitemap.xml`, title, H1, description, canonical, `noindex`, sintaksa JSON-LD.
- **Alerti**: nedostupna stranica, sitemap/robots problem, značajan pad prosečne pozicije samo uz dovoljan broj prikaza, nova degradacija indeksiranja i API problemi.
- **Izveštaji**: JSON snapshots, Markdown, UTF-8 CSV za Excel i statički `dashboard.html`, bez korisničkih podataka.

**Ograničenja:** GSC ne garantuje sve retke upite, broj/pozicija u API-ju nisu live SERP i zavise od perioda, uređaja i lokacije. URL Inspection API **ne omogućava live test, Indexing Request ni Validate Fix**. Bot ne lažira Google klikove i ne šalje robotske pretrage Google-u. Nema hardkodovanih lozinki.

## 1. Lokalno pokretanje

Potrebni su Python 3.11+ i instalacioni pristup PyPI-ju.

```bash
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# Linux/macOS: source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pytest -q
ruff check seo_monitor tests
```

Bez Google naloga proveri samo tehničko zdravlje (bez GSC/URL Inspection API-ja):

```bash
python -m seo_monitor run --skip-gsc --no-notify
```

Pun režim:

```bash
# PowerShell (putanja do privatnog JSON fajla lokalno)
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\\secure\\seo-gsc.json"
python -m seo_monitor run --config config/sites.yml --output data --reports reports
```

```bash
# Linux/macOS
export GOOGLE_APPLICATION_CREDENTIALS="$HOME/.config/lotos/gsc.json"
python -m seo_monitor run
```

Za jednu prodavnicu:

```bash
python -m seo_monitor run --site indjija --skip-inspection
```

Izveštaji: `reports/overview.md`, `reports/dashboard.html`, `reports/ruma-latest.md`, `reports/indjija-latest.md`, CSV fajlovi i `data/{site_id}/YYYY-MM-DD.json`.

## 2. Google Search Console API pristup

1. U Google Cloud Console napravi projekat namenjen samo ovom monitoringu.
2. Uključi **Google Search Console API** za taj projekat (Search Analytics i URL Inspection).
3. Napravi **Service Account**. Ako koristiš JSON ključ, čuvaj ga isključivo u GitHub Secrets ili lokalno, van repozitorijuma. Ako je dostupna bezbednija Workload Identity Federation, preferiraj nju uz zasebnu integraciju.
4. U Google Search Console, za **svaki domen posebno**, dodaj email Service Account-a u **Settings → Users and permissions** sa dovoljnim dozvolama da čita property podatke i URL Inspection informacije. Dodavanje servisnog naloga ne stvara novi web sajt i ne utiče na indeksiranje.
5. U `config/sites.yml` postavi `gsc_property` tačno prema stvarnom Search Console property-ju:
   - Domain property: `sc-domain:cvecararuma.rs`
   - URL-prefix property: `https://cvecararuma.rs/`
6. Testiraj ručno preko `workflow_dispatch`; proveri logs, `reports/overview.md` i snapshot fajlove.

**Nemoj** stavljati service-account JSON u Netlify, Django, frontend `NEXT_PUBLIC_*`, Git ili commit logove. Bot radi read-only preko `webmasters.readonly` OAuth scope-a.

## 3. Poseban GitHub repozitorijum — preporučeni deploy

Preporučeno ime: `lotos-seo-monitor` (privatan GitHub repozitorijum). Zaseban repo znači da nijedna promena monitora ne može redeploy-ovati prodajni Next.js ili Django servis.

1. Prenesi sadržaj ovog paketa u **koren novog repozitorijuma**.
2. Settings → Secrets and variables → Actions → **New repository secret**:
   - `SEO_GSC_SERVICE_ACCOUNT_JSON` — kompletan Google service account JSON (tajna).
   - `SEO_TELEGRAM_BOT_TOKEN` — opciono.
   - `SEO_TELEGRAM_CHAT_ID` — opciono.
3. Settings → Actions → General → Workflow permissions → omogućiti **Read and write permissions** da bi dnevni snapshot mogao da se komituje u `data/` i `reports/`. Ako postoje branch protection pravila, dozvoli odgovarajućem botu upis ili koristi zasebnu data granu.
4. Actions → **SEO Daily Monitoring** → **Run workflow**. Raspored je svakog dana u **06:17 UTC**.
5. Monitor je idempotentan po lokalnom datumu: ponovni run istog dana menja postojeći JSON i izveštaj, ne duplira zapise.
6. GitHub Actions čuva i artefakt rezultata 30 dana; Git istorija čuva dnevne JSON snimke u privatnom repozitorijumu. Vremenom uvedi arhiviranje (npr. starijih od 12 meseci) ako volumen poraste.

GitHub Actions cron može kasniti pod opterećenjem ili biti pauziran u neaktivnom repozitorijumu; za stroge SLA zahteve koristiti pouzdan scheduler.

## 4. Dodavanje novih domena

Primer za `cvecarastarpazova.rs` — **aktivirati tek kada je sajt objavljen i dodat u Search Console**:

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

Dodaj na kraj liste `sites:` u `config/sites.yml`, zatim u Search Console dodaj isti Service Account za novi property. **Nije potreban novi bot, Render servis, Django migracija ni Netlify promena.**

Predviđeni nazivi: `staramitrovica`/`sremskamitrovica`, `sabac`, `novapazova`, `vrdnik` — ID možeš odabrati, ali mora biti jedinstven. Stvarni domeni, DNS, dostupnost dostave i lokalni sadržaj proveravaju se nezavisno.

## 5. Alarm politika

- **HTTP greške i noindex:** prijavljuju se odmah.
- **Pad pozicije:** alarm tek ako su i trenutni i prethodni period imali najmanje `min_impressions_for_rank_alert` prikaza (podrazumevano 20), i ako se prosečna pozicija pogoršala za najmanje `rank_drop_alert_positions` (podrazumevano 3).
- **N/D nije nula**: kada Google ne vrati red za retku ključnu reč, ne prikazujemo lažnu poziciju 0.
- **Telegram:** slanje samo kada ima novih upozorenja ili ako `SEO_DAILY_TELEGRAM_SUMMARY=true`; bot ne skladišti podatke kupaca.
- **Upozorenja nisu dokaz uzročnosti**: promena pozicije može nastati zbog lokacije, konkurencije, ponašanja pretrage, promene datuma itd.

## 6. Bezbednosna i SEO ograničenja

- Konfiguracija dozvoljava samo HTTPS hostove i relativne putanje; HTTP monitoring ne prati redirect na drugi host.
- Ograničava se preuzimanje odgovora na 2 MB i broj testiranih URL-ova po domenu, kako se ne bi opterećivali produkcioni sajtovi.
- HTTP/SEO provera nije zamena za Lighthouse, mobilni UX ili proveru Checkout toka. Ne šalje test porudžbine.
- Izveštaj može otkriti interne URL-ove pa **GitHub repozitorijum držati privatnim**.
- Izbegavati nenamerne SEO regresije: za `cvecararuma.rs` nema automatskih izmena, a buduća implementacija treba da prođe postojeće Ruma regression testove.

## 7. Testovi

```bash
python -m pytest -q
ruff check seo_monitor tests
python -m compileall -q seo_monitor
```

Nema izmene postojećeg repozitorijuma, pa nisu potrebne Django migracije, Render/Netlify deploy ili frontend build za ovaj nezavisni paket. Kada se bot kasnije integriše direktno u postojeći repozitorijum, obavezno ponoviti punu postojeću Django/Next.js CI kontrolu.

## Relevantna Google dokumentacija

- [Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- [URL Inspection API](https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect)
- [Search Console API reference](https://developers.google.com/webmaster-tools/v1/api_reference_index)

## Kompletna dokumentacija na srpskom

- **[KOMPLETNO UPUTSTVO](docs/KOMPLETNO_UPUTSTVO.md)** — funkcije, koristi, Windows instalacija, Google Cloud, Google Search Console dozvole, GitHub Actions, Telegram, dodavanje domena, troubleshooting i testovi.
- **[STRUKTURA I TEHNIČKA DOKUMENTACIJA](docs/STRUKTURA_I_TEHNICKA_DOKUMENTACIJA.md)** — moduli, API ugovori, izlazni podaci, bezbednost i error kodovi.
- **[SEO STRATEGIJA I KPI](docs/SEO_STRATEGIJA_I_KPI.md)** — Ruma, Inđija, budući regionalni domeni, SEO metrike, alarmi i radni proces.

Posle svakog pokretanja nastaju i `reports/{site_id}-history.csv` (dnevni trend ukupnih GSC metrika) i `reports/{site_id}-rank-history.csv` (trend pozicija odabranih ključnih reči). Istorijski CSV čita prethodne JSON snapshotove iz `data/` i ne zahteva novu bazu podataka.

**Napomena o verifikaciji:** offline testovi i sintaksa mogu se proveriti u dostavljenom paketu; bez pristupa privatnim Google, GitHub i Telegram kredencijalima nije moguće tvrditi da je monitoring već uspešno povezan sa produkcionim Search Console nalozima.
