"""
Konsolidiert die 6 events_*.json zu einer events_master.json.
- Laedt alle, validiert Felder
- Vergibt IDs
- Sortiert chronologisch
- Erkennt Duplikat-Kandidaten (gleiches Jahr + Titel-Aehnlichkeit > 0.6)
- Mergt Quellen bei Duplikaten
- Schreibt events_master.json + statistik
"""
import json
import os
import re
import unicodedata
from difflib import SequenceMatcher

FOLDER = os.path.dirname(os.path.abspath(__file__))

SOURCE_FILES = [
    "events_Matt_Geschichte.json",
    "events_Aberer_Stadtentwicklung.json",
    "events_Fessler_Wirtschaften.json",
    "events_Friebe_Naturraum.json",
    "events_Haemmerle_Innovation.json",
    "events_Pichler_Auswanderer.json",
]

CATEGORIES = {
    "Politik", "Wirtschaft", "Industrie", "Kultur", "NS-Zeit", "Krieg",
    "Natur", "Migration", "Stadtentwicklung", "Bildung", "Sport",
    "Religion", "Soziales", "Bauten", "Verkehr", "Persönlichkeit",
}

CATEGORY_ALIASES = {
    "Persoenlichkeit": "Persönlichkeit",
}


def normalize_category(c):
    return CATEGORY_ALIASES.get(c, c)


