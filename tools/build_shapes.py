#!/usr/bin/env python3
"""Sestaví reálné trasy mezi sousedními zastávkami a vloží je do index.html.

Vstupy:
  --html      index.html s vloženým `const DATA={...};`
  --network   GeoJSON sítě linek IDS JMK (data.brno.cz, „Trasy linek IDS JMK“),
              MultiLineString se všemi úseky, po kterých linky IDS JMK jezdí
  --lines     volitelně GeoJSON „Linky MHD“ DPMB (data.brno.cz, transit_routes):
              z prvků typ=tramvaj vznikne kolejová síť pro tramvaje, z typ=vlak
              železniční síť pro vlaky v okolí Brna (přesnější než síť IDS JMK)
  --rail      volitelně Overpass JSON s železničními kolejemi (railway=rail),
              použije se přednostně pro vlaky
Výstup: do index.html se za řádek s DATA zapíše řádek `const SHP=[...];`
(pole zarovnané s DATA.segs, pro každý úsek Google-encoded polyline mezilehlých
bodů ve směru segs[i][0] -> segs[i][1]; prázdný řetězec = rovná čára).

Postup: síť se převede na graf (uzly = sdílené souřadnice), každá zastávka se
přichytí na nejbližší hranu do 200 m, mezi každou dvojicí sousedních zastávek
se najde nejkratší cesta (A*). Když cesta vyjde nesmyslně dlouhá proti vzdušné
vzdálenosti, zůstane rovná čára.
"""
import argparse, json, math, re, sys, heapq, collections, time

KX = math.cos(49.195 * math.pi / 180) * 111200.0
KY = 111200.0
LON0, LAT0 = 16.61, 49.195

def proj(lon, lat):
    return ((lon - LON0) * KX, (lat - LAT0) * KY)

def unproj(x, y):
    return (x / KX + LON0, y / KY + LAT0)

