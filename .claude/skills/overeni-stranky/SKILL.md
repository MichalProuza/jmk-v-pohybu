---
name: overeni-stranky
description: Ověří, že index.html projektu jmk-v-pohybu funguje – kontrola syntaxe JavaScriptu, chyb v konzoli a snímky obrazovky v headless Chromiu (desktop, mobil, tmavý režim, libovolný stav přes parametry adresy). Použij po každé úpravě stránky před commitem a vždy, když uživatel chce vidět, jak stránka vypadá, nebo hlásí, že něco nefunguje.
---

# Ověření stránky

Skript `check.mjs` vedle tohoto souboru:

1. vytáhne inline `<script>` z `index.html` a zkontroluje syntaxi (`node --check`),
2. otevře stránku v headless Chromiu (Playwright z globálních npm modulů, prohlížeč z `/opt/pw-browsers`),
3. pro každý zadaný hash udělá snímek a vypíše čas, počet vozidel a výsledný hash,
4. vypíše JS chyby a `console.error`; při chybě skončí s kódem 1.

```bash
SHOTS=<scratchpad>/shots   # snímky patří do scratchpadu, ne do repozitáře
node .claude/skills/overeni-stranky/check.mjs --out "$SHOTS"                       # výchozí stav
node .claude/skills/overeni-stranky/check.mjs --out "$SHOTS" "#cas=08:00&rekordy"  # víc stavů = víc snímků
node .claude/skills/overeni-stranky/check.mjs --out "$SHOTS" --mobile --dark "#cas=17:30&1953"
```

Snímky si prohlédni nástrojem Read (je to obrázek) a když je výsledek pro uživatele zajímavý, pošli mu je.

## Užitečné stavy v adrese

| hash | stav |
|---|---|
| `cas=HH:MM` | čas dne (zastaví přehrávání) |
| `pohled=lon,lat,zoom` | výřez mapy, např. `16.6080,49.1950,9000` centrum Brna, zoom < 2000 = celý kraj |
| `spoj=linka@HH:MM` | otevře kartu spoje a sleduje ho (odjezd z výchozí zastávky) |
| `obec=Název` | karta obce, např. `obec=Kuřim` |
| `1953` | režim Brno v roce 1953 |
| `rekordy` | karta Rekordy dne |
| `expozice` | Dlouhá expozice |
| `bezsite` | vypnutá síť linek |

Parametry se spojují `&`. Po načtení stránka `cas/pohled/spoj` z adresy odstraní, to je správně.

## Omezení

- Síť je zablokovaná (všechny `http(s)` požadavky se ruší): fonty Barlow se nenačtou (použije se náhradní
  písmo) a v režimu 1953 nejsou letecké snímky. Rozvržení, data, vozidla a karty se tím neovlivní.
- Animace běží: snímek se pořizuje ~2,5 s po načtení. Pro deterministický obraz zadej `cas=`.
- Interakce (klik, tažení) se dá doplnit přímo do skriptu přes `page.mouse` / `page.click('#id')`
  – pro jednorázovou kontrolu napiš vlastní krátký skript do scratchpadu podle `check.mjs`.
