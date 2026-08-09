#!/usr/bin/env python3
"""חיפוש תמונות בפלאש 90 (flash90.net).

בונה URL חיפוש (JSON מקודד הקס), מושך את עמוד התוצאות (מרונדר בצד השרת)
ומחזיר את קישור החיפוש + N תמונות ראשונות עם שם הקובץ הרשמי והכיתוב.

חשוב: כתובות ה-thumb חתומות בטוקן סשן שפג תוקף — הן **לא** קישור מרכזי
בדוח. הפריטים היציבים הם image_id + file_name + search_url; ה-thumb נשמר
כשדה משני בלבד (thumb_note מסביר).

שימוש: python3 flash90_search.py "שאילתת חיפוש" [N]
פלט: JSON — search_url (יציב), images[{image_id, file_name, caption, thumb}]
שגיאת רשת מחזירה JSON שגיאה מסודר (exit code 1); 0 תוצאות = JSON תקין עם
רשימה ריקה.
"""
import html as _html
import json, re, ssl, sys, urllib.error, urllib.request

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _CTX = ssl.create_default_context()

USAGE = 'שימוש: python3 flash90_search.py "שאילתת חיפוש" [N]'

_TAG_RE = re.compile(r"<[^>]+>")


def _clean(s: str) -> str:
    """מנקה תגיות HTML ורווחים, ומפענח entities."""
    return _html.unescape(_TAG_RE.sub("", s)).strip()


def _near(body: str, pos: int, window: int = 3000) -> str:
    """חלון טקסט סביב מיקום ההתאמה — לחילוץ שם קובץ וכיתוב סמוכים."""
    return body[pos:pos + window]


def search(query: str, n: int = 6) -> dict:
    payload = {"searchbar": query, "category": "DFL", "ordermode": "2", "orderby": "7"}
    hexpart = "0x" + json.dumps(payload, ensure_ascii=False).encode("utf-8").hex().upper()
    url = f"https://www.flash90.net/search/en/1/{hexpart}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh)"})
    body = ""
    with urllib.request.urlopen(req, context=_CTX, timeout=20) as r:
        body = r.read().decode("utf-8", "ignore")

    seen, images = set(), []
    for m in re.finditer(r'https?://[^"\'\s\\]+?\.jpe?g[^"\'\s\\]*', body):
        u = m.group(0)
        idm = re.search(r"(Image\d+)\.jpe?g", u)
        key = idm.group(1) if idm else u
        if key in seen:
            continue
        seen.add(key)

        # שם הקובץ הרשמי (<p class="file_name">) והכיתוב — מהאזור הסמוך לתמונה
        ctx = _near(body, m.end())
        fn = re.search(r'<p[^>]*class="[^"]*file_name[^"]*"[^>]*>(.*?)</p>', ctx, re.S)
        file_name = _clean(fn.group(1)) if fn else ""
        cap = re.search(r'<p[^>]*class="[^"]*(?:caption|description)[^"]*"[^>]*>(.*?)</p>',
                        ctx, re.S)
        caption = _clean(cap.group(1)) if cap else ""
        if not caption:
            # פולבק: alt/title של תג התמונה עצמו
            alt = re.search(r'<img[^>]*\b(?:alt|title)="([^"]{3,})"', ctx)
            caption = _clean(alt.group(1)) if alt else ""

        images.append({
            "image_id": key,
            "file_name": file_name,
            "caption": caption,
            # משני בלבד: כתובת חתומת-סשן שפגה — לא לצטט בדוח כקישור מרכזי
            "thumb": u,
        })
        if len(images) >= n:
            break

    return {"query": query, "search_url": url, "count": len(images),
            "thumb_note": "כתובות thumb חתומות בטוקן סשן ופגות — השתמש ב-search_url וב-image_id",
            "images": images}


def main() -> int:
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print(USAGE, file=sys.stderr)
        return 2
    q = sys.argv[1]
    try:
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    except ValueError:
        print(USAGE, file=sys.stderr)
        return 2
    try:
        print(json.dumps(search(q, n), ensure_ascii=False, indent=1))
        return 0
    except urllib.error.HTTPError as e:
        print(json.dumps({"error": f"HTTP {e.code}", "detail": str(e.reason),
                          "query": q}, ensure_ascii=False))
        return 1
    except (urllib.error.URLError, TimeoutError, ssl.SSLError, OSError) as e:
        print(json.dumps({"error": "network", "detail": str(e), "query": q},
                         ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
