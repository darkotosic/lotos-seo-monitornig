# Lotos SEO Monitor — Bezbednosna politika

## Tajne

- Google JSON Service Account nikada u Git, ZIP, `.env`, `data/`, `reports/`, Netlify `NEXT_PUBLIC_*`, browser ili Telegram poruke.
- Sva tri GitHub Secrets čuvati u Repository Secrets. Daily workflow zapisuje JSON u `${{ runner.temp }}` sa pravima `0600` i briše fajl u koraku `Cleanup private credentials`.
- Telegram token objavljen u razgovoru smatra se kompromitovanim. Rotirati ga preko BotFather i ažurirati **sve** zavisne sisteme koji dele istog bota, ne samo GitHub.
- Preporuka: zaseban Telegram bot za Lotos SEO, sa minimalnim administrativnim pravima za slanje poruka.

## API i prava

- Google Search Console scope: `https://www.googleapis.com/auth/webmasters.readonly`.
- `SEO Daily Monitoring` ima `contents: write` samo radi upisa CSV/JSON/HTML izveštaja u privatni repo.
- `CI`, `SEO Telegram Connection Test` imaju `contents: read`.
- `SEO Monitoring Watchdog` ima `actions: read`, `contents: read`, pristupa samo zvaničnom GitHub API-ju.
- Nijedna skripta ne menja Google indeks, SEO kod produkcionih sajtova, Django modele, narudžbine ili korisničke podatke.

## Tehničke zaštite

- Mrežne HTTP provere ostaju na navedenom HTTPS hostu; ne slede eksterni redirect.
- Odgovori ograničeni na 2 MB; mali broj URL provera po domenu.
- Google API greške se prikazuju kao HTTP status i dozvoljen Google reason; sirovi exception s URL-ovima ili tokenima se ne loguje.
- CSV escape je uključen za opasne formule u query poljima.
- HTML dashboard escape-uje GSC upite i konfiguracione nazive.
- JSON snapshot se zamenjuje atomski; čitanje istorije ignoriše pokvarene fajlove.

## Poznata ograničenja

- CSV/JSON/HTML izveštaji nisu podaci kupaca, ali otkrivaju poslovne SEO pokazatelje. Repo obavezno privatni.
- Sama Python aplikacija ne zahteva prijem spoljašnjih HTTP zahteva i nema server port.
- GitHub Actions raspored može kasniti; Watchdog na istoj platformi nije nezavisan od njenog pada.
- Zavisnosti su ograničene po major verzijama; za stroge supply-chain zahteve uvesti hash-pinned lockfile i pin GitHub Actions commit SHA nakon staging validacije.
- Google API quota nije garantovana; broj novih domena povećava broj Google upita i URL inspekcija.
