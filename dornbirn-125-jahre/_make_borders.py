"""
Generiert die Laendergrenzen (Natural Earth admin_0_boundary_lines_land)
als SVG-Path und injiziert sie in eine Ziel-HTML als <path class="borders" d="..."/>.

Verwendet dieselbe Projektion wie _make_worldmap.py.
"""
import json
import os
import re
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--target", default="neue-welt-v2.html")
parser.add_argument("--lng-min", type=float, default=-140)
parser.add_argument("--lng-max", type=float, default=35)
parser.add_argument("--lat-min", type=float, default=-10)
parser.add_argument("--lat-max", type=float, default=78)
parser.add_argument("--width", type=float, default=1000)
parser.add_argument("--height", type=float, default=500)
args = parser.parse_args()

FOLDER = os.path.dirname(os.path.abspath(__file__))
GEO_COUNTRIES = os.path.join(FOLDER, "_ne_borders.geojson")          # admin_0 lines
GEO_STATES = os.path.join(FOLDER, "_ne_states.geojson")              # admin_1 lines
STATE_COUNTRIES = {"USA", "CAN"}  # Nur diese Länder Sub-Grenzen zeichnen

print(f"Target: {args.target}")
print(f"Range: lng [{args.lng_min} .. {args.lng_max}], lat [{args.lat_min} .. {args.lat_max}]")


def proj_x(lng):
    return (lng - args.lng_min) / (args.lng_max - args.lng_min) * args.width


def proj_y(lat):
    return (args.lat_max - lat) / (args.lat_max - args.lat_min) * args.height


def render_lines(geo, include_filter=None):
    """include_filter: function(feature) -> bool. None = alle."""
    parts = []
    count = 0
    for feat in geo["features"]:
        if include_filter and not include_filter(feat):
            continue
        geom = feat["geometry"]
        if geom["type"] == "LineString":
            lines = [geom["coordinates"]]
        elif geom["type"] == "MultiLineString":
            lines = geom["coordinates"]
        else:
            continue
        for line in lines:
            if len(line) < 2:
                continue
            count += 1
            sub = []
            for i, (lng, lat) in enumerate(line):
                x = round(proj_x(lng), 1)
                y = round(proj_y(lat), 1)
                sub.append(("M" if i == 0 else "L") + f" {x} {y}")
            parts.append(" ".join(sub))
    return parts, count


# Country borders (admin_0): alle
with open(GEO_COUNTRIES, "r", encoding="utf-8") as f:
    countries_geo = json.load(f)
country_parts, country_count = render_lines(countries_geo)
print(f"Country borders: {country_count} lines")

# State borders (admin_1): nur USA + CAN
state_parts, state_count = [], 0
if os.path.exists(GEO_STATES):
    with open(GEO_STATES, "r", encoding="utf-8") as f:
        states_geo = json.load(f)
    state_parts, state_count = render_lines(
        states_geo,
        include_filter=lambda f: f.get("properties", {}).get("ADM0_A3") in STATE_COUNTRIES,
    )
    print(f"State/Province borders (USA+CAN): {state_count} lines")
else:
    print("WARN: _ne_states.geojson nicht gefunden, States werden übersprungen")

path_d = " ".join(country_parts + state_parts)
print(f"Combined path-d length: {len(path_d)} chars (~{len(path_d)/1024:.1f} KB)")

# Injizere in target HTML
HTML_PATH = os.path.join(FOLDER, args.target)
if not os.path.exists(HTML_PATH):
    print(f"FEHLER: {HTML_PATH} nicht gefunden")
    raise SystemExit(1)

with open(HTML_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# Pattern: vorhandenen <path class="borders" d="..."/> ersetzen oder neu einfuegen
pattern_borders = re.compile(r'<path class="borders" d="[^"]*"/>', re.DOTALL)
replacement = f'<path class="borders" d="{path_d}"/>'

if pattern_borders.search(html):
    html_new = pattern_borders.sub(replacement, html, count=1)
    print("Bestehenden borders-Path ersetzt")
else:
    # Einfuegen nach dem land-Path
    pattern_land = re.compile(r'(<path class="land" d="[^"]*"/>)', re.DOTALL)
    if not pattern_land.search(html):
        print("FEHLER: kein <path class=\"land\".../> in target gefunden")
        raise SystemExit(2)
    html_new = pattern_land.sub(r'\1\n      ' + replacement, html, count=1)
    print("Borders-Path neu eingefuegt nach Land-Path")

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(html_new)

kb = os.path.getsize(HTML_PATH) / 1024
print(f"Injected into {args.target} ({kb:.1f} KB)")
