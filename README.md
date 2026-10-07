# Jižní Morava v pohybu – 1953 a dnes

Animovaná mapa všech spojů IDS JMK (MHD Brno, regionální autobusy a vlaky) podle jízdního řádu,
s porovnáním leteckých snímků Brna z roku 1953 a dneška.

Celá stránka je jeden soubor `index.html` – data jízdních řádů i trasy jsou vložená přímo v něm,
žádný build ani server není potřeba.

Vozidla jedou po skutečných trasách linek (ulice, koleje), ne vzdušnou čarou.
Síť linek je ve výchozím stavu zobrazená, vypíná a zapíná se tlačítkem **Síť linek** v dolní liště
(vypnutý stav se ukládá do adresy jako `#bezsite`).

## Přepočet tras (`tools/build_shapes.py`)

Trasy mezi sousedními zastávkami se počítají jako nejkratší cesta po síti linek IDS JMK
a vkládají se do `index.html` jako řádek `const SHP=...`. Po změně jízdních řádů (nový `DATA`)
je potřeba je přepočítat:

```bash
curl -L -o ids_jmk_sit.geojson "https://data.brno.cz/api/download/v1/items/791c63fd7190477196de14a05177757c/geojson?layers=0"
curl -o transit_routes.geojson "https://services6.arcgis.com/fUWVlHWZNxUvTUh8/arcgis/rest/services/transit_routes/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
python3 tools/build_shapes.py --html index.html --network ids_jmk_sit.geojson --lines transit_routes.geojson
```

Skript nepotřebuje žádné knihovny mimo standardní Python. Kde zastávka leží dál než 200 m
od sítě nebo cesta nejde najít, zůstane mezi zastávkami rovná čára.

## Publikace přes GitHub Pages

1. Na GitHubu otevři **Settings → Pages**.
2. V části **Build and deployment** zvol **Source: Deploy from a branch**.
3. Vyber větev `main` a složku `/ (root)`, ulož.
4. Za pár minut bude stránka dostupná na `https://michalprouza.github.io/jmk-v-pohybu/`.

Soubor `.nojekyll` říká GitHubu, aby stránku jen zkopíroval a nespouštěl na ní Jekyll.

## Zdroje dat

- Jízdní řády: IDS JMK
- Trasy linek: „Trasy linek IDS JMK“ a „Linky městské hromadné dopravy“ (DPMB), data.brno.cz
- Historická ortofotomapa (50. léta) © CENIA 2010, © GEODIS BRNO 2010; snímky VGHMÚř Dobruška, © MO ČR 2009
- Ortofoto ČR © ČÚZK, CC BY 4.0
