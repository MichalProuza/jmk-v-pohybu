# jmk-v-pohybu

Animovaná mapa spojů IDS JMK – celý web je jeden soubor `index.html` (~4 MB), data v něm generují skripty v `tools/`.

- `index.html` **nikdy nečti celý**: řádky `const DATA=`, `const SHP=`, `const T53=` mají miliony znaků. Čti po částech
  (`sed -n … | cut -c1-400`, grep) a datové řádky needituj ručně.
- Skills v `.claude/skills/`: `uprava-stranky` (struktura a konvence kódu), `overeni-stranky` (syntaxe, konzole,
  snímky v Chromiu), `data-jizdniho-radu` (GTFS, trasy, tramvaje 1953).
- Komunikace, texty v UI, komentáře i commit zprávy česky.
