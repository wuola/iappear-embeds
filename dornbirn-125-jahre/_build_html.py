"""
Build-Schritt: injiziert events_master.json in alle HTML-Dateien,
die einen <script id="events-data" type="application/json">...</script> Block enthalten.
"""
import json
import os
import re

FOLDER = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(FOLDER, "events_master.json")

# Liste der HTMLs die mit Daten gefuettert werden sollen
HTML_FILES = [
    "index.html",
    "dein-leben.html",
]

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# Kompakt JSON (kein indent) um die HTML kleiner zu halten
data_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
# </script>-Bruch verhindern
data_str_safe = data_str.replace("</", "<\\/")

pattern = re.compile(
    r'(<script id="events-data" type="application/json">).*?(</script>)',
    re.DOTALL,
)

for fn in HTML_FILES:
    path = os.path.join(FOLDER, fn)
    if not os.path.exists(path):
        print(f"SKIP: {fn} nicht gefunden")
        continue
    with open(path, "r", encoding="utf-8") as f:
        html = f.read()
    new_html, n = pattern.subn(lambda m: m.group(1) + data_str_safe + m.group(2), html, count=1)
    if n == 0:
        print(f"WARN: events-data Placeholder nicht gefunden in {fn}")
        continue
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_html)
    size_kb = os.path.getsize(path) / 1024
    print(f"OK: {fn} ({size_kb:.1f} KB)")

print(f"\nFertig. {len(data['events'])} Events injiziert.")
