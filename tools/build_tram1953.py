#!/usr/bin/env python3
"""Sestaví vrstvu „Tramvaje 1953“ a vloží ji do index.html jako řádek `const T53={...};`.

Vstupy:
  --html    index.html
  --lines   GeoJSON „Linky MHD“ DPMB (data.brno.cz, transit_routes), z prvků typ=tramvaj
            vznikne dnešní tramvajová síť
  --defs    tools/tram1953.json: úseky postavené po roce 1953 (`remove`, dvojice bodů a–b,
            mezi nimiž se úsek vyřízne z dnešní sítě) a úseky, které v roce 1953 existovaly
            a dnes už ne (`add`, souřadnice z OpenStreetMap, rok zrušení `z`)

Výstup: řádek `const T53={"o":[...],"z":[[název,rok,poly],...],"n":[...],"km":[1953,dnes]};`
  o  … tratě z roku 1953, které jsou v provozu dodnes
  z  … tratě z roku 1953, které byly později zrušeny
  n  … dnešní tratě postavené až po roce 1953
Polylinie jsou ve formátu Google encoded polyline (stejně jako `SHP`).

Postup: trasy všech tramvajových linek se sloučí do jedné sítě (souběžné úseky do 6 m
se berou jako jedna trať), úseky z `remove` se v ní označí jako nové a ke zbytku se přidají
zrušené tratě z `add`. Vrstva se mění jen při změně tramvajové sítě, denní aktualizace
(tools/update_day.sh) ji nepřepočítává.
"""
import argparse, json, math, re, sys, collections

KX = math.cos(49.195 * math.pi / 180) * 111200.0
KY = 111200.0
LON0, LAT0 = 16.61, 49.195
DEDUP = 6.0     # m: bod do této vzdálenosti od už přidané trati je souběh
MARK = 15.0     # m: úsek do této vzdálenosti od vyříznuté trasy je nový
STEP = 8.0      # m: zhuštění polylinií před porovnáváním

def proj(p):
    return ((p[0] - LON0) * KX, (p[1] - LAT0) * KY)

def unproj(q):
    return (q[0] / KX + LON0, q[1] / KY + LAT0)

