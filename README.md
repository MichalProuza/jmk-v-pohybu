# Jižní Morava v pohybu – 1953 a dnes

Animovaná mapa všech spojů IDS JMK (MHD Brno, regionální autobusy a vlaky) podle jízdního řádu,
s porovnáním leteckých snímků Brna z roku 1953 a dneška.

Stránka je statická: `index.html` obsahuje kód, data jízdních řádů jsou ve složce `data/`
po dnech (`st.js` všední den, `so.js` sobota, `ne.js` neděle). Den se přepíná výběrem
v dolní liště, do adresy se ukládá jako `#den=so` nebo `#den=ne`. Žádný build ani server
není potřeba.

Vozidla jedou po skutečných trasách linek (ulice, koleje), ne vzdušnou čarou.
Síť linek je ve výchozím stavu zobrazená, vypíná a zapíná se tlačítkem **Síť linek** v dolní liště
(vypnutý stav se ukládá do adresy jako `#bezsite`).

## Generování dat (`tools/build_data.py`)

Data pro jeden den vznikají z GTFS IDS JMK (data.brno.cz, „Jízdní řády IDS JMK ve formátu GTFS“):

```bash
curl -L -o gtfs.zip "https://www.arcgis.com/sharing/rest/content/items/379d2e9a7907460c8ca7fda1f3e84328/data"
mkdir gtfs && unzip gtfs.zip -d gtfs
python3 tools/build_data.py --gtfs gtfs --date 2026-10-07 --out data/st.js
python3 tools/build_data.py --gtfs gtfs --date 2026-10-10 --out data/so.js
python3 tools/build_data.py --gtfs gtfs --date 2026-10-11 --out data/ne.js
```

Skript vybere spoje jedoucí v daný den (včetně nočních spojů předchozího dne po půlnoci),
spočítá pro každou obec počet odjezdů, histogram, linky, první ranní spojení do centra Brna,
poslední spojení z centra domů a nejdelší pauzu mezi odjezdy. Popisky mapy bere z `tools/labels.json`.

## Přepočet tras (`tools/build_shapes.py`)

Trasy mezi sousedními zastávkami se počítají jako nejkratší cesta po síti linek IDS JMK
a vkládají se do datového souboru jako řádek `const SHP=...`. Po vygenerování dat je potřeba je doplnit:

```bash
curl -L -o ids_jmk_sit.geojson "https://data.brno.cz/api/download/v1/items/791c63fd7190477196de14a05177757c/geojson?layers=0"
curl -o transit_routes.geojson "https://services6.arcgis.com/fUWVlHWZNxUvTUh8/arcgis/rest/services/transit_routes/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
for d in st so ne; do python3 tools/build_shapes.py --html data/$d.js --network ids_jmk_sit.geojson --lines transit_routes.geojson; done
```

Oba skripty nepotřebují žádné knihovny mimo standardní Python. Kde zastávka leží dál než 200 m
od sítě nebo cesta nejde najít, zůstane mezi zastávkami rovná čára.

## Publikace přes GitHub Pages

1. Na GitHubu otevři **Settings → Pages**.
2. V části **Build and deployment** zvol **Source: Deploy from a branch**.
3. Vyber větev `main` a složku `/ (root)`, ulož.
4. Za pár minut bude stránka dostupná na `https://michalprouza.github.io/jmk-v-pohybu/`.

Soubor `.nojekyll` říká GitHubu, aby stránku jen zkopíroval a nespouštěl na ní Jekyll.

## Zdroje dat

- Jízdní řády: GTFS IDS JMK (KORDIS JMK, DPMB), data.brno.cz
- Trasy linek: „Trasy linek IDS JMK“ a „Linky městské hromadné dopravy“ (DPMB), data.brno.cz
- Historická ortofotomapa (50. léta) © CENIA 2010, © GEODIS BRNO 2010; snímky VGHMÚř Dobruška, © MO ČR 2009
- Ortofoto ČR © ČÚZK, CC BY 4.0
