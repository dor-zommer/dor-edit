# -*- coding: utf-8 -*-
"""
from_figma.py — שלב 4ג של הניוזלטר: לוקח את העריכות שדור עשה בעמוד הפיגמה
ומתרגם אותן חזרה לקוד, בלי לנחש.

קלט:
  figma_spec.json   — המפרט שנוצר ב-to_figma.py (שם שכבה → לאן לכתוב)
  figma_dump.json   — מה שקראנו מהפיגמה אחרי העריכות:
      {"order":["sec:lead", ...], "text":{"t:...":"..."},
       "tokens":{"ds:ACCENT":"#..."}, "images":{"img:...":"https://..."}}

פלט:
  issue.json         — מעודכן (גיבוי: issue.pre-figma.bak.json)
  ds.override.json   — טוקני עיצוב שדור שינה (build_newsletter.py קורא אותו)
  דוח שינויים ל-stdout

דגלים:  DRY=1 מדפיס בלי לכתוב.
הרצה:   python3 from_figma.py issue.json
"""
import json, os, re, sys, io, shutil

ISSUE = next((a for a in sys.argv[1:] if a.endswith(".json")), os.environ.get("ISSUE", "issue.json"))
SPEC = os.environ.get("SPEC", "figma_spec.json")
DUMP = os.environ.get("DUMP", "figma_dump.json")
DS_OUT = os.environ.get("DS_OUT", "ds.override.json")
DRY = os.environ.get("DRY", "") in ("1", "true", "yes")

# שם frame בפיגמה → שם בלוק ב-build_newsletter.py
SEC2BLOCK = {
    "header": "chrome_top", "editor_note": "editor_note", "project": "project",
    "month_stats": "month_stats", "lead": "lead", "data_stat": "data_stat",
    "followup": "followup", "rundown": "rundown", "photo_of_week": "photo_of_week",
    "hero": "hero", "ongoing": "ongoing", "reel": "reel", "collab": "collab",
    "quote": "quote", "opinions": "opinions", "reads": "reads",
}


def load(p, what):
    if not os.path.exists(p):
        sys.exit(f"חסר {what}: {p}")
    return json.load(io.open(p, encoding="utf-8"))


spec = load(SPEC, "מפרט הפיגמה")
dump = load(DUMP, "הקריאה מהפיגמה")
cfg = load(ISSUE, "קובץ הגיליון")

# אינדקס: שם שכבה → node מהמפרט
IDX = {n["layer"]: n for s in spec.get("sections", []) for n in s.get("nodes", [])}
DS_DEF = spec.get("ds", {})

CH, SKIP = [], []


def norm(s):
    """נרמול לפני השוואה: רווחים כפולים, וחוק המקף של דור."""
    if s is None:
        return ""
    s = re.sub(r"\s*[—–]\s*", " - ", str(s))
    return re.sub(r"[ \t]+", " ", s).strip()


def set_path(obj, path, val):
    """קובע ערך בנתיב מנוקד. מקטע מספרי = אינדקס ברשימה."""
    parts = path.split(".")
    cur = obj
    for i, k in enumerate(parts[:-1]):
        nxt = parts[i + 1]
        if k.isdigit():
            cur = cur[int(k)]
            continue
        if k not in cur or cur[k] is None:
            cur[k] = [] if nxt.isdigit() else {}
        cur = cur[k]
    last = parts[-1]
    if last.isdigit():
        idx = int(last)
        while len(cur) <= idx:
            cur.append("")
        cur[idx] = val
    else:
        cur[last] = val


def get_path(obj, path):
    cur = obj
    for k in path.split("."):
        try:
            cur = cur[int(k)] if k.isdigit() else cur[k]
        except (KeyError, IndexError, TypeError):
            return None
    return cur


# ---------- 1. טקסט ותמונות ----------
edits = dict(dump.get("text", {}) or {})
edits.update(dump.get("images", {}) or {})

