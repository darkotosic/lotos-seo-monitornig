# LOTOS SEO MONITOR — KOMPLETNO UPUTSTVO

**Verzija:** 1.0.0  
**Domeni pri isporuci:** `cvecararuma.rs`, `cvecaraindjija.rs`  
**Namena:** automatizovan, samo-za-čitanje SEO monitoring za regionalnu mrežu Cvećare Lotos.  
**Status:** kod i lokalni automatizovani testovi provereni; pristup stvarnom Google Search Console nalogu, produkcioni GitHub Actions i Telegram isporuka **nisu** provereni, jer nisu dostupni kredencijali.

## 1. Šta sistem radi

**Google Search Console:** čita zvanične Google Web Search rezultate za dva uzastopna perioda od po 28 dana (podrazumevano), sa odmakom od 3 dana radi stabilnijih podataka. Prati ukupne organske klikove, prikaze, CTR, prosečnu poziciju; izabrane ključne reči; vodeće URL-ove po klikovima; Search Appearance (npr. Product snippets kada je dostupno).

**Google URL Inspection API:** za odabrane URL-ove čita poslednje Google-u poznato stanje indeksiranja, coverage, robote, vreme poslednjeg Googlebot crawla i canonical, kada API te podatke vrati. Ne radi Google *Live Test*, ne indeksira sam URL-ove i ne klikće `Validate Fix`.

**Tehnički monitoring:** svakodnevno proverava odabrane HTTPS URL-ove, `sitemap.xml`, `robots.txt`, HTTP 4xx/5xx i dostupnost, HTML title, opis, H1, canonical, `noindex` i ispravnost JSON-LD sintakse. Slike kao `/twitter-image` ne tumači kao HTML.

**Upozorenja:** greške dostupnosti, blokirano indeksiranje, problem robots/sitemap, pad prosečne pozicije na dovoljno prikazivanoj ključnoj reči, upozorenja iz URL Inspection i nedostupnost GSC API-ja. Po izboru šalje Telegram poruke za *nova* upozorenja.

**Izveštaji i istorija:** lokalni JSON snapshot po domenu i danu, Markdown po domenu, pregled svih domena, Excel-kompatibilni CSV za ključne reči, dnevnu istoriju i istoriju pozicija, kao i HTML dashboard koji se otvara u browseru.

**Ne radi:** ne generiše lažne posete, ne otvara Google pretrage preko VPN-a, ne garantuje pozicije, ne menja SEO automatski, ne šalje narudžbine i ne pristupa podacima kupaca.

## 2. Prednosti

1. **Jedinstven pogled na više gradova.** Ruma, Inđija i budući gradovi u jednom dnevnom izveštaju, bez mešanja GSC podataka.
2. **Čuvanje SEO rezultata.** Pad na relevantnoj ključnoj reči može da se otkrije uz zaštitu od alarmiranja na 1–2 prikaza.
3. **Rano otkrivanje tehničkih grešaka.** HTTP 500, nestanak `sitemap.xml`, `noindex`, problem canonical ili neuspešan JSON-LD može da se otkrije pre naredne ručne provere.
4. **Praćenje rasta.** CSV istorija omogućava poređenja kroz mesece; GSC prosečna pozicija nije garantovana trenutna pozicija u Google SERP-u.
5. **Minimalni trošak infrastrukture.** Predviđen GitHub Actions schedule; ne zahteva poseban Render servis ni izmenu Netlify frontendova. Troškovi i ograničenja zavise od GitHub plana/kvota.
6. **Bez rizika po checkout.** Samo čita javne stranice i read-only GSC API; ne menja Django modele, proizvode, status narudžbina ni plaćanje.
7. **Skaliranje.** Novi grad dodaje se samo u YAML konfiguraciju i dodeljuje se odgovarajući GSC pristup.

## 3. Arhitektura