def densify(pts):
    out = [pts[0]]
    for a, b in zip(pts, pts[1:]):
        d = math.dist(a, b); n = max(1, int(d // STEP))
        for i in range(1, n + 1):
            out.append((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    return out

def seg_dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)

class SegIndex:
    def __init__(self, cell=50.0):
        self.cell = cell; self.grid = collections.defaultdict(list)
    def add(self, a, b):
        c = self.cell
        for cx in range(int(min(a[0], b[0]) // c), int(max(a[0], b[0]) // c) + 1):
            for cy in range(int(min(a[1], b[1]) // c), int(max(a[1], b[1]) // c) + 1):
                self.grid[(cx, cy)].append((a, b))
    def near(self, p, r):
        cx, cy = int(p[0] // self.cell), int(p[1] // self.cell)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for a, b in self.grid.get((cx + dx, cy + dy), ()):
                    if seg_dist(p, a, b) < r: return True
        return False

def simplify(pts, tol=1.5):
    if len(pts) < 3: return pts
    keep = [False] * len(pts); keep[0] = keep[-1] = True; stack = [(0, len(pts) - 1)]
    while stack:
        i, j = stack.pop(); best, bi = 0, -1
        for k in range(i + 1, j):
            d = seg_dist(pts[k], pts[i], pts[j])
            if d > best: best, bi = d, k
        if best > tol: keep[bi] = True; stack += [(i, bi), (bi, j)]
    return [p for p, k in zip(pts, keep) if k]

def encode(pts):
    out, plat, plon = [], 0, 0
    for lon, lat in pts:
        la, lo = round(lat * 1e5), round(lon * 1e5)
        for v in (la - plat, lo - plon):
            v = ~(v << 1) if v < 0 else v << 1
            while v >= 0x20:
                out.append(chr((0x20 | (v & 0x1f)) + 63)); v >>= 5
            out.append(chr(v + 63))
        plat, plon = la, lo
    return ''.join(out)

def length(pts):
    return sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--html', required=True)
    ap.add_argument('--lines', required=True)
    ap.add_argument('--defs', required=True)
    a = ap.parse_args()

    feats = []
    for f in json.load(open(a.lines, encoding='utf-8'))['features']:
        if f['properties'].get('typ') != 'tramvaj' or not f.get('geometry'): continue
        g = f['geometry']; prev = None
        for part in (g['coordinates'] if g['type'] == 'MultiLineString' else [g['coordinates']]):
            if len(part) < 2: continue
            pts = [proj(p) for p in part]
            # navazující části jedné trasy spojit, aby šel úsek vyříznout i přes jejich hranici
            if prev is not None and math.dist(prev[-1], pts[0]) < 30: prev += pts[1:]
            else: prev = pts; feats.append(prev)
    feats = [densify(p) for p in feats]
    if not feats: sys.exit('v --lines nejsou žádné tramvajové trasy')

    # 1) sloučení souběžných tras do jedné sítě
    idx, net = SegIndex(), []
    for pts in feats:
        cov = [idx.near(p, DEDUP) for p in pts]
        runs, cur = [], None
        for i, c in enumerate(cov):
            if not c:
                if cur is None: cur = [max(0, i - 1)]
                cur.append(i)
            elif cur is not None:
                cur.append(i); runs.append(cur); cur = None
        if cur is not None: runs.append(cur)
        for r in runs:
            seg = [pts[i] for i in range(r[0], r[-1] + 1)]
            if len(seg) > 1: net.append(seg)
        for r in runs:
            for i in range(r[0], r[-1]): idx.add(pts[i], pts[i + 1])

    # 2) vyříznutí úseků postavených po roce 1953
    defs = json.load(open(a.defs, encoding='utf-8'))
    rem = SegIndex()
    for d in defs['remove']:
        pa, pb = proj(d['a']), proj(d['b']); best = None
        for pts in feats:
            ia = min(range(len(pts)), key=lambda i: math.dist(pts[i], pa))
            ib = min(range(len(pts)), key=lambda i: math.dist(pts[i], pb))
            s = math.dist(pts[ia], pa) + math.dist(pts[ib], pb)
            if best is None or s < best[0]: best = (s, pts, ia, ib)
        s, pts, ia, ib = best
        if s > 120: sys.exit(f'úsek „{d["n"]}“: body a–b neleží na žádné tramvajové trase ({s:.0f} m)')
        lo, hi = sorted((ia, ib)); sub = pts[lo:hi + 1]
        print(f'  − {d["n"]}: {length(sub) / 1000:.2f} km (odchylka {s:.0f} m)', file=sys.stderr)
        for p, q in zip(sub, sub[1:]): rem.add(p, q)

    old, new = [], []
    for pts in net:
        runs, cur, flag = [], [pts[0]], None
        for p, q in zip(pts, pts[1:]):
            f = rem.near(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2), MARK)
            if flag is not None and f != flag:
                runs.append((flag, cur)); cur = [p]
            cur.append(q); flag = f
        runs.append((flag, cur))
        for f, r in runs: (new if f else old).append(r)

    # 3) zrušené tratě
    gone = [(d['n'], d['z'], [proj(p) for p in d['c']]) for d in defs['add']]

    km_o, km_n = sum(map(length, old)) / 1000, sum(map(length, new)) / 1000
    km_z = sum(length(g[2]) for g in gone) / 1000
    print(f'  1953: {km_o + km_z:.1f} km (z toho dnes zrušeno {km_z:.1f} km), dnes: {km_o + km_n:.1f} km',
          file=sys.stderr)
    enc = lambda pts: encode([unproj(p) for p in simplify(pts)])
    T53 = {'o': [enc(p) for p in old if length(p) > 40],
           'z': [[n, z, enc(p)] for n, z, p in gone],
           'n': [enc(p) for p in new if length(p) > 40],
           'km': [round(km_o + km_z, 1), round(km_o + km_n, 1)]}

    html = open(a.html, encoding='utf-8').read()
    line = 'const T53=' + json.dumps(T53, ensure_ascii=False, separators=(',', ':')) + ';\n'
    if re.search(r'^const T53=.*$\n', html, re.M):
        html = re.sub(r'^const T53=.*$\n', lambda _: line, html, count=1, flags=re.M)
    else:
        m = re.search(r'^const (SHP|DATA)=.*$\n', html, re.M)
        if not m: sys.exit('v HTML chybí řádek const DATA=')
        # vložit za SHP (nebo za DATA, když SHP chybí)
        m2 = re.search(r'^const SHP=.*$\n', html, re.M) or m
        html = html[:m2.end()] + line + html[m2.end():]
    open(a.html, 'w', encoding='utf-8').write(html)
    print(f'T53: {len(line) // 1024} kB', file=sys.stderr)

if __name__ == '__main__':
    main()
