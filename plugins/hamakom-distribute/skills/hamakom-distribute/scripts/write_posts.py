#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
write_posts.py — מייצר שלד קופי לכל פלטפורמה לפי ה-DNA האמיתי של @ha_makom
(references/social-voice-dna.md — 299 פוסטים, 21.4.2025–24.7.2026).

חשוב: הסקריפט בונה את *המבנה* והמוסכמות (פייפ, סיומת, קרדיט, אורך, ריסון פיסוק).
את *הניסוח* של שורת הפתיח כותב קלוד בזמן ריצת הסקיל — סקריפט לא מנסח עיתונאות.
לכן הפלט מסמן <<< ... >>> במקומות שדורשים ניסוח, בדיוק כמו בניוזלטר.

כללי ה-DNA שמקודדים כאן:
  · אורך: חציון 350 תווים / 57 מילים, 1-2 פסקאות
  · תבנית פייפ (28%): [טענה חדה] | [ז'אנר/ייחוס] | [גוף]
  · פתיחה = הצהרת ממצא (90%), לא שאלה (2%), בלי "חימום"
  · סיום (31%): "הכתבה המלאה של <כותב/ת>, עכשיו בביו ובסטורי שלנו"
  · קרדיט תמונה בשורה נפרדת (52%): "צילום: פלאש 90"
  · תוכן רגיש → + "למצולמים אין קשר לכתבה"
  · ריסון: 7 סימני קריאה ב-299 פוסטים; אימוג'ים סמליים בלבד (12%); פנייה לקורא 2.7%
  · em dash — פספוס עריכה, לא כוונה. מנורמל ל-" - ".

תגיות UTM: כל קישור לכתבה יוצא עם utm_source של הפלטפורמה, utm_medium=social ו-utm_campaign
= ה-slug של הכתבה. בלי זה טלגרם, וואטסאפ ו-X לא נראים בכלל ב-Google Analytics (הדפדפן
שבתוך האפליקציה לא מעביר מאיפה הגיעו, והביקור נספר כ"ישיר"). אינסטגרם מתייג לבד (ig/social),
ושיתוף אוטומטי של Jetpack לפייסבוק מתייג לבד (facebook/jetpack_social).

הרצה: python3 write_posts.py article.json OUT_DIR
"""
import json, os, re, sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

HASHTAG = "#המקום_הכי_חם_בגיהנום"
CREDIT = "צילום: פלאש 90"
SENSITIVE_NOTE = "למצולמים אין קשר לכתבה"
# מילות-סף לתוכן רגיש → מוסיפות את שורת ההסתייגות (מוסכמת האתר)
SENSITIVE = ("תקיפה מינית", "אונס", "הטרדה מינית", "התעללות", "פגיעה מינית",
             "אובדנות", "התאבדות", "קטין", "נפגעות", "נפגעי")


def tagged(art, source):
    """הקישור לכתבה עם תגיות UTM לפלטפורמה. תגית קיימת באותו שם לא נדרסת."""
    link = (art.get("link") or "").strip()
    if not link:
        return ""
    u = urlsplit(link)
    q = dict(parse_qsl(u.query, keep_blank_values=True))
    slug = [p for p in u.path.split("/") if p][-1:] or ["home"]
    for k, v in (("utm_source", source), ("utm_medium", "social"), ("utm_campaign", slug[0])):
        q.setdefault(k, v)
    return urlunsplit((u.scheme, u.netloc, u.path, urlencode(q), u.fragment))


def proof(s):
    """חוק המקף + ריסון סימני קריאה (ה-DNA: 7 ב-299 פוסטים)."""
    s = re.sub(r"\s*[—–]\s*", " - ", s or "")
    s = re.sub(r"!{2,}", "!", s)
    return s.strip()


def is_sensitive(art):
    blob = " ".join([art.get("title", ""), art.get("excerpt", "")])
    return any(k in blob for k in SENSITIVE)


def sig(art, genre="הכתבה"):
    """הסיומת הקבועה של החשבון (31% מהפוסטים)."""
    a = art.get("author", "").strip()
    return f"{genre} המלאה של {a}, עכשיו בביו ובסטורי שלנו" if a else f"{genre} המלאה עכשיו בביו ובסטורי שלנו"


def credit_block(art):
    c = CREDIT
    if is_sensitive(art):
        c += f". {SENSITIVE_NOTE}"
    return c


def instagram(art):
    """קאפשיין IG — התבנית המובהקת של החשבון."""
    return "\n\n".join([
        "<<< שורת פתיח: הממצא הכי חד, כהצהרה. לא שאלה, בלי חימום. ~12-18 מילים >>>"
        " | <<< ז'אנר/ייחוס: תחקיר / טור דעה / שם הדובר >>>",
        "<<< פסקה: מה נמצא ומה המשמעות. ~35-45 מילים, משפטים טעונים במידע. "
        "אם יש תגובה - לצטט במרכאות עבריות ״...״, לא לפרפרזה >>>",
        sig(art),
        credit_block(art),
        HASHTAG,
    ])


def facebook(art):
    """פייסבוק — מעט ארוך יותר, אותו קול, לינק ישיר."""
    return "\n\n".join([
        "<<< שורת פתיח: הצהרת ממצא חדה >>> | <<< ז'אנר/ייחוס >>>",
        "<<< 2 פסקאות קצרות: הממצא + ההקשר. ~60-80 מילים. גוף שלישי, בלי פנייה לקורא >>>",
        sig(art),
        tagged(art, "facebook"),
        credit_block(art),
    ])


def x_post(art):
    """X — הכי קצר, הממצא בלבד + לינק."""
    return ("<<< הממצא בשורה אחת חדה, עד ~200 תווים. בלי סימן קריאה >>>\n\n"
            + tagged(art, "x"))


def whatsapp(art, source="whatsapp"):
    """וואטסאפ/טלגרם — ידיעה קצרה לקבוצות. אותו טקסט, קישור מתויג לכל אחת."""
    return "\n".join([
        f"*{proof(art.get('title',''))}*",
        "",
        "<<< 2-3 שורות: מה הממצא ולמה זה חשוב >>>",
        "",
        sig(art),
        tagged(art, source),
    ])


def reel_caption(art):
    return "\n\n".join([
        "<<< משפט אחד: ה-hook של הריל, הממצא הכי חד >>>",
        sig(art),
        HASHTAG,
    ])


def main():
    if len(sys.argv) < 3:
        raise SystemExit("שימוש: write_posts.py article.json OUT_DIR")
    art = json.load(open(sys.argv[1], encoding="utf-8"))
    out = sys.argv[2]
    os.makedirs(out, exist_ok=True)

    blocks = [
        ("אינסטגרם (קרוסלה)", instagram(art)),
        ("פייסבוק", facebook(art)),
        ("X", x_post(art)),
        ("וואטסאפ", whatsapp(art, "whatsapp")),
        ("טלגרם", whatsapp(art, "telegram")),
        ("ריל", reel_caption(art)),
    ]
    md = [f"# קופי הפצה - {proof(art.get('title',''))}", ""]
    md.append(f"**מאת:** {art.get('author','')}  ·  **קישור:** {art.get('link','')}")
    if is_sensitive(art):
        md.append("\n> תוכן רגיש זוהה - נוספה שורת ההסתייגות \"למצולמים אין קשר לכתבה\".")
    md.append("\n> הסימונים `<<< ... >>>` ממתינים לניסוח של קלוד/דור לפי קול האתר.")
    md.append("> מוסכמות מקודדות: פתיחה=הצהרת ממצא · תבנית פייפ · סיומת ביו+סטורי · קרדיט פלאש 90 · בלי סימני קריאה.")
    md.append("> הקישורים מתויגים ב-UTM לכל פלטפורמה, כדי שהביקורים ייספרו לה ב-Google Analytics. לא להחליף בקישור הנקי.\n")
    for name, body in blocks:
        md += [f"\n## {name}\n", "```", proof(body), "```"]

    p = os.path.join(out, "posts.md")
    open(p, "w", encoding="utf-8").write("\n".join(md) + "\n")
    print(f"  ✓ posts.md — {len(blocks)} פלטפורמות")
    return p


if __name__ == "__main__":
    main()
