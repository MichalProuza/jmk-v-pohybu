#!/usr/bin/env bash
# Přegeneruje index.html podle jízdního řádu na zadaný den (výchozí dnešek v Europe/Prague):
# stáhne GTFS IDS JMK a sítě linek, sestaví DATA (tools/build_data.py) a trasy (tools/build_shapes.py).
# Použití: tools/update_day.sh [RRRR-MM-DD]
set -euo pipefail
cd "$(dirname "$0")/.."
DATE=${1:-$(TZ=Europe/Prague date +%F)}
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

echo "== stahuji podklady" >&2
curl -fsSL --retry 3 --retry-delay 10 -o "$TMP/gtfs.zip" "https://kordis-jmk.cz/gtfs/gtfs.zip"
curl -fsSL --retry 3 --retry-delay 10 -o "$TMP/ids_jmk_sit.geojson" \
  "https://data.brno.cz/api/download/v1/items/791c63fd7190477196de14a05177757c/geojson?layers=0"
curl -fsSL --retry 3 --retry-delay 10 -o "$TMP/transit_routes.geojson" \
  "https://services6.arcgis.com/fUWVlHWZNxUvTUh8/arcgis/rest/services/transit_routes/FeatureServer/0/query?where=1%3D1&outFields=*&outSR=4326&f=geojson"
python3 -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).testzip()" "$TMP/gtfs.zip"

echo "== sestavuji data na $DATE" >&2
python3 tools/build_data.py --gtfs "$TMP/gtfs.zip" --html index.html --date "$DATE"

echo "== přepočítávám trasy" >&2
python3 tools/build_shapes.py --html index.html --network "$TMP/ids_jmk_sit.geojson" --lines "$TMP/transit_routes.geojson"

grep -q "\"date\":\"$DATE\"" index.html || { echo "index.html neobsahuje datum $DATE" >&2; exit 1; }
echo "== hotovo: index.html platí pro $DATE" >&2
