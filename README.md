# Jižní Morava v pohybu – 1953 a dnes

Animovaná mapa všech spojů IDS JMK (MHD Brno, regionální autobusy a vlaky) podle jízdního řádu,
s porovnáním leteckých snímků Brna z roku 1953 a dneška.

Celá stránka je jeden soubor `index.html` (asi 2,6 MB) – data jízdních řádů i trasy jsou vložená přímo v něm,
žádný build ani server není potřeba. Z internetu si stránka bere jen písmo Barlow (Google Fonts)
a v režimu Brno v roce 1953 letecké snímky; bez nich mapa, vozidla i karty fungují dál.

Vozidla jedou po skutečných trasách linek (ulice, koleje), ne vzdušnou čarou.
Síť linek je ve výchozím stavu zobrazená, vypíná a zapíná se tlačítkem **Síť linek** v dolní liště
(vypnutý stav se ukládá do adresy jako `#bezsite`).

Mapa se posouvá tažením, přibližuje kolečkem, dvojklikem nebo dvěma prsty. Tlačítko **Celý kraj** / **Brno**
přepíná mezi výřezem Brna a celým krajem. V dolní liště je dál přehrávání a pauza, tři rychlosti
(**Pomalu**, **24 h za 90 s**, **Rychle**), časová osa s grafem počtu vozidel během dne (kliknutím nebo tažením
se čas přetočí) a legenda: každý druh dopravy (tramvaje, trolejbusy, autobusy MHD, noční autobusy, loď,
regionální autobusy, vlaky) v ní jde kliknutím vypnout a zapnout a ukazuje, kolik vozidel je právě na trati.

Kliknutí na zastávku otevře kartu obce: počet odjezdů za den, linky, odjezdy po hodinách, první ranní
spojení do centra Brna a nejdelší pauzu mezi odjezdy (5–22 h); u Brna jen počet odjezdů ze všech zastávek.
Spoje, které obcí neprojíždějí, na mapě zeslábnou. V adrese `#obec=Kuřim`.

Stránka vždy začíná o půlnoci a hned přehrává (při systémovém nastavení omezení pohybu začíná pozastavená),
ve 23:59 se přehrávání zastaví. Tlačítko **Teď** přetočí na aktuální čas (Europe/Prague) a přepne na přehrávání naživo:
čas běží podle hodin a vozidla jedou reálným tempem (červená tečka na tlačítku). Pauza, posun času
nebo volba rychlosti režim naživo ukončí. V jiný den, než je jízdní řád, je tlačítko skryté.

Na kartě obce je tlačítko **Kam se odsud dostanu za hodinu**. Od času na mapě spočítá nejdřívější příjezd
na všechny zastávky do hodiny (s přestupy, přestup na téže zastávce 1 min, pěšky k zastávkám do 400 m)
a vykreslí spoje, kterými se tam jede, barevně po 10 minutách. Karta ukáže počet obcí a zastávek
do 30 minut a do hodiny a nejvzdálenější dosažitelnou obec. Když se obec vybrala kliknutím na zastávku,
počítá se z této zastávky (všech nástupišť stejného jména), jinak ze všech zastávek obce (Brno ze zastávky
nejblíž středu). Při posunu času nebo přehrávání se dojezd přepočítává, kliknutím na jinou zastávku se změní
výchozí místo. V adrese `#obec=Kuřim&dojezd`, případně `dojezd=Název zastávky`.

Tlačítko **Dlouhá expozice** přestane mazat stopy vozidel, takže za den z nich vznikne světelný obraz
dopravy v kraji (v adrese `#expozice`). Zapnutí spustí přehrávání a síť linek se po dobu expozice nekreslí.
Obraz se kreslí od chvíle zapnutí, po posunu mapy, změně filtru v legendě nebo
přetočení času zpět se překreslí celý. Tlačítko **Uložit obrázek** (je vidět jen při zapnuté expozici)
stáhne mapu jako PNG s popiskem
(datum a časové rozpětí). V režimu Brno v roce 1953 uložení nejde, letecké snímky export neumožňují.

Tlačítko **Rekordy dne** otevře kartu se zajímavostmi spočítanými z jízdního řádu daného dne:
nejvíc vozidel naráz, nejklidnější chvíle noci, počet spojů a ujeté kilometry, nejdelší
a nejrychlejší spoj, linka s nejvíc spoji a obec s nejvíc odjezdy. U většiny je odkaz
„Ukázat na mapě“, který přetočí čas, přiblíží mapu nebo zvýrazní trasu spoje (v adrese `#rekordy`).

