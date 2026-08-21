# -*- coding: utf-8 -*-
"""
to_figma.py — שלב 4א של הניוזלטר: הופך issue.json + articles.json ל-figma_spec.json,
המפרט שממנו קלוד בונה את עמוד הגיליון בפיגמה דרך use_figma.

הרעיון: כל שכבה בפיגמה נושאת שם קנוני שמצביע חזרה למקום שממנו הטקסט בא, ולכן
from_figma.py יכול לתרגם כל עריכה של דור בפיגמה חזרה ל-issue.json / ds.override.json
בלי לנחש. חוזה שמות השכבות:

  sec:<name>            frame של פינה. הסדר על העמוד = סדר הפינות. מחיקת frame = הורדת הפינה.
  t:<path>              טקסט. path = נתיב ב-issue.json או מזהה כתבה (ראה writeback).
  img:<path>            תמונה.
  ds:<TOKEN>            טוקן עיצוב (צבע/פונט) מהרשימה הלבנה של build_newsletter.py.
  ro:<...>              read-only — נוצר מוורדפרס, עריכה בפיגמה תתעלם (מאת/תאריך).

הרצה:
  python3 to_figma.py issue.json            # כותב figma_spec.json
"""
import json, os, re, sys, io

ISSUE = next((a for a in sys.argv[1:] if a.endswith(".json")), os.environ.get("ISSUE", "issue.json"))
ARTICLES = os.environ.get("ARTICLES", "articles.json")
OUT = os.environ.get("SPEC_OUT", "figma_spec.json")

cfg = json.load(io.open(ISSUE, encoding="utf-8")) if os.path.exists(ISSUE) else {}
_raw = json.load(io.open(ARTICLES, encoding="utf-8")) if os.path.exists(ARTICLES) else {}
ART = _raw if isinstance(_raw, dict) else {a.get("slug"): a for a in _raw}
OV = cfg.get("overrides", {}) or {}

MONTHLY = str(cfg.get("accent", "")).lower() in ("heather", "monthly", "אברש")
DS = {
    "INK": "#141413", "IVORY": "#faf9f5", "FRAME": "#e6e3da", "PAPER": "#f3f1ea",
    "TERRA": "#D97757", "TERRA_D": "#B4581F", "SC_TERRA": "#E8906F",
    "SAGE": "#788C5D", "HEATHER": "#8E6FA8",
    "INK2": "#333333", "INK3": "#6B6B6B", "LINE": "#E6E6E6",
    "ACCENT": "#8E6FA8" if MONTHLY else "#D97757",
    "ACCENT_D": "#5F4478" if MONTHLY else "#B4581F",
    "ACCENT_SC": "#B79BD0" if MONTHLY else "#E8906F",
    "FONT_HEAD": "Suez One", "FONT_BODY": "IBM Plex Sans Hebrew",
}

# סטיילים — משקפים 1:1 את ה-CSS ב-build_newsletter.py, כדי שהפיגמה תיראה כמו המייל
STYLES = {
    "h1":          {"font": "FONT_HEAD", "size": 27, "weight": 900, "lh": 34, "color": "INK"},
    "h2":          {"font": "FONT_HEAD", "size": 23, "weight": 900, "lh": 30, "color": "INK"},
    "h3":          {"font": "FONT_BODY", "size": 16, "weight": 700, "lh": 22, "color": "INK"},
    "body":        {"font": "FONT_BODY", "size": 15, "weight": 400, "lh": 24, "color": "INK2"},
    "body_sm":     {"font": "FONT_BODY", "size": 13, "weight": 400, "lh": 19, "color": "INK2"},
    "byline":      {"font": "FONT_BODY", "size": 12, "weight": 700, "lh": 18, "color": "ACCENT_D"},
    "label":       {"font": "FONT_BODY", "size": 13, "weight": 800, "lh": 18, "color": "ACCENT_D", "ls": 3},
    "label_dark":  {"font": "FONT_BODY", "size": 13, "weight": 800, "lh": 18, "color": "ACCENT_SC", "ls": 3},
    "quote":       {"font": "FONT_HEAD", "size": 24, "weight": 800, "lh": 33, "color": "IVORY"},
    "caption":     {"font": "FONT_BODY", "size": 14, "weight": 400, "lh": 21, "color": "IVORY"},
    "credit":      {"font": "FONT_BODY", "size": 12, "weight": 400, "lh": 18, "color": "INK3"},
    "banner":      {"font": "FONT_HEAD", "size": 22, "weight": 900, "lh": 29, "color": "INK"},
}

CANVAS_W, PAD = 600, 28
SEC = []


def ph(x):
    return (not x) or str(x).strip() == "" or str(x).strip().startswith("<<<")


def rec(s):
    r = dict(ART.get(s, {}))
    r.update({k: v for k, v in (OV.get(s) or {}).items() if v not in (None, "")})
    return r


def art_title(s):
    return re.sub(r"\s*\|\s*(תחקיר|טור|דעה)\s*$", "", rec(s).get("title", s or "")).strip()