```text
GitHub Actions (svaki dan u 06:17 UTC, ručni start moguć)
          |
          v
  Python CLI  seo_monitor/cli.py
          |
          +--> config/sites.yml --> domeni / ključne reči / URL-ovi
          |
          +--> Google Search Console API (read-only)
          |        +--> Search Analytics
          |        +--> URL Inspection (indeksno stanje)
          |
          +--> HTTPS GET (samo na konfigurisanom hostu)
          |        +--> stranice / twitter-image
          |        +--> robots.txt / sitemap.xml
          |
          +--> pravila alarmiranja
          |        +--> opcioni Telegram
          |
          +--> data/<domen-id>/<datum>.json
          +--> reports/*.md / *.csv / dashboard.html
          +--> privatna GitHub istorija + 30-dnevni Actions artifacts
```

GitHub Actions workflow koristi `contents: write` da bi sačuvao istoriju u **privatnom repozitorijumu**. Za strože organizacione zahteve, prebaciti istoriju u namenski storage i isključiti Git push korak. Bot nema administratorski API ka Django backendu.

## 4. Zahtevi

- Python **3.11 ili noviji** (preporuka: 3.12)
- Git i opcionalno GitHub nalog sa privatnim repozitorijumom
- Google Cloud projekat sa uključenim **Google Search Console API**
- Google Service Account kojem je dat pristup Search Console property-ju za **svaki domen**
- Internet za pristup Google API-ju i domenima
- Opciono: Telegram bot token i chat ID

## 5. Instalacija — Windows / PowerShell

Raspakuj paket; u PowerShell-u otvori njegov folder:

```powershell
cd C:\projekti\lotos-seo-monitor
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest -q
ruff check seo_monitor tests
```

Ako PowerShell odbija aktivaciju virtualnog okruženja, bez izmene sistemskih politika koristi direktno `\.venv\Scripts\python.exe -m pip install -e ".[dev]"` i `\.venv\Scripts\python.exe -m pytest -q`.

**Prvi rad bez Google API-ja** (HTTP/SEO provere):

```powershell
python -m seo_monitor run --skip-gsc --no-notify
```

Rezultati se stvaraju u `reports/` i `data/`. Otvori `reports/dashboard.html`. Nedostajuće Google metrike označene su `N/D`, nikad izmišljenim brojevima.

## 6. Google Cloud i Search Console: korak po korak

