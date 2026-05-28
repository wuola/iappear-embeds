# 125 Jahre Dornbirn — Interaktive Timeline

Mobile-First Timeline der wichtigsten Ereignisse Dornbirns seit der Stadterhebung 1901.
227 Ereignisse, durchsuchbar und filterbar nach Kategorie und Jahrzehnt.

**Live:** https://wuola.github.io/iappear-embeds/dornbirn-125-jahre/

## Datenbasis

Die Inhalte sind paraphrasierte Zusammenfassungen aus der 8-bändigen Buchreihe
**„Dornbirn Portrait"** (Stadt Dornbirn, 2012). Verwendet wurden 6 Bände:

- **Matt, Werner** — *Geschichte Dornbirns*
- **Aberer, Markus** — *Von der Stadterhebung zur lebenswerten Stadt*
- **Fessler, Klaus** — *Wirtschaften*
- **Friebe, J. Georg** — *Naturraum Dornbirn*
- **Hämmerle, Ralf** — *Innovation*
- **Pichler, Meinrad** — *Von Dornbirn in die Neue Welt*

## Aufbau

- `index.html` — Single-File-Timeline (Daten inline eingebettet)
- `events_master.json` — Master-Datensatz, kuratierbar
- `_consolidate.py` — Baut `events_master.json` aus den 6 Roh-Extraktionen
- `_build_html.py` — Injiziert `events_master.json` als JSON in `index.html`

## Workflow

```bash
# Daten ändern → HTML neu bauen
python _build_html.py
```
