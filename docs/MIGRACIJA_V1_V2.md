# Bezbedna migracija — v1 → v2

## Preduslovi

- Pristup privatnom GitHub repozitorijumu `darkotosic/lotos-seo-monitornig`.
- Tri postojeća Repository Secrets; vrednosti se **ne preuzimaju i ne prenose** u ZIP:
  `SEO_GSC_SERVICE_ACCOUNT_JSON`, `SEO_TELEGRAM_BOT_TOKEN`, `SEO_TELEGRAM_CHAT_ID`.
- Service account i dalje ima Full pristup Search Console Domain properties za Rumu i Inđiju.
- API `searchconsole.googleapis.com` je uključen u Cloud projektu.

## GitHub deploy (preporuka: PR)

1. Napravi backup/branch trenutnog `main` i preuzmi aktuelne `data/` i `reports/` iz GitHub-a.
2. Otpakuj novi v2 ZIP u privremeni direktorijum.
3. Kopiraj v2 kod, `.github/workflows/`, `tests/`, `docs/`, `pyproject.toml`, `README.md`, `RELEASE_NOTES.md` i `config/sites.yml` u radnu granu.
4. **Ne briši postojeće `data/` snapshotove koji su noviji od kopije iz ZIP-a.** Reši eventualni konflikt na `reports/` u korist aktuelnih podataka; sačuvani snapshoti imaju prioritet.
5. `python -m pip install -e ".[dev]"`; `python -m pytest -q`; `ruff check seo_monitor tests`; `python -m seo_monitor validate`.
6. Napravi pull request i potvrdi da `Monitor CI` prolazi. Spoji promene u `main`.
7. GitHub → Actions → `SEO Daily Monitoring` → `Run workflow`.
8. Pregledaj `Check GSC, HTTP, SEO and index status` i `Upload reports` korake. U logu očekuj `GSC: OK` za Rumu i Inđiju.
9. U GitHub reports preuzmi `telegram-preview.txt`, `dashboard.html` i Markdown izveštaje. Proveri stvarne rezultate i URL Inspection uzorak.
10. Telegram kanal treba da dobije **detaljan dnevni izveštaj**, ne samo „Bez novih upozorenja“.

## GitHub Secrets / ENV

**Nema novih tajni.** Workflow varijable:

- `GOOGLE_APPLICATION_CREDENTIALS` se pravi privremeno iz GitHub Secret-a na runner-u; nije deo frontend-a.
- `TELEGRAM_BOT_TOKEN` i `TELEGRAM_CHAT_ID` dobijaju vrednosti iz ranijih `SEO_TELEGRAM_*` secrets.
- `SEO_DAILY_TELEGRAM_SUMMARY` je već postavljen na `'true'` u `.github/workflows/seo-daily.yml`.
- `GITHUB_REPOSITORY` i `GH_MONITOR_TOKEN` za Watchdog se dobijaju iz samog GitHub Actions (`github.repository`, `github.token`), bez nove tajne.

GitHub Repository → Settings → Actions → General → default **Read** dozvole su preporučene; `seo-daily.yml` ima eksplicitno `permissions: contents: write` za podatke. Ako `main` ima branch protection, nemoj ga isključivati radi monitora; koristi PR / zasebnu data granu uz prilagođavanje workflow-a.

## Rollback

Ako se v2 ponaša pogrešno, vrati prethodni commit koda iz backup grane. Ne uklanjaj poslednje tačne `data/{site}/YYYY-MM-DD.json` snimke i ne briši Secrets. Nikakav Django/Next.js rollback nije potreban.

## Zašto se podaci razlikuju od Google UI-ja

GSC API meri finalizovane podatke, sa 3 dana zakašnjenja. Pozicija je prosek u periodu, ne trenutni Google rezultat. Privatno filtrirani upiti možda nisu vraćeni. URL Inspection proverava samo konfigurisan podskup, ne ukupan broj indeksiranih stranica.
