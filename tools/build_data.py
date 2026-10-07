#!/usr/bin/env python3
"""Vygeneruje datovou sadu (const DATA) pro zadaný den z GTFS IDS JMK.

  python3 tools/build_data.py --gtfs cesta/k/rozbalenemu/gtfs --date 2026-10-10 --out data/so.js

Formát odpovídá původním datům vloženým v index.html:
  routes    [zkratka, mód, název]  v pořadí routes.txt
  stops     [lon, lat]  v pořadí prvního použití ve spojích
  segs      [a, b, mód] neorientované dvojice sousedních zastávek
  trips     [route, t0, s0, dt, s, dt, s, ...]; na zastávce zvlášť příjezd a
            (liší-li se) odjezd; spoje předchozího dne přesahující půlnoc jsou
            posunuté o -24 h (záporné časy)
  places    [název, lon, lat, odjezdů, histogram[24], linky[], první spojení
            do centra, nejdelší pauza 5–22 h, poslední spojení z centra domů]
  stopPlace index místa pro každou zastávku
  labels    popisky mapy (tools/labels.json)

Odjezdů z místa = počet spojů, které místem projedou (jeden spoj = jeden odjezd).
První/poslední spojení se hledá algoritmem Connection Scan; přestup je možný
mezi zastávkami téže stanice (parent_station) s rezervou 3 min, na téže zastávce
1 min; centrum = Hlavní nádraží a ÚAN Zvonařka. Poslední spojení se hledá mezi
odjezdy z centra od 12:00 (včetně nočních po půlnoci), první spojení mezi
odjezdy z místa od 3:00.
"""
import argparse, csv, json, os, re, sys, datetime, collections, statistics, bisect

MODE_NAMES = ['tram', 'trol', 'bus', 'night', 'boat', 'reg', 'train']
CENTRE_PARENTS = {'U1146N170', 'U1696N29'}   # Hlavní nádraží, ÚAN Zvonařka
WD = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
CZ_DAYS = ['pondělí', 'úterý', 'středu', 'čtvrtek', 'pátek', 'sobotu', 'neděli']
CZ_MONTHS = ['ledna', 'února', 'března', 'dubna', 'května', 'června', 'července', 'srpna', 'září', 'října', 'listopadu', 'prosince']

