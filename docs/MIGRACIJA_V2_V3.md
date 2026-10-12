# Bezbedna migracija v2.0.0 → v3.0.0

## Šta se čuva

- `config/sites.yml`: postojeći Domain property-ji, Ruma/Inđija upiti i URL-ovi.
- `data/ruma/`, `data/indjija/`: dnevni JSON snimci **se ne brišu**.
- `reports/`: postojeći HTML/CSV/Markdown format ostaje; v3 dodaje nove sekcije.
- Postojeći GitHub Secrets: `SEO_GSC_SERVICE_ACCOUNT_JSON`, `SEO_TELEGRAM_BOT_TOKEN`, `SEO_TELEGRAM_CHAT_ID`.
- `seo-daily.yml`, `seo-watchdog.yml`, `telegram-test.yml`, `ci.yml` — nadograđeni, bez potrebe za novim servisima.

## Redosled instalacije (ne direktno preko produkcionog sajta)

1. Izvezi/sačuvaj postojeći GitHub repo (posebno `data/`), napravi granu `feature/seo-zero-cost-v3`.
2. Raspakuj ZIP v3 u poseban folder; kopiraj kod, `config/limits.yml`, testove i workflow fajlove. Nema potrebe menjati `config/sites.yml`.
3. Sačuvaj sve novije dnevne JSON snimke koje GitHub repo ima, a ZIP ne sadrži. Kopiranje ZIP-a ne sme obrisati postojeće snapshotove.
4. Pokreni lokalne testove i `validate` komandu.
5. Napravi PR; GitHub CI mora biti zelen pre spajanja.
6. Uradi ručni *daily* run, proveri GSC: OK za oba domena i Telegram poruku.
7. Uradi ručni *weekly* run sa `--skip-pagespeed` lokalno, pregledaj crawl izveštaje, pa (opciono) ručni GitHub weekly workflow sa PageSpeed.
8. Nakon uspešne provere uključi raspored u `seo-weekly.yml` (po default-u aktivan čim je workflow na glavnoj grani; po potrebi privremeno ukloni `schedule`).

### Lokalno (PowerShell)

```powershell
cd C:\projekti\lotos-seo-monitornig
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pytest -q
ruff check seo_monitor tests
python -m compileall -q seo_monitor
python -m seo_monitor validate --config config/sites.yml --limits config/limits.yml
python -m seo_monitor rebuild-db --output data --db local/seo_history.db
```

Za GSC testiranje lokalno, koristi privatni JSON ključ **van repoa**, preko `GOOGLE_APPLICATION_CREDENTIALS`. Nikada ne šalji ključ na GitHub niti u razgovor.

### Promene ENV / deploy

- **Nove GitHub Secrets: nijedna.**
- **Render env: nema izmena.**
- **Netlify env: nema izmena.**
- **Django migracije: nisu potrebne.**
- **Frontend build: nije potreban**, jer repo ne menja prodavnice.
- GitHub Actions: novi `seo-weekly.yml` koristi isti Telegram token i `contents: write` samo za taj workflow. `ci.yml` ima `contents: read`.

### Komande

```bash
python -m seo_monitor validate --config config/sites.yml --limits config/limits.yml
python -m seo_monitor run --skip-gsc --no-notify    # HTTP-only, bez Google kredencijala
python -m seo_monitor audit --skip-pagespeed --no-notify  # crawl, BEZ PSI poziva
python -m seo_monitor rebuild-db --db local/seo_history.db
python -m pytest -q
```

Za puni dnevni monitoring ne koristi `--skip-gsc` i obezbedi postojeći `GOOGLE_APPLICATION_CREDENTIALS` ključ. Za PageSpeed nedeljni audit izostavi `--skip-pagespeed`; anonimni PSI može biti ograničen i ne garantuje rezultate.

### Rollback

Vrati se na poslednji v2 commit u **SEO repo-u**. Zadrži sve nove `data/` snapshotove i `reports/` u backup-u. Ne koristi `git push --force`. Ne menjaj repozitorijume prodajnih sajtova.
