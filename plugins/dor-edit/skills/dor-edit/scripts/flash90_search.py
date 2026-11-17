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
import http.client, json, re, ssl, sys, time, urllib.error, urllib.request

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


_IMG_URL_RE = re.compile(r'https?://[^"\'\s\\]+?\.jpe?g[^"\'\s\\]*')
MAX_PAGES = 5  # תקרה לדפדוף - לא לסרוק את כל הארכיון בשאילתה אחת


def _fetch(url: str, retries: int = 3) -> str:
    """GET עם timeout ו-retry (GET אידמפוטנטי - בטוח לנסות שוב).

    IncompleteRead (חיבור שנסגר באמצע הגוף) נזרק מתוך read(), אחרי ש-urlopen
    כבר חזר - ולכן ה-read חייב להיות בתוך ה-try."""
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Macintosh)"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, context=_CTX, timeout=20) as r:
                return r.read().decode("utf-8", "ignore")
        except urllib.error.HTTPError as e:
            if e.code == 429 or e.code >= 500:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
            raise
        except (http.client.HTTPException, urllib.error.URLError, TimeoutError, OSError):
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError("unreachable")  # pragma: no cover


def _search_url(query: str, page: int = 1) -> str:
    payload = {"searchbar": query, "category": "DFL", "ordermode": "2", "orderby": "7"}
    hexpart = "0x" + json.dumps(payload, ensure_ascii=False).encode("utf-8").hex().upper()
    return f"https://www.flash90.net/search/en/{page}/{hexpart}"


def _tag_start(body: str, pos: int) -> int:
    """תחילת התג שמכיל את המיקום (למשל <img ... src="..."> - alt יכול לבוא לפני src)."""
    lt = body.rfind("<", 0, pos)
    return lt if lt != -1 and body.rfind(">", lt, pos) == -1 else pos


def parse_results(body: str) -> list:
    """מחלץ פריטים מעמוד תוצאות. החלון של כל תמונה נמתח מתחילת התג שלה ועד
    תחילת התג של התמונה **הבאה השונה** - כך שכיתוב או alt של הפריט הבא לא
    נשאב לפריט שאין לו כיתוב (הבאג של חלון קבוע של 3000 תווים קדימה)."""
    hits, seen = [], set()
    for m in _IMG_URL_RE.finditer(body):
        u = m.group(0)
        idm = re.search(r"(Image\d+)\.jpe?g", u)
        key = idm.group(1) if idm else u
        if key in seen:
            continue
        seen.add(key)
        hits.append((key, u, _tag_start(body, m.start()), m.end()))

    images = []
    for i, (key, u, start, url_end) in enumerate(hits):
        end = hits[i + 1][2] if i + 1 < len(hits) else len(body)
        ctx = body[start:end]
        fn = re.search(r'<p[^>]*class="[^"]*file_name[^"]*"[^>]*>(.*?)</p>', ctx, re.S)
        file_name = _clean(fn.group(1)) if fn else ""
        cap = re.search(r'<p[^>]*class="[^"]*(?:caption|description)[^"]*"[^>]*>(.*?)</p>',
                        ctx, re.S)
        caption = _clean(cap.group(1)) if cap else ""
        if not caption:
            # פולבק: alt/title של תג התמונה עצמו בלבד (התג שמכיל את ה-URL)
            tag_end = body.find(">", url_end)
            tag = body[start:tag_end + 1] if tag_end != -1 else ""
            alt = re.search(r'\b(?:alt|title)="([^"]{3,})"', tag) if tag.startswith("<img") else None
            caption = _clean(alt.group(1)) if alt else ""
        images.append({
            "image_id": key,
            "file_name": file_name,
            "caption": caption,
            # משני בלבד: כתובת חתומת-סשן שפגה - לא לצטט בדוח כקישור מרכזי
            "thumb": u,
        })
    return images


def search(query: str, n: int = 6) -> dict:
    """עמוד 1, ואם צריך עוד - עמודים נוספים (עד MAX_PAGES), עד n תמונות.
    מבנה ה-URL של הדפדוף (/search/en/<page>/...) לא אומת מול האתר; עמוד שלא
    מביא אף תמונה חדשה עוצר את הלולאה."""
    url = _search_url(query, 1)
    images, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        body = _fetch(_search_url(query, page))
        fresh = [im for im in parse_results(body) if im["image_id"] not in seen]
        if not fresh:
            break
        for im in fresh:
            seen.add(im["image_id"])
            images.append(im)
        if len(images) >= n:
            break
    images = images[:n]
    return {"query": query, "search_url": url, "count": len(images),
            "thumb_note": "כתובות thumb חתומות בטוקן סשן ופגות - השתמש ב-search_url וב-image_id",
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
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError,
            ssl.SSLError, OSError) as e:
        print(json.dumps({"error": "network", "detail": str(e), "query": q},
                         ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
