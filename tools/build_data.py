#!/usr/bin/env python3
"""Sestaví z GTFS IDS JMK data jízdního řádu pro jeden den a vloží je do index.html.

Vstupy:
  --gtfs   gtfs.zip (https://kordis-jmk.cz/gtfs/gtfs.zip, totéž co data.brno.cz
           „Jízdní řád IDS JMK ve formátu GTFS“)
  --html   index.html s vloženým řádkem `const DATA={...};`
  --date   den ve tvaru RRRR-MM-DD (výchozí: dnešek v Europe/Prague)
Výstup: do index.html se přepíše řádek `const DATA=...;` a datum v nadpisu
stránky. Řádek `const SHP=...;` (trasy) zůstane, ale po změně DATA už nesedí –
je potřeba znovu spustit tools/build_shapes.py.

Formát DATA (shodný s původní stránkou):
  routes     [zkratka linky, mód 0–6, název]
  stops      [lon, lat] jen zastávek, kterými ten den něco jede
  segs       [zastávka A, zastávka B, mód] – úseky mezi sousedními zastávkami
  trips      [linka, odjezd s, zastávka, +s, zastávka, +s, ...]; spoje
             z předchozího dne, které končí až po půlnoci, mají záporný čas
  places     [obec, lon, lat, spojů/den, histogram po hodinách, linky,
              první ranní spojení do centra Brna [odj, příj, přestupy],
              nejdelší pauza 5–22 h [od, do],
              poslední spojení z centra Brna domů [odj, příj, přestupy];
              časy ≥ 86400 jsou po půlnoci následujícího dne]
  stopPlace  index obce pro každou zastávku (Brno = 0)
  stopNames  názvy zastávek (každý jednou), stopName index do stopNames pro každou zastávku
  labels     popisky mapy – přebírají se z předchozí verze stránky

Skript nepotřebuje nic mimo standardní Python; běží asi 20 s.
"""
import argparse, bisect, collections, csv, datetime, io, json, re, sys, time, zipfile

CENTER_NAMES = {'Hlavní nádraží', 'ÚAN Zvonařka'}
BRNO_ZONES = {'100', '101'}
DAYS_ACC = ['pondělí', 'úterý', 'středu', 'čtvrtek', 'pátek', 'sobotu', 'neděli']
MONTHS_GEN = ['ledna', 'února', 'března', 'dubna', 'května', 'června',
              'července', 'srpna', 'září', 'října', 'listopadu', 'prosince']
