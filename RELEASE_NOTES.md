# LOTOS SEO MONITOR v2.0.0 — release notes

Datum: 12. oktobar 2026.

## Osnova i kompatibilnost

Nadograđen je konkretan korisnikov ZIP `lotos-seo-monitornig-main.zip`, ne fiktivni novi projekat. Sačuvan je `config/sites.yml` za Rumu i Inđiju, HTML/CSV/Markdown/JSON report izlazi, postojeće dve Search Console Domain property konfiguracije, istorija JSON snapshotova i sva tri postojeća GitHub Secrets naziva.

## Implementirano

1. Dnevni **Telegram Executive Digest** sa 28d Google KPI-jevima, poređenjem sa prethodnih 28d, najvažnijim upitima, pozicijama, indeksiranim URL uzorkom, HTTP odgovorima i upozorenjima.
2. **Nedeljno poređenje** dva 7-dnevna perioda (dodatni finalizovani GSC pozivi); prikazuje se u dnevnoj poruci svakog ponedeljka i u Markdown izveštajima.
3. Nedostajući/privatno filtrirani podaci više **ne prikazuju poziciju 0** nego `N/D`.
4. Bezbedna GSC dijagnostika sa HTTP statusom i dozvoljenim Google reason-ima; bez prenošenja raw API grešaka, URL query stringova ili kredencijala u Git istoriju.
5. Poboljšan **HTML dashboard**, sa upitima, indeksnim uzorkom, periodom i GSC ograničenjima; iz GSC polja se HTML-escape-uje sadržaj.
6. CLI komande `validate`, `notify-test` i `--preview-telegram`; offline i live test procedure; testovi Telegram isporuke bez GSC.
7. Atomski upis dnevnih JSON snapshotova i čitanje poslednjeg ispravnog snimka ako je noviji pokvaren.
8. Informativna detekcija SSR H1 placeholdera (npr. „Učitavanje...“), bez lažnog fatal alarma.
9. Detekcija praznog sitemap XML; konzervativne postojeće HTTP/canonical/robots zaštite ostaju.
10. Samostalni **SEO Monitoring Watchdog** na GitHub Actions (`12:00 UTC`), koji proverava da li je dnevni run uspeo u poslednjih 27 sati i šalje Telegram alarm.
11. Odvojeni **SEO Telegram Connection Test** workflow; proširen CI; brisanje privremenog Google JSON ključa iz runner-a posle merenja.
12. Opsežna dokumentacija za GitHub Secrets, migraciju, bezbednost i operacije.

## Validacija u okruženju izrade

- `python -m pytest -q` — 50 passed (offline unit/regresioni testovi, GSC/Telegram/GitHub HTTP pozivi su mockovani).
- `python -m compileall -q seo_monitor` — uspešno.
- `python -m seo_monitor validate` — oba postojeća domena ispravna.
- `ruff check seo_monitor tests` — **nije lokalno izvršen** jer ruff nije instaliran u okruženju; automatski se izvršava na GitHub CI-u.

## Potrebna produkciona verifikacija

- GitHub **PR → CI** mora biti zelen pre merge-a.
- Ručni `SEO Daily Monitoring` treba da vrati GSC=OK za oba domena i generiše pun dnevni Telegram izveštaj.
- Pokreni **SEO Telegram Connection Test** i proveri poruku u Telegram kanalu.
- Watchdog se može testirati ručno, ali normalno završava 0 samo ako postoji uspešan dnevni run u poslednjih 27 sati.
- Potvrdi da `reports/overview.md` i `reports/telegram-preview.txt` prikazuju stvarne podatke; oni koji su u arhivi pre release-a pripadaju prethodnoj v1 instanci i namenjeni su očuvanju istorije.

## Nema izmene

Nema nikakvih izmena na `cvecararuma.rs`, `cvecaraindjija.rs`, Django/DRF, PostgreSQL, Render, Netlify, narudžbinama ili payment toku. Bot ne kreira lažne Google pretrage ni klikove.