1. Otvori [Google Cloud Console](https://console.cloud.google.com/) i izaberi ili napravi zaseban projekat, npr. **Lotos SEO Monitor**.
2. Idi na **APIs & Services → Library**, pronađi i omogući **Google Search Console API**.
3. Idi na **IAM & Admin → Service Accounts**, napravi nalog, npr. `lotos-seo-monitor`.
4. Sačuvaj njegovu email adresu (format `ime@projekat.iam.gserviceaccount.com`).
5. Za jednostavan početak: **Keys → Add key → Create new key → JSON**. Preuzeti ključ čuvaj u privatnom folderu izvan Git repozitorijuma. Ako organizacija podržava Workload Identity Federation, to je poželjnije dugoročno rešenje koje ne zahteva stalni JSON ključ; ovaj paket je isporučen sa JSON autentikacijom.
6. Otvori [Google Search Console](https://search.google.com/search-console), izaberi **cvecararuma.rs** property, zatim **Settings → Users and permissions → Add user**. Dodaj email Service Account-a sa pristupom dovoljnim za Search Analytics i URL Inspection (preporuka Full user). Ponovi za **cvecaraindjija.rs**.
7. U `config/sites.yml` proveri `gsc_property`. Za **Domain property** tačan format je `sc-domain:cvecararuma.rs`; za **URL-prefix property** je `https://cvecararuma.rs/`. Format mora odgovarati property-ju kojem Google nalog zaista ima pristup.
8. Sačekaj da se dozvole propagiraju; testiraj lokalno ili GitHub `workflow_dispatch`.

**Lokalni test sa Google API-jem:**

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\secure\lotos-seo-service-account.json"
python -m seo_monitor run --config config/sites.yml --output data --reports reports --no-notify
```

**Nikada ne kopiraj JSON ključ u `NEXT_PUBLIC_*`, frontend, Netlify environment, Django Admin, commit ili javni GitHub issue.** Service Account JSON može omogućiti pristup domenima; tretiraj ga kao lozinku.

## 7. GitHub repozitorijum — preporučena automatizacija

1. Napravi **nov, prazan i privatan** GitHub repo, npr. `lotos-seo-monitor`.
2. U njega raspakuj kompletan sadržaj ZIP paketa (folder `.github` mora ostati uključen).
3. Iz korena lokalnog foldera izvrši:

```powershell
git init
git add .
git commit -m "Initial Lotos SEO monitoring bot"
git branch -M main
git remote add origin https://github.com/TVOJ_GITHUB_NALOG/lotos-seo-monitor.git
git push -u origin main
```

Ako GitHub repo već ima README/commit, nemoj naslepo prepisivati istoriju; povuci postojeći branch ili otvori prazan repo.

4. U GitHub-u idi u **Settings → Secrets and variables → Actions** i napravi `SEO_GSC_SERVICE_ACCOUNT_JSON` sa **celim** sadržajem Google service-account JSON fajla.
5. Opciono dodaj `SEO_TELEGRAM_BOT_TOKEN` i `SEO_TELEGRAM_CHAT_ID`. Ovi tokeni nisu potrebni za osnovni monitoring.
6. U **Settings → Actions → General** obezbedi da workflow ima prava upisa u repozitorijum (`Read and write permissions`) ili prilagodi branch policy. Workflow pokušava da komituje istoriju u `data/` i `reports/`.
7. U tabu **Actions → SEO Daily Monitoring → Run workflow** pokreni prvi ručni run. Proveri da su koraci zeleni, u `reports/overview.md` postoje GSC podaci, a u `reports/dashboard.html` kartice domena.
8. Scheduler radi **svakog dana u 06:17 UTC**, što je približno 08:17 leti ili 07:17 zimi u Srbiji. GitHub može odložiti cron izvršavanje; nije hard real-time SLA.

Ako je prvi run crven, pogledaj `Actions → konkretan run → Check GSC, HTTP, SEO and index status` i odeljak **Problemi** ispod.

## 8. Kako čitati izveštaje

| Fajl | Namena |
|---|---|
| `reports/overview.md` | uporedni pregled svih domena |
| `reports/dashboard.html` | offline HTML dashboard sa karticama domena |
| `reports/ruma-latest.md` | detaljan dnevni izveštaj za Rumu |
| `reports/indjija-latest.md` | detaljan dnevni izveštaj za Inđiju |
| `reports/ruma-keywords.csv` | ključne reči i poređenje dva perioda |
| `reports/ruma-history.csv` | dnevna istorija ukupnih metrika |
| `reports/ruma-rank-history.csv` | dnevna istorija pozicija konfigurisanih upita |
| `data/ruma/YYYY-MM-DD.json` | sirovi dnevni snapshot sa datumom |

Analogni fajlovi nastaju za svaki drugi site ID. CSV je kodiran kao UTF-8 BOM radi lakšeg otvaranja u Excel-u.

**Objašnjenje metrika:**

- *Klikovi:* klikovi iz Google Web pretrage koje prijavljuje GSC.
- *Prikazi:* broj pojavljivanja rezultata, nije broj različitih ljudi.
- *CTR:* odnos klikova i prikaza; nizak CTR nije sam po sebi dokaz lošeg title-a.
- *Prosečna pozicija:* agregirana pozicija; nije uvek ista kao trenutni Google rezultat koji vidiš na svom računaru.
- *N/D:* Google nije vratio podatak, nije isto što i 0.
- *Google indeks status:* najnoviji indeksni podaci dostupni URL Inspection API-ju, a ne trenutna live dostupnost.

## 9. Upozorenja i pragovi

U `config/sites.yml`:

```yaml
settings:
  window_days: 28
  reporting_lag_days: 3
  request_timeout_seconds: 15
  min_impressions_for_rank_alert: 20
  rank_drop_alert_positions: 3
```

Za alarm o padu pozicije, i tekući i prethodni 28-dnevni period moraju imati **najmanje 20 prikaza** za ključnu reč; prosečna pozicija mora se pogoršati za **3 ili više**. Primer: 2,5 → 6,2 uz dovoljan uzorak aktivira upozorenje. Promene u uzorku od 1–2 prikaza se ne tretiraju kao pouzdan signal.

HTTP greške, `noindex`, problem u `robots.txt`/`sitemap.xml` i problem sa API-jem odmah su prikazani u izveštaju. Telegram, kada je konfigurisan, podrazumevano šalje samo *nova* upozorenja u odnosu na prethodni snapshot. Za dnevni Telegram rezime promeni `SEO_DAILY_TELEGRAM_SUMMARY` na `true` u GitHub workflow okruženju.

**Nema garancije** da će alarm objasniti uzrok pada; pozicije zavise od lokacije, upita, drugih sajtova, uređaja i Google-ovih promena.

## 10. Dodavanje novih domena

**Pravilo:** novi domen se uključuje tek kada DNS/HTTPS radi, stvarna dostava je organizovana, sajt postoji i ima sopstveni GSC property.

Primer za **Staru Pazovu** — dodaj pod `sites:` u `config/sites.yml`:

```yaml
  - id: starapazova
    enabled: true
    name: "Cvećara Stara Pazova — Lotos"
    base_url: "https://cvecarastarpazova.rs"
    gsc_property: "sc-domain:cvecarastarpazova.rs"
    keywords:
      - "cvecara stara pazova"
      - "cvećara stara pazova"
      - "dostava cveca stara pazova"
      - "buketi stara pazova"
    check_paths:
      - "/"
      - "/kategorije"
      - "/dostava"
      - "/kontakt"
    inspect_paths:
      - "/"
      - "/kategorije"
```

Zatim dodaj Service Account u Search Console property za novi domen, testiraj:

```powershell
python -m seo_monitor run --site starapazova --skip-gsc --no-notify
python -m seo_monitor run --site starapazova --no-notify
python -m pytest -q
```

Za Sremsku Mitrovicu, Šabac, Novu Pazovu i Vrdnik isti postupak, sa jedinstvenim `id`, tačnim domenom i lokalnim ključnim rečima. **Nije potrebna migracija Django baze niti izmena postojećeg frontend repozitorijuma.** Bot ne pravi nove prodavnice — samo prati već postojeće.

## 11. Bezbednost i uticaj na produkciju

- Google API ima samo OAuth `webmasters.readonly` scope.
- Mrežne provere su HTTPS GET, na konfigurisanom hostu; redirect na drugi host se blokira.
- Svaki odgovor je ograničen na 2 MB; broj proveravanih putanja je ograničen po domenu.
- Nema pristupa kupcima, porudžbinama, plaćanjima, OpenAI ključu ili Django Adminu.
- Telegram bot šalje samo SEO upozorenja, bez korisničkih podataka.
- Kreirani izveštaji mogu sadržati interne URL-ove; repozitorijum treba da bude privatan.
- Ne koristi generisanje lažnih recenzija, lažne lokalne adrese, automatske Google klikove ili manipulaciju CTR-om.
- Monitoring je **read-only**, tako da ne menja Rumu, Inđiju niti buduće storefrontove.

## 12. Troubleshooting / česte greške

**`Missing SEO_GSC_SERVICE_ACCOUNT_JSON repository secret`:** u GitHub Secrets nije dodat kompletan servisni JSON ključ.

**`Google authentication/init failed`:** proveri putanju `GOOGLE_APPLICATION_CREDENTIALS`, JSON format, validnost ključa i da li je API uključen.

**`Search Console API failed`:** proveri Service Account pristup svakom property-ju, format `gsc_property`, kvote Google API-ja i internet konekciju. Pogrešan property nije isto što i pogrešan domen sajta.

**`Index inspection: ... Inspection unavailable`:** nekim URL-ovima Google nije vratio indeksni status ili nalog nema odgovarajuća prava; proveri URL Inspection u Search Console i API pristup. Ovo ne dokazuje da je URL pokvaren.

**`HTTP monitoring failed` / `ReadTimeout`:** proveri HTTPS dostupnost i response time. Moguća je privremena mrežna greška GitHub runner-a; ponovi jednom nakon dijagnostike.

**`URL outside configured HTTPS host`:** kontrolisani URL preusmerava na drugi host (npr. `www.`). Uskladi `base_url` sa stvarnim produkcionim canonical hostom ili dokumentuj redirect; ne isključuj zaštitu bez revizije.

**`Canonical points to a different page/domain`:** proveri server-renderovan `<link rel="canonical">`. Kod regionalnih sajtova mora da pokazuje očekivanu lokalizovanu URL adresu, ako je stranica namenjena samostalnom indeksiranju.

**`No GSC data` / `N/D`:** moguće je da je property nov, da je prijavljeno premalo pretraga, da su podaci anonimizovani ili credentials nisu povezani. Ne prikazuj nedostajuće podatke kao nulu.

**`git push` neuspešan u Actions:** proveri workflow `contents: write`, Actions permissions i branch protection. Monitoring se može izvršiti i kad snimanje istorije nije dozvoljeno, a artefakt ostaje dostupan ako je upload uspeo.

**Nepravilni znakovi u Excel-u:** otvori CSV kao UTF-8; fajlovi su zapisani sa BOM.

## 13. QA pre produkcionog pokretanja

```powershell
python -m pytest -q
ruff check seo_monitor tests
python -m compileall -q seo_monitor
python -m seo_monitor run --skip-gsc --no-notify
```

Zatim nakon povezivanja GSC naloga izvrši pun run i potvrdi:

- oba domena imaju nenulte ili opravdano `N/D` GSC podatke;
- nema autentikacionih/API grešaka;
- report za svaki domen koristi odgovarajući Google property;
- proverene URL putanje su stvarne i ne proizvode lažne 404 alarme;
- HTTP robots/sitemap provere rade;
- Telegram test stigne, ako je uključen;
- GitHub workflow završava uspešno, a dnevni snapshot se čuva u privatnom repozitorijumu.

## 14. Ograničenja i sledeći mogući moduli

Trenutna verzija **ne** meri PageSpeed/Lighthouse automatski, ne prikuplja GA4 konverzije, ne broji porudžbine, ne šalje indeksne zahteve, ne prati Google Maps pozicije i ne procenjuje direktno poziciju konkurenta. Za to su potrebni odvojeni API-ji, dozvole i po potrebi dodatni modul.

Moguće naredne funkcije: GA4 analiza konverzija bez privatnih podataka, PageSpeed Insights API, email/dnevni rezime, arhiviranje starijih snapshotova, read-only dashboard na privatnom hostingu i kontrolisano praćenje 5xx događaja.

## 15. Referentna dokumentacija

- [Google Search Console Search Analytics API](https://developers.google.com/webmaster-tools/v1/searchanalytics/query)
- [Google URL Inspection API](https://developers.google.com/webmaster-tools/v1/urlInspection.index/inspect)
- [Google Search Console API reference](https://developers.google.com/webmaster-tools/v1/api_reference_index)
- [GitHub Actions schedule](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule)
- [Google Search Console permissions](https://support.google.com/webmasters/answer/7687615)

---

**Bitno:** ovaj projekat je isporučen kao samostalan ZIP repozitorijum. Nijedan Google nalog, GitHub repo ili Telegram bot nisu automatski povezani tokom kreiranja ovog paketa. Pravljenje novog privatnog repo-a i unos kredencijala su ručni koraci korisnika.
