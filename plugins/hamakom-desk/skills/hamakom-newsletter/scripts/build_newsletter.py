#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_newsletter.py — בונה את הניוזלטר של "המקום הכי חם בגיהנום" כ-HTML למייל (Brevo).
מבנה: 26 הפינות של הגיליון שנשלח (13.6.2026), בעיצוב HaMakom DS 2026:
  שנהב #faf9f5 (כרטיס) על מסגרת #e6e3da · דיו #141413 (כותרות/סקשנים) · טרקוטה #D97757 (אקסנט).
  פונט: Suez One לכותרות → IBM Plex Sans Hebrew לגוף (Google Fonts). פס-חתימה טריקולור בראש.
  בלי בלוק SLAPP (הקמפיין נגמר).
  מנוע משותף לשבועי ולחודשי — cfg['accent']='heather' + cfg['stats'] הופכים אותו לחודשי.
קלט: argv[1]=<issue.json> (או ENV ISSUE)  ARTICLES=articles.json  OUT_DIR=.
דגלים: NO_EDITOR=1 מדלג על פתיח העורך.
"""
import json, os, re, sys, datetime, html as _html

# קובץ הגיליון: argv[1] גובר על ENV ISSUE גובר על ברירת המחדל issue.json
_argv_issue = next((a for a in sys.argv[1:] if a.endswith(".json")), None)
ISSUE    = _argv_issue or os.environ.get("ISSUE", "issue.json")
ARTICLES = os.environ.get("ARTICLES", "articles.json")
OUT_DIR  = os.environ.get("OUT_DIR", ".")
UTM      = os.environ.get("UTM", "?utm_source=brevo&utm_medium=email&utm_campaign=weekly")

cfg = json.load(open(ISSUE, encoding="utf-8")) if os.path.exists(ISSUE) else {}
# articles.json = dict keyed by slug → record. (אם בטעות list — ממפים לפי slug.)
_raw = json.load(open(ARTICLES, encoding="utf-8")) if os.path.exists(ARTICLES) else {}
ART = _raw if isinstance(_raw, dict) else {a.get("slug"): a for a in _raw}
MISSING = []

# ---------- פלטה HaMakom DS 2026 ----------
INK      = "#141413"   # דיו — רקע כהה, טקסט ראשי
IVORY    = "#faf9f5"   # שנהב — כרטיס
FRAME    = "#e6e3da"   # מסגרת חיצונית
PAPER    = "#f3f1ea"   # שנהב-כהה — קופסאות (שיתוף)
TERRA    = "#D97757"   # טרקוטה — כפתורים/פסים על דיו
TERRA_D  = "#B4581F"   # טרקוטה כהה — קיקר/מאת/אקסנט על בהיר
SC_TERRA = "#E8906F"   # טרקוטה מובהרת — לייבלים על דיו
SAGE     = "#788C5D"   # מרווה
HEATHER  = "#8E6FA8"   # אברש
INK2     = "#333333"; INK3 = "#6B6B6B"; LINE = "#E6E6E6"
ON_DARK  = "#C7C7C7"; ON_DARK_SOFT = "#8a8a8a"; WHITE = "#ffffff"

# ---------- צבע אקסנט לפי מהדורה ----------
# השבועי = טרקוטה. החודשי = אברש (heather). פס-החתימה הטריקולור נשאר זהה בשתיהן (DNA מותגי);
# רק התוויות/קיקרים/כפתורים/המספרים משתנים — כדי שיהיה הבדל עיצובי ברור בין המהדורות.
if str(cfg.get("accent", "")).lower() in ("heather", "monthly", "אברש"):
    ACCENT, ACCENT_D, ACCENT_SC = HEATHER, "#5F4478", "#B79BD0"   # אברש + כהה (על בהיר) + מובהר (על דיו)
else:
    ACCENT, ACCENT_D, ACCENT_SC = TERRA, TERRA_D, SC_TERRA         # טרקוטה (ברירת מחדל — שבועי)

FONT_HEAD = "'Suez One','Frank Ruhl Libre',Georgia,serif"
FONT      = "'IBM Plex Sans Hebrew','Heebo',-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif"

# ---------- helpers ----------
def _ph(x):
    return (not x) or str(x).strip() == "" or str(x).strip().startswith("<<<")

def hl(t):
    """מדגיש placeholder בצהוב שיבלוט ב-preview."""
    if _ph(t):
        return (f'<span style="background:#FFF3B0;color:#7a5b00;padding:1px 5px;border-radius:3px">'
                f'{_html.escape(str(t))}</span>')
    return t

def _proof(s):
    """הגהה לפי חוק המקף של דור: אין קו מפריד ארוך (—/–) בעברית.
    קו מפריד ארוך המשמש כהפרדה → מקף רגיל עם רווחים ' - '. חל על כל טקסט הפלט."""
    if not s:
        return s
    # em/en-dash (וגם ־ עברי שהוקף ברווחים בטעות) → מקף מפריד תקין
    s = re.sub(r"\s*[—–]\s*", " - ", s)
    return s

def rec(s):    return ART.get(s, {})
def link(s):   return (rec(s).get("link", "#")) + UTM
def img(s):    return rec(s).get("img", "")
def title(s):  return re.sub(r"\s*\|\s*(תחקיר|טור|דעה)\s*$", "", rec(s).get("title", s or "")).strip()
def author(s): return rec(s).get("author", "")
def dt(s):
    d = rec(s).get("date", "")
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", d or "")
    return f"{m.group(3)}/{m.group(2)}" if m else ""
def excerpt(s, n=200):
    e = re.sub(r"<[^>]+>", "", rec(s).get("excerpt", "")).strip()
    return (e[:n].rstrip() + "…") if len(e) > n else e
def A(href, t, color=ACCENT_D):
    return f'<a target="_blank" href="{href}" style="text-decoration:none;color:{color};font-weight:700">{t}</a>'
def P(t, c=INK2, sz=15, mb=12, extra=""):
    return (f'<p style="Margin:0 0 {mb}px;font-family:{FONT};font-size:{sz}px;line-height:24px;'
            f'color:{c};direction:rtl;text-align:right{extra}">{t}</p>')

def sig_bar(h=6):
    cell = lambda x, c: f'<td width="200" style="width:200px;height:{h}px;background:{c};font-size:0;line-height:0">&nbsp;</td>'
    return (f'<tr><td style="padding:0;font-size:0;line-height:0"><table role="presentation" width="100%" '
            f'cellpadding="0" cellspacing="0" style="border-collapse:collapse"><tbody><tr>'
            f'{cell(1,TERRA)}{cell(2,SAGE)}{cell(3,HEATHER)}</tr></tbody></table></td></tr>')

def section_label(t):
    return (f'<tr><td dir="rtl" style="padding:26px 28px 4px;Margin:0"><p style="Margin:0;font-family:{FONT};'
            f'font-size:13px;font-weight:800;letter-spacing:3px;color:{ACCENT_D};direction:rtl;'
            f'border-bottom:2px solid {INK};padding-bottom:8px;display:inline-block">{t}</p></td></tr>')

def dark(label, inner):
    return (f'<tr><td bgcolor="{INK}" dir="rtl" align="right" style="padding:30px 28px;Margin:0;background-color:{INK}">'
            f'<p style="Margin:0 0 14px;font-family:{FONT};font-size:13px;font-weight:800;letter-spacing:3px;'
            f'color:{ACCENT_SC};direction:rtl">{label}</p>{inner}</td></tr>')

# ---------- sections ----------
def header():
    c = cfg.get("logo_dark", "https://uccprg.stripocdn.email/content/guids/CABINET_63cfa9cad8ed0171fb3fe41bc5aa8946a5ebd57995774e9a3e262bf666f3a22b/images/hamakomsquarewhiteh600_JLe.png")
    return (f'<tr><td align="center" bgcolor="{INK}" style="padding:24px 0 18px;Margin:0;background-color:{INK}">'
            f'<a href="https://ha-makom.co.il/{UTM}" target="_blank"><img src="{c}" height="80" '
            f'alt="המקום הכי חם בגיהנום" style="display:block;border:0;margin:0 auto;height:80px"></a>'
            f'<p style="Margin:12px 0 0;font-family:{FONT};font-size:12px;font-weight:700;letter-spacing:5px;'
            f'color:{ACCENT_SC};direction:rtl">{cfg.get("edition_label","הניוזלטר השבועי")}'
            f'&nbsp;&nbsp;·&nbsp;&nbsp;{cfg.get("period", cfg.get("week_date",""))}</p></td></tr>')

def note():
    en = cfg.get("editor_note", {}) or {}
    head = en.get("headline", "<<< כותרת פתיח — דור ממלא >>>")
    paras = en.get("paragraphs") or ["<<< פתיח העורך — דור ממלא >>>"]
    if _ph(head) or any(_ph(p) for p in paras):
        MISSING.append("פתיח עורך")
    inner = (f'<p style="Margin:0 0 16px;font-family:{FONT_HEAD};font-size:27px;font-weight:900;line-height:34px;'
             f'color:{INK};direction:rtl;text-align:right">{hl(head)}</p>')
    for p in paras:
        inner += P(hl(p) if _ph(p) else p, INK2, 15, 12)
    inner += P("<strong>דור זומר</strong>, עורך ראשי", INK3, 14, 0)
    return (f'<tr><td dir="rtl" style="padding:26px 28px 24px;Margin:0">{inner}</td></tr>')

def project():
    pr = cfg.get("project", {}) or {}
    if _ph(pr.get("title", "")):
        return ""
    u = (pr.get("url", "") or "#") + UTM
    out = (f'<tr><td bgcolor="{INK}" align="center" dir="rtl" style="padding:38px 30px;Margin:0;background-color:{INK}">'
           f'<p style="Margin:0 0 14px;font-family:{FONT};font-size:12px;font-weight:800;letter-spacing:4px;color:{ACCENT_SC};direction:rtl">{pr.get("label","חדש באתר · פרויקט מתעדכן")}</p>'
           f'<p style="Margin:0 0 14px;font-family:{FONT_HEAD};font-size:44px;font-weight:900;line-height:48px;color:{IVORY};direction:rtl">'
           f'<a target="_blank" href="{u}" style="text-decoration:none;color:{IVORY}">{pr["title"]}</a></p>')
    if pr.get("desc"):
        out += f'<p style="Margin:0 0 22px;font-family:{FONT};font-size:16px;line-height:25px;color:{ON_DARK};direction:rtl">{pr["desc"]}</p>'
    out += (f'<table cellpadding="0" cellspacing="0" align="center" style="margin:0 auto"><tbody><tr>'
            f'<td bgcolor="{ACCENT}" style="border-radius:6px"><a target="_blank" href="{u}" style="display:inline-block;'
            f'padding:13px 36px;font-family:{FONT};font-size:16px;font-weight:800;color:{INK};text-decoration:none">'
            f'{pr.get("cta","לפרויקט המלא")}&nbsp;⟵</a></td></tr></tbody></table></td></tr>')
    return out

def lead(slug, kicker="תחקיר השבוע"):
    return (f'<tr><td dir="rtl" style="padding:18px 28px 8px;Margin:0">'
            f'<p style="Margin:0 0 12px;font-family:{FONT};font-size:13px;font-weight:800;letter-spacing:3px;color:{ACCENT_D};direction:rtl">{kicker}</p>'
            f'<a target="_blank" href="{link(slug)}"><img src="{img(slug)}" alt="" width="544" style="display:block;border:0;width:100%;border-radius:8px;margin:0 0 16px"></a>'
            f'<h1 style="Margin:0 0 10px;font-family:{FONT_HEAD};font-size:30px;font-weight:900;line-height:37px;color:{INK};direction:rtl;text-align:right">'
            f'<a target="_blank" href="{link(slug)}" style="text-decoration:none;color:{INK}">{title(slug)}</a></h1>'
            + P(excerpt(slug, 220), INK2, 16)
            + f'<p style="Margin:0;font-family:{FONT};font-size:12px;font-weight:700;color:{ACCENT_D};direction:rtl;text-align:right">מאת {author(slug)} · {dt(slug)}</p></td></tr>')

def data_strip():
    d = cfg.get("data_stat", {}) or {}
    if _ph(d.get("img", "")):
        return ""
    u = (d.get("url", "") or "#") + UTM
    return dark(d.get("label", "הנתון של השבוע"),
                f'<a target="_blank" href="{u}"><img src="{d["img"]}" alt="{d.get("alt","")}" width="440" '
                f'style="display:block;border:0;width:100%;max-width:440px;margin:0 auto;border-radius:8px"></a>')

def month_stats():
    """קופסת 'החודש במספרים' — ייחודי לגיליון החודשי. cfg['stats'] = [{num, label}, ...]."""
    stats = [s for s in (cfg.get("stats", []) or []) if isinstance(s, dict) and s.get("num")]
    if not stats:
        return ""
    cells = ""
    w = max(1, 100 // min(len(stats), 4))
    for s in stats:
        cells += (f'<td width="{w}%" valign="top" align="center" style="padding:6px 8px">'
                  f'<p style="Margin:0;font-family:{FONT_HEAD};font-size:42px;font-weight:900;line-height:46px;color:{ACCENT_SC};direction:rtl">{s["num"]}</p>'
                  f'<p style="Margin:4px 0 0;font-family:{FONT};font-size:13px;font-weight:700;line-height:18px;color:{ON_DARK};direction:rtl">{s.get("label","")}</p></td>')
    inner = (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" dir="rtl" '
             f'style="border-collapse:collapse"><tbody><tr>{cells}</tr></tbody></table>')
    return dark(cfg.get("stats_label", "החודש במספרים"), inner)

def item(slug, featured=False):
    """אייטם רשימה. featured=True — כרטיס בולט (כותרת סריף גדולה, תמונה גדולה, תקציר).
    featured=False — שורה קומפקטית (כותרת קטנה + מאת, תמונה קטנה, בלי תקציר) לרשימה סרוקה."""
    if featured:
        return (f'<tr><td dir="rtl" style="padding:20px 28px 8px;Margin:0;border-top:1px solid {LINE}">'
                f'<a target="_blank" href="{link(slug)}"><img src="{img(slug)}" alt="" width="544" style="display:block;border:0;width:100%;border-radius:6px;margin:0 0 14px"></a>'
                f'<a target="_blank" href="{link(slug)}" style="text-decoration:none"><span style="font-family:{FONT_HEAD};font-size:24px;font-weight:900;line-height:31px;color:{INK};direction:rtl">{title(slug)}</span></a>'
                + P(excerpt(slug, 150), INK2, 15, 0, ";margin-top:10px")
                + f'<p style="Margin:8px 0 0;font-family:{FONT};font-size:12px;font-weight:700;color:{ACCENT_D};direction:rtl">מאת {author(slug)} · {dt(slug)}</p></td></tr>')
    # קומפקטי
    return (f'<tr><td dir="rtl" style="padding:14px 28px;Margin:0;border-top:1px solid {LINE}">'
            f'<table width="100%" dir="rtl" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse"><tbody><tr>'
            f'<td class="imgcell" width="92" valign="top" style="padding:0 0 0 14px"><a target="_blank" href="{link(slug)}">'
            f'<img class="thumb" src="{img(slug)}" alt="" width="92" style="display:block;border:0;width:92px;border-radius:5px"></a></td>'
            f'<td class="txtcell" valign="top" align="right" dir="rtl" style="padding:0">'
            f'<a target="_blank" href="{link(slug)}" style="text-decoration:none;color:{INK}"><span style="font-family:{FONT};font-size:16px;font-weight:700;line-height:22px;color:{INK}">{title(slug)}</span></a>'
            f'<p style="Margin:5px 0 0;font-family:{FONT};font-size:12px;color:{INK3};direction:rtl">מאת {author(slug)} · {dt(slug)}</p>'
            f'</td></tr></tbody></table></td></tr>')

def followup():
    f = cfg.get("followup", {}) or {}
    s = f.get("slug", "")
    if _ph(s):
        return ""
    out = (f'<tr><td bgcolor="{ACCENT}" align="center" dir="rtl" style="padding:16px 28px;Margin:0;background-color:{ACCENT}">'
           f'<p style="Margin:0;font-family:{FONT};font-size:20px;font-weight:900;letter-spacing:1px;color:{INK};direction:rtl">{f.get("banner_title","בעקבות הפרסום")}</p>')
    if f.get("banner_sub"):
        out += f'<p style="Margin:4px 0 0;font-family:{FONT};font-size:13px;font-weight:700;color:{INK};direction:rtl">{f["banner_sub"]}</p>'
    out += "</td></tr>"
    out += (f'<tr><td dir="rtl" align="right" style="padding:18px 28px 8px">'
            f'<a target="_blank" href="{link(s)}"><img src="{img(s)}" alt="" width="544" style="display:block;border:0;width:100%;border-radius:8px;margin:0 0 14px"></a>'
            f'<a target="_blank" href="{link(s)}" style="text-decoration:none"><span style="font-family:{FONT_HEAD};font-size:23px;font-weight:900;line-height:30px;color:{INK};direction:rtl">{title(s)}</span></a>'
            + P(excerpt(s, 180), INK2, 15, 0, ";margin-top:10px")
            + f'<p style="Margin:8px 0 0;font-family:{FONT};font-size:12px;font-weight:700;color:{ACCENT_D};direction:rtl">מאת {author(s)} · {dt(s)}</p></td></tr>')
    return out

def photo_strip():
    p = cfg.get("photo_of_week", {}) or {}
    im = p.get("img", ""); cap = p.get("caption", ""); cr = p.get("credit", "צילום: ___ / פלאש 90")
    if _ph(im) or _ph(cap):
        MISSING.append("תמונת השבוע (פלאש90)")
    body = ""
    if not _ph(im):
        body += f'<img src="{im}" alt="" width="544" style="display:block;border:0;width:100%;border-radius:8px;margin:0 0 12px">'
    else:
        body += (f'<div style="width:100%;height:180px;background:#2a2a28;border-radius:8px;margin:0 0 12px;'
                 f'text-align:center;line-height:180px;font-family:{FONT};color:{ON_DARK_SOFT};font-size:14px">'
                 f'{hl("&lt;&lt;&lt; תמונת השבוע — פלאש90 &gt;&gt;&gt;")}</div>')
    body += (f'<p style="Margin:0 0 6px;font-family:{FONT};font-size:14px;line-height:24px;color:#D8D8D8;direction:rtl;text-align:right">'
             f'{hl(cap) if _ph(cap) else cap}</p>'
             f'<p style="Margin:0;font-family:{FONT};font-size:12px;color:{ON_DARK_SOFT};direction:rtl;text-align:right">{cr}</p>')
    return dark("תמונת השבוע", body)

def hero(slug, kicker="מתחת לרדאר"):
    return (f'<tr><td style="padding:22px 28px 8px;Margin:0;border-top:6px solid {INK}">'
            f'<p style="Margin:0 0 12px;font-family:{FONT};font-size:13px;font-weight:800;letter-spacing:3px;color:{ACCENT_D};direction:rtl">{kicker}</p>'
            f'<a target="_blank" href="{link(slug)}"><img src="{img(slug)}" alt="" width="544" style="display:block;border:0;width:100%;border-radius:8px;margin:0 0 16px"></a>'
            f'<h2 style="Margin:0 0 10px;font-family:{FONT_HEAD};font-size:27px;font-weight:900;line-height:34px;color:{INK};direction:rtl;text-align:right">'
            f'<a target="_blank" href="{link(slug)}" style="text-decoration:none;color:{INK}">{title(slug)}</a></h2>'
            + P(excerpt(slug, 200), INK2, 16)
            + f'<p style="Margin:0;font-family:{FONT};font-size:12px;font-weight:700;color:{ACCENT_D};direction:rtl">מאת {author(slug)} · {dt(slug)}</p></td></tr>')

def _placeholder_box(txt):
    return (f'<div style="width:100%;padding:26px 12px;background:#2a2a28;border-radius:8px;'
            f'text-align:center;font-family:{FONT};color:{ON_DARK_SOFT};font-size:14px">'
            f'{hl("&lt;&lt;&lt; " + txt + " &gt;&gt;&gt;")}</div>')

def ongoing_story():
    """סיפורים שלא שחררנו — סיפור אחד שהמערכת נשארת עליו: כותרת-סיפור + פתיח + כתבות המעקב
    לאורך זמן (מיני-דוסייה). פינה קבועה: תמיד מופיעה. ריק → placeholder מסומן.
    cfg['ongoing'] = {title, intro, items:[slug,...]}."""
    og = cfg.get("ongoing", {}) or {}
    label = cfg.get("ongoing_label", "סיפורים שלא שחררנו")
    title_t = og.get("title", "")
    items = [s for s in (og.get("items", []) or []) if not _ph(s)]
    if _ph(title_t) or not items:
        MISSING.append("סיפורים שלא שחררנו")
        return (section_label(label)
                + f'<tr><td dir="rtl" align="right" style="padding:8px 28px 20px;Margin:0">'
                + f'<div style="width:100%;padding:22px 12px;background:#EFECE3;border-radius:8px;text-align:center;'
                + f'font-family:{FONT};color:#8a8271;font-size:14px">'
                + f'{hl("&lt;&lt;&lt; סיפור שנשארים עליו: כותרת + פתיח + כתבות המעקב - דור ממלא &gt;&gt;&gt;")}</div></td></tr>')
    out = section_label(label)
    out += (f'<tr><td dir="rtl" align="right" style="padding:8px 28px 4px;Margin:0">'
            f'<p style="Margin:0 0 6px;font-family:{FONT_HEAD};font-size:26px;font-weight:900;line-height:33px;color:{INK};direction:rtl;text-align:right">{title_t}</p>')
    if not _ph(og.get("intro", "")):
        out += P(og["intro"], INK2, 15, 0, ";margin-top:6px")
    out += "</td></tr>"
    for s in items:
        out += (f'<tr><td dir="rtl" style="padding:16px 28px;Margin:0;border-top:1px solid {LINE}">'
                f'<table width="100%" dir="rtl" cellpadding="0" cellspacing="0" role="presentation" style="border-collapse:collapse"><tbody><tr>'
                f'<td class="imgcell" width="120" valign="top" style="padding:0 0 0 14px"><a target="_blank" href="{link(s)}">'
                f'<img class="thumb" src="{img(s)}" alt="" width="120" style="display:block;border:0;width:120px;border-radius:5px"></a></td>'
                f'<td class="txtcell" valign="top" align="right" dir="rtl" style="padding:0">'
                f'<p style="Margin:0 0 4px;font-family:{FONT};font-size:12px;font-weight:800;color:{ACCENT_D};direction:rtl">{dt(s)}</p>'
                f'<a target="_blank" href="{link(s)}" style="text-decoration:none"><span style="font-family:{FONT};font-size:16px;font-weight:700;line-height:22px;color:{INK}">{title(s)}</span></a>'
                f'<p class="m-hide" style="Margin:5px 0 0;font-family:{FONT};font-size:13px;line-height:19px;color:#444;direction:rtl">{excerpt(s,90)}</p>'
                f'<p style="Margin:5px 0 0;font-family:{FONT};font-size:12px;color:{INK3};direction:rtl">מאת {author(s)}</p>'
                f'</td></tr></tbody></table></td></tr>')
    return out

def reel_strip():
    r = cfg.get("reel", {}) or {}
    u = (r.get("url", "") or "")
    if _ph(u) or _ph(r.get("poster", "")):
        MISSING.append("ברשתות שלנו (ריל/פוסט)")
        cap = r.get("caption", "") if not _ph(r.get("caption", "")) else "ריל או פוסט מהרשתות - דור ממלא"
        return dark("ברשתות שלנו",
                    _placeholder_box("ריל/פוסט מהרשתות שלנו - קישור + פוסטר")
                    + f'<p style="Margin:12px 0 0;font-family:{FONT};font-size:14px;color:#D8D8D8;direction:rtl;text-align:center">{cap} {A("https://www.instagram.com/ha_makom/"+UTM, "@ha_makom ⟵", ACCENT_SC)}</p>')
    uu = u + UTM
    body = (f'<a target="_blank" href="{uu}"><img src="{r["poster"]}" alt="" width="280" style="display:block;border:0;width:280px;max-width:100%;margin:0 auto 14px;border-radius:8px"></a>'
            f'<table cellpadding="0" cellspacing="0" align="center" style="margin:0 auto 12px"><tbody><tr>'
            f'<td bgcolor="{ACCENT}" style="border-radius:6px"><a target="_blank" href="{uu}" style="display:inline-block;padding:11px 28px;font-family:{FONT};font-size:15px;font-weight:700;color:{INK};text-decoration:none">{r.get("cta","▶  לריל")}</a></td></tr></tbody></table>'
            f'<p style="Margin:0;font-family:{FONT};font-size:14px;line-height:24px;color:#D8D8D8;direction:rtl;text-align:center">{r.get("caption","")} {A("https://www.instagram.com/ha_makom/"+UTM, "@ha_makom ⟵", ACCENT_SC)}</p>')
    return dark("ברשתות שלנו", body)

def collab_box():
    cb = cfg.get("collab", {}) or {}
    feat = cb.get("feature", {}) or {}
    partner = cb.get("partner", "") if not _ph(cb.get("partner", "")) else "הפורום לחשיבה אזורית"
    if _ph(feat.get("title", "")):
        MISSING.append(f"שיתוף ({partner})")
        return (f'<tr><td dir="rtl" align="right" style="padding:24px 28px;Margin:0;background:{PAPER};border-top:3px solid {INK}">'
                f'<p style="Margin:0 0 12px;font-family:{FONT};font-size:13px;font-weight:800;letter-spacing:1px;color:{INK};direction:rtl">'
                f'המקום הכי חם בגיהנום&nbsp;<span style="color:{ACCENT_D}">✕</span>&nbsp;{partner}</p>'
                f'<div style="width:100%;padding:22px 12px;background:#E4DFD1;border-radius:8px;text-align:center;'
                f'font-family:{FONT};color:#8a8271;font-size:14px">{hl("&lt;&lt;&lt; כתבה של השותפות - דור ממלא &gt;&gt;&gt;")}</div></td></tr>')
    fu = (feat.get("url", "") or "#") + UTM
    out = (f'<tr><td dir="rtl" align="right" style="padding:0;Margin:0;background:{PAPER};border-top:3px solid {INK}">'
           f'<table width="100%" cellpadding="0" cellspacing="0"><tbody>'
           f'<tr><td dir="rtl" align="right" style="padding:24px 28px 6px"><p style="Margin:0 0 8px;font-family:{FONT};font-size:13px;font-weight:800;letter-spacing:1px;color:{INK};direction:rtl">'
           f'המקום הכי חם בגיהנום&nbsp;<span style="color:{ACCENT_D}">✕</span>&nbsp;{cb.get("partner","שותף")}</p></td></tr>'
           f'<tr><td style="padding:0 28px"><a target="_blank" href="{fu}"><img src="{feat.get("img","")}" alt="" width="544" style="display:block;border:0;width:100%;border-radius:8px"></a></td></tr>'
           f'<tr><td dir="rtl" align="right" style="padding:13px 28px 18px">'
           f'<a target="_blank" href="{fu}" style="text-decoration:none"><span style="font-family:{FONT_HEAD};font-size:23px;font-weight:900;line-height:30px;color:{INK};direction:rtl">{feat["title"]}</span></a>'
           + P(feat.get("dek", ""), INK2, 15, 0, ";margin-top:10px")
           + f'<p style="Margin:8px 0 0;font-family:{FONT};font-size:12px;font-weight:700;color:{INK3};direction:rtl">מאת {feat.get("author","")} · {cb.get("partner","")}</p></td></tr>')
    for it in cb.get("items", []) or []:
        if _ph(it.get("title", "")):
            continue
        iu = (it.get("url", "") or "#") + UTM
        out += (f'<tr><td dir="rtl" align="right" style="padding:16px 28px;border-top:1px solid #DAD3C4">'
                f'<table width="100%" dir="rtl" cellpadding="0" cellspacing="0"><tbody><tr>'
                f'<td class="imgcell" width="120" valign="top" style="padding:0 0 0 14px"><a target="_blank" href="{iu}"><img class="thumb" src="{it.get("img","")}" alt="" width="120" style="display:block;border:0;width:120px;border-radius:5px"></a></td>'
                f'<td class="txtcell" valign="top" align="right" dir="rtl"><a target="_blank" href="{iu}" style="text-decoration:none"><span style="font-family:{FONT};font-size:16px;font-weight:700;color:{INK};line-height:22px">{it["title"]}</span></a>'
                f'<p style="Margin:6px 0 0;font-family:{FONT};font-size:12px;color:{INK3};direction:rtl">מאת {it.get("author","")} · {cb.get("partner","")}</p></td></tr></tbody></table></td></tr>')
    out += "</tbody></table></td></tr>"
    return out

def quote_strip():
    q = cfg.get("quote", {}) or {}
    txt = q.get("text", ""); attrib = q.get("attrib", ""); u = q.get("url", "")
    if _ph(txt) and _ph(u):
        return ""
    if _ph(txt) or _ph(attrib):
        MISSING.append("ציטוט השבוע")
    uu = (u or "#") + UTM
    body = ""
    if q.get("img"):
        body += f'<a target="_blank" href="{uu}"><img src="{q["img"]}" alt="" width="544" style="display:block;border:0;width:100%;border-radius:8px;margin:0 0 16px"></a>'
    body += (f'<p style="Margin:0 0 12px;font-family:{FONT_HEAD};font-size:24px;font-weight:800;line-height:33px;color:{IVORY};direction:rtl;text-align:right">'
             f'{hl(txt) if _ph(txt) else "״" + txt + "״"}</p>')
    more = A(uu, "לטור המלא ⟵", ACCENT_SC) if not _ph(u) else ""
    body += f'<p style="Margin:0;font-family:{FONT};font-size:14px;line-height:24px;color:#D8D8D8;direction:rtl;text-align:right">{(hl(attrib) if _ph(attrib) else attrib)} {more}</p>'
    return dark("ציטוט השבוע", body)

def opinions_block():
    op = cfg.get("opinions", {}) or {}
    feat = op.get("feature", ""); items = op.get("items", []) or []
    if _ph(feat) and not items:
        return ""
    out = section_label("דעות וטורים")
    if not _ph(feat):
        out += (f'<tr><td dir="rtl" align="right" style="padding:6px 28px 16px;Margin:0">'
                f'<a target="_blank" href="{link(feat)}"><img src="{img(feat)}" alt="" width="544" style="display:block;border:0;width:100%;border-radius:8px;margin:0 0 14px"></a>'
                f'<p style="Margin:0 0 8px;font-family:{FONT};font-size:12px;font-weight:800;letter-spacing:2px;color:{ACCENT_D};direction:rtl">הטור של {author(feat)}</p>'
                f'<a target="_blank" href="{link(feat)}" style="text-decoration:none"><span style="font-family:{FONT_HEAD};font-size:23px;font-weight:900;line-height:30px;color:{INK};direction:rtl">{title(feat)}</span></a>'
                + P(excerpt(feat, 180), INK2, 15, 0, ";margin-top:10px") + '</td></tr>')
    for s in items:
        if _ph(s):
            continue
        out += (f'<tr><td dir="rtl" align="right" style="padding:16px 28px;Margin:0;border-top:1px solid {LINE}">'
                f'<table width="100%" dir="rtl" cellpadding="0" cellspacing="0" role="presentation"><tbody><tr>'
                f'<td class="imgcell" width="96" valign="top" style="padding:0 0 0 14px"><a target="_blank" href="{link(s)}"><img class="thumb" src="{img(s)}" alt="" width="96" style="display:block;border:0;width:96px;border-radius:5px"></a></td>'
                f'<td class="txtcell" valign="top" align="right" dir="rtl"><a target="_blank" href="{link(s)}" style="text-decoration:none"><span style="font-family:{FONT};font-size:16px;font-weight:700;color:{INK};line-height:22px">{title(s)}</span></a>'
                f'<p style="Margin:6px 0 0;font-family:{FONT};font-size:12px;color:{INK3};direction:rtl">מאת {author(s)}</p></td></tr></tbody></table></td></tr>')
    return out

def reads_block():
    reads = [r for r in (cfg.get("reads", []) or []) if isinstance(r, dict) and not _ph(r.get("headline", ""))]
    if not reads:
        MISSING.append("המלצות קריאה (העין השביעית + שקוף)")
        reads = [{"outlet": "העין השביעית", "headline": "<<< כתבה מהעין השביעית >>>", "dek": "", "url": "https://www.the7eye.org.il/"},
                 {"outlet": "שקוף", "headline": "<<< כתבה משקוף >>>", "dek": "", "url": "https://shakuf.co.il/"}]
    body = f'<p style="Margin:0 0 16px;font-family:{FONT};font-size:14px;line-height:24px;color:#D8D8D8;direction:rtl;text-align:right">מהשותפות שלנו ב״עיתונות העצמאית״:</p>'
    for i, r in enumerate(reads):
        if i:
            body += '<div style="height:18px;border-bottom:1px solid #3a3a3a;margin:0 0 18px;font-size:0">&nbsp;</div>'
        u = (r.get("url", "#") or "#")
        body += (f'<p style="Margin:0 0 3px;font-family:{FONT};font-size:12px;font-weight:800;letter-spacing:2px;color:{ACCENT_SC};direction:rtl">{r.get("outlet","")}</p>'
                 f'<p style="Margin:0 0 6px;font-family:{FONT};font-size:18px;font-weight:800;line-height:25px;color:{IVORY};direction:rtl;text-align:right"><a target="_blank" href="{u}" style="text-decoration:none;color:{IVORY}">{r["headline"]}</a></p>'
                 + P((r.get("dek", "") + " " + A(u, "לכתבה ⟵", ACCENT_SC)).strip(), "#CFCFCF", 14, 0))
    return dark("המלצות קריאה", body)

def banner_block():
    b = cfg.get("banner", "default")
    if b in (None, "", False):
        return ""
    url = (b.get("url") if isinstance(b, dict) else None) or "https://shakuf.co.il/join"
    im = (b.get("img") if isinstance(b, dict) else None) or "https://uccprg.stripocdn.email/content/guids/CABINET_5253251cce9b3dc788ada2ba543bf444757c1feedcc6d2fa83b5d411bda0d7c8/images/bbanner_horizontal2_copy.png"
    return (f'<tr><td align="center" dir="rtl" style="padding:24px 28px 6px;Margin:0">'
            f'<a target="_blank" href="{url}{UTM}"><img src="{im}" alt="עיתונות עצמאית — הצטרפו אלינו" width="544" '
            f'style="display:block;border:0;width:100%;max-width:544px;margin:0 auto;border-radius:8px"></a></td></tr>')

def footer():
    socials = cfg.get("socials") or [
        ("פייסבוק", "https://www.facebook.com/hottestplaceinhell/"),
        ("אינסטגרם", "https://www.instagram.com/ha_makom/"),
        ("X", "https://twitter.com/ha_makom"),
        ("טלגרם", "https://t.me/ha_makom"),
        ("יוטיוב", "https://www.youtube.com/Ha-makomCoIl")]
    links = "&nbsp;&nbsp;·&nbsp;&nbsp;".join(
        f'<a href="{u}{UTM}" target="_blank" style="color:{IVORY};text-decoration:none;font-weight:700">{n}</a>' for n, u in socials)
    logo = cfg.get("logo_dark", "https://uccprg.stripocdn.email/content/guids/CABINET_63cfa9cad8ed0171fb3fe41bc5aa8946a5ebd57995774e9a3e262bf666f3a22b/images/hamakomsquarewhiteh600_JLe.png")
    return (f'<tr><td align="center" bgcolor="{INK}" dir="rtl" style="padding:30px 28px;Margin:0;background-color:{INK}">'
            f'<img src="{logo}" height="56" alt="המקום הכי חם בגיהנום" style="display:block;border:0;height:56px;margin:0 auto 14px">'
            f'<p style="Margin:0 0 12px;font-family:{FONT};font-size:13px;direction:rtl;color:#bbb">{links}</p>'
            f'<table cellpadding="0" cellspacing="0" align="center" style="margin:0 auto 16px"><tbody><tr>'
            f'<td bgcolor="{ACCENT}" style="border-radius:6px"><a target="_blank" href="https://ha-makom.co.il/invest{UTM}" style="display:inline-block;padding:11px 30px;font-family:{FONT};font-size:15px;font-weight:800;color:{INK};text-decoration:none">תמכו בעיתונות עצמאית</a></td></tr></tbody></table>'
            f'<p style="Margin:0 0 14px;font-family:{FONT};font-size:12px;line-height:19px;color:#bbb;direction:rtl">'
            f'יש לך הצעה לשיפור הניוזלטר? כתבו לנו: <a href="mailto:open@ha-makom.co.il" style="color:{ACCENT_SC};text-decoration:none;font-weight:700">open@ha-makom.co.il</a></p>'
            f'<p style="Margin:0;font-family:{FONT};font-size:11px;line-height:18px;color:#888;direction:rtl">קיבלת מייל זה כי נרשמת לניוזלטר של המקום הכי חם בגיהנום.<br>'
            f'<a href="{{{{unsubscribe}}}}" style="color:#888;text-decoration:underline">להסרה מרשימת התפוצה</a></p></td></tr>')

# ---------- assemble ----------
def build():
    no_editor = os.environ.get("NO_EDITOR", "") in ("1", "true", "yes") or bool(cfg.get("no_editor"))
    rows = [sig_bar(), header()]
    if not no_editor:
        rows.append(note())
    rows.append(project())
    rows.append(month_stats())          # ריק בשבועי (אין stats); "החודש במספרים" בחודשי
    if not _ph(cfg.get("lead", "")):
        rows.append(lead(cfg["lead"], cfg.get("lead_kicker", "תחקיר השבוע")))
    rows.append(data_strip())
    rows.append(followup())
    rows.append(section_label(cfg.get("rundown_label", "עוד דברים שקרו השבוע במקום הכי חם בגיהנום")))
    rundown = [s for s in (cfg.get("rundown", []) or []) if not _ph(s)]
    place = cfg.get("photo_of_week", {}).get("place_after", 1)
    photo_done = False
    for i, s in enumerate(rundown):
        rows.append(item(s, featured=(i == 0)))   # ראשון בולט, השאר רשימה קומפקטית — היררכיה
        if i == place:
            rows.append(photo_strip()); photo_done = True
    if not photo_done:
        rows.append(photo_strip())
    he = cfg.get("hero", {}) or {}
    if not _ph(he.get("slug", "")):
        rows.append(hero(he["slug"], he.get("kicker", "מתחת לרדאר")))
    rows.append(ongoing_story())     # סיפורים שלא שחררנו — פינה קבועה
    rows.append(reel_strip())        # ברשתות שלנו — פינה קבועה
    rows.append(collab_box())        # שיתוף (הפורום) — פינה קבועה
    rows.append(quote_strip())
    rows.append(opinions_block())
    rows.append(reads_block())
    # אין בלוק SLAPP/קרן הגנה — הקמפיין נגמר.
    rows.append(banner_block())
    rows.append(footer())

    inner = "".join(r for r in rows if r)
    pre = cfg.get("preheader", "")
    doc = f'''<!DOCTYPE html>
<html dir="rtl" lang="he" xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>השבוע ב״המקום הכי חם בגיהנום״ · {cfg.get("week_date","")}</title>
<style type="text/css">
@import url('https://fonts.googleapis.com/css2?family=Suez+One&family=IBM+Plex+Sans+Hebrew:wght@400;500;600;700&family=Frank+Ruhl+Libre:wght@500;700;900&family=Heebo:wght@400;500;700;800;900&display=swap');
body,table,td,p,a,span,div,strong{{font-family:'IBM Plex Sans Hebrew','Heebo',-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;}}
h1,h2,h3{{font-family:'Suez One','Frank Ruhl Libre',Georgia,serif;}}
body{{margin:0;padding:0;background:{FRAME};}}
img{{-ms-interpolation-mode:bicubic;}}
@media only screen and (max-width:600px){{
 .ct{{width:100%!important;}}
 .imgcell{{width:104px!important;padding:0 0 0 12px!important;}}
 .thumb{{width:104px!important;height:auto!important;}}
 .m-hide{{display:none!important;max-height:0!important;overflow:hidden!important;}}
}}
</style>
</head>
<body style="margin:0;padding:0;background:{FRAME}">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{pre}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{FRAME}"><tbody><tr><td align="center" style="padding:18px 0">
<table role="presentation" class="ct" width="600" cellpadding="0" cellspacing="0" style="width:600px;max-width:600px;background:{IVORY};border-radius:10px;overflow:hidden"><tbody>
{inner}
</tbody></table>
</td></tr></tbody></table>
</body></html>'''

    doc = _proof(doc)          # הגהה סופית: נרמול קו מפריד ארוך בכל הטקסט (חוק המקף)

    os.makedirs(OUT_DIR, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out = os.path.join(OUT_DIR, f"newsletter_{stamp}.html")
    while os.path.exists(out):
        out = os.path.join(OUT_DIR, f"newsletter_{stamp}_1.html")
    open(out, "w", encoding="utf-8").write(doc)
    c = re.sub(r"<!--.*?-->", "", doc, flags=re.S)
    print("WROTE", out, "|", len(doc), "bytes")
    print("tag balance  tr:", c.count("<tr") - c.count("</tr"),
          " td:", c.count("<td") - c.count("</td"),
          " table:", c.count("<table") - c.count("</table"))
    print("TO FILL  →  " + ("  |  ".join(dict.fromkeys(MISSING)) if MISSING else "no placeholders."))
    return out

if __name__ == "__main__":
    build()