class Graph:
    def __init__(self):
        self.coord = {}      # rounded (lon,lat) -> node id
        self.xy = []         # node id -> (x,y)
        self.ll = []         # node id -> (lon,lat)
        self.adj = []        # node id -> list of (nbr, length)
        self.edges = []      # (u,v) for spatial index
        self.cell = 250.0
        self.grid = collections.defaultdict(list)

    def node(self, lon, lat):
        k = (round(lon, 7), round(lat, 7))
        i = self.coord.get(k)
        if i is None:
            i = len(self.xy); self.coord[k] = i
            self.xy.append(proj(lon, lat)); self.ll.append((lon, lat)); self.adj.append([])
        return i

    def add_edge(self, u, v):
        if u == v: return
        (x1, y1), (x2, y2) = self.xy[u], self.xy[v]
        d = math.hypot(x2 - x1, y2 - y1)
        self.adj[u].append((v, d)); self.adj[v].append((u, d))
        eid = len(self.edges); self.edges.append((u, v))
        for cx in range(int(min(x1, x2) // self.cell), int(max(x1, x2) // self.cell) + 1):
            for cy in range(int(min(y1, y2) // self.cell), int(max(y1, y2) // self.cell) + 1):
                self.grid[(cx, cy)].append(eid)

    def add_line(self, coords):
        prev = None
        for lon, lat in coords:
            n = self.node(lon, lat)
            if prev is not None: self.add_edge(prev, n)
            prev = n

    def nearest_edge(self, x, y, maxd):
        r = int(maxd // self.cell) + 1
        cx, cy = int(x // self.cell), int(y // self.cell)
        best = (maxd * maxd, None, 0.0)
        seen = set()
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                for eid in self.grid.get((cx + dx, cy + dy), ()):
                    if eid in seen: continue
                    seen.add(eid)
                    u, v = self.edges[eid]
                    if u < 0: continue  # removed
                    (x1, y1), (x2, y2) = self.xy[u], self.xy[v]
                    ddx, ddy = x2 - x1, y2 - y1
                    L2 = ddx * ddx + ddy * ddy
                    t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((x - x1) * ddx + (y - y1) * ddy) / L2))
                    px, py = x1 + t * ddx, y1 + t * ddy
                    d2 = (px - x) * (px - x) + (py - y) * (py - y)
                    if d2 < best[0]: best = (d2, eid, t)
        return best

    def split_edge(self, eid, t):
        """Vloží uzel na hranu v parametru t a vrátí jeho id."""
        u, v = self.edges[eid]
        if t < 1e-6: return u
        if t > 1 - 1e-6: return v
        (x1, y1), (x2, y2) = self.xy[u], self.xy[v]
        lon1, lat1 = self.ll[u]; lon2, lat2 = self.ll[v]
        n = len(self.xy)
        self.xy.append((x1 + t * (x2 - x1), y1 + t * (y2 - y1)))
        self.ll.append((lon1 + t * (lon2 - lon1), lat1 + t * (lat2 - lat1)))
        self.adj.append([])
        # odpojit původní hranu
        self.adj[u] = [(w, d) for (w, d) in self.adj[u] if w != v]
        self.adj[v] = [(w, d) for (w, d) in self.adj[v] if w != u]
        self.edges[eid] = (-1, -1)
        self.add_edge(u, n); self.add_edge(n, v)
        return n

    def astar(self, s, g, limit):
        if s == g: return [s], 0.0
        xy = self.xy; gx, gy = xy[g]
        h = lambda n: math.hypot(xy[n][0] - gx, xy[n][1] - gy)
        dist = {s: 0.0}; prev = {}
        pq = [(h(s), 0.0, s)]
        while pq:
            f, d, n = heapq.heappop(pq)
            if n == g:
                path = [g]
                while path[-1] != s: path.append(prev[path[-1]])
                return path[::-1], d
            if d > dist.get(n, 1e18) or d > limit: continue
            for w, L in self.adj[n]:
                nd = d + L
                if nd < dist.get(w, 1e18):
                    dist[w] = nd; prev[w] = n
                    heapq.heappush(pq, (nd + h(w), nd, w))
        return None, None

def simplify(pts, tol):
    """Douglas–Peucker, pts = [(x,y)] v metrech."""
    if len(pts) <= 2: return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True
    stack = [(0, len(pts) - 1)]
    while stack:
        a, b = stack.pop()
        ax, ay = pts[a]; bx, by = pts[b]
        dx, dy = bx - ax, by - ay; L2 = dx * dx + dy * dy
        imax, dmax = -1, tol * tol
        for i in range(a + 1, b):
            px, py = pts[i]
            if L2 == 0: d2 = (px - ax) ** 2 + (py - ay) ** 2
            else:
                t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L2))
                d2 = (px - (ax + t * dx)) ** 2 + (py - (ay + t * dy)) ** 2
            if d2 > dmax: imax, dmax = i, d2
        if imax >= 0:
            keep[imax] = True; stack.append((a, imax)); stack.append((imax, b))
    return [p for p, k in zip(pts, keep) if k]

def encode_polyline(coords):
    """Google encoded polyline, přesnost 1e-5; coords = [(lon,lat)]."""
    out = []; plat = plon = 0
    for lon, lat in coords:
        ilat, ilon = round(lat * 1e5), round(lon * 1e5)
        for v in (ilat - plat, ilon - plon):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1f)) + 63)); v >>= 5
            out.append(chr(v + 63))
        plat, plon = ilat, ilon
    return ''.join(out)

def load_network(path):
    d = json.load(open(path, encoding='utf-8'))
    lines = []
    for f in d['features']:
        g = f.get('geometry')
        if not g: continue
        if g['type'] == 'LineString': lines.append(g['coordinates'])
        elif g['type'] == 'MultiLineString': lines.extend(g['coordinates'])
    return lines

def load_overpass_ways(path):
    d = json.load(open(path, encoding='utf-8'))
    return [[(p['lon'], p['lat']) for p in e['geometry']] for e in d['elements'] if e.get('type') == 'way' and e.get('geometry')]