def rd(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def tsec(x):
    h, m, s = x.split(':'); return int(h) * 3600 + int(m) * 60 + int(s)

def mode_of(r):
    t = r['route_type']; n = r['route_short_name']
    if t == '0': return 0
    if t == '2': return 6
    if t == '4': return 4
    if t in ('800', '11'): return 1
    if n.startswith('N'): return 3
    m = re.match(r'^[xšE]?(\d+)$', n)
    if m:
        v = int(m.group(1))
        if v < 40: return 1
        if v < 100: return 2
    return 5

def active_services(cal, cal_dates, date):
    d = date.strftime('%Y%m%d'); wd = WD[date.weekday()]
    s = {c['service_id'] for c in cal if c['start_date'] <= d <= c['end_date'] and c[wd] == '1'}
    for e in cal_dates:
        if e['date'] == d:
            if e['exception_type'] == '1': s.add(e['service_id'])
            else: s.discard(e['service_id'])
    return s

def place_of(stop):
    if stop['zone_id'] in ('100', '101'): return 'Brno'
    return stop['stop_name'].split(',')[0].strip()

def line_key(n): return (len(n), n)

class CSA:
    """Spojení s přestupy. conns = [(dep, arr, from, to, trip)] seřazené podle dep."""
    def __init__(self, conns, transfers, same):
        self.conns = conns
        self.by_dep = conns                                   # podle odjezdu
        self.by_arr = sorted(conns, key=lambda c: c[1])       # podle příjezdu
        self.transfers = transfers                            # stop -> [(stop2, dt)]
        self.same = same                                      # stop -> dt pro přestup na téže zastávce
        self.ntrips = 1 + max(c[4] for c in conns)

    def earliest(self, sources, targets, t0):
        """Nejdřívější příjezd do některé z targets při odjezdu ze sources od času t0.
        Vrací (odjezd ze zdroje, příjezd, přestupy) nebo None."""
        INF = 10 ** 9
        ea = collections.defaultdict(lambda: (INF, 0, None))  # stop -> (čas, přestupy, odjezd ze zdroje)
        for s in sources: ea[s] = (t0, -1, None)
        trip = {}                                             # trip -> (přestupy, odjezd ze zdroje)
        best = (INF, 0, None); targets = set(targets)
        i = bisect.bisect_left(self.by_dep, (t0, -1, '', '', -1))
        conns = self.by_dep
        while i < len(conns):
            dep, arr, u, v, tr = conns[i]; i += 1
            if dep > best[0]: break
            lab = trip.get(tr)
            if lab is None:
                e = ea.get(u)
                if e is not None and e[0] <= dep:
                    lab = (e[1] + 1, e[2] if e[2] is not None else dep); trip[tr] = lab
            if lab is None: continue
            k, d0 = lab
            def relax(w, t):
                cur = ea.get(w)
                if cur is None or t < cur[0] or (t == cur[0] and k < cur[1]):
                    ea[w] = (t, k, d0)
            relax(v, arr + self.same.get(v, 0))
            for w, dt in self.transfers.get(v, ()):
                relax(w, arr + dt)
            if v in targets and (arr < best[0] or (arr == best[0] and k < best[1])):
                best = (arr, k, d0)
        return None if best[2] is None else (best[2], best[0], best[1])

    def latest(self, sources, targets, tmax, tmin=0):
        """Nejpozdější odjezd ze sources tak, aby se dalo dojet do targets (do tmax).
        Vrací (odjezd, příjezd do cíle, přestupy) nebo None."""
        NEG = -10 ** 9
        la = collections.defaultdict(lambda: (NEG, 0, None))  # stop -> (nejpozdější čas na zastávce, přestupy, příjezd do cíle)
        for s in targets: la[s] = (tmax, -1, None)
        trip = {}
        best = (NEG, 0, None); sources = set(sources)
        conns = self.by_arr; i = len(conns) - 1
        same = self.same; transfers = self.transfers
        while i >= 0:
            dep, arr, u, v, tr = conns[i]; i -= 1
            if arr > tmax: continue
            if arr < best[0]: break
            lab = trip.get(tr)
            if lab is None:
                cands = []
                l = la.get(v)
                if l is not None:
                    if l[2] is None:  # v je cílová zastávka
                        cands.append((l[1] + 1, arr))
                    elif arr + same.get(v, 0) <= l[0]:
                        cands.append((l[1] + 1, l[2]))
                for w, dt in transfers.get(v, ()):
                    l = la.get(w)
                    if l is not None and l[2] is not None and arr + dt <= l[0]:
                        cands.append((l[1] + 1, l[2]))
                if cands:
                    lab = min(cands); trip[tr] = lab
            elif v in targets:
                lab = (0, arr); trip[tr] = lab   # vystoupit už na první zastávce cílového místa
            if lab is None: continue
            k, a1 = lab
            cur = la.get(u)
            if cur is None or cur[2] is None and cur[0] < dep or (cur[2] is not None and (dep > cur[0] or (dep == cur[0] and k < cur[1]))):
                if cur is None or cur[2] is not None: la[u] = (dep, k, a1)
            if u in sources and dep >= tmin and (dep > best[0] or (dep == best[0] and k < best[1])):
                best = (dep, k, a1)
        return None if best[2] is None else (best[0], best[2], best[1])

def prepare(gtfs, date):
    routes = rd(os.path.join(gtfs, 'routes.txt'))
    trips = rd(os.path.join(gtfs, 'trips.txt'))
    stops = {s['stop_id']: s for s in rd(os.path.join(gtfs, 'stops.txt'))}
    cal = rd(os.path.join(gtfs, 'calendar.txt'))
    cal_dates = rd(os.path.join(gtfs, 'calendar_dates.txt'))
    ridx = {r['route_id']: i for i, r in enumerate(routes)}
    rmode = [mode_of(r) for r in routes]
    act = active_services(cal, cal_dates, date)
    prev = active_services(cal, cal_dates, date - datetime.timedelta(days=1))
    tinfo = {t['trip_id']: t for t in trips}
    st = collections.defaultdict(list)
    with open(os.path.join(gtfs, 'stop_times.txt'), encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            sv = tinfo[row['trip_id']]['service_id']
            if sv in act or sv in prev:
                st[row['trip_id']].append((int(row['stop_sequence']), tsec(row['arrival_time']), tsec(row['departure_time']), row['stop_id']))
    for v in st.values(): v.sort()
    print(f'{date}: služeb {len(act)}, spojů se zastávkami {len(st)}', file=sys.stderr)

    stop_index = {}; stop_ids = []
    def sidx(sid):
        i = stop_index.get(sid)
        if i is None:
            i = len(stop_ids); stop_index[sid] = i; stop_ids.append(sid)
        return i

    out_trips = []; conns = []; conn_trip = 0
    dep_events = collections.defaultdict(list)   # place -> [čas odjezdu]
    place_lines = collections.defaultdict(set)
    seg_mode = {}
    def emit(tid, shift, is_day):
        nonlocal conn_trip
        rows = st[tid]; r = ridx[tinfo[tid]['route_id']]; m = rmode[r]
        enc = [r]; prevt = None; prev_stop = None
        for i, (_, a, d, sid) in enumerate(rows):
            times = [d] if i == 0 else ([a] if a == d else [a, d])
            si = sidx(sid)
            for tt in times:
                tt -= shift
                enc += ([tt, si] if prevt is None else [tt - prevt, si]); prevt = tt
            if prev_stop is not None and prev_stop != si:
                key = (min(prev_stop, si), max(prev_stop, si))
                if key not in seg_mode or m < seg_mode[key]: seg_mode[key] = m
            prev_stop = si
        out_trips.append(enc)
        if is_day:
            name = routes[r]['route_short_name']; seen = set()
            for i, (_, a, d, sid) in enumerate(rows):
                p = place_of(stops[sid]); place_lines[p].add(name)
                if p not in seen:
                    seen.add(p); dep_events[p].append(d)
        # spojení pro CSA (časy bez posunu, včetně >24 h; posunuté spoje předchozího dne s posunem)
        for (_, a0, d0, s0), (_, a1, d1, s1) in zip(rows, rows[1:]):
            conns.append((d0 - shift, a1 - shift, s0, s1, conn_trip))
        conn_trip += 1

    for t in trips:
        if t['service_id'] in act and t['trip_id'] in st: emit(t['trip_id'], 0, True)
    for t in trips:
        if t['service_id'] in prev and t['trip_id'] in st:
            rows = st[t['trip_id']]
            if rows[-1][2] > 86400: emit(t['trip_id'], 86400, False)
    print(f'spojů {len(out_trips)}, zastávek {len(stop_ids)}, úseků {len(seg_mode)}', file=sys.stderr)

    # místa
    names = sorted({place_of(stops[s]) for s in stop_ids} - {'Brno'})
    names = ['Brno'] + names
    pidx = {n: i for i, n in enumerate(names)}
    stop_place = [pidx[place_of(stops[s])] for s in stop_ids]
    place_stops = collections.defaultdict(list)
    for i, p in enumerate(stop_place): place_stops[p].append(stop_ids[i])

    conns.sort()
    centre = [s for s in stop_ids if stops[s]['parent_station'] in CENTRE_PARENTS or s in CENTRE_PARENTS]
    return dict(gtfs=gtfs, date=date, routes=routes, rmode=rmode, stops=stops, stop_ids=stop_ids, out_trips=out_trips,
                seg_mode=seg_mode, names=names, stop_place=stop_place, place_stops=place_stops, dep_events=dep_events,
                place_lines=place_lines, conns=conns, centre=centre)

def footpaths(P, opts):
    """Přestupní vazby: transfers.txt, volitelně + stejná stanice (parent_station) a blízké zastávky."""
    stops, stop_ids = P['stops'], P['stop_ids']
    transfers = collections.defaultdict(dict); same = {}
    used = set(stop_ids)
    if opts.get('use_transfers', True):
        for row in rd(os.path.join(P['gtfs'], 'transfers.txt')):
            a, b = row['from_stop_id'], row['to_stop_id']
            if a not in used or b not in used: continue
            dt = int(row['min_transfer_time'] or 0)
            if a == b: same[a] = dt
            else: transfers[a][b] = dt
    pdt = opts.get('parent_dt')
    if pdt is not None:
        byp = collections.defaultdict(list)
        for s in stop_ids:
            if stops[s]['parent_station']: byp[stops[s]['parent_station']].append(s)
        for grp in byp.values():
            for a in grp:
                for b in grp:
                    if a != b and b not in transfers[a]: transfers[a][b] = pdt
    rad = opts.get('near_m')
    if rad:
        import math
        cell = rad; g = collections.defaultdict(list)
        xy = {s: (float(stops[s]['stop_lon']) * 72700, float(stops[s]['stop_lat']) * 111200) for s in stop_ids}
        for s, (x, y) in xy.items(): g[(int(x // cell), int(y // cell))].append(s)
        for s, (x, y) in xy.items():
            cx, cy = int(x // cell), int(y // cell)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for b in g.get((cx + dx, cy + dy), ()):
                        if b == s: continue
                        d = math.hypot(xy[b][0] - x, xy[b][1] - y)
                        if d <= rad and b not in transfers[s]:
                            transfers[s][b] = opts.get('near_dt', 0) + int(d / opts.get('walk_mps', 1.0))
    sdt = opts.get('same_dt')
    if sdt is not None:
        for s in stop_ids: same.setdefault(s, sdt)
    return {a: list(b.items()) for a, b in transfers.items()}, same

DEFAULT_OPTS = dict(use_transfers=False, parent_dt=180, same_dt=60, last_from=12 * 3600, t0=3 * 3600)

def compute_places(P, labels, opts=None, limit=None, quiet=False):
    opts = dict(DEFAULT_OPTS, **(opts or {}))
    stops, names = P['stops'], P['names']
    transfers, same = footpaths(P, opts)
    csa = CSA(P['conns'], transfers, same)
    centre = P['centre']; t0 = opts.get('t0', 0)
    places = []
    for i, n in enumerate(names[:limit] if limit else names):
        ss = P['place_stops'][i]
        ss = P['place_stops'][i]
        if n == 'Brno': lon, lat = 16.6087, 49.1951
        else:
            lon = statistics.median(float(stops[s]['stop_lon']) for s in ss)
            lat = statistics.median(float(stops[s]['stop_lat']) for s in ss)
        deps = sorted(P['dep_events'][n])
        hist = [0] * 24
        for d in deps: hist[(d // 3600) % 24] += 1
        lines = sorted(P['place_lines'][n], key=line_key)
        mid = [d for d in deps if 5 * 3600 <= d <= 22 * 3600]
        gap = None
        if len(mid) >= 2:
            j = max(range(1, len(mid)), key=lambda k: mid[k] - mid[k - 1])
            gap = [mid[j - 1], mid[j]]
        first = last = None
        if i > 0:
            first = csa.earliest(ss, centre, t0)
            last = csa.latest(centre, ss, 86400 + 8 * 3600, opts.get('last_from', 0))
            if first: first = list(first)
            if last: last = list(last)
        places.append([n, round(lon, 5), round(lat, 5), len(deps), hist, lines, first, gap, last])
        if i % 100 == 0 and not quiet: print(f'  místa {i}/{len(names)}', file=sys.stderr)
    return places

def assemble(P, places, labels):
    stops, routes, rmode = P['stops'], P['routes'], P['rmode']
    return {
        'date': P['date'].isoformat(),
        'routes': [[r['route_short_name'], rmode[i], r['route_long_name']] for i, r in enumerate(routes)],
        'stops': [[round(float(stops[s]['stop_lon']), 5), round(float(stops[s]['stop_lat']), 5)] for s in P['stop_ids']],
        'segs': [[a, b, m] for (a, b), m in P['seg_mode'].items()],
        'trips': P['out_trips'],
        'places': places,
        'stopPlace': P['stop_place'],
        'labels': labels,
    }

def build(gtfs, date, labels, opts=None):
    P = prepare(gtfs, date)
    return assemble(P, compute_places(P, labels, opts), labels)

def cz_date(date):
    return f'{CZ_DAYS[date.weekday()]} {date.day}. {CZ_MONTHS[date.month - 1]} {date.year}'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gtfs', required=True)
    ap.add_argument('--date', required=True)
    ap.add_argument('--out', required=True, help='výstupní .js (const DATA=...;) nebo .json')
    ap.add_argument('--labels', default=os.path.join(os.path.dirname(__file__), 'labels.json'))
    ap.add_argument('--compare', help='soubor s const DATA= pro porovnání (např. původní index.html)')
    a = ap.parse_args()
    date = datetime.date.fromisoformat(a.date)
    labels = json.load(open(a.labels, encoding='utf-8'))
    D = build(a.gtfs, date, labels)
    D['label'] = cz_date(date)
    if a.compare:
        s = open(a.compare, encoding='utf-8').read()
        O = json.loads(re.search(r'^const DATA=(\{.*\});$', s, re.M).group(1))
        print('--- porovnání s', a.compare, file=sys.stderr)
        for k in ('routes', 'stops', 'segs', 'trips', 'stopPlace', 'labels'):
            print(f'  {k}: shoda {D[k] == O[k]} ({len(D[k])} vs {len(O[k])})', file=sys.stderr)
        if sorted(map(tuple, D['segs'])) == sorted(map(tuple, O['segs'])): print('  segs jako množina: shoda', file=sys.stderr)
        fields = ['název', 'lon', 'lat', 'odjezdů', 'hist', 'linky', 'první', 'pauza', 'poslední']
        if len(D['places']) == len(O['places']):
            for f in range(9):
                ok = sum(1 for p, q in zip(D['places'], O['places']) if p[f] == q[f])
                print(f'  places.{fields[f]}: shoda {ok}/{len(O["places"])}', file=sys.stderr)
            for f in (6, 8):
                ex = [(p[0], p[f], q[f]) for p, q in zip(D['places'], O['places']) if p[f] != q[f]][:6]
                for e in ex: print('    ', fields[f], e, file=sys.stderr)
        else:
            print(f'  places: {len(D["places"])} vs {len(O["places"])}', file=sys.stderr)
    js = json.dumps(D, ensure_ascii=False, separators=(',', ':'))
    with open(a.out, 'w', encoding='utf-8') as f:
        if a.out.endswith('.json'): f.write(js)
        else: f.write('const DATA=' + js + ';\n')
    print(f'zapsáno {a.out} ({len(js)/1e6:.2f} MB)', file=sys.stderr)

if __name__ == '__main__':
    main()