def art_excerpt(s, n=200):
    e = re.sub(r"<[^>]+>", "", rec(s).get("excerpt", "")).strip()
    return (e[:n].rstrip() + "…") if len(e) > n else e


def art_dt(s):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", rec(s).get("date", "") or "")
    return f"{m.group(3)}/{m.group(2)}" if m else ""


def T(layer, value, style, wb=None, note=""):
    return {"layer": layer, "type": "text", "value": value, "style": style,
            "writeback": wb, "note": note}


def IMG(layer, src, wb=None, h=340):
    return {"layer": layer, "type": "image", "src": src, "h": h, "writeback": wb}


def wb_issue(path):
    return {"kind": "issue", "path": path}


def wb_ov(slug, field):
    return {"kind": "override", "slug": slug, "field": field}


def section(name, kind, nodes, bg="IVORY"):
    nodes = [n for n in nodes if n]
    if nodes:
        SEC.append({"layer": f"sec:{name}", "kind": kind, "bg": bg, "nodes": nodes})


def article_nodes(slug, prefix, title_style="h2", exc=200, with_img=True):
    """בלוק כתבה. הכותרת/תקציר/תמונה ניתנים לעריכה ונכתבים ל-overrides[slug];
    מאת/תאריך read-only (מגיעים מוורדפרס)."""
    if not slug or not rec(slug):
        return []
    out = []
    if with_img and rec(slug).get("img"):
        out.append(IMG(f"img:{prefix}.img", rec(slug)["img"], wb_ov(slug, "img")))
    out.append(T(f"t:{prefix}.title", art_title(slug), title_style, wb_ov(slug, "title")))
    e = art_excerpt(slug, exc)
    if e:
        out.append(T(f"t:{prefix}.excerpt", e, "body", wb_ov(slug, "excerpt")))
    by = " · ".join(x for x in [f"מאת {rec(slug).get('author','')}".strip(), art_dt(slug)] if x.strip())
    out.append(T(f"ro:{prefix}.byline", by, "byline", None, "read-only: מוורדפרס"))
    return out


# ---------- header ----------
section("header", "header", [
    T("t:edition_label", cfg.get("edition_label", "הניוזלטר השבועי"), "label_dark",
      wb_issue("edition_label")),
    T("t:week_date", cfg.get("period", cfg.get("week_date", "")), "label_dark",
      wb_issue("week_date")),
], bg="INK")

# ---------- פתיח עורך ----------
en = cfg.get("editor_note", {}) or {}
_n = [T("t:editor_note.headline", en.get("headline", ""), "h1", wb_issue("editor_note.headline"))]
for i, p in enumerate(en.get("paragraphs") or []):
    _n.append(T(f"t:editor_note.paragraphs.{i}", p, "body", wb_issue(f"editor_note.paragraphs.{i}")))
section("editor_note", "editor_note", _n)


# ---------- פרויקט מתעדכן ----------
pr = cfg.get("project", {}) or {}
if not ph(pr.get("title")):
    section("project", "project", [
        T("t:project.label", pr.get("label", ""), "label", wb_issue("project.label")),
        T("t:project.title", pr.get("title", ""), "h2", wb_issue("project.title")),
        T("t:project.desc", pr.get("desc", ""), "body", wb_issue("project.desc")),
    ], bg="PAPER")

# ---------- תחקיר השבוע ----------
section("lead", "article", [T("t:lead_label", cfg.get("lead_kicker") or "תחקיר השבוע", "label",
                              wb_issue("lead_kicker"))]
        + article_nodes(cfg.get("lead", ""), "lead", "h1", 260))

# ---------- הנתון של השבוע ----------
dst = cfg.get("data_stat", {}) or {}
if not ph(dst.get("img")):
    section("data_stat", "data_stat", [
        T("t:data_stat.label", dst.get("label", "הנתון של השבוע"), "label_dark",
          wb_issue("data_stat.label")),
        IMG("img:data_stat.img", dst["img"], wb_issue("data_stat.img")),
    ], bg="INK")

# ---------- בעקבות הפרסום ----------
fu = cfg.get("followup", {}) or {}
if not ph(fu.get("slug")):
    section("followup", "followup", [
        T("t:followup.banner_title", fu.get("banner_title", "בעקבות הפרסום"), "banner",
          wb_issue("followup.banner_title")),
        T("t:followup.banner_sub", fu.get("banner_sub", ""), "body_sm",
          wb_issue("followup.banner_sub")),
    ] + article_nodes(fu["slug"], "followup", "h2", 200), bg="ACCENT")


# ---------- עוד דברים שקרו השבוע ----------
_n = [T("t:rundown_label", cfg.get("rundown_label", "עוד דברים שקרו השבוע במקום הכי חם בגיהנום"),
        "label", wb_issue("rundown_label"))]
for i, s in enumerate(cfg.get("rundown", []) or []):
    big = i in (cfg.get("rundown_big") or []) or i == 0
    _n += article_nodes(s, f"rundown.{i}", "h2" if big else "h3", 200 if big else 90, big)
section("rundown", "rundown", _n)

