"""
Build-Schritt: injiziert events_master.json in index.html.
Sucht <script id="events-data" type="application/json">...</script>
und ersetzt den Inhalt mit der frischen JSON.
"""
import json
import os
import re

FOLDER = os.path.dirname(os.path.abspath(__file__))
HTML_PATH = os.path.join(FOLDER, "index.html")
JSON_PATH = os.path.join(FOLDER, "events_master.json")

with open(JSON_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

# Kompakt JSON (kein indent) um die HTML kleiner zu halten
data_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))

# JSON darf </script> nicht enthalten (sonst Browser-Bruch)
# Escape: ersetze </ mit <\/ (im JSON-String-Kontext erlaubt)
data_str_safe = data_str.replace("</", "<\\/")

with open(HTML_PATH, "r", encoding="utf-8") as f:
    html = f.read()

pattern = re.compile(
    r'(<script id="events-data" type="application/json">).*?(</script>)',
    re.DOTALL,
)
new_html, n = pattern.subn(lambda m: m.group(1) + data_str_safe + m.group(2), html, count=1)

if n == 0:
    raise RuntimeError("events-data Placeholder nicht gefunden in index.html")

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(new_html)

size_kb = os.path.getsize(HTML_PATH) / 1024
print(f"OK: {len(data['events'])} Events in index.html injiziert ({size_kb:.1f} KB)")
