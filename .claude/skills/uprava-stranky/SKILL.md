---
name: uprava-stranky
description: Úpravy webu „Jižní Morava v pohybu“ (index.html) – nové funkce, tlačítka, karty, režimy, vzhled, opravy chyb v animaci mapy, režimu Brno v roce 1953, Rekordech dne, kartě spoje, sdílení odkazu. Použij vždy, když se mění kód nebo texty stránky, i když uživatel napíše jen „přidej…“, „oprav…“, „změň…“, „na mobilu…“.
---

# Úprava stránky index.html

Celý web je jeden soubor `index.html` (~4 MB, ~580 řádků). Žádný build, žádné knihovny,
publikuje se přes GitHub Pages z `main`.

## Nikdy nečti celý soubor

Řádky s daty mají miliony znaků a zahltí kontext:

| řádek | obsah | velikost |
|---|---|---|
| `const DATA={...}` | jízdní řád dne (generuje `tools/build_data.py`) | ~3,5 MB |
| `const SHP={...}` | trasy mezi zastávkami (generuje `tools/build_shapes.py`) | ~0,5 MB |
| `const T53={...}` | tramvajová síť 1953 (generuje `tools/build_tram1953.py`) | ~4 kB |

Tyto řádky **ruční editací neměň** – přegenerují se skripty (viz skill `data-jizdniho-radu`).

Bezpečné čtení:

```bash
grep -n "const DATA=\|const SHP=\|const T53=" index.html | cut -c1-80   # kde jsou datové řádky
sed -n 1,185p index.html                  # hlavička, CSS, HTML ovládacích prvků
sed -n 189,579p index.html | cut -c1-400  # skript bez datových řádků
grep -n "pattern" index.html | cut -c1-300
```

Nástroj Read používej jen s `offset`/`limit` mimo datové řádky. Edit funguje normálně
(old_string musí být z řádků kódu, ne z dat).

## Mapa souboru

- **ř. 1–16** `<head>`: title, meta/OG popisy, fonty Barlow a Barlow Condensed (Google Fonts).
- **ř. 17–132** `<style>`: barvy jen jako proměnné v `:root` (`--bg --net --net-strong --ink --ink-2
  --panel --rule --label` + barvy módů `--tram --trol --bus --night --boat --reg --train`).
  Tmavý režim je definovaný **dvakrát** (`@media (prefers-color-scheme:dark)` s `:root:not([data-theme="light"])`
  a `:root[data-theme="dark"]`) – novou barvu přidej do všech tří bloků. Mobil: `@media (max-width:640px)`.
- **ř. 133–184** HTML: `.head` (nadpis + datum), `.clock`, `.finder` (Brno v roce 1953, Rekordy dne),
  `#histBar`, `#swipe`, karty `aside.card` (`#card` obec, `#veh` spoj, `#rec` rekordy), `.dock`
  (play, rychlost, Celý kraj, Síť linek, Dlouhá expozice, Sdílet, Uložit obrázek, `#scrub` časová osa, `#leg` legenda).
- **ř. 185+** `<script>`, oddíly začínají komentářem `// =====`:
  - základ: `MODES` (7 módů: tram, trol, bus, night, boat, reg, train), dekódování `trips`
    (`T` časy, `S` zastávky, `a`/`b` začátek/konec, `m` mód, `r` linka), projekce `P`, `SHAPES`/`shapeOf`
  - kreslení: `view {cx,cy,z}`, `px/py`, `fit()`, `drawNet()` (síť + popisky do offscreen canvasu, `netDirty=true` vynutí překreslení),
    `frame()` hlavní smyčka, `posAt/trail/segAt`, `css` (čte CSS proměnné přes `readCss()`)
  - Dlouhá expozice (`expo`, `expPaint`, `setExpo`), uložení PNG
  - časová osa `drawScrub`, play/rychlost, legenda
  - `// ===== places: card` – karta obce (`select`, `showBox`, `zoomTo`)
  - `// ===== rekordy dne` – `buildRec`, `setRec`
  - `// ===== vozidlo` – `selVeh`, `renderVeh`, `setFollow`, `stopName`, `esc`
  - `// ===== sdílení` – `shareUrl`, `share`, `hashParts`, `setHash`
  - `// ===== 1953` – Křovák `KR`, dlaždice CENIA (1953) a ČÚZK (dnes), swipe, `T53`, `setHist`, `goTo`
  - ovládání myší/dotykem, zoom, start: čtení hashe a `requestAnimationFrame(frame)`

## Zavedené vzory – drž se jich

- **Styl kódu**: hustý, minifikovaný (víc příkazů na řádek, krátké názvy, žádné knihovny).
  Komentáře česky a krátce. Nepřeformátovávej existující kód.
- **Přepínací tlačítko**: `<button id="xB" aria-pressed="false" title="…">` v `.dock .ctrls` nebo `.finder`,
  funkce `setX(v)` nastaví stav, `aria-pressed`, `netDirty=true` pokud se mění mapa, a zavolá `setHash()`.
- **Adresa (hash)**: stav, který má přežít reload, přidej do `hashParts()` (`1953`, `bezsite`, `expozice`,
  `rekordy`, `obec=`) a do čtení hashe na konci skriptu. Okamžik (`cas=`, `pohled=`, `spoj=`) je jen ve sdíleném odkazu.
- **Karty**: najednou je otevřená jen jedna – při otevření zavři ostatní (`select(-1)`, `selVeh(-1)`, `setRec(false)`)
  a přepni `document.body.classList.toggle('card-open', …)` (na mobilu skryje dock).
- **Mobil**: v JS `W<640`, v CSS `max-width:640px`. Každou změnu UI ověř i na mobilu.
- **Texty**: česky, s diakritikou, typografické uvozovky „…“, pomlčka –, nezlomitelné mezery tam,
  kde už jsou. Čísla `toLocaleString('cs-CZ')`. Uživatelské texty do HTML přes `esc()`.
- **Časy**: v sekundách od půlnoci (0–86400), noční spoje z předchozího dne mají záporný čas; formát `fmt()`, `hhmm()`.
- **Souřadnice**: `[(lon-16.61)*kx, -(lat-lat0)]`; převod zpět viz `shareUrl()` a `goTo(lon,lat,z)`.
- **Výkon**: `frame()` běží každý snímek přes ~20 000 spojů – žádné alokace ani DOM dotazy navíc ve smyčce,
  drahé věci počítej jednou nebo líně (viz `buildRec` při prvním otevření).

## Postup

1. Najdi místo grepem, přečti jen příslušné řádky (`sed -n A,Bp index.html | cut -c1-400`).
2. Uprav Editem.
3. Ověř skillem `overeni-stranky` (syntaxe, konzole, snímek – desktop i `--mobile`, u barev i `--dark`).
4. Nová nebo změněná funkce pro uživatele → aktualizuj `README.md` (popis tlačítka, parametry adresy).
5. Commit: krátká česká věta bez tečky ve stylu historie (`git log --oneline`), např.
   „Karta Rekordy dne“, „1953: neposouvat mapu ani po přiblížení mimo centrum Brna“.
   Neprováděj commit datových řádků vygenerovaných pro jiný den, než je v `main` (pokud to není účel změny).
