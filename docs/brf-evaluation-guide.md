# BRF-guide: snabb bedömning innan bud

Praktisk guide för Erik & Jenny (och liknande köpare) som vill bedöma en **bostadsrättsförening (BRF)** innan visning och budgivning. Inget ersätter att läsa hela **årsredovisningen** och **underhållsplanen** – men här är vad ni ska leta efter och vilka tumregler API:et använder.

## Vad ni ska hämta hem

| Källa | Vad |
| --- | --- |
| **Årsredovisning** (senaste, ofta på föreningens eller mäklarens sida) | Resultat, balans, noter, förvaltningsberättelse, revisor |
| **Underhållsplan** | Planerade åtgärder, kostnader, tidslinje |
| **Stadgar** | Inre/ytre underhåll, andrahandsuthyrning, avgifter vid överlåtelse |
| **Mäklarens objektsbeskrivning** | Avgift, yta, byggår – dubbelkolla mot årsredovisningen |

### Nyckeltal i årsredovisningen (sedan 2023)

BFNAR 2023:1 kräver att BRF:er redovisar i förvaltningsberättelsen, bland annat:

- **Skuldsättning per kvm** (bostadsrättsarea, BOA)
- **Årsavgift per kvm**
- **Sparande per kvm** (kassaflöde före avskrivningar och underhöll)
- **Räntekänslighet** – hur mycket avgiften ökar om räntan stiger 1 procentenhet
- **Energikostnad per kvm**

## Ekonomi: skuld vs kassa

### Belåning per kvm

Det vanligaste jämförelsetalet:

| Skuld per kvm | Tolkning |
| --- | --- |
| **Under ~5 000 kr** | Låg – ofta äldre förening med amorterat eller litet lån |
| **5 000–10 000 kr** | Normalt i många storstadsområden |
| **12 000–15 000 kr** | Högt – nyproduktion eller stora investeringar |
| **Över ~15 000 kr** | Mycket högt – stark räntekänslighet |

**Dold skuld:** `skuld per kvm × er lägenhets yta` = den föreningsskuld ni indirekt betalar ränta på via avgiften.

### Kassa och likviditet

Titta på **kassa och bank** (och ev. kortfristiga placeringar) i balansräkningen.

- **Röd flagga:** negativ kassa, eller mycket låg kassa i relation till skulden (under ~2 % av total skuld)
- **Grön flagga:** god buffert – tumregel **minst ~25 000 kr per lägenhet** i kassa; **över ~75 000 kr/lgh** är starkt

Jämför också **sparande per kvm** i nyckeltalen: under ~150 kr/kvm/år är svagt för äldre hus; över ~300 kr/kvm/år är starkt.

### Vad pengarna gått till

I resultaträkningen och noterna: har stora utgifter varit **investeringar** (tak, stambyte) eller **löpande drift**? Ökande **skuld utan färdigställda projekt** är en varning. Läs **väsentliga händelser** och revisorns text om tvister, vattenskador eller avgiftshöjningar.

### Räntekänslighet

Över **~10 %** räntekänslighet (enligt årsredovisningen) betyder att en räntehöjning slår hårt mot avgiften.

## Mark: äganderätt vs tomträtt

| | **Äganderätt** | **Tomträtt** |
| --- | --- | --- |
| **Betydelse** | Föreningen **äger** marken | Föreningen **hyr** marken av markägare (ofta kommunen) |
| **Kostnad** | Ingen tomträttsavgäld | Tomträttsavgäld till markägaren |
| **Risk** | Lägre långsiktig markkostnad | **Omreglering** var 10:e–20:e år – avgälden kan höjas kraftigt |
| **Fråga** | Bekräfta i årsredovisningen | När är nästa omreglering? Finns möjlighet att **friköpa** till äganderätt? |

I årsredovisningen står det oftast uttryckligen om föreningen har äganderätt eller tomträtt – läs noterna, inte bara rubriken "fastigheten".

API-fältet `owns_land` (boolean): **`true` = äganderätt**, **`false` = tomträtt**. Tomträtt ger röd flagga i bedömningen; hög `tomtratt_fee` (> ~500 000 kr/år) ytterligare varning.

## Äkta förening (privatbostadsföretag)

En **äkta** förening uppfyller kraven i inkomstskattelagen (minst 60 % av taxeringsvärdet på bostäder som används av medlemmarna). I en **oäkta** förening får ni sämre skatteeffekter vid försäljning och annan beskattning.

- Står ofta uttryckligen i årsredovisningen eller stadgarna
- **Röd flagga:** `is_genuine: false` – behandla som allvarlig legal/riskpunkt

