"""
Konvertiert ne_110m_land.geojson zu einem einzigen SVG-Path-d
mit Atlantik-zentrierter Equirektangular-Projektion.

Projektion: lng [-130 ... +30] → x [0 ... 1000]
            lat [0 ... 75]    → y [500 ... 0]
"""
import json
import os

FOLDER = os.path.dirname(os.path.abspath(__file__))
GEO_PATH = os.path.join(FOLDER, "_ne_land.geojson")
OUT_PATH = os.path.join(FOLDER, "_land_path.txt")

LNG_MIN, LNG_MAX = -130, 30
LAT_MIN, LAT_MAX = 0, 75
WIDTH, HEIGHT = 1000, 500


def proj_x(lng):
    return (lng - LNG_MIN) / (LNG_MAX - LNG_MIN) * WIDTH


def proj_y(lat):
    return (LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * HEIGHT


with open(GEO_PATH, "r", encoding="utf-8") as f:
    geo = json.load(f)

# Sammle alle rings, beruecksichtige Multipolygon
# Ein einziger Path mit vielen M/L Subpfaden ist effizienter als viele <path> Elemente

d_parts = []
ring_count = 0
for feat in geo["features"]:
    geom = feat["geometry"]
    if geom["type"] == "Polygon":
        polys = [geom["coordinates"]]
    elif geom["type"] == "MultiPolygon":
        polys = geom["coordinates"]
    else:
        continue

    for poly in polys:
        # Nur outer ring (poly[0]); holes (poly[1:]) ignorieren
        ring = poly[0]
        if len(ring) < 3:
            continue
        ring_count += 1
        # Filter: skip rings die komplett ausserhalb des sichtbaren Bereichs liegen
        # (z.B. Pazifik-only). Einfacher: skip wenn alle lng > LNG_MAX + 10 oder < LNG_MIN - 10
        lngs = [pt[0] for pt in ring]
        if min(lngs) > LNG_MAX + 5 and max(lngs) > LNG_MAX + 5:
            continue
        if max(lngs) < LNG_MIN - 5 and min(lngs) < LNG_MIN - 5:
            continue
        sub = []
        for i, (lng, lat) in enumerate(ring):
            x = round(proj_x(lng), 1)
            y = round(proj_y(lat), 1)
            sub.append(("M" if i == 0 else "L") + f" {x} {y}")
        d_parts.append(" ".join(sub) + " Z")

path_d = " ".join(d_parts)
print(f"Rings: {ring_count}")
print(f"Path-d length: {len(path_d)} chars (~{len(path_d)/1024:.1f} KB)")

with open(OUT_PATH, "w", encoding="utf-8") as f:
    f.write(path_d)
print(f"Written: {OUT_PATH}")

# Injizere in neue-welt.html
import re
HTML_PATH = os.path.join(FOLDER, "neue-welt.html")
if os.path.exists(HTML_PATH):
    with open(HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()
    pattern = re.compile(r'<path class="land" d="[^"]*"/>', re.DOTALL)
    n = len(pattern.findall(html))
    if n == 0:
        print("WARN: kein <path class=\"land\".../> in neue-welt.html gefunden")
    else:
        replacement = f'<path class="land" d="{path_d}"/>'
        html_new = pattern.sub(replacement, html, count=1)
        with open(HTML_PATH, "w", encoding="utf-8") as f:
            f.write(html_new)
        kb = os.path.getsize(HTML_PATH) / 1024
        print(f"Injected into neue-welt.html ({kb:.1f} KB)")
else:
    print(f"WARN: {HTML_PATH} nicht gefunden")
