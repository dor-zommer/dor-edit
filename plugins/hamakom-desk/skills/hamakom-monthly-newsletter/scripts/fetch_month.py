# -*- coding: utf-8 -*-
"""
fetch_month.py — הגרסה החודשית של משיכת הכתבות. מייצר:
  articles.json          — מילון slug -> רשומה (זהה לשבועי)
  issue.month.draft.json — שלד ניוזלטר חודשי: כותרת טווח-חודש + קופסת "החודש במספרים"

משתמש במנוע המשותף: מייבא את פונקציות המשיכה מ-fetch_articles.py (של hamakom-newsletter)
ואת ה-build מ-build_newsletter.py של אותו סקיל — כדי לשמור *אחידות עיצוב* מוחלטת בין
השבועי לחודשי. ה-SKILL.md מוסיף את תיקיית ה-scripts של hamakom-newsletter ל-PYTHONPATH.

הרצה:
  DAYS=30 PYTHONPATH="<weekly scripts>" python3 fetch_month.py
"""
import json, os, datetime, collections

# מיובא מהמנוע המשותף (hamakom-newsletter/scripts ב-PYTHONPATH)
from fetch_articles import (BASE, FIELDS, _get, strip_tags, author_of,
                            external_reads, HE_MONTHS, OPINION_CAT)
import html as _html

DAYS    = int(os.environ.get("DAYS", "30"))
OUT_DIR = os.environ.get("OUT_DIR", ".")


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
                "title": _html.unescape(p.get("title", {}).get("rendered", "")).strip(),
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
    authors = {arts[s]["author"] for s in order if arts[s]["author"]}

    # תווית טווח-חודש: החודש שבו נמצא רוב הכתבות (בד"כ החודש החולף)
    today = datetime.date.today()
    month_i = today.month - 1 if today.day <= 7 else today.month  # אם מוקדם בחודש, החודש שעבר
    if month_i == 0:
        month_i, year = 12, today.year - 1
    else:
        year = today.year
    period = f"{HE_MONTHS[month_i - 1]} {year}"

    # "החודש במספרים" — auto-draft; דור יכול לערוך/להוסיף מספרים ידניים (ביקורים, תורמים)
    stats = [
        {"num": str(len(order)), "label": "כתבות שפורסמו"},
        {"num": str(len(news)),  "label": "תחקירים וידיעות"},
        {"num": str(len(ops)),   "label": "טורים ודעות"},
        {"num": str(len(authors)), "label": "כתבים וכותבים"},
    ]

    issue = {
        "edition_label": "הניוזלטר החודשי",
        "accent": "heather",          # החודשי = אקסנט אברש (מבדיל ויזואלית מהשבועי-טרקוטה)
        "period": period,
        "week_date": period,
        "preheader": f'הגיליון החודשי של "המקום הכי חם בגיהנום" - {period}: {len(order)} כתבות',
        "editor_note": {
            "headline": "<<< כותרת פתיח חודשי — דור ממלא >>>",
            "paragraphs": ["<<< פתיח עורך — סיכום החודש בקול האתר. דור ממלא. >>>"],
        },
        "project":   {"label": "פרויקט מתעדכן", "title": "", "url": "",
                       "desc": "", "cta": "לפרויקט המלא ⟵"},
        "stats_label": "החודש במספרים",
        "stats": stats,
        "lead": news[0] if news else "",
        "lead_kicker": "תחקיר החודש",
        "data_stat": {"label": "הנתון של החודש", "img": "", "alt": "", "url": ""},
        "followup":  {"slug": "", "banner_title": "בעקבות הפרסום", "banner_sub": ""},
        "rundown_label": "עוד מהחודש האחרון במקום הכי חם בגיהנום",
        "rundown": news[2:] if len(news) > 2 else news[1:],
        "photo_of_week": {
            "img": "",
            "caption": "<<< תמונת החודש: מקום, הקשר ותאריך — דור/קלוד ממלא >>>",
            "credit": "צילום: ___ / פלאש 90",
            "place_after": 2,
        },
        "hero":  {"slug": news[1] if len(news) > 1 else "", "kicker": "מתחת לרדאר"},
        "reel":  {"url": "", "poster": "", "cta": "▶ לריל", "caption": ""},
        "quote": {"slug": ops[0] if ops else (news[0] if news else ""),
                   "text": "<<< ציטוט החודש - דור/קלוד ממלא (אפשר גם מתקשורת אחרת) >>>",
                   "attrib": "<<< מי אמר + הקשר >>>"},
        "ongoing": {"title": "", "intro": "", "items": []},  # סיפורים שלא שחררנו — סיפור+פתיח+כתבות מעקב
        "collab": {"partner": "הפורום לחשיבה אזורית", "feature": {}, "items": []},  # שיתוף
        "opinions": {"feature": ops[0] if ops else "", "items": ops[1:8]},
        "reads": external_reads(),
        "banner": "default",
    }
    json.dump(issue, open(os.path.join(OUT_DIR, "issue.month.draft.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    print(f"fetched {len(order)} posts ({len(news)} news, {len(ops)} opinions, "
          f"{len(authors)} authors) since {after[:10]} · period={period}")
    print("wrote articles.json + issue.month.draft.json")


if __name__ == "__main__":
    main()
