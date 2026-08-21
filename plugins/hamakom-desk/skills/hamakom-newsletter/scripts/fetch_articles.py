# -*- coding: utf-8 -*-
"""
fetch_week.py — מושך את הכתבות שפורסמו השבוע מ-WordPress REST API של ha-makom.co.il
ומייצר:
  articles.json     — מילון slug -> רשומה {link,title,excerpt,date,img,author,is_opinion}
  issue.draft.json  — שלד ניוזלטר מוצע שהעורך עורך לפני build_weekly.py

הרצה:
  DAYS=7  python3 fetch_week.py            # 7 הימים האחרונים (ברירת מחדל)
  DAYS=14 OUT_DIR=/path python3 fetch_week.py

הערות:
  * לא משתמשים ב-_embed (מנפח את התשובה ל~1.6MB לקריאה); מושכים שדות נבחרים בלבד.
  * שם הכותב נמשך מ-yoast_head_json.author (ה-byline האמיתי). שדה ה-author הרגיל של
    וורדפרס מחזיר משתמש מערכת ולא את הכתב/ת.
  * תמונה ראשית מ-jetpack_featured_media_url.
  * "דעות/טורים" מזוהה לפי קטגוריה 547.
"""
import json, re, html, os, urllib.request, datetime, ssl
try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _CTX = ssl.create_default_context()

BASE        = "https://www.ha-makom.co.il/wp-json/wp/v2"
DAYS        = int(os.environ.get("DAYS", "7"))
OPINION_CAT = 547                       # קטגוריית "דעות"
OUT_DIR     = os.environ.get("OUT_DIR", ".")
UA          = {"User-Agent": "Mozilla/5.0 hamakom-newsletter-bot"}
FIELDS      = ("slug,link,title,excerpt,date,categories,"
               "jetpack_featured_media_url,coauthors,yoast_head_json")
HE_MONTHS   = ["ינואר","פברואר","מרץ","אפריל","מאי","יוני",
               "יולי","אוגוסט","ספטמבר","אוקטובר","נובמבר","דצמבר"]


def _get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30, context=_CTX) as r:
        return json.load(r)


def strip_tags(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return html.unescape(s).replace("\xa0", " ").strip()


def external_reads():
    """המלצות קריאה מהעין השביעית + שקוף (RSS). fail-soft — לא מפיל את ה-fetch."""
    try:
        from fetch_external import get_reads
        return get_reads(per_source=1)
    except Exception as e:
        print("external reads skipped:", e)
        return []


def author_of(post):
    y = post.get("yoast_head_json", {}) or {}
    if y.get("author"):
        return y["author"]
    co = post.get("coauthors") or []
    names = [c.get("display_name") or c.get("name") for c in co if isinstance(c, dict)]
    names = [n for n in names if n]
    return ", ".join(names) if names else ""


def main():
    after = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=DAYS)) \
        .strftime("%Y-%m-%dT00:00:00")
    arts, order, page = {}, [], 1
    while True:
        url = (f"{BASE}/posts?per_page=30&page={page}&after={after}"
               f"&orderby=date&order=desc&_fields={FIELDS}")
        try:
            batch = _get(url)
        except Exception as e:
            print("fetch stopped:", e)
            break
        if not isinstance(batch, list) or not batch:
            break
        for p in batch:
            slug = p.get("slug")
            if not slug:
                continue
            cat_ids = p.get("categories", []) or []
            arts[slug] = {
                "slug": slug,
                "link": p.get("link", ""),
                "title": html.unescape(p.get("title", {}).get("rendered", "")).strip(),
                "excerpt": strip_tags(p.get("excerpt", {}).get("rendered", "")),
                "date": p.get("date", "")[:10],
                "img": p.get("jetpack_featured_media_url") or "",
                "author": author_of(p),
                "is_opinion": OPINION_CAT in cat_ids,
            }
            order.append(slug)
        if len(batch) < 30:
            break
        page += 1

    json.dump(arts, open(os.path.join(OUT_DIR, "articles.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    news = [s for s in order if not arts[s]["is_opinion"]]
    ops  = [s for s in order if arts[s]["is_opinion"]]

    today = datetime.date.today()
    week_date = f"{today.day} ב{HE_MONTHS[today.month - 1]} {today.year}"

    issue = {
        "week_date": week_date,
        "preheader": f'השבוע ב"המקום הכי חם בגיהנום": {len(order)} כתבות',
        "editor_note": {
            "headline": "<<< כותרת פתיח — דור ממלא >>>",
            "paragraphs": ["<<< פתיח עורך — דור ממלא. אפשר כמה פסקאות. >>>"],
        },
        "project":   {"label": "חדש באתר · פרויקט מתעדכן", "title": "", "url": "",
                       "desc": "", "cta": "לפרויקט המלא ⟵"},
        "lead": news[0] if news else "",
        "data_stat": {"label": "הנתון של השבוע", "img": "", "alt": "", "url": ""},
        "followup":  {"slug": "", "banner_title": "בעקבות הפרסום", "banner_sub": ""},
        "rundown_label": "עוד דברים שקרו השבוע במקום הכי חם בגיהנום",
        "rundown": news[2:] if len(news) > 2 else news[1:],
        "photo_of_week": {
            "img": "",
            "caption": "<<< מקום, הקשר ותאריך — דור/קלוד ממלא >>>",
            "credit": "צילום: ___ / פלאש 90",
            "place_after": 1,
        },
        "hero":  {"slug": news[1] if len(news) > 1 else "", "kicker": "מתחת לרדאר"},
        "reel":  {"url": "", "poster": "", "cta": "▶ לריל", "caption": ""},
        "quote": {"slug": ops[0] if ops else (news[0] if news else ""),
                   "text": "<<< ציטוט השבוע - דור/קלוד ממלא (אפשר גם מתקשורת אחרת) >>>",
                   "attrib": "<<< מי אמר + הקשר >>>"},
        "ongoing": {"title": "", "intro": "", "items": []},  # סיפורים שלא שחררנו — סיפור+פתיח+כתבות מעקב
        "collab": {"partner": "הפורום לחשיבה אזורית", "feature": {}, "items": []},  # שיתוף
        "opinions": {"feature": ops[0] if ops else "", "items": ops[1:6]},
        "reads": external_reads(),
        "legal": "default",
        "support_banner": "default",
    }
    json.dump(issue, open(os.path.join(OUT_DIR, "issue.draft.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(f"fetched {len(order)} posts ({len(news)} news, {len(ops)} opinions) since {after[:10]}")
    print("wrote articles.json + issue.draft.json")


if __name__ == "__main__":
    main()
