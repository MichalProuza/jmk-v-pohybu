# Jižní Morava v pohybu – 1953 a dnes

Animovaná mapa všech spojů IDS JMK (MHD Brno, regionální autobusy a vlaky) podle jízdního řádu,
s porovnáním leteckých snímků Brna z roku 1953 a dneška.

Celá stránka je jeden soubor `index.html` – data jízdních řádů i trasy jsou vložená přímo v něm,
žádný build ani server není potřeba.

Vozidla jedou po skutečných trasách linek (ulice, koleje), ne vzdušnou čarou.
Síť linek je ve výchozím stavu zobrazená, vypíná a zapíná se tlačítkem **Síť linek** v dolní liště
(vypnutý stav se ukládá do adresy jako `#bezsite`).

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