Kliknutí na vozidlo otevře kartu spoje: linka, směr, projeté a další zastávky s časy. Tlačítko
**Sledovat** přepne na pomalou rychlost a mapa vozidlo veze s sebou (posunem mapy se sledování
vypne). Názvy zastávek jsou v `DATA.stopNames` / `DATA.stopName`.

Tlačítko **Sdílet** (v liště i na kartě spoje) zkopíruje odkaz na aktuální okamžik: k běžným
parametrům adresy přidá `cas=HH:MM`, `pohled=lon,lat,zoom` a u vybraného vozidla `spoj=linka@HH:MM`
(odjezd z výchozí zastávky). Na mobilu se otevře systémové sdílení.

## Parametry adresy

Stav stránky se zapisuje za `#`, parametry se spojují `&`:

| parametr | stav |
|---|---|
| `obec=Název` | otevřená karta obce |
| `dojezd`, `dojezd=Název zastávky` | dojezd do hodiny z obce / ze zastávky (jen spolu s `obec=`) |
| `1953` | režim Brno v roce 1953 |
| `bezsite` | vypnutá síť linek |
| `expozice` | Dlouhá expozice |
| `rekordy` | karta Rekordy dne |
| `cas=HH:MM` | čas na mapě, přehrávání se pozastaví |
| `pohled=lon,lat,zoom` | výřez mapy (zoom pod 2000 = celý kraj) |
| `spoj=linka@HH:MM` | otevře kartu spoje a sleduje ho |

`cas`, `pohled` a `spoj` jsou jen ve sdíleném odkazu, po načtení je stránka z adresy odstraní.
Datum v adrese není: odkaz vždy ukazuje jízdní řád dne, na který je stránka právě sestavená,
takže `spoj=` z jiného dne nemusí nic najít.

## Klávesnice a textový přehled spojů

Mezerník přepíná přehrávání a pauzu. Šipky **← / →** posunou čas o 10 minut,
se **Shiftem** o hodinu, a přehrávání pozastaví. Fungují i na časové ose.
Zkratky nezasahují do psaní ve vyhledávání, tlačítek a odkazů ani do zkratek
s Ctrl, Alt či Cmd. Tlačítka se běžně ovládají Tabem, Enterem a mezerníkem.
**Esc** zavře otevřenou kartu.

Tlačítko **Spoje na trati** otevře textový seznam vozidel aktivních v čase mapy
v celém kraji podle zapnutých druhů dopravy. Při otevření se přehrávání pozastaví,
aby se seznam během čtení neměnil. Hledat lze linku nebo kteroukoli zastávku spoje,
i bez diakritiky. Seznam obsahuje směr, výchozí a konečný čas a další zastávku;
po 20 výsledcích se stránkuje. Výběr spoje otevře jeho detail se zastávkami.
Zavření detailu vrátí přehled. Při změně minuty mapy nebo filtrů se výsledky obnoví.
Změny stavu výsledků jsou označeny pro oznámení čtečkou obrazovky; po návratu
z detailu se zaměření vrátí na vybraný spoj. Seznam doplňuje mapu; nezobrazuje skutečná zpoždění.

Automatická kontrola klávesnice, hledání, filtrů, stránkování a návratu z detailu
na desktopu i mobilu: `node tools/check_accessibility.cjs`. Vyžaduje Node.js,
Playwright a Chromium (volitelně cesta v `CHROMIUM`). Repozitář nemá `package.json`, Playwright
musí být nainstalovaný tak, aby ho Node našel (globálně přes `NODE_PATH`). Sama spustí dočasný HTTP server,
blokuje externí požadavky a uloží snímky do dočasného adresáře. Nemění data stránky.

## Ověření stránky

`node .claude/skills/overeni-stranky/check.mjs [--out složka] [--mobile] [--dark] ["#parametry adresy" …]`
zkontroluje syntaxi vloženého skriptu (`node --check`), otevře stránku v headless Chromiu bez přístupu
na internet, pro každý zadaný stav adresy uloží snímek a vypíše chyby z konzole (při chybě končí kódem 1).
Bez `--out` ukládá snímky do složky `shots/`, která je v `.gitignore`.
Jiné automatické testy repozitář nemá.

## Denní aktualizace jízdního řádu (`tools/update_day.sh`)

Stránka zobrazuje jízdní řád na jeden konkrétní den (datum je v nadpisu a v `DATA.date`).
Data na zadaný den (výchozí dnešek) sestaví jeden příkaz:

```bash
tools/update_day.sh            # dnešek podle Europe/Prague
tools/update_day.sh 2026-10-20 # konkrétní den
```