def normalize_title(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def title_similarity(a, b):
    return SequenceMatcher(None, normalize_title(a), normalize_title(b)).ratio()


def load_all():
    all_events = []
    per_book = {}
    for fn in SOURCE_FILES:
        path = os.path.join(FOLDER, fn)
        if not os.path.exists(path):
            print(f"WARN: fehlt: {fn}")
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        book = data.get("source_book", fn)
        events = data.get("events", [])
        per_book[book] = len(events)
        for e in events:
            e["_book"] = book
            if "category" in e:
                e["category"] = normalize_category(e["category"])
            all_events.append(e)
    return all_events, per_book


def validate(events):
    issues = []
    for e in events:
        y = e.get("year")
        if not isinstance(y, int) or not (1901 <= y <= 2026):
            issues.append(f"{e.get('_book')} | {e.get('title','?')}: year={y}")
        cat = e.get("category")
        if cat not in CATEGORIES:
            issues.append(f"{e.get('_book')} | {e.get('title','?')}: category={cat}")
    return issues


def find_duplicates(events, threshold=0.6):
    """Gleiches Jahr + Titel-Aehnlichkeit > threshold -> Kandidaten-Cluster."""
    by_year = {}
    for i, e in enumerate(events):
        by_year.setdefault(e["year"], []).append(i)

    clusters = []
    seen = set()
    for year, idxs in by_year.items():
        for i in idxs:
            if i in seen:
                continue
            cluster = [i]
            seen.add(i)
            for j in idxs:
                if j == i or j in seen:
                    continue
                if title_similarity(events[i]["title"], events[j]["title"]) >= threshold:
                    cluster.append(j)
                    seen.add(j)
            if len(cluster) > 1:
                clusters.append(cluster)
    return clusters


def merge_cluster(events, cluster):
    """Mergt mehrere Events zu einem. Behaelt laengste summary, vereinigt Quellen/Personen/Orte."""
    chosen = max(cluster, key=lambda i: len(events[i].get("summary", "")))
    base = dict(events[chosen])
    sources = []
    page_hints = []
    people = list(base.get("people") or [])
    places = list(base.get("places") or [])
    titles = []
    summaries = []
    for i in cluster:
        e = events[i]
        src = e.get("source")
        if src and src not in sources:
            sources.append(src)
        ph = e.get("page_hint")
        if ph:
            page_hints.append(f"{e.get('source','?')} {ph}")
        for p in (e.get("people") or []):
            if p not in people:
                people.append(p)
        for p in (e.get("places") or []):
            if p not in places:
                places.append(p)
        titles.append(e.get("title", ""))
        summaries.append({"book": e.get("_book", e.get("source", "?")),
                          "title": e.get("title", ""),
                          "summary": e.get("summary", "")})
    base["sources"] = sources
    base["page_hints"] = page_hints
    base["people"] = people
    base["places"] = places
    base["alt_titles"] = [t for t in titles if t != base["title"]]
    base["source_summaries"] = summaries  # zur spaeteren Kuration
    return base


def consolidate():
    all_events, per_book = load_all()
    print(f"Gesamt geladen: {len(all_events)} Events aus {len(per_book)} Büchern")
    for b, n in per_book.items():
        print(f"  {b}: {n}")

    issues = validate(all_events)
    if issues:
        print(f"\nValidierungs-Probleme ({len(issues)}):")
        for x in issues[:20]:
            print(f"  - {x}")
        if len(issues) > 20:
            print(f"  ... und {len(issues)-20} weitere")
    else:
        print("\nValidierung OK")

    clusters = find_duplicates(all_events, threshold=0.6)
    print(f"\n{len(clusters)} Duplikat-Cluster gefunden (Titel-Aehnlichkeit >= 0.6, gleiches Jahr)")

    in_cluster = set()
    merged = []
    for cl in clusters:
        for i in cl:
            in_cluster.add(i)
        merged.append(merge_cluster(all_events, cl))

    # Einzeln stehende Events
    for i, e in enumerate(all_events):
        if i in in_cluster:
            continue
        base = dict(e)
        base["sources"] = [e.get("source")] if e.get("source") else []
        base["page_hints"] = [f"{e.get('source','?')} {e.get('page_hint','')}"] if e.get("page_hint") else []
        base["alt_titles"] = []
        base["source_summaries"] = [{"book": e.get("_book", e.get("source", "?")),
                                     "title": e.get("title", ""),
                                     "summary": e.get("summary", "")}]
        merged.append(base)

    # Sortieren: Jahr, dann Titel
    merged.sort(key=lambda e: (e["year"], normalize_title(e.get("title", ""))))

    # IDs
    for i, e in enumerate(merged, start=1):
        e["id"] = f"E{i:03d}"
        e.pop("_book", None)
        e.pop("page_hint", None)
        e.pop("source", None)

    # Statistik
    by_decade = {}
    by_category = {}
    for e in merged:
        dec = (e["year"] // 10) * 10
        by_decade[dec] = by_decade.get(dec, 0) + 1
        c = e.get("category", "?")
        by_category[c] = by_category.get(c, 0) + 1

    stats = {
        "total_events": len(merged),
        "raw_events": len(all_events),
        "merged_clusters": len(clusters),
        "per_book": per_book,
        "by_decade": dict(sorted(by_decade.items())),
        "by_category": dict(sorted(by_category.items(), key=lambda x: -x[1])),
    }

    out = {
        "version": "1.0",
        "title": "Dornbirn Portrait — Timeline 1901-2026",
        "description": "Konsolidierte Ereignisliste aus 6 Buechern der Dornbirn-Portrait-Reihe (Stadt Dornbirn, 2012). Großzuegige Sammlung zur weiteren Kuration.",
        "stats": stats,
        "events": merged,
    }

    out_path = os.path.join(FOLDER, "events_master.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # JS-Wrapper fuer file:// Browser-Loading ohne Server
    js_path = os.path.join(FOLDER, "events_master.js")
    with open(js_path, "w", encoding="utf-8") as f:
        f.write("window.EVENTS_DATA = ")
        json.dump(out, f, ensure_ascii=False)
        f.write(";\n")

    print(f"\n--- Ergebnis ---")
    print(f"Konsolidiert: {len(merged)} Events (von urspruenglich {len(all_events)})")
    print(f"Geschrieben: events_master.json")
    print(f"\nPro Jahrzehnt:")
    for dec, n in sorted(by_decade.items()):
        print(f"  {dec}er: {'#'*n} {n}")
    print(f"\nPro Kategorie:")
    for c, n in sorted(by_category.items(), key=lambda x: -x[1]):
        print(f"  {c:20s} {n}")

    return out


if __name__ == "__main__":
    consolidate()