def build_graph(lines):
    g = Graph()
    for c in lines: g.add_line(c)
    return g

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--html', default='index.html')
    ap.add_argument('--network', required=True)
    ap.add_argument('--rail')
    ap.add_argument('--lines')
    ap.add_argument('--snap', type=float, default=200.0, help='max. vzdálenost přichycení zastávky k síti [m]')
    ap.add_argument('--tol', type=float, default=3.0, help='tolerance zjednodušení [m]')
    ap.add_argument('--dump', help='uložit i čitelný JSON se statistikou')
    a = ap.parse_args()

    html = open(a.html, encoding='utf-8').read()
    m = re.search(r'^const DATA=(\{.*\});$', html, re.M)
    DATA = json.loads(m.group(1))
    stops = DATA['stops']; routes = DATA['routes']; segs = DATA['segs']
    nst = len(stops)
    mode_names = ['tram', 'trol', 'bus', 'night', 'boat', 'reg', 'train']

    # které módy jezdí mezi kterými dvojicemi (neorientovaně)
    pair_modes = collections.defaultdict(set)
    for f in DATA['trips']:
        md = routes[f[0]][1]; n = (len(f) - 1) // 2
        S = [f[2 + 2 * i] for i in range(n)]
        for x, y in zip(S, S[1:]):
            if x != y: pair_modes[(min(x, y), max(x, y))].add(md)
    seg_index = {(min(s[0], s[1]), max(s[0], s[1])): i for i, s in enumerate(segs)}
    extra = [k for k in pair_modes if k not in seg_index]
    print(f'zastávek {nst}, segs {len(segs)}, dvojic z jízd {len(pair_modes)}, mimo segs {len(extra)}', file=sys.stderr)

    t0 = time.time()
    nets = {'road': build_graph(load_network(a.network))}
    print(f'síť IDS JMK: uzlů {len(nets["road"].xy)}, hran {len(nets["road"].edges)} ({time.time()-t0:.1f}s)', file=sys.stderr)
    if a.rail:
        nets['rail'] = build_graph(load_overpass_ways(a.rail))
        print(f'železnice OSM: uzlů {len(nets["rail"].xy)}, hran {len(nets["rail"].edges)}', file=sys.stderr)
    if a.lines:
        d = json.load(open(a.lines, encoding='utf-8'))
        for typ, name in (('tramvaj', 'tram'), ('vlak', 'rail_brno')):
            lines = []
            for f in d['features']:
                g = f.get('geometry')
                if not g or f['properties'].get('typ') != typ: continue
                lines.extend(g['coordinates'] if g['type'] == 'MultiLineString' else [g['coordinates']])
            nets[name] = build_graph(lines)
            print(f'DPMB {typ}: uzlů {len(nets[name].xy)}, hran {len(nets[name].edges)}', file=sys.stderr)
    snap_dist = {'tram': 60.0, 'rail': 150.0, 'rail_brno': 150.0, 'road': a.snap}

    def nets_for(modes):
        """Pořadí sítí, na kterých se zkouší najít cesta."""
        order = []
        if modes == {0}: order.append('tram')
        if modes == {6}: order += ['rail', 'rail_brno']
        order.append('road')
        return [n for n in order if n in nets]

    # přichycení zastávek: pro každou síť zvlášť (uzel vzniká jen tam, kde je potřeba)
    snapped = {}  # (netname, stop) -> node | None
    def snap(netname, si):
        k = (netname, si)
        if k in snapped: return snapped[k]
        g = nets[netname]; x, y = proj(*stops[si])
        d2, eid, t = g.nearest_edge(x, y, snap_dist[netname])
        n = g.split_edge(eid, t) if eid is not None else None
        snapped[k] = n
        return n

    out = [''] * len(segs); extra_out = []
    stats = collections.Counter(); ratios = []
    cache = {}
    def route(key, modes):
        if key in cache: return cache[key]
        s1, s2 = key
        (x1, y1), (x2, y2) = proj(*stops[s1]), proj(*stops[s2])
        straight = math.hypot(x2 - x1, y2 - y1)
        if straight < 15:
            stats['rovné'] += 1; cache[key] = ''; return ''
        why = 'nesnapnuto'
        for netname in nets_for(modes):
            g = nets[netname]
            n1, n2 = snap(netname, s1), snap(netname, s2)
            if n1 is None or n2 is None: continue
            path, L = g.astar(n1, n2, 4.0 * straight + 1500.0)
            if path is None: why = 'bez cesty'; continue
            if L > 3.0 * straight + 600.0:
                # typicky nepropojené jízdní pruhy v síti: objížďka přes celý blok; radši rovně
                why = 'podezřelá objížďka'; continue
            stats['síť ' + netname] += 1
            return finish(key, g, path, L, straight)
        stats[why] += 1; cache[key] = ''; return ''

    def finish(key, g, path, L, straight):
        s1, s2 = key
        (x1, y1), (x2, y2) = proj(*stops[s1]), proj(*stops[s2])
        ratios.append((L + 1) / (straight + 1))
        pts = [(x1, y1)] + [g.xy[n] for n in path] + [(x2, y2)]
        pts = simplify(pts, a.tol)
        inner = pts[1:-1]
        if not inner:
            stats['rovné'] += 1; cache[key] = ''; return ''
        enc = encode_polyline([unproj(x, y) for x, y in inner])
        stats['ok'] += 1; cache[key] = enc
        return enc

    t0 = time.time()
    for i, s in enumerate(segs):
        key = (min(s[0], s[1]), max(s[0], s[1]))
        modes = pair_modes.get(key, {s[2]})
        enc = route(key, modes)
        if enc and s[0] > s[1]:
            # uložené body jdou od menšího indexu; otočit do směru segs[i]
            enc = encode_polyline(decode_polyline(enc)[::-1])
        out[i] = enc
        if i % 2000 == 0: print(f'  {i}/{len(segs)} ({time.time()-t0:.0f}s)', file=sys.stderr)
    for key in extra:
        enc = route(key, pair_modes[key])
        if enc: extra_out.append([key[0], key[1], enc])

    ratios.sort()
    print('výsledek:', dict(stats), file=sys.stderr)
    if ratios:
        print(f'poměr cesta/vzdušná: medián {ratios[len(ratios)//2]:.2f}, p90 {ratios[int(len(ratios)*.9)]:.2f}, max {ratios[-1]:.2f}', file=sys.stderr)
    SHP = {'segs': out, 'x': extra_out}
    line = 'const SHP=' + json.dumps(SHP, ensure_ascii=False, separators=(',', ':')) + ';\n'
    if re.search(r'^const SHP=.*$\n', html, re.M):
        html = re.sub(r'^const SHP=.*$\n', lambda _: line, html, count=1, flags=re.M)
    else:
        html = html.replace(m.group(0) + '\n', m.group(0) + '\n' + line, 1)
    open(a.html, 'w', encoding='utf-8').write(html)
    print(f'zapsáno {len(line)/1e6:.2f} MB do {a.html}', file=sys.stderr)
    if a.dump:
        json.dump({'stats': stats, 'segs': out, 'x': extra_out}, open(a.dump, 'w'), ensure_ascii=False)

def decode_polyline(s):
    coords = []; i = 0; lat = lon = 0
    while i < len(s):
        for which in (0, 1):
            shift = result = 0
            while True:
                b = ord(s[i]) - 63; i += 1
                result |= (b & 0x1f) << shift; shift += 5
                if b < 0x20: break
            d = ~(result >> 1) if result & 1 else result >> 1
            if which == 0: lat += d
            else: lon += d
        coords.append((lon / 1e5, lat / 1e5))
    return coords

if __name__ == '__main__':
    main()
