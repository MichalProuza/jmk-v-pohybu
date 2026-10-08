# Jižní Morava v pohybu – 1953 a dnes

Animovaná mapa všech spojů IDS JMK (MHD Brno, regionální autobusy a vlaky) podle jízdního řádu,
s porovnáním leteckých snímků Brna z roku 1953 a dneška.

Celá stránka je jeden soubor `index.html` – data jízdních řádů i trasy jsou vložená přímo v něm,
žádný build ani server není potřeba.

Vozidla jedou po skutečných trasách linek (ulice, koleje), ne vzdušnou čarou.
Síť linek je ve výchozím stavu zobrazená, vypíná a zapíná se tlačítkem **Síť linek** v dolní liště
(vypnutý stav se ukládá do adresy jako `#bezsite`).

Tlačítko **Dlouhá expozice** přestane mazat stopy vozidel, takže za den z nich vznikne světelný obraz
dopravy v kraji (v adrese `#expozice`). Obraz se kreslí od chvíle zapnutí, po posunu mapy nebo
přetočení času zpět se překreslí celý. Tlačítko **Uložit obrázek** stáhne mapu jako PNG s popiskem
(datum a časové rozpětí). V režimu Brno v roce 1953 uložení nejde, letecké snímky export neumožňují.

Tlačítko **Rekordy dne** otevře kartu se zajímavostmi spočítanými z jízdního řádu daného dne:
nejvíc vozidel naráz, nejklidnější chvíle noci, počet spojů a ujeté kilometry, nejdelší
a nejrychlejší spoj, linka s nejvíc spoji a obec s nejvíc odjezdy. U většiny je odkaz
„Ukázat na mapě“, který přetočí čas, přiblíží mapu nebo zvýrazní trasu spoje (v adrese `#rekordy`).

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
- `tools/build_shapes.py` – přepočítá trasy mezi zastávkami (viz níže).

Celý běh trvá asi půl minuty a nepotřebuje nic mimo standardní Python a `curl`.
Popisky mapy (`DATA.labels`) se přebírají z předchozí verze stránky.

Automatické spouštění každé ráno zajišťuje naplánovaný úkol (Routine) v Claude Code:
spustí `tools/update_day.sh`, výsledek commitne do `main` a GitHub Pages ho zveřejní.

## Přepočet tras (`tools/build_shapes.py`)

Trasy mezi sousedními zastávkami se počítají jako nejkratší cesta po síti linek IDS JMK
a vkládají se do `index.html` jako řádek `const SHP=...`. Po změně jízdních řádů (nový `DATA`)
je potřeba je přepočítat (`tools/update_day.sh` to dělá sám):

```bash
curl -L -o ids_jmk_sit.geojson "https://data.brno.cz/api/download/v1/items/791c63fd7190477196de14a05177757c/geojson?layers=0"
curl -o transit_routes.geojson "https://services6.arcgis.com/fUWVlHWZNxUvTUh8/arcgis/rest/services/transit_routes/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
python3 tools/build_shapes.py --html index.html --network ids_jmk_sit.geojson --lines transit_routes.geojson
```

Skript nepotřebuje žádné knihovny mimo standardní Python. Kde zastávka leží dál než 200 m
od sítě nebo cesta nejde najít, zůstane mezi zastávkami rovná čára.

## Tramvaje 1953 (`tools/build_tram1953.py`)

V režimu **Brno v roce 1953** se přes letecké snímky kreslí tramvajová síť z roku 1953 (tlačítko
**Tramvaje 1953**): bíle tratě, které jezdí dodnes, oranžově tratě později zrušené (Kobližná,
Dornych, Olomoucká – Černovice, Stránská skála – Líšeň, Židenice, kasárna) a čárkovaně tratě
postavené až po roce 1953. Data jsou v `index.html` jako řádek `const T53=...`.

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

## Zdroje dat

- Jízdní řády: IDS JMK (GTFS, KORDIS JMK / data.brno.cz)
- Trasy linek: „Trasy linek IDS JMK“ a „Linky městské hromadné dopravy“ (DPMB), data.brno.cz
- Historická ortofotomapa (50. léta) © CENIA 2010, © GEODIS BRNO 2010; snímky VGHMÚř Dobruška, © MO ČR 2009
- Ortofoto ČR © ČÚZK, CC BY 4.0
- Tramvajová síť 1953: Seznam tramvajových tratí v Brně (Wikipedie, CC BY-SA), zrušené tratě © přispěvatelé OpenStreetMap (ODbL)