Skript stáhne GTFS IDS JMK (`https://kordis-jmk.cz/gtfs/gtfs.zip`, stejná data jako
„Jízdní řád IDS JMK ve formátu GTFS“ na data.brno.cz) a sítě linek z data.brno.cz, pak spustí:

- `tools/build_data.py` – z GTFS vybere spoje platné pro daný den (calendar + calendar_dates)
  a přepíše v `index.html` řádek `const DATA=...` i datum v nadpisu. Kromě spojů dne přidá
  spoje z předchozí noci, které končí po půlnoci (mají záporný čas), a pro každou obec spočítá
  první ranní spojení do centra Brna (odjezd od 3:00), nejdelší pauzu mezi odjezdy (5–22 h)
  a poslední spojení z centra domů (odjezd z Hlavního nádraží nebo ÚAN Zvonařka po poledni,
  nejpozději ve 3:00 následujícího rána, s přestupy podle `transfers.txt`).
  Poslední spojení domů je v datech (`DATA.places`), karta obce ho ale nezobrazuje.
  Když GTFS začíná platit až zadaným dnem (nový feed), chybí v něm předchozí den i noční spoje
  po půlnoci, které IDS JMK vede pod službou následujícího dne. Skript je pak vezme z jízdního
  řádu stejného dne v týdnu o týden později (předchozí noc a spoje dne do 4:00).
- `tools/build_shapes.py` – přepočítá trasy mezi zastávkami (viz níže).

Výpočet trvá asi čtvrt minuty, zbytek je stahování podkladů (asi 15 MB). Nepotřebuje nic mimo
standardní Python a `curl`. Popisky mapy (`DATA.labels`) se přebírají z předchozí verze stránky.
Stažené podklady jdou do dočasného adresáře, který se po běhu smaže.

Skript skončí chybou, když se stahování nepovede, když GTFS není platný zip, když pro zadaný den vyjde
méně než 1000 spojů nebo když výsledný `index.html` neobsahuje zadané datum. `index.html` se ale
přepisuje na místě a ve dvou krocích: když běh spadne až při přepočtu tras, zůstane v souboru nový
jízdní řád se starými trasami. V tom případě soubor vrať (`git checkout index.html`) a spusť skript znovu.

Automatické spouštění zajišťuje naplánovaný úkol (Routine) v Claude Code: každou noc krátce po půlnoci
(commity „Jízdní řád na …“ vznikají kolem 0:26 Europe/Prague) spustí `tools/update_day.sh`, výsledek
commitne do `main` a GitHub Pages ho zveřejní. Nastavení úkolu není součástí repozitáře, žádný
GitHub Actions workflow tu není. Dokud úkol neproběhne, ukazuje stránka jízdní řád předchozího dne
a tlačítko Teď je skryté.

## Přepočet tras (`tools/build_shapes.py`)

Trasy mezi sousedními zastávkami se počítají jako nejkratší cesta po síti linek IDS JMK
a vkládají se do `index.html` jako řádek `const SHP=...`. Po změně jízdních řádů (nový `DATA`)
je potřeba je přepočítat (`tools/update_day.sh` to dělá sám):

```bash
curl -L -o ids_jmk_sit.geojson "https://data.brno.cz/api/download/v1/items/791c63fd7190477196de14a05177757c/geojson?layers=0"
curl -o transit_routes.geojson "https://services6.arcgis.com/fUWVlHWZNxUvTUh8/arcgis/rest/services/transit_routes/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
python3 tools/build_shapes.py --html index.html --network ids_jmk_sit.geojson --lines transit_routes.geojson
```

Skript nepotřebuje žádné knihovny mimo standardní Python. Úseky, po kterých jezdí jen tramvaje,
se nejdřív hledají v kolejové síti DPMB (`--lines`, přichycení zastávky do 60 m), úseky jen s vlaky
v železniční síti z téhož souboru (do 150 m), všechno ostatní a to, co se nenašlo, v síti IDS JMK
(do 200 m, jde změnit přes `--snap`). Kde zastávka leží od sítě dál, cesta nejde najít nebo vyjde
podezřele dlouhá (víc než trojnásobek vzdušné vzdálenosti + 600 m), zůstane mezi zastávkami rovná čára.
Další volby: `--rail` (Overpass JSON s kolejemi `railway=rail`, pro vlaky má přednost; denní aktualizace
ho nepoužívá), `--tol` (zjednodušení tras, výchozí 3 m) a `--dump soubor.json` (výsledek se statistikou).

## Brno v roce 1953 a tramvaje 1953 (`tools/build_tram1953.py`)