# ---------- תמונת השבוע ----------
pw = cfg.get("photo_of_week", {}) or {}
if not ph(pw.get("img")):
    section("photo_of_week", "photo_of_week", [
        T("t:photo_of_week.label", "תמונת השבוע", "label_dark", None),
        IMG("img:photo_of_week.img", pw["img"], wb_issue("photo_of_week.img")),
        T("t:photo_of_week.caption", pw.get("caption", ""), "caption",
          wb_issue("photo_of_week.caption")),
        T("t:photo_of_week.credit", pw.get("credit", ""), "credit",
          wb_issue("photo_of_week.credit")),
    ], bg="INK")

# ---------- מתחת לרדאר ----------
he = cfg.get("hero", {}) or {}
if not ph(he.get("slug")):
    section("hero", "article", [T("t:hero.kicker", he.get("kicker", "מתחת לרדאר"), "label",
                                  wb_issue("hero.kicker"))]
            + article_nodes(he["slug"], "hero", "h1", 220))

# ---------- ריל ----------
rl = cfg.get("reel", {}) or {}
if not ph(rl.get("url")) and not ph(rl.get("poster")):
    section("reel", "reel", [
        T("t:reel.label", "ברשתות שלנו", "label_dark", None),
        IMG("img:reel.poster", rl["poster"], wb_issue("reel.poster"), 420),
        T("t:reel.caption", rl.get("caption", ""), "caption", wb_issue("reel.caption")),
    ], bg="INK")


# ---------- ציטוט השבוע ----------
q = cfg.get("quote", {}) or {}
if not (ph(q.get("text")) and ph(q.get("url"))):
    section("quote", "quote", [
        T("t:quote.label", "ציטוט השבוע", "label_dark", None),
        T("t:quote.text", q.get("text", ""), "quote", wb_issue("quote.text")),
        T("t:quote.attrib", q.get("attrib", ""), "caption", wb_issue("quote.attrib")),
    ], bg="INK")

# ---------- שיתוף ----------
cb = cfg.get("collab", {}) or {}
_f = (cb.get("feature") or {}) if isinstance(cb, dict) else {}
if not ph(_f.get("title")):
    section("collab", "collab", [
        T("t:collab.partner", cb.get("partner", ""), "label", wb_issue("collab.partner")),
        IMG("img:collab.feature.img", _f.get("img", ""), wb_issue("collab.feature.img")),
        T("t:collab.feature.title", _f.get("title", ""), "h2", wb_issue("collab.feature.title")),
        T("t:collab.feature.dek", _f.get("dek", ""), "body", wb_issue("collab.feature.dek")),
    ], bg="PAPER")

# ---------- דעות וטורים ----------
op = cfg.get("opinions", {}) or {}
if not ph(op.get("feature")):
    _n = [T("t:opinions_label", cfg.get("opinions_label", "דעות וטורים"), "label",
            wb_issue("opinions_label"))]
    _n += article_nodes(op["feature"], "opinions.feature", "h2", 200)
    for i, s in enumerate(op.get("items", []) or []):
        _n += article_nodes(s, f"opinions.items.{i}", "h3", 90, False)
    section("opinions", "opinions", _n)


# ---------- המלצות קריאה ----------
_n = [T("t:reads_label", "המלצות קריאה", "label_dark", None)]
for i, r in enumerate(cfg.get("reads", []) or []):
    _n.append(T(f"t:reads.{i}.outlet", r.get("outlet", ""), "label_dark",
                wb_issue(f"reads.{i}.outlet")))
    _n.append(T(f"t:reads.{i}.headline", r.get("headline", ""), "h3",
                wb_issue(f"reads.{i}.headline")))
    if r.get("dek"):
        _n.append(T(f"t:reads.{i}.dek", r["dek"], "body_sm", wb_issue(f"reads.{i}.dek")))
section("reads", "reads", _n, bg="INK")

# ---------- טוקני עיצוב ----------
# frame נפרד בשולי העמוד: ריבועי צבע + דגימות פונט. שינוי צבע/פונט כאן = ds.override.json.
TOKENS = [{"layer": f"ds:{k}", "type": "token", "value": v,
           "kind": "font" if k.startswith("FONT") else "color"}
          for k, v in DS.items()]

spec = {
    "meta": {
        "issue": os.path.basename(ISSUE),
        "week_date": cfg.get("week_date", ""),
        "page_name": cfg.get("week_date", ""),
        "canvas_w": CANVAS_W,
        "pad": PAD,
        "dir": "rtl",
        "edition": "monthly" if MONTHLY else "weekly",
    },
    "ds": DS,
    "styles": STYLES,
    "tokens": TOKENS,
    "sections": SEC,
}

json.dump(spec, io.open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
_txt = sum(1 for s in SEC for n in s["nodes"] if n["type"] == "text")
_edit = sum(1 for s in SEC for n in s["nodes"] if n.get("writeback"))
print(f"wrote {OUT} — {len(SEC)} sections, {_txt} text nodes, {_edit} editable, {len(TOKENS)} tokens")
print("sections: " + " · ".join(s["layer"] for s in SEC))