for layer, new in edits.items():
    node = IDX.get(layer)
    if node is None:
        SKIP.append(f"{layer}: שכבה שלא במפרט - התעלמתי")
        continue
    old = node.get("value") if node["type"] == "text" else node.get("src")
    if norm(old) == norm(new):
        continue
    wb = node.get("writeback")
    if not wb:
        SKIP.append(f"{layer}: read-only (מוורדפרס) - העריכה לא נשמרה")
        continue
    if wb["kind"] == "issue":
        set_path(cfg, wb["path"], new)
        CH.append(f"issue.{wb['path']}\n    לפני: {norm(old)[:70]}\n    אחרי: {norm(new)[:70]}")
    elif wb["kind"] == "override":
        cfg.setdefault("overrides", {}).setdefault(wb["slug"], {})[wb["field"]] = new
        CH.append(f"overrides.{wb['slug']}.{wb['field']}\n    לפני: {norm(old)[:70]}\n    אחרי: {norm(new)[:70]}")

# ---------- 2. טוקני עיצוב ----------
ds_out = {}
if os.path.exists(DS_OUT):
    try:
        ds_out = json.load(io.open(DS_OUT, encoding="utf-8")) or {}
    except Exception:
        ds_out = {}
for layer, val in (dump.get("tokens", {}) or {}).items():
    tok = re.sub(r"^ds:", "", layer)
    if tok not in DS_DEF:
        SKIP.append(f"{layer}: טוקן לא מוכר - התעלמתי")
        continue
    if norm(val) == norm(DS_DEF[tok]):
        ds_out.pop(tok, None)          # חזר לברירת המחדל - מסירים את הדריסה
        continue
    key = "FONT_HEAD" if tok == "FONT_HEAD" else ("FONT" if tok == "FONT_BODY" else tok)
    if key.startswith("FONT"):
        fb = "'Frank Ruhl Libre',Georgia,serif" if key == "FONT_HEAD" else \
             "'Heebo',-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif"
        val = f"'{val}',{fb}"
    ds_out[key] = val
    CH.append(f"ds.{key}\n    לפני: {DS_DEF[tok]}\n    אחרי: {val}")


# ---------- 3. סדר הפינות ומחיקות ----------
order = [re.sub(r"^sec:", "", s) for s in (dump.get("order") or [])]
if order:
    blocks = [SEC2BLOCK[s] for s in order if s in SEC2BLOCK]
    unknown = [s for s in order if s not in SEC2BLOCK]
    if unknown:
        SKIP.append("frames לא מוכרים בסדר: " + ", ".join(unknown))
    # chrome תמיד בקצוות - הבילדר נועל אותם בעצמו
    blocks = [b for b in blocks if b not in ("chrome_top", "chrome_bottom")]
    spec_secs = [re.sub(r"^sec:", "", s["layer"]) for s in spec.get("sections", [])]
    spec_blocks = [SEC2BLOCK[s] for s in spec_secs if s in SEC2BLOCK and
                   SEC2BLOCK[s] not in ("chrome_top", "chrome_bottom")]
    if blocks != spec_blocks:
        cfg["section_order"] = blocks
        gone = [b for b in spec_blocks if b not in blocks]
        CH.append("section_order\n    סדר חדש: " + " → ".join(blocks) +
                  (("\n    הורדו: " + ", ".join(gone)) if gone else ""))

# ---------- 4. כתיבה ----------
print(f"\n{'=' * 60}\nסבב פיגמה → קוד   ({len(CH)} שינויים)\n{'=' * 60}")
for c in CH:
    print("  · " + c)
if SKIP:
    print("\n  לא הוחל:")
    for s in SKIP:
        print("    ! " + s)
if not CH:
    print("  אין שינויים - הפיגמה זהה ל-issue.json.")

if DRY:
    print("\nDRY=1 - לא נכתב כלום.")
elif CH:
    bak = os.path.join(os.path.dirname(os.path.abspath(ISSUE)), "issue.pre-figma.bak.json")
    shutil.copyfile(ISSUE, bak)
    json.dump(cfg, io.open(ISSUE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\nנכתב {ISSUE}  (גיבוי: {os.path.basename(bak)})")
    if ds_out:
        json.dump(ds_out, io.open(DS_OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"נכתב {DS_OUT}  ({len(ds_out)} טוקנים)")
    elif os.path.exists(DS_OUT):
        os.remove(DS_OUT)
        print(f"הוסר {DS_OUT} - כל הטוקנים חזרו לברירת המחדל")
    print("\nהשלב הבא: build_newsletter.py issue.json  ואז אימות ויזואלי.")
