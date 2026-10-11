# SEO operativni plan — Ruma, Inđija i budući gradovi

## Bazna merenja (ručno dostavljena, ne podaci iz pokrenutog bota)

**Ruma:** prethodno dostavljeni Search Console Performance PDF za period 3 meseca prikazuje 506 organskih klikova, oko 11.500 prikaza, CTR 4,4%, ukupnu prosečnu poziciju 6,0; za upit `cvecara ruma` 1,8 uz 1.119 prikaza. Poslednjih 28 dana u Insights: 147 klikova (+9%) i 3.770 prikaza (+17%).

**Inđija:** raniji Search Console screenshot prikazuje 9 klikova, 113 prikaza, CTR 8%, prosečnu poziciju 7,6 i upit `cvecara indjija` na prosečnoj poziciji 11,3 uz 33 prikaza. Naknadni screenshot jedne Google pretrage prikazao je sajt na 3. organskom mestu uz fotografiju buketa. To nije isto što i stabilna prosečna pozicija 3.

Ove vrednosti služe samo kao **istorijski kontekst iz korisničkih izveštaja**; nisu unapred upisane u bot i ne prikazuju se kao verifikovan live API rezultat.

## Šta posmatramo svake nedelje

1. Da li padaju ukupni prikazi i klikovi uz stabilno trajanje merenja?
2. Kako se menja pozicija glavne ključne reči **uz dovoljno prikaza**?
3. Da li je broj indeksiranih URL-ova prema inspekcijama stabilan? (URL Inspection uzorak nije kompletan indeksni izveštaj.)
4. Da li postoji HTTP 5xx, noindex, problem sitemap-a ili canonical-a?
5. Koji URL-ovi i upiti ostvaruju rast i pokazuju nameru kupovine?
6. Da li su promenjene SEO metrike nakon poslednjeg deployment-a — bez automatske tvrdnje o uzročnosti?

## KPI ciljevi, bez garancije

- **Ruma:** stabilnost glavnih lokalnih upita oko prve 1–3 prosečne pozicije; manje tehničkih grešaka; rast stvarnih poseta i potvrđenih porudžbina.
- **Inđija:** povećanje prikaza i potvrđenih organskih klikova; postepeno približavanje stabilnom Top 5, pa Top 3 za ciljnu ključnu reč.
- **Novi gradovi:** pozitivan rast indeksiranih kvalitetnih URL-ova i lokalnih kupovnih upita u prva 2–3 meseca, uz realne mogućnosti dostave.

Nijedan bot ili izveštaj ne može garantovati poziciju #1. Bez GA4 ili sopstvene anonimizovane metrike naručivanja ovaj alat **ne izračunava konverzije**.

## Odluke nakon alarma

| Alarm | Operativna provera | Potencijalna akcija |
|---|---|---|
| HTTP 5xx | proveriti Netlify/Render logove i API zavisnosti | ciljano ispraviti grešku, pa validirati |
| `noindex` | proveriti SSR meta tag, robots i stvarni zahtev za indeksiranjem | ispraviti samo nenamerni `noindex` |
| canonical problem | proveriti da li je regionalna stranica za samostalno indeksiranje | ukloniti duplu/konfliktnu konfiguraciju |
| pad pozicije | pogledati GSC upit, period, uređaje, landinge i konkurenciju | ažurirati sadržaj samo uz dokaz o potrebi |
| upozorenje URL Inspection | pogledati status konkretne URL adrese u Search Console | validirati problem ručno; bot ga ne „popravlja“ |
| rast prikaza bez klikova | proveriti SERP izgled, naslov, relevantnost i nameru | testirati poboljšanje snippet-a bez agresivnih SEO promena |

## Regionalni domeni — pravila

Svaki budući domen predstavlja istinitu uslugu dostave za grad, a ne fizičku poslovnicu koja ne postoji. Nema izmišljenih recenzija, Google Maps adresa, brzine dostave ili garancija plaćanja. Regionalni sadržaj mora imati stvarnu informativnu vrednost; kopije promenom imena grada povećavaju rizik od Google doorway procene i međusobne konkurencije URL-ova.