Tlačítko **Brno v roce 1953** (v adrese `#1953`) rozdělí mapu svislou čárou: vlevo letecké snímky
z 50. let, vpravo dnešní letecký snímek nebo po přepnutí **Mapa linek** běžná mapa se sítí linek.
Čárou se táhne, dnešní vozidla jezdí přes obojí, čas i výřez mapy zůstávají. Tlačítka čtvrtí
(Lesná, Bohunice, Starý Lískovec, Líšeň, Bystrc, Vinohrady, Centrum, Královo Pole) na ně mapu přiblíží.
Snímky se načítají za běhu z mapových služeb CENIA (historické) a ČÚZK (dnešní).

V tomto režimu se přes letecké snímky kreslí tramvajová síť z roku 1953 (tlačítko
**Tramvaje 1953**): bíle tratě, které jezdí dodnes, oranžově tratě později zrušené (Kobližná,
Dornych, Olomoucká – Černovice, Stránská skála – Líšeň, Židenice, kasárna) a čárkovaně tratě
postavené až po roce 1953. Data jsou v `index.html` jako řádek `const T53=...`.
Na mobilu je panel režimu sbalený do záložky **Tramvaje a čtvrti ▾**, aby nezakrýval mapu;
po klepnutí se rozbalí a po výběru čtvrti se zase sbalí.

Vrstva vzniká z dnešní tramvajové sítě (data.brno.cz, transit_routes), ze které se vyříznou úseky
otevřené po roce 1953, a z geometrií zrušených tratí. Obojí je v `tools/tram1953.json`:
`remove` jsou dvojice bodů, mezi kterými se úsek vyřízne, `add` souřadnice zrušených tratí
s rokem zrušení. Data zahájení a zrušení provozu jsou ze [Seznamu tramvajových tratí v Brně](https://cs.wikipedia.org/wiki/Seznam_tramvajov%C3%BDch_trat%C3%AD_v_Brn%C4%9B)
(podle Z. Nesiba: *100 let elektrické pouliční dráhy v Brně 1900–2000*), geometrie zrušených
tratí z OpenStreetMap (`railway=razed`/`abandoned`), obojí ověřené nad ortofotem z 50. let.
Vedení spojky u černovického nádraží je přibližné.

Denní aktualizace vrstvu nemění. Přepočítá se jen při změně tramvajové sítě nebo `tram1953.json`:

```bash
curl -o transit_routes.geojson "https://services6.arcgis.com/fUWVlHWZNxUvTUh8/arcgis/rest/services/transit_routes/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
python3 tools/build_tram1953.py --html index.html --lines transit_routes.geojson --defs tools/tram1953.json
```

## Publikace přes GitHub Pages

1. Na GitHubu otevři **Settings → Pages**.
2. V části **Build and deployment** zvol **Source: Deploy from a branch**.
3. Vyber větev `main` a složku `/ (root)`, ulož.
4. Za pár minut bude stránka dostupná na `https://michalprouza.github.io/jmk-v-pohybu/`.

Soubor `.nojekyll` říká GitHubu, aby stránku jen zkopíroval a nespouštěl na ní Jekyll.

## Co je v repozitáři

- `index.html` – celá stránka; řádky `const DATA=`, `const SHP=` a `const T53=` jsou vygenerovaná data
  (dohromady asi 2,5 MB), ručně se needitují
- `tools/` – `update_day.sh`, `build_data.py`, `build_shapes.py`, `build_tram1953.py` s definicemi
  v `tram1953.json` a kontrola `check_accessibility.cjs`
- `CLAUDE.md` a `.claude/skills/` – pokyny pro Claude Code: úpravy stránky (`uprava-stranky`),
  ověření (`overeni-stranky` se skriptem `check.mjs`) a data (`data-jizdniho-radu`)

## Zdroje dat

- Jízdní řády: IDS JMK (GTFS, KORDIS JMK / data.brno.cz)
- Trasy linek: „Trasy linek IDS JMK“ a „Linky městské hromadné dopravy“ (DPMB), data.brno.cz
- Historická ortofotomapa (50. léta) © CENIA 2010, © GEODIS BRNO 2010; snímky VGHMÚř Dobruška, © MO ČR 2009
- Ortofoto ČR © ČÚZK, CC BY 4.0
- Písmo Barlow a Barlow Condensed (Google Fonts)
- Tramvajová síť 1953: Seznam tramvajových tratí v Brně (Wikipedie, CC BY-SA), zrušené tratě © přispěvatelé OpenStreetMap (ODbL)
