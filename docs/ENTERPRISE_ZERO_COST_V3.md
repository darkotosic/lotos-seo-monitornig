# LOTOS SEO INTELLIGENCE v3.0 — ENTERPRISE ZERO-COST

## Garancije i granice

- Ovaj repozitorijum **ne kreira Google Cloud resurse i ne poziva plaćene servise** (BigQuery, Vertex AI, Cloud Vision, Cloud Functions, Scheduler, Cloud CDN/Storage).
- Uključen je **Google Search Console API** (Search Analytics i URL Inspection); korisnik sam aktivira besplatan API i dodaje service account na svaki GSC property. Nema obrade privatnih podataka kupaca.
- Nedeljni PageSpeed koristi javni/keyless REST API; ako zahteva ključ, vrati 403/429 ili premaši limit odgovora, rezultat je **N/D**, bez zaobilaženja kvota i plaćenog rezervnog načina. Mobilni i desktop *lab* nisu isto što i CrUX/field vrednosti.
- Lokalni crawler poštuje robots.txt, dozvoljava isključivo isti HTTPS host i ima stroga ograničenja URL-ova, sitemap fajlova i veličine odgovora. Ne pristupa checkout-u i ne šalje narudžbine.
- Nema „instant indeksiranja proizvoda“: Google Indexing API nije namenjen običnom e-commerce sadržaju. Nema automatskog `Request indexing`, niti obećanja Top 1 rangiranja.
- SQLite baza (`local/*.db`) pravi se lokalno i **ne komituje** u Git; JSON istorija ostaje izvor istine.

**Važno:** Nulta *dodatna* cena se ne može garantovati samo Python kodom ako su na GitHub/GCP nalogu uključeni plaćeni paketi ili automatska naplata nakon kvote. U GitHub Billing & licensing eksplicitno postavi Actions budžet i **Stop usage when budget limit is reached**; prati deljenu kvotu naloga i ne uključuj plaćene GCP proizvode. Repo ne naplaćuje ništa, ali ne upravlja pravilima naplate korisničkog naloga. Domeni, Netlify i Render su nezavisni troškovi postojeće prodavnice.

## Cost Guard — konfiguracija

`config/limits.yml` definiše isključivo `free_only` i limite (validirane bez mogućnosti njihove neograničene eskalacije):

| Kategorija | Po domenu | Podrazumevana granica |
|---|---|---:|
| GSC Search Analytics | dnevni monitoring | 40 logičkih API poziva |
| URL Inspection | dnevni monitoring | 8 URL-ova |
| Sitemap datoteke | nedeljni audit | 3 |
| HTML stranice | nedeljni audit | 80 |
| PageSpeed | nedeljni audit | 4 (2 URL-a × mobilni/desktop) |
| Slike — mrežna provera | rezervisan limit, v3 vrši samo HTML meta audit | 12 |
| Veličina jednog HTTP odgovora | mrežna provera | 2 MB |
| Aktivni domeni | svi | 20 |

`CostGuard.consume(category)` mora se izvršiti **pre** izlaznog poziva. Dostignuta kvota prekida pojedinačnu opcionu proveru pre slanja zahteva. GSC upiti koje nije bilo moguće proveriti označavaju se sa `status: quota_skipped` i N/D. Ako je obavezni provajder nedostupan, dnevni workflow završava neuspešno da se ne bi prikazivao lažni uspeh.

**Napomena:** Limiti su naši unutrašnji limiti, ne zvanične Google kvote. Retries Search Console API-ja mogu predstavljati više HTTP pokušaja za jedan logički poziv. Svi korišćeni izvori ostaju besplatni API-ji, uz ograničenja pristupa/kvota.

## Šta radi v3

1. GSC: ukupne dnevno osvežene 28-dnevne i nedeljne metrike, praćene reči, do 250 dodatnih upita, uređaji, zemlje, image-search agregat, top stranice, Search appearance, URL Inspection uzorak.
2. Local crawler: sitemap XML i ograničeni sitemap-index, robots.txt, HTTP status, canonical, H1 u serverskom HTML-u, title/description, JSON-LD sintaksa, interni linkovi i broj slika bez alt atributa.
3. SEO recommendations: deterministička pravila sa dokazima (pozicija, CTR, prikazi); zadaci su predlozi za **ljudsku proveru**, ne auto deploy.
4. PageSpeed: jednom nedeljno za `/` i `/proizvodi`, mobile/desktop; greške i nedostupni field podaci su jasno vidljivi.
5. Dnevni i nedeljni Telegram izveštaji; nezavisan v2 watchdog ostaje aktivan.
6. `rebuild-db`: lokalni SQLite pregled obnovljiv iz dnevnih JSON snapshotova.
7. Multi-domain: svaki domen je nezavisno podešen u `config/sites.yml` i koristi postojeće GitHub Secrets.

## Preciznost rezultata

- `position` je Google Search Console **prosečna** pozicija za istorijski period, ne trenutni SERP rank.
- GSC sakriva neke retke upite zbog privatnosti; zbir prikaza po upitima ne mora biti jednak ukupnim prikazima.
- `N/D` znači odsustvo pouzdanog podatka, a ne nulu, pad ili grešku indeksa.
- Status URL Inspection potiče iz Google indeksa i nije live test.
- Kandidat za orphan link je samo URL bez ulaznog linka u *ograničenom uzorku* crawl-a.
- Stranice zasnovane na React hydration-u mogu imati `Učitavanje...` u početnom HTML-u; to je signal za proveru renderovanja, ne automatska greška Google indeksiranja.
- Recenzije, ocene, politika povraćaja i rokovi dostave se **ne izmišljaju** radi nestanka GSC upozorenja.

## Privatnost i produkciona izolacija

Repo ne menja `cvecararuma.rs`, `cvecaraindjija.rs`, Django, Netlify, checkout ili Admin. Fizička cvećara je u Rumi; lokalizovani domeni ne smeju tvrditi da postoji nepostojeća fizička poslovnica. GSC JSON i Telegram tokeni ostaju samo u GitHub Secrets; repo ostaje privatan.

## Sledeći moduli koji nisu automatski aktivirani

`seo_monitor/ga4.py`: read-only agregirani GA4 podaci. Zahteva GA4 property sa dozvolom Viewer i uključenu odgovarajuću Google API uslugu. Nije deo rasporeda, ne koristi PII i ne smatra `keyEvents` potvrđenim uplatama. Ako ga ne želiš, ne podešavaš ništa.