## Renoveringar: gjort vs planerat

| Åtgärd | Typisk livslängd | Kommentar |
| --- | --- | --- |
| **Stambyte** | ~40–60 år | Hus byggda före ~1975 utan stambyte/relining = hög risk |
| **Tak** | ~30–50 år | Planerat takbyte = avgift eller lån |
| **Fasad** | varierar | Fukt, puts, energi |
| **Fönster** | ~30–40 år | Ofta stort projekt i 60–70-tals hus |
| **Hiss** | modernisering ~25–30 år | Viktigt i höga hus |

**Grönt:** `status: done` med rimligt år i underhållsplan/årsredovisning.  
**Rött:** `status: planned` eller text i `planned_works` utan tydlig finansiering.

Relining är billigare än fullt stambyte men kortare livslängd – fråga vilket som gjorts.

## Storlek och förvaltning

- **Under ~15 lägenheter:** varje stor åtgärd blir dyr per hushåll
- **15–80 lägenheter:** ofta effektiv storlek
- **Mycket stora föreningar:** kontrollera att underhållsplanen följer per byggnad

**Förvaltare:** HSB, Riksbyggen, SBC, Nabo och liknande är etablerade – det är inte en garanti, men ofta bättre process och dokumentation än helt egen skötsel. Notera namnet i årsredovisningen (`management_brand` i API).

## Bostadsrätter vs hyresrätter i samma förening

Ibland finns **hyresrätter** eller många **lokaler** i samma juridiska förening (eller närliggande ekonomisk förening). Det kan påverka prioritering av underhåll och avgiftsnivå.

- Fråga hur många hyresrätter det finns och hur intäkterna används
- Flera hyresrätter (t.ex. ≥ 5) flaggas som högre risk i API:et

## Röda flaggor (sammanfattning)

- Oäkta förening
- Mycket hög skuld per kvm utan tydlig amorteringsplan
- Låg kassa / negativt kassaflöde flera år
- Tomträtt med nära omreglering eller hög avgäld
- Gamla hus utan stambyte/relining
- Stora **planerade** arbeten (tak, fasad, stambyte) utan buffert
- Revisorns anmärkningar, tvister, upprepade avgiftshöjningar
- Beroende av en enda stor lokalhyresgäst

## Gröna flaggor

- Äkta förening, **äganderätt** till marken (inte tomträtt)
- Skuld per kvm under eller i normalintervallet
- God kassa i relation till skuld och antal lägenheter
- Genomförda större underhåll (stambyte, tak, fönster) i tid
- Uppdaterad underhållsplan som matchar avsättningar
- Rimlig räntekänslighet och sparande per kvm

## Frågor på visning / till mäklaren

1. När senast höjdes avgiften och varför?
2. Finns **underhållsplan** – får vi den? Stämmer avsättning med planen?
3. Stambyte/relining – gjort, planerat, kostnad per lägenhet?
4. **Äganderätt eller tomträtt?** Om tomträtt: nästa omreglering? Möjligt friköp till äganderätt?
5. Planerade arbeten de närmaste 5 åren – finansiering (lån vs avgift)?
6. Hyresrätter eller lokaler – hur stor andel av ekonomin?
7. Kända fukt-, läckage- eller tvistärenden?
8. Vad ingår i avgiften (värme, vatten, bredband, el)?

## Rule-based API (`POST /associations/assess`)

Skicka JSON med fält som i `associations` plus valfritt `management_brand`, `rental_units_count`, `only_bostadsratter` och en lista `renovations`. Svaret innehåller:

- `economy_score` (0–100, start ~70, justeras med heuristik ovan)
- `red_flags`, `green_flags`
- `summary`, `questions_to_ask`

Exempel:

```bash
curl -s -X POST http://127.0.0.1:8642/associations/assess \
  -H 'content-type: application/json' \
  -d '{
    "built_year": 1965,
    "num_apartments": 42,
    "debt_per_sqm": 9500,
    "cash_balance": 3200000,
    "owns_land": true,
    "is_genuine": true,
    "management_brand": "HSB",
    "only_bostadsratter": true,
    "renovations": [
      {"kind": "stambyte", "year": 2018, "status": "done"},
      {"kind": "roof", "year": 2030, "status": "planned"}
    ]
  }'
```

**Antaganden:** Poängen är en **snabb screening**, inte juridisk eller ekonomisk rådgivning. Trösklar följer branschtumregler i `db/seed.sql` och denna guide. PDF/LLM-tolkning av årsredovisning kommer i senare steg.
