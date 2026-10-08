---
name: data-jizdniho-radu
description: Data stránky jmk-v-pohybu – denní sestavení jízdního řádu z GTFS IDS JMK (tools/update_day.sh, build_data.py), přepočet tras po síti linek (build_shapes.py) a tramvajové sítě 1953 (build_tram1953.py, tram1953.json). Použij při aktualizaci na jiný den, chybách v datech (chybějící spoje, špatné časy, rovné čáry místo tras, špatné obce), změně formátu DATA nebo úpravách vrstvy Tramvaje 1953.
---

# Data jízdního řádu a tras

Data jsou vložená v `index.html` jako tři jednořádkové konstanty. Generují je skripty v `tools/`
(jen standardní Python + `curl`), **nikdy je needituj ručně a nečti celé** (viz skill `uprava-stranky`).

## Denní aktualizace

```bash
tools/update_day.sh             # dnešek (Europe/Prague)
tools/update_day.sh 2026-10-20  # konkrétní den
```

Stáhne GTFS (`https://kordis-jmk.cz/gtfs/gtfs.zip`), síť IDS JMK a `transit_routes` (data.brno.cz / ArcGIS),
spustí `build_data.py` (přepíše `const DATA=` a datum v nadpisu) a `build_shapes.py` (přepíše `const SHP=`).
Trvá ~30 s. Každé ráno to dělá Routine v Claude Code a commitne do `main`.
Pokud stahování selže na síťové politice prostředí, přečti `read_documentation` (environment.network).

## Formát DATA (zdroj pravdy: docstring `tools/build_data.py`)

- `date` RRRR-MM-DD
- `routes` `[linka, mód 0–6, název]` – módy: 0 tram, 1 trol, 2 bus MHD, 3 noční, 4 loď, 5 regionální bus, 6 vlak
- `stops` `[lon, lat]`; `stopPlace` index obce (Brno = 0); `stopNames` + `stopName` názvy zastávek
- `segs` `[zastávka A, zastávka B, mód]` – úseky sítě
- `trips` `[linka, odjezd s, zastávka, +s, zastávka, +s, …]` (delta časy; noční spoje z předchozího dne záporné)
- `places` `[obec, lon, lat, spojů/den, histogram 24 h, linky, první spojení do Brna, nejdelší pauza, poslední spojení domů]`
- `labels` popisky mapy – přebírají se z předchozí verze stránky (měnit je jde jen v `index.html`
  přes Python skript, který přepíše `DATA.labels`, nebo úpravou `build_data.py`)

Změna formátu = upravit `build_data.py` **i** dekódování v `index.html` (`const trips=DATA.trips.map…`, `PL`, `SP`…)
a docstring. Pak přegenerovat a ověřit (`overeni-stranky`).

Rychlý přehled dat bez vypsání celého řádku:

```bash
python3 - <<'PY'
import re, json
s = open('index.html').read()
d = json.loads(re.search(r'^const DATA=(.*?);?$', s, re.M).group(1).rstrip(';'))
for k, v in d.items(): print(k, len(v) if hasattr(v, '__len__') else v, str(v[:2] if isinstance(v, list) else v)[:150])
PY
```

## Trasy (`build_shapes.py`)

Nejkratší cesta po síti linek mezi sousedními zastávkami; kde je zastávka dál než `--snap` (200 m)
od sítě nebo cesta neexistuje, zůstane rovná čára. Výpis statistiky: `--dump soubor.json`.
Po každé změně `DATA` je nutné trasy přepočítat (update_day.sh to dělá sám):

```bash
python3 tools/build_shapes.py --html index.html --network ids_jmk_sit.geojson --lines transit_routes.geojson
```

## Tramvaje 1953 (`build_tram1953.py` + `tools/tram1953.json`)

Denní aktualizace vrstvu nemění. `tram1953.json`: `remove` – dvojice bodů, mezi kterými se z dnešní sítě
vyřízne úsek otevřený po roce 1953; `add` – geometrie zrušených tratí s rokem zrušení.
Zdroje a postup jsou v README (Wikipedie / Nesiba, OSM `railway=razed|abandoned`, ověření nad ortofotem).

```bash
python3 tools/build_tram1953.py --html index.html --lines transit_routes.geojson --defs tools/tram1953.json
```

## Pravidla

- Stažené podklady (`*.geojson`, `gtfs.zip`) dávej do scratchpadu/`mktemp`, ne do repozitáře.
- Po přegenerování zkontroluj `grep -o '"date":"[0-9-]*"' index.html` a nadpis, a spusť `overeni-stranky`.
- Commit jen s regenerovanými daty dělej jen když o to jde; při úpravě kódu na feature větvi nech data tak, jak jsou
  (jinak vznikají zbytečné konflikty s ranní aktualizací v `main`).
- Změna chování skriptů → aktualizuj README (oddíly o `update_day.sh`, `build_shapes.py`, Tramvaje 1953).
