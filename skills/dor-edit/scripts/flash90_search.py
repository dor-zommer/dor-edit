#!/usr/bin/env python3
"""חיפוש תמונות בפלאש 90 (flash90.net).

בונה URL חיפוש (JSON מקודד הקס), מושך את עמוד התוצאות (מרונדר בצד השרת)
ומחזיר את קישור החיפוש + N תמונות ראשונות.

שימוש: python3 flash90_search.py "שאילתת חיפוש" [N]
פלט: JSON — search_url, images[{thumb, image_id}]
"""
import json, re, ssl, sys, urllib.request

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _CTX = ssl.create_default_context()


def search(query: str, n: int = 6) -> dict:
    payload = {"searchbar": query, "category": "DFL", "ordermode": "2", "orderby": "7"}
    hexpart = "0x" + json.dumps(payload, ensure_ascii=False).encode("utf-8").hex().upper()
    url = f"https://www.flash90.net/search/en/1/{hexpart}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh)"})
    with urllib.request.urlopen(req, context=_CTX, timeout=20) as r:
        body = r.read().decode("utf-8", "ignore")
    seen, images = set(), []
    for u in re.findall(r'https?://[^"\'\s\\]+?\.jpe?g[^"\'\s\\]*', body):
        m = re.search(r"(Image\d+)\.jpe?g", u)
        key = m.group(1) if m else u
        if key in seen:
            continue
        seen.add(key)
        images.append({"thumb": u, "image_id": key})
        if len(images) >= n:
            break
    return {"query": query, "search_url": url, "images": images}


if __name__ == "__main__":
    q = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    print(json.dumps(search(q, n), ensure_ascii=False, indent=1))
