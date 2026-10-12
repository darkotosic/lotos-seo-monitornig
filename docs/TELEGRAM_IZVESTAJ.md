# Telegram SEO izveštaj — v2

## Format

Dnevna poruka se šalje u jedan konfigurisani Telegram kanal preko `SEO_TELEGRAM_BOT_TOKEN` i `SEO_TELEGRAM_CHAT_ID`. U poruci su svi aktivni domeni iz `config/sites.yml`.

Primer **ilustrativnog** sadržaja (brojevi samo primer, nisu live podaci):

```text
LOTOS SEO MONITORING | 2026-10-12
Google Search Console · Web · poslednjih 28 dana (sa zakašnjenjem)

Cvećara Lotos Ruma | https://cvecararuma.rs
Period: 2026-09-12 — 2026-10-09
Klikovi: 148 (+11%)
Prikazi: 3.765 (+15%)
CTR: 3.9%
Prosečna pozicija: 5.9 (bolje 0.2)
Upiti (prosečne pozicije):
- cvecara ruma: 1.5 (bolje 1.1) · 331 prikaza
URL Inspection uzorak: 3 indeksirano, 0 problem, 0 nepoznato
HTTP: 5/5 odgovora 200
Nedeljni pregled (7d naspram prethodnih 7d):
- Klikovi: ...
- Prikazi: ...

...
Upozorenja: 0
Bez aktivnih upozorenja.
N/D = nema pouzdanih podataka; nije pozicija 0.
Pozicije su GSC proseci, ne trenutni Google rezultati.
```

## Izvori i granice

- Glavni pokazatelji: poslednjih 28 **finalizovanih** dana sa podešenim kašnjenjem 3 dana, upoređeni sa prethodnih 28 dana.
- Ponedeljkom: 7d protiv prethodnih 7d, sa istim GSC pravilom.
- Pozicije upita su GSC prosek, a ne status „trenutno mesto 1/2/3“.
- URL Inspection prikazuje samo URL-ove iz `inspect_paths` i nije kompletna Search Console pokrivenost.
- Telegram API podržava ograničenu dužinu poruke; izveštaj se bezbedno skraćuje na <=3500 karaktera, a detalji su u GitHub `reports/`.
- Nema ličnih podataka kupaca, bot ne analizira poruke niti zahteva admin pristup drugim servisima.
- Jedno ručno ponovno pokretanje istog dana može poslati novu istu poruku; datum JSON istorije ostaje idempotentan.
