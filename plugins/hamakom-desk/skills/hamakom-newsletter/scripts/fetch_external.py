# -*- coding: utf-8 -*-
"""
fetch_external.py — מושך המלצות קריאה מהשותפות ב"עיתונות העצמאית":
העין השביעית + שקוף (דרך RSS), ומחזיר רשומות מוכנות לפינת "המלצות קריאה" בניוזלטר.

הרצה עצמאית:
  python3 fetch_external.py            # כותב external_reads.json
  N=1 python3 fetch_external.py        # פריט אחד מכל מקור (ברירת מחדל)

שימוש כמודול:
  from fetch_external import get_reads
  reads = get_reads(per_source=1)      # [{outlet, headline, dek, url}, ...]

הערות:
  * דור ביקש המלצות מ*תקשורת אחרת ולא בהכרח מהאתר שלנו* — כאן שני המקורות הקבועים.
  * ה-RSS מחזיר את האחרונות; העורך יכול להחליף ידנית ל"טובה יותר" מאותו פיד.
  * fail-soft: אם מקור נופל, מדלגים עליו ומחזירים את מה שיש (לא מפילים את ה-fetch).
"""
import json, os, re, html, urllib.request, ssl
try:
    import defusedxml.ElementTree as ET      # מגן מפני XXE / billion-laughs
except Exception:
    import xml.etree.ElementTree as ET       # fallback: ET מודרני לא מרחיב ישויות חיצוניות כברירת מחדל

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _CTX = ssl.create_default_context()

UA = {"User-Agent": "Mozilla/5.0 hamakom-newsletter-bot"}

# מקורות קבועים — השותפות ב"עיתונות העצמאית"
SOURCES = [
    {"outlet": "העין השביעית", "feed": "https://www.the7eye.org.il/feed"},
    {"outlet": "שקוף",         "feed": "https://shakuf.co.il/feed"},
]


def _strip(s, n=120):
    s = re.sub(r"<[^>]+>", "", s or "")
    s = html.unescape(s).replace("\xa0", " ").strip()
    s = re.sub(r"\s*[—–]\s*", " - ", s)          # חוק המקף
    return (s[:n].rstrip() + "…") if len(s) > n else s


def _get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20, context=_CTX) as r:
        return r.read()


def _items_from_feed(url, outlet, per_source):
    out = []
    try:
        raw = _get(url)
        root = ET.fromstring(raw)
    except Exception as e:
        print(f"  external skip {outlet}: {e}")
        return out
    # RSS 2.0: channel/item ; Atom: entry
    items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    for it in items[: max(per_source, 1)]:
        def _t(tag, atom=None):
            el = it.find(tag)
            if el is None and atom is not None:
                el = it.find(atom)
            return (el.text or "").strip() if el is not None and el.text else ""
        title = _t("title", "{http://www.w3.org/2005/Atom}title")
        link = _t("link", "{http://www.w3.org/2005/Atom}link")
        if not link:  # Atom משתמש ב-href
            le = it.find("{http://www.w3.org/2005/Atom}link")
            if le is not None:
                link = le.get("href", "")
        desc = _t("description", "{http://www.w3.org/2005/Atom}summary")
        if not title or not link:
            continue
        out.append({
            "outlet": outlet,
            "headline": _strip(title, 90),
            "dek": _strip(desc, 110),
            "url": link.strip(),
        })
    return out


def get_reads(per_source=1):
    reads = []
    for s in SOURCES:
        reads.extend(_items_from_feed(s["feed"], s["outlet"], per_source))
    return reads


def main():
    per = int(os.environ.get("N", "1"))
    out_dir = os.environ.get("OUT_DIR", ".")
    reads = get_reads(per)
    path = os.path.join(out_dir, "external_reads.json")
    json.dump(reads, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {path} — {len(reads)} reads")
    for r in reads:
        print(f"  · {r['outlet']}: {r['headline']}")


if __name__ == "__main__":
    main()
