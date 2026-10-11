# Tehnička dokumentacija — Lotos SEO Monitor

## Struktura projekta

```text
lotos-seo-monitor/
├─ .github/workflows/
│  ├─ ci.yml                  # provera testa i lint-a na push/PR
│  └─ seo-daily.yml           # zakazani/rucni dnevni monitoring
├─ config/sites.yml           # domeni, ključne reči i pragovi
├─ docs/
│  ├─ KOMPLETNO_UPUTSTVO.md
│  └─ STRUKTURA_I_TEHNICKA_DOKUMENTACIJA.md
├─ seo_monitor/
│  ├─ __init__.py
│  ├─ __main__.py
│  ├─ cli.py                  # CLI, orkestracija, dnevni snimci
│  ├─ config.py               # validacija konfiguracije
│  ├─ gsc.py                  # OAuth i GSC API, samo čitanje
│  ├─ checks.py               # HTTPS, robots, sitemap, SSR metadata
│  ├─ report.py               # alarmiranje, Markdown, HTML, CSV
│  └─ notify.py               # opcioni Telegram
├─ data/.gitkeep              # JSON istorija nastaje nakon run-a
├─ reports/.gitkeep           # dashboard, report i CSV nastaju nakon run-a
├─ tests/                     # automatizovani offline testovi
├─ pyproject.toml             # instalacija i zavisnosti
├─ .gitignore
└─ README.md
```

## Programski ugovori

### `config.py`

`load_config(Path)` vraća `(Settings, list[Site])`. Odbija: ne-HTTPS URL, host sa portom ili korisničkim kredencijalima, nepravilnu GSC property adresu, nekontrolisane putanje poput `//evil.example/`, prevelike liste, duple ID-ove. Aktivni domenski ID je alfanumerički niz sa `_` ili `-`.

`Site.url(path)` daje potpun URL unutar konfigurisanog domena, za `/` dodaje završnu kosu crtu.

### `gsc.py`

`GoogleSearchConsole(credentials_file)` koristi Google servisni nalog sa `https://www.googleapis.com/auth/webmasters.readonly` scope-om. `query()` poziva `searchanalytics.query`, `inspect()` poziva `urlInspection.index.inspect`.

`collect_gsc()` koristi finalizovane web podatke (`dataState=final`, `type=web`), dva nepoklapajuća perioda: trenutnih 28 dana (do T-3) i prethodnih 28 dana. Za svaku ključnu reč primenjuje `query equals` i čita metrike. Vraća Top 200 stranica po API redosledu i do 100 Search Appearance tipova. URL Inspection se poziva samo za izabrane putanje, sa izolacijom greške po URL-u.

**Nijedan API ne vraća univerzalnu live Google poziciju za svaki grad i uređaj.**

### `checks.py`

`collect_checks(site, settings)` koristi GET provere na nekoliko javnih URL-ova. `httpx` stream onemogućava preuzimanje više od 2 MB po odgovoru. Redirekcije se ručno validiraju i smeju ostati samo na istom HTTPS hostu. Robots se analizira kroz `RobotFileParser`; sitemap XML kroz `defusedxml`.

HTML analiza izvuče prvi H1, title, meta description, canonical, noindex i listu tipova JSON-LD objekata. **Ne proverava semantičku ispravnost Google Merchant rich rezultata**, već samo sintaksu JSON-LD i osnovni SEO signal.

### `report.py`

`assess()` vraća alarmne stringove sa minimalnim pragom prikaza. `opportunities()` predlaže *kandidate za ručnu proveru*, a ne automatske izmene. `markdown()`, `csv_keywords()`, `csv_history()`, `dashboard()` stvaraju izlazne fajlove. Snapshot istog lokalnog dana se prepisuje, pa nema dupliranih zapisa po datumu.

### `notify.py`

Telegram šalje poruku korišćenjem `sendMessage` endpoint-a, samo kada postoje novi alarmi ili je dozvoljen dnevni rezime. Token je samo environment varijabla, nikad u repo fajlu. Ne postoji Telegram webhook niti mogućnost dolaznih naredbi.

## Exit kodovi

- `0`: monitoring završen bez kritičnih HTTP ili API grešaka. Pojedina SEO upozorenja (npr. canonical) mogu biti prijavljena i bez rušenja komande.
- `2`: kritična HTTP/robots/sitemap/API greška otkrivena. Report fajlovi se i dalje generišu kad je moguće.
- Ostali exit kodovi mogu nastati pre monitoringa usled greške konfiguracije, instalacije ili sintakse CLI-ja.

## Bezbednosne granice

Bot je read-only i ne zahteva Django/Netlify pristup. Ni GitHub Actions ni lokalni program ne smeju se pokretati sa poverljivim ključevima unutar frontend build varijabli. Ako se repo podeli sa saradnicima, istorija može otkriti interne URL-ove i SEO planove; preferiraj private visibility i kontrolu prava.

## Testovi

Test paket sadrži imitacije HTTP transporta i GSC API-ja, tako da radi bez mreže i tajni. Pokriva URL validaciju, zabranu cross-host redirect-a, HTML/JSON-LD analizu, `noindex`, sitemap/robots, generisanje izveštaja, poređenje pozicija i error exit. Pre merge u produkcioni repo: `python -m pytest -q`, `ruff check seo_monitor tests`.

## Deploy strategija

Ne uvoditi bot u Next.js i Django deploy pipeline dok za to ne postoji jasan razlog. Održavati ga u posebnom GitHub repo-u; start `workflow_dispatch` i cron; omogućiti privatno čuvanje istorije. Budući sajtovi se dodaju preko `config/sites.yml`, bez promene Python modula.