DAY = 86400
FIRST_FROM = 3 * 3600      # první ranní spojení: odjezd od 3:00
LAST_FROM = 12 * 3600      # poslední spojení domů: odjezd z centra po poledni
NIGHT_END = 3 * 3600       # ... nejpozději ve 3:00 následujícího rána, doma do 4:00
EARLY_END = 4 * 3600       # doplnění nočních spojů v prvním dni feedu (viz build)
GAP_FROM, GAP_TO = 5 * 3600, 22 * 3600


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def read_csv(zf, name):
    with zf.open(name) as f:
        return list(csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig', newline='')))


def hms(s):
    h, m, sec = s.split(':')
    return int(h) * 3600 + int(m) * 60 + int(sec)


def route_mode(r):
    t = r['route_type']
    name = r['route_short_name']
    if t == '0': return 0
    if t == '800': return 1
    if t == '2': return 6
    if t == '4': return 4
    if name[:1] in ('N', 'n'): return 3
    digits = re.sub(r'\D', '', name)
    if digits and int(digits) < 100: return 2
    return 5


def active_services(cal, cal_dates, day):
    """Množina service_id platných pro den (datetime.date)."""
    d = day.strftime('%Y%m%d')
    dow = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'][day.weekday()]
    s = set()
    for c in cal:
        if c['start_date'] <= d <= c['end_date'] and c[dow] == '1':
            s.add(c['service_id'])
    for r in cal_dates:
        if r['date'] == d:
            if r['exception_type'] == '1': s.add(r['service_id'])
            else: s.discard(r['service_id'])
    return s


def place_of(stop):
    if stop['zone_id'] in BRNO_ZONES: return 'Brno'
    return stop['stop_name'].split(',', 1)[0].strip()


def lines_key(n):
    return (len(n), n)


def trip_end(f):
    t = f[1]
    for k in range(1, (len(f) - 1) // 2): t += f[1 + 2 * k]
    return t


def connections(trips, shift=0):
    """(odjezd, příjezd, ze zastávky, do zastávky, spoj) pro všechny úseky spojů."""
    out = []
    for ti, f in enumerate(trips):
        t = f[1] + shift; n = (len(f) - 1) // 2
        for k in range(1, n):
            t2 = t + f[1 + 2 * k]
            out.append((t, t2, f[2 * k], f[2 + 2 * k], (ti, shift)))
            t = t2
    return out


def journey_to(conns, n_stops, foot, origins, targets, start):
    """Nejdřívější příjezd do některé z `targets` při odjezdu z `origins` po `start`.
    Connection scan přes spoje seřazené podle odjezdu. Vrací [odjezd, příjezd, přestupy]."""
    INF = 1 << 60
    T = [INF] * n_stops          # nejdřívější čas, kdy jsme na zastávce
    N = [0] * n_stops            # počet použitých spojů
    D = [0] * n_stops            # odjezd z výchozí obce
    for o in origins: T[o] = start
    boarded = {}                 # spoj -> (počet spojů, odjezd z výchozí obce)
    best = (INF, 0, 0)
    i = bisect.bisect_left(conns, (start,))
    L = len(conns)
    while i < L:
        dep, arr, a, b, tr = conns[i]; i += 1
        if dep >= best[0]: break
        bt = boarded.get(tr)
        if T[a] <= dep:
            cand = (N[a] + 1, dep if a in origins else D[a])
            if bt is None or cand[0] < bt[0]: bt = boarded[tr] = cand
        if bt is None: continue
        n, d0 = bt
        if arr < T[b] or (arr == T[b] and n < N[b]):
            T[b] = arr; N[b] = n; D[b] = d0
            if b in targets and (arr < best[0] or (arr == best[0] and n - 1 < best[2])):
                best = (arr, d0, n - 1)
            for c, dur in foot.get(b, ()):
                t2 = arr + dur
                if t2 < T[c] or (t2 == T[c] and n < N[c]):
                    T[c] = t2; N[c] = n; D[c] = d0
                    if c in targets and (t2 < best[0] or (t2 == best[0] and n - 1 < best[2])):
                        best = (t2, d0, n - 1)
    if best[0] >= INF: return None
    return [best[1], best[0], best[2]]


def journey_from(rconns, n_stops, rfoot, origins, targets, earliest, latest, latest_arr):
    """Nejpozdější odjezd z `origins` (centrum), ze kterého se dá dojet do `targets` (obec).
    Zpětný connection scan přes spoje seřazené sestupně podle odjezdu; odjezd z centra
    musí být v intervalu <earliest, latest>, příjezd do obce nejpozději v latest_arr."""
    NEG = -(1 << 60)
    Lt = [NEG] * n_stops         # nejpozdější čas, kdy ze zastávky ještě stihneme dojet
    N = [0] * n_stops
    A = [0] * n_stops            # příjezd do cílové obce
    for t in targets: Lt[t] = latest_arr
    reached = {}                 # spoj -> (počet spojů, příjezd do cíle)
    best = (NEG, 0, 0)
    for dep, arr, a, b, tr in rconns:
        if dep < earliest or dep < best[0]: break
        rt = reached.get(tr)
        if Lt[b] >= arr:
            cand = (N[b] + 1, arr if b in targets else A[b])
            if rt is None or cand < rt: rt = reached[tr] = cand
        if rt is None: continue
        n, a1 = rt
        if a in origins:
            if dep <= latest and (dep > best[0] or (dep == best[0] and n - 1 < best[2])):
                best = (dep, a1, n - 1)
            continue
        if dep > Lt[a] or (dep == Lt[a] and n < N[a]):
            Lt[a] = dep; N[a] = n; A[a] = a1
            for c, dur in rfoot.get(a, ()):
                t2 = dep - dur
                if c in origins:
                    if t2 <= latest and (t2 > best[0] or (t2 == best[0] and n - 1 < best[2])):
                        best = (t2, a1, n - 1)
                elif t2 > Lt[c] or (t2 == Lt[c] and n < N[c]):
                    Lt[c] = t2; N[c] = n; A[c] = a1
    if best[0] <= NEG: return None
    return [best[0], best[1], best[2]]


def build(zf, day, old_labels):
    t0 = time.time()
    cal, cal_dates = read_csv(zf, 'calendar.txt'), read_csv(zf, 'calendar_dates.txt')
    prev, nxt = day - datetime.timedelta(days=1), day + datetime.timedelta(days=1)
    svc = {d: active_services(cal, cal_dates, d) for d in (prev, day, nxt)}
    # GTFS často začíná platit až dnešním dnem (nebo končí dneškem) – chybějící sousední den
    # nahradíme stejným dnem v týdnu o týden dál/dřív, jinak by chyběly noční spoje po půlnoci
    feed_starts = not svc[prev]
    for d, step in ((prev, 7), (nxt, -7)):
        if not svc[d]:
            sub = d + datetime.timedelta(days=step)
            svc[d] = active_services(cal, cal_dates, sub)
            log(f'GTFS nepokrývá {d}, použit jízdní řád dne {sub} (služeb {len(svc[d])})')
    # noční spoje po půlnoci mají v GTFS službu následujícího dne a v prvním dni feedu chybějí
    # -> ranní spoje do EARLY_END doplníme ze služeb, které platí o týden později a dnes ne
    early_svc = set()
    if feed_starts:
        early_svc = active_services(cal, cal_dates, day + datetime.timedelta(days=7)) - svc[day]
    routes_raw = {r['route_id']: r for r in read_csv(zf, 'routes.txt')}
    all_trips = read_csv(zf, 'trips.txt')
    by_day = {d: [t for t in all_trips if t['service_id'] in s] for d, s in svc.items()}
    early = [t for t in all_trips if t['service_id'] in early_svc]
    trip_ids = {t['trip_id'] for ts in (*by_day.values(), early) for t in ts}
    log(f'den {day}: služeb {len(svc[day])}, spojů {len(by_day[day])} '
        f'(předchozí den {len(by_day[prev])}, následující {len(by_day[nxt])}) ({time.time()-t0:.0f}s)')

    st_by_trip = collections.defaultdict(list)
    with zf.open('stop_times.txt') as f:
        for r in csv.DictReader(io.TextIOWrapper(f, encoding='utf-8-sig', newline='')):
            if r['trip_id'] in trip_ids:
                st_by_trip[r['trip_id']].append((int(r['stop_sequence']), hms(r['arrival_time']),
                                                 hms(r['departure_time']), r['stop_id']))
    log(f'zastávkové časy načteny ({time.time()-t0:.0f}s)')
    stops_raw = {s['stop_id']: s for s in read_csv(zf, 'stops.txt')}

    route_idx, routes = {}, []
    stop_idx, stops, stop_ids = {}, [], []

    def encode(raw):
        """Spoje -> [linka, odjezd, zastávka, +s, zastávka, ...]; doplňuje linky a zastávky."""
        out = []
        for t in raw:
            st = st_by_trip.get(t['trip_id'])
            if not st or len(st) < 2: continue
            st.sort()
            r = routes_raw[t['route_id']]
            ri = route_idx.get(r['route_id'])
            if ri is None:
                ri = route_idx[r['route_id']] = len(routes)
                routes.append([r['route_short_name'], route_mode(r), r['route_long_name']])
            last = len(st) - 1
            f = [ri]
            prev_t = None
            for k, (_, arr, dep, sid) in enumerate(st):
                si = stop_idx.get(sid)
                if si is None:
                    s = stops_raw[sid]
                    si = stop_idx[sid] = len(stops)
                    stops.append([round(float(s['stop_lon']), 5), round(float(s['stop_lat']), 5)])
                    stop_ids.append(sid)
                tt = arr if k == last else dep      # spoj končí příjezdem na konečnou
                f.append(tt if prev_t is None else tt - prev_t); f.append(si)
                prev_t = tt
            out.append(f)
        return out

    trips = encode(by_day[day])
    if early:
        have = {(f[0], f[1], f[2]) for f in trips}
        add = [f for f in encode(early) if f[1] < EARLY_END and (f[0], f[1], f[2]) not in have]
        trips += add
        log(f'GTFS začíná dnešním dnem, doplněno {len(add)} nočních spojů do {EARLY_END // 3600}:00 '
            f'z jízdního řádu o týden později')
    n_today = len(trips)
    # spoje z předchozí noci, které končí po půlnoci -> záporné časy
    for f in encode(by_day[prev]):
        if trip_end(f) >= DAY:
            f[1] -= DAY; trips.append(f)
    # spoje následujícího rána (jen pro poslední spojení domů)
    next_trips = [f for f in encode(by_day[nxt]) if f[1] < NIGHT_END + 3600]

    segs, seg_seen = [], set()
    for f in trips:
        mode = routes[f[0]][1]
        for k in range(1, (len(f) - 1) // 2):
            a, b = f[2 * k], f[2 + 2 * k]
            key = (min(a, b), max(a, b))
            if a != b and key not in seg_seen:
                seg_seen.add(key); segs.append([a, b, mode])
    log(f'linek {len(routes)}, zastávek {len(stops)}, úseků {len(segs)}, '
        f'spojů {n_today} + {len(trips)-n_today} z předchozí noci')

    # obce
    names = sorted({place_of(stops_raw[sid]) for sid in stop_ids} - {'Brno'})
    place_names = ['Brno'] + names
    place_idx = {n: i for i, n in enumerate(place_names)}
    stop_place = [place_idx[place_of(stops_raw[sid])] for sid in stop_ids]
    stop_names = sorted({stops_raw[sid]['stop_name'] for sid in stop_ids})
    sn_idx = {n: i for i, n in enumerate(stop_names)}
    stop_name = [sn_idx[stops_raw[sid]['stop_name']] for sid in stop_ids]
    NP = len(place_names)
    psum = [[0.0, 0.0, 0] for _ in range(NP)]
    for si, p in enumerate(stop_place):
        psum[p][0] += stops[si][0]; psum[p][1] += stops[si][1]; psum[p][2] += 1
    hist = [[0] * 24 for _ in range(NP)]
    lines = [set() for _ in range(NP)]
    deps = [[] for _ in range(NP)]      # odjezdy spojů z obce (jednou na spoj)
    for f in trips[:n_today]:
        ri = f[0]; t = f[1]; seen = set()
        n = (len(f) - 1) // 2
        for k in range(n):
            if k: t += f[1 + 2 * k]
            p = stop_place[f[2 + 2 * k]]
            lines[p].add(routes[ri][0])
            if k < n - 1 and p not in seen:
                seen.add(p); hist[p][(t // 3600) % 24] += 1; deps[p].append(t)

    # spojení do/z centra Brna
    center = {si for si, sid in enumerate(stop_ids) if stops_raw[sid]['stop_name'] in CENTER_NAMES}
    foot, rfoot = collections.defaultdict(list), collections.defaultdict(list)
    for r in read_csv(zf, 'transfers.txt'):
        a, b = stop_idx.get(r['from_stop_id']), stop_idx.get(r['to_stop_id'])
        if a is None or b is None or a == b: continue
        d = int(r['min_transfer_time'] or 0)
        foot[a].append((b, d)); rfoot[b].append((a, d))
    conns = sorted(connections(trips[:n_today]))
    rconns = sorted(connections(trips[:n_today]) + connections(next_trips, DAY), reverse=True)
    log(f'centrum: {len(center)} zastávek, přestupů {sum(map(len, foot.values()))}, '
        f'spojení {len(conns)} ({time.time()-t0:.0f}s)')
    place_stops = [set() for _ in range(NP)]
    for si, p in enumerate(stop_place): place_stops[p].add(si)
    places = []
    for p in range(NP):
        cx, cy, cn = psum[p]
        rec = [place_names[p], round(cx / cn, 5), round(cy / cn, 5), len(deps[p]), hist[p],
               sorted(lines[p], key=lines_key), None, None, None]
        d = sorted(x for x in deps[p] if GAP_FROM <= x <= GAP_TO)
        if len(d) >= 2:
            k = max(range(1, len(d)), key=lambda i: d[i] - d[i - 1])
            rec[7] = [d[k - 1], d[k]]
        if p:
            rec[6] = journey_to(conns, len(stops), foot, place_stops[p], center, FIRST_FROM)
            rec[8] = journey_from(rconns, len(stops), rfoot, center, place_stops[p],
                                  LAST_FROM, DAY + NIGHT_END, DAY + NIGHT_END + 3600)
        places.append(rec)
        if p % 200 == 0: log(f'  obce {p}/{NP} ({time.time()-t0:.0f}s)')
    log(f'obcí {NP}, bez ranního spojení {sum(1 for r in places[1:] if not r[6])}, '
        f'bez večerního {sum(1 for r in places[1:] if not r[8])} ({time.time()-t0:.0f}s)')
    return {'date': day.isoformat(), 'routes': routes, 'stops': stops, 'segs': segs,
            'trips': trips, 'places': places, 'stopPlace': stop_place,
            'stopNames': stop_names, 'stopName': stop_name, 'labels': old_labels}


def czech_date(d):
    return f'{DAYS_ACC[d.weekday()]} {d.day}. {MONTHS_GEN[d.month-1]} {d.year}'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gtfs', required=True)
    ap.add_argument('--html', default='index.html')
    ap.add_argument('--date', default=None, help='RRRR-MM-DD, výchozí dnešek (Europe/Prague)')
    ap.add_argument('--out', default=None, help='výstupní soubor (výchozí přepíše --html)')
    a = ap.parse_args()
    if a.date:
        day = datetime.date.fromisoformat(a.date)
    else:
        from zoneinfo import ZoneInfo
        day = datetime.datetime.now(ZoneInfo('Europe/Prague')).date()
    html = open(a.html, encoding='utf-8').read()
    m = re.search(r'^const DATA=(\{.*?\});$', html, re.M)
    if not m: sys.exit('v HTML chybí řádek const DATA=')
    old = json.loads(m.group(1))
    with zipfile.ZipFile(a.gtfs) as zf:
        data = build(zf, day, old.get('labels', []))
    if len(data['trips']) < 1000:
        sys.exit(f'podezřele málo spojů ({len(data["trips"])}), GTFS asi nepokrývá den {day}')
    line = 'const DATA=' + json.dumps(data, ensure_ascii=False, separators=(',', ':')) + ';'
    html = html[:m.start()] + line + html[m.end():]
    html, n = re.subn(r'(podle jízdního řádu na )[^<]+?\d{4}\.', lambda mm: mm.group(1) + czech_date(day) + '.',
                      html, count=1)
    if n != 1: log('varování: datum v nadpisu se nepodařilo přepsat')
    open(a.out or a.html, 'w', encoding='utf-8').write(html)
    log(f'zapsáno {len(line)/1e6:.2f} MB dat pro {czech_date(day)} do {a.out or a.html}')


if __name__ == '__main__':
    main()
