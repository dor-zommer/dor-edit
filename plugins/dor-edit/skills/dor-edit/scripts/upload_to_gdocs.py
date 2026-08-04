#!/usr/bin/env python3
"""העלאת .docx ל-Drive עם המרה ל-Google Docs, ולשונית "דוח עורך" בתוך המסמך.

Track changes בקובץ הופכים ל"הצעות עריכה" (suggestions) במסמך שנוצר.
משתמש בטוקנים של gmail-multi-account-mcp. ה-scope `auth/drive` שבטוקנים
מספיק גם ל-Docs API — אין צורך ב-scope `documents` נפרד (אומת 17.07.2026).

שימוש:
    python3 upload_to_gdocs.py <path.docx> [--account dor.zommer@shakuf.co.il] \
        [--name "שם המסמך"] [--folder <folder_id>]
    python3 upload_to_gdocs.py <path.docx> --update <file_id>
    # לשונית דוח עורך בתוך מסמך קיים (קיימת כבר? מוסיף בסופה, לא דורס):
    python3 upload_to_gdocs.py --report-tab report.txt --doc <doc_id>
    # אכיפת פונט Alef 14 על מסמך קיים (אפשר להגביל ללשונית אחת):
    python3 upload_to_gdocs.py --enforce-font --doc <doc_id> [--only-tab <tab_id>]
    # מסלול מסירה API טהור — visual-diff (הוספה ירוקה+קו-תחתון, מחיקה אדומה+קו-חוצה):
    python3 upload_to_gdocs.py --propose edits.json --doc <doc_id> [--tab <tab_id>]
    # ניקוי הסימון אחרי החלטת דור (accept משאיר את החדש בשחור; reject מחזיר את הישן):
    python3 upload_to_gdocs.py --resolve accept --doc <doc_id> [--tab <tab_id>]

פלט (stdout): JSON עם doc_id ו-url.

ממצאים מאומתים (17.07.2026) — אל תשנה בלי לבדוק מחדש:
- `addDocumentTab` **כן** נתמך ב-API. הסכימה: `{"addDocumentTab":{"tabProperties":{"title":"..."}}}`
  (השדה `title` ברמה העליונה נדחה). דף ה-how-tos הרשמי לא מזכיר זאת — הוא מיושן;
  מקור האמת הוא reference/documents/request, ובדיקה בפועל.
- `range.tabId` מכובד — סגנון שמופנה ללשונית לא נוגע בלשונית הראשית.
- לשונית חדשה **יורשת** את ה-namedStyles של המסמך. אם המסמך נבנה ב-build_docx.py,
  הלשונית כבר Alef 14 בלי אף בקשת סגנון.
- `weightedFontFamily: Alef` עובד. אם קריאה חוזרת מחזירה font=None — זה **לא** כישלון:
  Google Docs שומר רק עיצוב ישיר שנבדל מהסגנון היורש. None = "יורש", והיורש הוא Alef.

מלכודת דריסה — `writeControl.writeMode: SUGGEST` (אומת בהרצה 17.07.2026):
- השדה **קיים** בסכימה ו-`SUGGEST` ערך חוקי (ערך שגוי מוחזר ב-400), אבל הוא
  **Developer Preview** ודורש רישום ל-Google Workspace Developer Preview Program.
- פרויקט שאינו רשום: הבקשה מחזירה **200 בלי שגיאה — והשינוי נכתב כעריכה ישירה**.
  כלומר בקשה שנראית "הצעה" מבצעת בפועל דריסה שקופה של טקסט קיים.
- **לעולם אל תסמוך על SUGGEST בלי אימות**: קרא חזרה עם
  `?suggestionsViewMode=PREVIEW_WITHOUT_SUGGESTIONS`. אם השינוי מופיע שם — הוא דרס.
- `addDocumentTab` ממילא **אינו נתמך** ב-SUGGEST mode (מתועד) — לשונית הדוח נוצרת
  תמיד ב-EDIT, וזה תקין: יצירת לשונית חדשה לא דורסת דבר.

מסלול המסירה --propose / --resolve (visual-diff, נוסף 17.07.2026):
- שכפול פייתוני של proposeEdits/resolveEdits מ-`~/Developer/google-docs-mcp/src/docs.ts`.
- **הפשרה המפורשת:** זה טקסט צבוע, לא הצעות (suggestions) אמיתיות של Docs. תוספת =
  טקסט חדש ירוק (rgb 0.1/0.5/0.1) עם קו-תחתון; מחיקה = הטקסט הישן נצבע אדום
  (rgb 0.8/0.1/0.1) עם קו-חוצה — **הישן לא נמחק** (חוק הברזל: נראה והפיך עד שדור מכריע).
- **חוק הברזל נשמר:** אף פעולה כאן לא מוחקת טקסט קיים. --propose רק צובע ומוסיף;
  --resolve accept/reject מנקה את הסימון לפי החלטת דור (accept מוחק את הישן-האדום;
  reject מוחק את החדש-הירוק). אין batchUpdate שדורס טקסט של דור.
- **מיון יורד לפי startIndex** לפני הכתיבה (docs.ts:139) — נקודת הכשל המרכזית: בלי זה
  ההכנסות מזיזות את האינדקסים של העריכות שאחריהן. כל הבקשות נשלחות ב-batchUpdate אחד.
"""
import json, re, ssl, sys, argparse, uuid, urllib.request, urllib.parse
from datetime import datetime
from pathlib import Path

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _CTX = ssl.create_default_context()


def _open(req):
    return urllib.request.urlopen(req, context=_CTX)

REPO = Path.home() / "Desktop" / "gmail-multi-account-mcp"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOCS_API = "https://docs.googleapis.com/v1/documents"
FONT = "Alef"
BODY_PT = 14
# היררכיית הכותרות של הסקיל — מפורשת, כדי שלא יירשו את גדלי ברירת המחדל של Docs
HEADING_PT = {"HEADING_1": 20, "HEADING_2": 17, "HEADING_3": 15, "TITLE": 22}
REPORT_TAB_TITLE = "דוח עורך"


def token_path(account: str) -> Path:
    slug = account.replace("@", "_at_").replace(".", "_")
    return REPO / "tokens" / f"{slug}.json"


def access_token(account: str) -> str:
    tok = json.loads(token_path(account).read_text())
    secret = json.loads((REPO / "client_secret.json").read_text())
    conf = secret.get("installed") or secret.get("web")
    data = urllib.parse.urlencode({
        "client_id": conf["client_id"],
        "client_secret": conf["client_secret"],
        "refresh_token": tok["refresh_token"],
        "grant_type": "refresh_token",
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data)
    with _open(req) as r:
        return json.load(r)["access_token"]


def upload(path: Path, account: str, name: str, folder: str | None) -> dict:
    meta = {"name": name, "mimeType": "application/vnd.google-apps.document"}
    if folder:
        meta["parents"] = [folder]
    boundary = uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode(),
        json.dumps(meta, ensure_ascii=False).encode(),
        f"\r\n--{boundary}\r\nContent-Type: {DOCX_MIME}\r\n\r\n".encode(),
        path.read_bytes(),
        f"\r\n--{boundary}--".encode(),
    ])
    req = urllib.request.Request(
        "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink&supportsAllDrives=true",
        data=body,
        headers={
            "Authorization": f"Bearer {access_token(account)}",
            "Content-Type": f"multipart/related; boundary={boundary}",
        },
    )
    with _open(req) as r:
        return json.load(r)


def update(path: Path, account: str, file_id: str) -> dict:
    """מחליף את תוכן ה-Google Doc הקיים (אותו קישור) בתוכן ה-docx."""
    req = urllib.request.Request(
        f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media&fields=id,name&supportsAllDrives=true",
        data=path.read_bytes(),
        headers={"Authorization": f"Bearer {access_token(account)}", "Content-Type": DOCX_MIME},
        method="PATCH",
    )
    with _open(req) as r:
        return json.load(r)


# ---------------------------------------------------------------- Docs API

def _docs(url: str, token: str, method: str = "GET", body: dict | None = None) -> dict:
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(body, ensure_ascii=False).encode() if body else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with _open(req) as r:
        return json.load(r)


def get_doc(doc_id: str, token: str) -> dict:
    return _docs(f"{DOCS_API}/{doc_id}?includeTabsContent=true", token)


def batch(doc_id: str, token: str, requests: list) -> dict:
    if not requests:
        return {}
    return _docs(f"{DOCS_API}/{doc_id}:batchUpdate", token, "POST", {"requests": requests})


def batch_suggest(doc_id: str, token: str, requests: list) -> dict:
    """batchUpdate במצב SUGGEST — כל insertText/deleteContentRange הופך להצעה אמיתית
    של Docs (accept/reject מובנה, מיוחסת למשתמש המאמת), בלי דריסת טקסט קיים.

    דורש שהטוקן יהיה מהפרויקט הרשום ב-Google Workspace Developer Preview
    (dor-gmail-mcp / 719854974771 — אושר 17.07.2026). על פרויקט לא-רשום SUGGEST
    נבלע בשקט והופך לדריסה — לכן suggest_edits תמיד מאמת אחרי הכתיבה.
    """
    if not requests:
        return {}
    return _docs(f"{DOCS_API}/{doc_id}:batchUpdate", token, "POST",
                 {"requests": requests, "writeControl": {"writeMode": "SUGGEST"}})


def get_doc_view(doc_id: str, token: str, view: str) -> dict:
    """קריאת המסמך במצב תצוגת-הצעות מפורש (SUGGESTIONS_INLINE / PREVIEW_WITHOUT_SUGGESTIONS)."""
    return _docs(f"{DOCS_API}/{doc_id}?includeTabsContent=true&suggestionsViewMode={view}", token)


def _stamp() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


def _paragraphs(tab: dict):
    """מחזיר (namedStyleType, startIndex, endIndex) לכל פסקה עם טקסט אמיתי.

    יורד גם לתוך תאי טבלה — בלעדיו טקסט בטבלאות לא מקבל את הפונט.
    """
    def walk(content):
        for el in content:
            p = el.get("paragraph")
            if p:
                runs = [e for e in p.get("elements", []) if e.get("textRun")]
                if runs and any(e["textRun"]["content"].strip() for e in runs):
                    style = p.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
                    yield style, runs[0]["startIndex"], runs[-1]["endIndex"]
            t = el.get("table")
            if t:
                for row in t.get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        yield from walk(cell.get("content", []))

    yield from walk(tab["documentTab"]["body"]["content"])


def _runs(tab: dict):
    """(namedStyleType, start, end, bold) לכל run עם טקסט — כולל בתוך טבלאות.

    ברמת ה-run ולא הפסקה, כי `weightedFontFamily` נושא שדה `weight`: אכיפה
    ברמת פסקה כותבת weight=400 על כל הפסקה ו**מוחקת הדגשה קיימת**.
    """
    def walk(content):
        for el in content:
            p = el.get("paragraph")
            if p:
                style = p.get("paragraphStyle", {}).get("namedStyleType", "NORMAL_TEXT")
                for e in p.get("elements", []):
                    tr = e.get("textRun")
                    if not tr or not tr.get("content", "").strip():
                        continue
                    ts = tr.get("textStyle", {})
                    bold = bool(ts.get("bold")) or \
                        ts.get("weightedFontFamily", {}).get("weight", 400) >= 700
                    end = e["endIndex"] - (1 if tr["content"].endswith("\n") else 0)
                    yield style, e["startIndex"], end, bold
            t = el.get("table")
            if t:
                for row in t.get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        yield from walk(cell.get("content", []))

    yield from walk(tab["documentTab"]["body"]["content"])


def font_requests(doc: dict, only_tab: str | None = None) -> list:
    """Alef על כל הטקסט; גודל לפי רמת הכותרת — והדגשה קיימת נשמרת.

    `only_tab` מגביל את האכיפה ללשונית אחת (ראה הערת חוק-הברזל ב-enforce_font).
    """
    reqs = []
    for tab in doc.get("tabs", []):
        tid = tab["tabProperties"]["tabId"]
        if only_tab and tid != only_tab:
            continue
        for style, start, end, bold in _runs(tab):
            if end <= start:
                continue
            rng = {"tabId": tid, "startIndex": start, "endIndex": end}
            reqs.append({"updateTextStyle": {
                "range": rng,
                # weight נגזר מהמצב הקיים — אחרת האכיפה מוחקת bold
                "textStyle": {"weightedFontFamily": {
                    "fontFamily": FONT, "weight": 700 if bold else 400}},
                "fields": "weightedFontFamily"}})
            # גודל מפורש לכל רמה — אחרת כותרות יורשות את גדלי ברירת המחדל של Docs
            pt = HEADING_PT.get(style, BODY_PT if style == "NORMAL_TEXT" else None)
            if pt:
                reqs.append({"updateTextStyle": {
                    "range": rng,
                    "textStyle": {"fontSize": {"magnitude": pt, "unit": "PT"}},
                    "fields": "fontSize"}})
    return reqs


def enforce_font(doc_id: str, account: str, only_tab: str | None = None) -> dict:
    """אכיפת טיפוגרפיית הסקיל (Alef; גוף 14) על מסמך קיים.

    חוק הברזל והכרעתו כאן (17.07.2026): **עיצוב אינו דריסת תוכן** — הפעולה הזו
    לא מוחקת אף מילה שדור כתב, ולכן היא מותרת ואינה מצריכה עצירה או אישור.
    שתי מגבלות שנשמרות בכוונה כדי שלא תמחק עיצוב מכוון של דור:
      1. `fields` מוגבל ל-weightedFontFamily ול-fontSize בלבד. הדגשה, נטוי,
         צבע, קישורים והיילייט של דור **שורדים**.
      2. גודל 14 נאכף רק על NORMAL_TEXT; כותרות שומרות על היררכיית הגדלים.
    בכל זאת — זו כן דריסה של *בחירת פונט/גודל* מכוונת. לכן: מריצים על מסמך
    מסירה טרי, ולא על מסמך שדור כבר עיצב. אם צריך לעצב רק את לשונית הדוח
    בלי לגעת בלשונית הראשית שדור ערך — `--only-tab <tab_id>`.
    """
    token = access_token(account)
    reqs = font_requests(get_doc(doc_id, token), only_tab)
    batch(doc_id, token, reqs)
    return {"id": doc_id, "font_requests": len(reqs), "only_tab": only_tab}


def _tab_end_index(tab: dict) -> int:
    """אינדקס הסוף של גוף הלשונית (לפני תו סוף-הגוף)."""
    content = tab["documentTab"]["body"]["content"]
    return max(1, content[-1]["endIndex"] - 1)


def _para_texts(tab: dict):
    """(text, start, end) לכל פסקה בגוף הלשונית (בלי טבלאות)."""
    for el in tab["documentTab"]["body"]["content"]:
        p = el.get("paragraph")
        if not p:
            continue
        runs = [e for e in p.get("elements", []) if e.get("textRun")]
        if not runs:
            continue
        text = "".join(e["textRun"]["content"] for e in runs)
        if text.strip():
            yield text.strip(), runs[0]["startIndex"], runs[-1]["endIndex"]


def mark_headings(doc_id: str, account: str, headings_path: Path,
                  tab_id: str | None = None) -> dict:
    """מסמן כותרות בכתבה עצמה בסגנון אמיתי: ראשית=H1, ביניים=H2.

    קלט: JSON (רשימת מחרוזות או [{"text":..,"level":2}]) או טקסט שורה-לכותרת
    (אפשר עם קידומת `#`/`##` שקובעת רמה; ברירת מחדל H2 = כותרת ביניים).

    זו פעולת **עיצוב**, לא תוכן: היא לא מוחקת ולא משנה אף מילה — רק מחילה
    namedStyleType על פסקה שכבר קיימת. לכן מותרת תחת חוק הברזל.
    """
    token = access_token(account)
    doc = get_doc(doc_id, token)
    tab = _pick_tab(doc, tab_id)
    tid = tab["tabProperties"]["tabId"]

    raw = Path(headings_path).read_text(encoding="utf-8")
    try:
        items = json.loads(raw)
        if isinstance(items, dict):
            items = items.get("headings") or items.get("subheads") or []
    except json.JSONDecodeError:
        items = [ln for ln in raw.split("\n") if ln.strip()]

    norm = []
    for it in items:
        if isinstance(it, str):
            m = re.match(r"^(#{1,3})\s+(.*)$", it.strip())
            norm.append({"text": (m.group(2) if m else it).strip(),
                         "level": len(m.group(1)) if m else 2})
        else:
            norm.append({"text": str(it.get("text", "")).strip(),
                         "level": int(it.get("level", 2))})

    paras = list(_para_texts(tab))
    reqs, matched, missed = [], [], []
    for h in norm:
        if not h["text"]:
            continue
        hit = next((p for p in paras if p[0] == h["text"]), None)
        if not hit:
            missed.append(h["text"][:60])
            continue
        _, s, e = hit
        reqs.append({"updateParagraphStyle": {
            "range": {"tabId": tid, "startIndex": s, "endIndex": e},
            "paragraphStyle": {"namedStyleType": f"HEADING_{h['level']}",
                               "direction": "RIGHT_TO_LEFT"},
            "fields": "namedStyleType,direction"}})
        matched.append({"text": h["text"][:60], "level": h["level"]})

    if reqs:
        batch(doc_id, token, reqs)
        # אכיפה חוזרת כדי שהכותרות יקבלו את גדלי ההיררכיה (20/17/15)
        batch(doc_id, token, font_requests(get_doc(doc_id, token), only_tab=tid))

    return {"id": doc_id, "tab_id": tid, "marked": len(matched),
            "headings": matched, "not_found": missed,
            "url": f"https://docs.google.com/document/d/{doc_id}/edit?tab={tid}"}


# ------------------------------------------------- מארקדאון → Google Docs
# Google Docs לא מרנדר מארקדאון. בלי השכבה הזו הדוח נכתב כטקסט גולמי:
# צינורות במקום טבלה, כוכביות במקום הדגשה, [טקסט](url) במקום קישור, ו---- מיותם.

_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _md_spans(text: str) -> list:
    """מפרק שורה ל-spans עם bold/link. מסיר את תווי המארקדאון עצמם."""
    spans, pos = [], 0
    # קודם קישורים, ואז הדגשה בתוך מה שנשאר
    for m in _LINK_RE.finditer(text):
        if m.start() > pos:
            spans.extend(_md_bold_spans(text[pos:m.start()]))
        spans.append({"t": m.group(1), "bold": False, "link": m.group(2)})
        pos = m.end()
    if pos < len(text):
        spans.extend(_md_bold_spans(text[pos:]))
    return [s for s in spans if s["t"]]


def _md_bold_spans(text: str) -> list:
    spans, pos = [], 0
    for m in _BOLD_RE.finditer(text):
        if m.start() > pos:
            spans.append({"t": text[pos:m.start()], "bold": False, "link": None})
        spans.append({"t": m.group(1), "bold": True, "link": None})
        pos = m.end()
    if pos < len(text):
        spans.append({"t": text[pos:], "bold": False, "link": None})
    return spans


def _is_table_row(ln: str) -> bool:
    return ln.strip().startswith("|") and ln.strip().endswith("|") and ln.count("|") >= 2


def _is_table_sep(ln: str) -> bool:
    return _is_table_row(ln) and set(ln.strip().strip("|")) <= set("-: |")


def _split_row(ln: str) -> list:
    return [c.strip() for c in ln.strip().strip("|").split("|")]


def _md_blocks(md: str) -> list:
    """מפרק מארקדאון לבלוקים: heading / para / bullet / table. `---` מושמט."""
    lines = md.replace("\r\n", "\n").split("\n")
    blocks, i = [], 0
    while i < len(lines):
        ln = lines[i]
        s = ln.strip()
        # טבלה: שורת כותרת + שורת מפריד
        if _is_table_row(ln) and i + 1 < len(lines) and _is_table_sep(lines[i + 1]):
            header = _split_row(ln)
            rows, i = [header], i + 2
            while i < len(lines) and _is_table_row(lines[i]):
                rows.append(_split_row(lines[i]))
                i += 1
            width = max(len(r) for r in rows)
            rows = [r + [""] * (width - len(r)) for r in rows]
            blocks.append({"kind": "table", "rows": rows})
            continue
        m = re.match(r"^(#{1,6})\s+(.*)$", s)
        if m:
            blocks.append({"kind": "heading", "level": min(len(m.group(1)), 3),
                           "spans": _md_spans(m.group(2))})
        elif re.match(r"^-{3,}$|^\*{3,}$|^_{3,}$", s):
            pass  # קו אופקי של מארקדאון — מושמט, לא נכתב כמקפים
        elif re.match(r"^[-*+]\s+", s):
            blocks.append({"kind": "bullet", "spans": _md_spans(re.sub(r"^[-*+]\s+", "", s))})
        elif re.match(r"^\d+[.)]\s+", s):
            blocks.append({"kind": "numbered", "spans": _md_spans(re.sub(r"^\d+[.)]\s+", "", s))})
        elif s:
            blocks.append({"kind": "para", "spans": _md_spans(s)})
        else:
            blocks.append({"kind": "blank", "spans": []})
        i += 1
    return blocks


def _style_reqs_for_spans(tid: str, spans: list, start: int) -> list:
    """updateTextStyle לכל span שיש לו bold/link. מחזיר גם את האינדקס הסופי."""
    reqs, idx = [], start
    for sp in spans:
        e = idx + len(sp["t"])
        if sp["bold"] or sp["link"]:
            ts, fields = {}, []
            if sp["bold"]:
                ts["bold"] = True
                fields.append("bold")
            if sp["link"]:
                ts["link"] = {"url": sp["link"]}
                fields.append("link")
            reqs.append({"updateTextStyle": {
                "range": {"tabId": tid, "startIndex": idx, "endIndex": e},
                "textStyle": ts, "fields": ",".join(fields)}})
        idx = e
    return reqs


def _render_text_blocks(tid: str, blocks: list, at: int) -> tuple:
    """בונה בקשות לרצף בלוקי טקסט (בלי טבלאות). מחזיר (requests, end_index)."""
    text = "".join("".join(s["t"] for s in b["spans"]) + "\n" for b in blocks)
    if not text:
        return [], at
    reqs = [{"insertText": {"location": {"tabId": tid, "index": at}, "text": text}}]
    idx, bullet_runs = at, []
    for b in blocks:
        line = "".join(s["t"] for s in b["spans"])
        start, end = idx, idx + len(line) + 1
        ps, fields = {"direction": "RIGHT_TO_LEFT"}, "direction"
        if b["kind"] == "heading":
            ps["namedStyleType"] = f"HEADING_{b['level']}"
            fields += ",namedStyleType"
        elif b["kind"] in ("bullet", "numbered"):
            bullet_runs.append((start, end, b["kind"]))
        reqs.append({"updateParagraphStyle": {
            "range": {"tabId": tid, "startIndex": start, "endIndex": end},
            "paragraphStyle": ps, "fields": fields}})
        reqs.extend(_style_reqs_for_spans(tid, b["spans"], start))
        idx = end
    for start, end, kind in bullet_runs:
        reqs.append({"createParagraphBullets": {
            "range": {"tabId": tid, "startIndex": start, "endIndex": end},
            "bulletPreset": "NUMBERED_DECIMAL_ALPHA_ROMAN" if kind == "numbered"
                            else "BULLET_DISC_CIRCLE_SQUARE"}})
    return reqs, idx


def _find_last_table(tab: dict) -> dict | None:
    tables = [e["table"] for e in tab["documentTab"]["body"]["content"] if "table" in e]
    return tables[-1] if tables else None


def _fill_table(doc_id: str, token: str, tid: str, rows: list) -> None:
    """ממלא את הטבלה האחרונה בלשונית. ממלא מהתא האחרון לראשון כדי שאינדקסים לא יזוזו."""
    tab = _pick_tab(get_doc(doc_id, token), tid)
    tbl = _find_last_table(tab)
    if not tbl:
        return
    cells = []
    for r, row in enumerate(tbl.get("tableRows", [])):
        for c, cell in enumerate(row.get("tableCells", [])):
            if r < len(rows) and c < len(rows[r]):
                cells.append((cell["content"][0]["startIndex"], rows[r][c], r == 0))
    reqs = []
    for idx, raw, is_header in sorted(cells, key=lambda x: x[0], reverse=True):
        spans = _md_spans(raw)
        txt = "".join(s["t"] for s in spans)
        if not txt:
            continue
        reqs.append({"insertText": {"location": {"tabId": tid, "index": idx}, "text": txt}})
        reqs.append({"updateParagraphStyle": {
            "range": {"tabId": tid, "startIndex": idx, "endIndex": idx + len(txt)},
            "paragraphStyle": {"direction": "RIGHT_TO_LEFT"}, "fields": "direction"}})
        if is_header:
            reqs.append({"updateTextStyle": {
                "range": {"tabId": tid, "startIndex": idx, "endIndex": idx + len(txt)},
                "textStyle": {"bold": True}, "fields": "bold"}})
        else:
            reqs.extend(_style_reqs_for_spans(tid, spans, idx))
    batch(doc_id, token, reqs)


def render_markdown(doc_id: str, token: str, tid: str, md: str, at: int) -> int:
    """מרנדר מארקדאון ללשונית: כותרות אמיתיות, טבלאות אמיתיות, קישורים על הטקסט,
    הדגשה אמיתית, בולטים אמיתיים — ובלי שאריות מארקדאון."""
    blocks = _md_blocks(md)
    pending = []
    for b in blocks:
        if b["kind"] == "table":
            reqs, at = _render_text_blocks(tid, pending, at)
            if reqs:
                batch(doc_id, token, reqs)
            pending = []
            rows = b["rows"]
            batch(doc_id, token, [{"insertTable": {
                "location": {"tabId": tid, "index": at},
                "rows": len(rows), "columns": len(rows[0])}}])
            _fill_table(doc_id, token, tid, rows)
            at = _tab_end_index(_pick_tab(get_doc(doc_id, token), tid))
        else:
            pending.append(b)
    reqs, at = _render_text_blocks(tid, pending, at)
    if reqs:
        batch(doc_id, token, reqs)
    return at


def add_report_tab(doc_id: str, account: str, report_path: Path) -> dict:
    """כותב את דוח העורך ללשונית "דוח עורך" בתוך המסמך (Alef 14, RTL).

    הגוף הראשי נשאר בלשונית הראשית ולא נגענו בו.

    חוק הברזל — לערוך כן, לדרוס לא: אם הלשונית כבר קיימת (דור אולי כבר ערך
    אותה), **מוסיפים בסופה** ולא בונים אותה מחדש ולא עוצרים. הוספה בסוף לא
    מוחקת דבר, ולכן היא מותרת; רק דריסה של תוכן קיים אסורה.
    """
    token = access_token(account)
    doc = get_doc(doc_id, token)
    tid, appending, at = None, False, 1
    for t in doc.get("tabs", []):
        if t["tabProperties"].get("title") == REPORT_TAB_TITLE:
            tid = t["tabProperties"]["tabId"]
            appending, at = True, _tab_end_index(t)
            break

    if tid is None:
        reply = batch(doc_id, token, [
            {"addDocumentTab": {"tabProperties": {"title": REPORT_TAB_TITLE}}}])
        tid = reply["replies"][0]["addDocumentTab"]["tabProperties"]["tabId"]

    md = report_path.read_text(encoding="utf-8")
    if appending:
        # מפריד ויזואלי, כדי שברור מה נוסף בסבב הזה ומה כבר היה שם.
        md = f"\n— עדכון דוח ({_stamp()}) —\n\n" + md
    # רנדור אמיתי: טבלאות Docs, קישורים על הטקסט, הדגשה, בולטים, כותרות בהיררכיה.
    render_markdown(doc_id, token, tid, md, at)

    # אכיפת הפונט אחרי שהפסקאות קיבלו את הסגנון הנקוב שלהן —
    # רק על לשונית הדוח. הלשונית הראשית היא של דור; לא נוגעים בעיצוב שלה.
    batch(doc_id, token, font_requests(get_doc(doc_id, token), only_tab=tid))
    return {"id": doc_id, "tab_id": tid, "tab_title": REPORT_TAB_TITLE,
            "mode": "appended" if appending else "created",
            "url": f"https://docs.google.com/document/d/{doc_id}/edit?tab={tid}"}


# -------------------------------------------------- visual-diff (propose / resolve)
# שכפול פייתוני של proposeEdits/resolveEdits מ-google-docs-mcp/src/docs.ts (17.07.2026).
# כל האינדקסים הם אינדקסי Google Docs בתוך לשונית; כל הבקשות נשלחות ב-batchUpdate אחד.

GREEN = {"red": 0.1, "green": 0.5, "blue": 0.1}   # תוספת (docs.ts)
RED = {"red": 0.8, "green": 0.1, "blue": 0.1}     # מחיקה (docs.ts)
DRIVE_API = "https://www.googleapis.com/drive/v3/files"


def _is_green(fg: dict | None) -> bool:
    """זיהוי הצבע הירוק שלנו (docs.ts isGreenColor): ירוק דומיננטי, אדום/כחול נמוכים."""
    if not fg or not fg.get("color", {}).get("rgbColor"):
        return False
    rgb = fg["color"]["rgbColor"]
    r, g, b = rgb.get("red", 0) or 0, rgb.get("green", 0) or 0, rgb.get("blue", 0) or 0
    return g > 0.4 and r < 0.25 and b < 0.25


def _pick_tab(doc: dict, tab_id: str | None = None) -> dict:
    """בוחר לשונית לעבודה. ברירת מחדל: הלשונית הראשית (הראשונה שאינה 'דוח עורך')."""
    tabs = doc.get("tabs", [])
    if not tabs:
        sys.exit("המסמך אינו מכיל לשוניות — ודא includeTabsContent")
    if tab_id:
        for t in tabs:
            if t["tabProperties"]["tabId"] == tab_id:
                return t
        sys.exit(f"לא נמצאה לשונית {tab_id}")
    for t in tabs:
        if t["tabProperties"].get("title") != REPORT_TAB_TITLE:
            return t
    return tabs[0]


def _tab_plaintext(tab: dict):
    """(plainText, indexMapping) ללשונית — כמו getDocContent ב-docs.ts.

    indexMapping ממפה אינדקס תו ב-plainText לאינדקס Google Docs. עברית ב-BMP,
    תו בודד = code-unit בודד, ולכן חיפוש מחרוזת פייתוני תואם את אינדוקס Docs.
    """
    plain, mapping = [], []

    def process(content):
        for el in content:
            p = el.get("paragraph")
            if p:
                for pe in p.get("elements", []):
                    tr = pe.get("textRun")
                    if tr and tr.get("content"):
                        s = tr["content"]
                        start = pe.get("startIndex", 0)
                        for i, ch in enumerate(s):
                            plain.append(ch)
                            mapping.append(start + i)
            elif el.get("table"):
                for row in el["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        process(cell.get("content", []))
            elif el.get("tableOfContents"):
                process(el["tableOfContents"].get("content", []))

    process(tab["documentTab"]["body"]["content"])
    return "".join(plain), mapping


def _norm_edit(rec: dict) -> dict:
    """מנרמל רשומת edits.json לפורמט אחיד, עם כינויים גמישים לשמות שדות."""
    t = (rec.get("type") or "").lower()
    find = rec.get("originalText") or rec.get("find") or rec.get("anchor") or ""
    new = rec.get("newText") or rec.get("text") or rec.get("insert") or ""
    comment = rec.get("comment") or rec.get("note") or ""
    occ = int(rec.get("occurrence", 1))
    if not t:
        t = "comment" if comment else ("replacement" if find and new else "insertion")
    return {"type": t, "find": find, "new": new, "occurrence": occ, "comment": comment}


def _editor_note(text: str) -> str:
    """הערת עורך כטקסט שנכתב **בגוף** כהצעת-הוספה.

    **למה לא הערת Docs אמיתית:** Drive API אינו יכול לייצר הערה מעוגנת בקובץ
    Google Docs. התיעוד של גוגל מפורש - "Anchored comments on blob files or
    Google Docs editor files aren't supported... Google Workspace editor apps
    treat these comments as un-anchored comments". התוצאה: ההערה נוצרת, ה-API
    מחזיר הצלחה, ודור לא רואה אותה בשוליים. אומת אמפירית 02.08.2026 מול ייצוא
    docx (`w:commentRangeStart` = 0 בכל הווריאציות שנוסו), ואושר מול התיעוד.

    לכן הערת עורך נכתבת כהצעת-הוספה בגוף: מעוגנת בהגדרה, נראית במקום הנכון,
    מיוחסת לדור, ודחייה בלחיצה אחת מוחקת אותה.
    """
    return f" [הערת עורך: {text.strip()}]"


def _find_occurrences(plain: str, needle: str) -> list:
    out, i = [], plain.find(needle)
    while i != -1:
        out.append(i)
        i = plain.find(needle, i + 1)
    return out


def _create_comment(file_id: str, token: str, content: str, quoted: str | None = None) -> dict:
    """הערת Docs דרך Drive API v3 (scope drive מספיק). quotedFileContent מצטט את העוגן."""
    body = {"content": content}
    if quoted:
        body["quotedFileContent"] = {"value": quoted}
    url = f"{DRIVE_API}/{file_id}/comments?fields=id&supportsAllDrives=true"
    req = urllib.request.Request(
        url, method="POST",
        data=json.dumps(body, ensure_ascii=False).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with _open(req) as r:
        return json.load(r)


def propose_edits(doc_id: str, account: str, edits_path: Path, tab_id: str | None = None) -> dict:
    """מחיל visual-diff מתוך edits.json על הלשונית: ירוק+underline לתוספת, אדום+strike לישן.

    חוק הברזל: הישן **נצבע** אדום ולא נמחק — נראה והפיך עד שדור מכריע ב-resolve.
    """
    token = access_token(account)
    doc = get_doc(doc_id, token)
    tab = _pick_tab(doc, tab_id)
    tid = tab["tabProperties"]["tabId"]
    plain, mapping = _tab_plaintext(tab)

    raw = json.loads(Path(edits_path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("edits") or raw.get("changes") or []

    resolved, notes, skipped = [], 0, []
    for rec in raw:
        e = _norm_edit(rec)
        if e["type"] == "comment":
            # הערת עורך = הצעת-הוספה בגוף, לא הערת Drive (ראה _editor_note)
            e = {**e, "type": "insertion", "new": _editor_note(e["comment"])}
            notes += 1
        find, new, occ = e["find"], e["new"], e["occurrence"]
        if e["type"] == "insertion" and not find:
            resolved.append({"start": 1, "end": 1, "new": new})  # הוספה טהורה → ראש המסמך
            continue
        if not find:
            skipped.append({"reason": "no-anchor", "new": new[:40]})
            continue
        matches = _find_occurrences(plain, find)
        if not matches:
            skipped.append({"reason": "not-found", "text": find[:60]})
            continue
        if occ > len(matches):
            skipped.append({"reason": f"occurrence {occ}>{len(matches)}", "text": find[:60]})
            continue
        mp = matches[occ - 1]
        start = mapping[mp]
        end = mapping[mp + len(find) - 1] + 1
        if e["type"] == "insertion":
            resolved.append({"start": end, "end": end, "new": new})  # אחרי העוגן, בלי לגעת בו
        else:
            resolved.append({"start": start, "end": end, "new": new})  # החלפה/מחיקה

    # חובה: מיון יורד לפי startIndex — אחרת הכנסות מזיזות אינדקסים של עריכות מאוחרות (docs.ts:139)
    resolved.sort(key=lambda x: x["start"], reverse=True)

    reqs = []
    for ed in resolved:
        s, e, new = ed["start"], ed["end"], ed["new"]
        if s == e:  # הוספה טהורה
            if new:
                reqs.append({"insertText": {"text": new, "location": {"tabId": tid, "index": s}}})
                reqs.append({"updateTextStyle": {
                    "range": {"tabId": tid, "startIndex": s, "endIndex": s + len(new)},
                    "textStyle": {"foregroundColor": {"color": {"rgbColor": GREEN}}, "underline": True},
                    "fields": "foregroundColor,underline"}})
        else:  # החלפה/מחיקה: הישן נצבע אדום+קו-חוצה, החדש (אם יש) מוכנס אחריו ירוק+קו-תחתון
            reqs.append({"updateTextStyle": {
                "range": {"tabId": tid, "startIndex": s, "endIndex": e},
                "textStyle": {"foregroundColor": {"color": {"rgbColor": RED}}, "strikethrough": True},
                "fields": "foregroundColor,strikethrough"}})
            if new:
                reqs.append({"insertText": {"text": new, "location": {"tabId": tid, "index": e}}})
                reqs.append({"updateTextStyle": {
                    "range": {"tabId": tid, "startIndex": e, "endIndex": e + len(new)},
                    "textStyle": {"foregroundColor": {"color": {"rgbColor": GREEN}},
                                  "underline": True, "strikethrough": False},
                    "fields": "foregroundColor,underline,strikethrough"}})

    if reqs:
        batch(doc_id, token, reqs)

    return {"id": doc_id, "tab_id": tid, "applied": len(resolved), "requests": len(reqs),
            "editor_notes": notes,
            "skipped": skipped,
            "url": f"https://docs.google.com/document/d/{doc_id}/edit?tab={tid}"}


def _count_suggestions(doc: dict) -> dict:
    """סופר מזהי הצעות בתצוגת SUGGESTIONS_INLINE, ומפריד נקי מול תגית-ייבוא."""
    ins, dele = set(), set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "suggestedInsertionIds" and isinstance(v, list):
                    ins.update(v)
                elif k == "suggestedDeletionIds" and isinstance(v, list):
                    dele.update(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for i in o:
                walk(i)

    walk(doc)
    allids = ins | dele
    tagged = [i for i in allids if "import" in i.lower()]
    return {"insertions": len(ins), "deletions": len(dele),
            "total": len(allids), "tagged": len(tagged)}


def suggest_edits(doc_id: str, account: str, edits_path: Path, tab_id: str | None = None) -> dict:
    """מחיל את edits.json כהצעות Docs אמיתיות (writeMode: SUGGEST).

    כל החלפה = הצעת-מחיקה של הישן + הצעת-הוספה של החדש; כל תוספת = הצעת-הוספה.
    הישן לא נמחק בפועל — הוא הצעת-מחיקה שדור יכול לדחות (חוק הברזל נשמר: אין
    batchUpdate שדורס טקסט; הכל הפיך דרך accept/reject המובנה של גוגל).
    אחרי הכתיבה **מאמת** שההצעות נוצרו ולא נבלעו לדריסה.
    """
    token = access_token(account)
    doc = get_doc(doc_id, token)
    tab = _pick_tab(doc, tab_id)
    tid = tab["tabProperties"]["tabId"]
    plain, mapping = _tab_plaintext(tab)

    raw = json.loads(Path(edits_path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("edits") or raw.get("changes") or []

    resolved, notes, skipped = [], 0, []
    for rec in raw:
        e = _norm_edit(rec)
        if e["type"] == "comment":
            # הערת עורך = הצעת-הוספה בגוף, לא הערת Drive (ראה _editor_note)
            e = {**e, "type": "insertion", "new": _editor_note(e["comment"])}
            notes += 1
        find, new, occ = e["find"], e["new"], e["occurrence"]
        if e["type"] == "insertion" and not find:
            resolved.append({"start": 1, "end": 1, "new": new})
            continue
        if not find:
            skipped.append({"reason": "no-anchor", "new": new[:40]})
            continue
        matches = _find_occurrences(plain, find)
        if not matches:
            skipped.append({"reason": "not-found", "text": find[:60]})
            continue
        if occ > len(matches):
            skipped.append({"reason": f"occurrence {occ}>{len(matches)}", "text": find[:60]})
            continue
        mp = matches[occ - 1]
        start = mapping[mp]
        end = mapping[mp + len(find) - 1] + 1
        if e["type"] == "insertion":
            resolved.append({"start": end, "end": end, "new": new})  # אחרי העוגן
        else:
            resolved.append({"start": start, "end": end, "new": new})  # החלפה/מחיקה

    # מיון יורד לפי startIndex — הכנסה במצב SUGGEST מזיזה אינדקסים ≥ נקודת ההכנסה,
    # ולכן מעבדים גבוה→נמוך כדי שהעריכות הנמוכות יישארו תקפות (כמו ב-propose).
    resolved.sort(key=lambda x: x["start"], reverse=True)

    reqs = []
    for ed in resolved:
        s, e, new = ed["start"], ed["end"], ed["new"]
        if s == e:  # תוספת טהורה
            if new:
                reqs.append({"insertText": {"text": new, "location": {"tabId": tid, "index": s}}})
        else:  # החלפה/מחיקה: קודם הצעת-הוספה של החדש אחרי הישן, ואז הצעת-מחיקה של הישן
            if new:
                reqs.append({"insertText": {"text": new, "location": {"tabId": tid, "index": e}}})
            reqs.append({"deleteContentRange": {
                "range": {"tabId": tid, "startIndex": s, "endIndex": e}}})

    if reqs:
        batch_suggest(doc_id, token, reqs)

    # אימות חובה — SUGGEST חייב לייצר הצעות; אם 0 הצעות עם עריכות פעילות → נבלע לדריסה
    counts = _count_suggestions(get_doc_view(doc_id, token, "SUGGESTIONS_INLINE"))
    overwrote = bool(reqs) and counts["total"] == 0

    return {"id": doc_id, "tab_id": tid, "mode": "suggest", "applied": len(resolved),
            "requests": len(reqs), "suggestions": counts,
            "clean": counts["tagged"] == 0 and not overwrote,
            "overwrote": overwrote,
            "editor_notes": notes,
            "skipped": skipped,
            "url": f"https://docs.google.com/document/d/{doc_id}/edit?tab={tid}"}


def _scan_visual_edits(tab: dict) -> list:
    """סורק את הלשונית ומחזיר טווחי inserted (ירוק+underline) ו-deleted (strikethrough)."""
    edits = []

    def traverse(content):
        for el in content:
            p = el.get("paragraph")
            if p:
                for pe in p.get("elements", []):
                    tr = pe.get("textRun")
                    if tr and tr.get("textStyle"):
                        st = tr["textStyle"]
                        start, end = pe.get("startIndex", 0), pe.get("endIndex", 0)
                        if st.get("strikethrough"):
                            edits.append({"start": start, "end": end, "type": "deleted"})
                        elif st.get("underline") and _is_green(st.get("foregroundColor")):
                            edits.append({"start": start, "end": end, "type": "inserted"})
            elif el.get("table"):
                for row in el["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        traverse(cell.get("content", []))
            elif el.get("tableOfContents"):
                traverse(el["tableOfContents"].get("content", []))

    traverse(tab["documentTab"]["body"]["content"])
    return edits


def _merge_edits(edits: list) -> list:
    """ממזג טווחים צמודים מאותו סוג (docs.ts mergeEdits)."""
    if not edits:
        return []
    edits.sort(key=lambda x: x["start"])
    merged = [dict(edits[0])]
    for cur in edits[1:]:
        last = merged[-1]
        if cur["type"] == last["type"] and cur["start"] == last["end"]:
            last["end"] = cur["end"]
        else:
            merged.append(dict(cur))
    return merged


def resolve_edits(doc_id: str, account: str, action: str, tab_id: str | None = None) -> dict:
    """מנקה את סימוני ה-visual-diff לפי החלטת דור (docs.ts resolveEdits).

    accept: מוחק את הישן-האדום, מנקה עיצוב מהחדש (נשאר שחור).
    reject: מוחק את החדש-הירוק, מנקה עיצוב מהישן (חוזר לשחור).
    """
    token = access_token(account)
    doc = get_doc(doc_id, token)
    tab = _pick_tab(doc, tab_id)
    tid = tab["tabProperties"]["tabId"]
    merged = _merge_edits(_scan_visual_edits(tab))
    # יורד לפי startIndex — מחיקה לא מזיזה אינדקסים של עריכות באינדקס נמוך יותר
    merged.sort(key=lambda x: x["start"], reverse=True)

    reqs = []
    for ed in merged:
        s, e, ty = ed["start"], ed["end"], ed["type"]
        rng = {"tabId": tid, "startIndex": s, "endIndex": e}
        clear = {"updateTextStyle": {"range": rng, "textStyle": {},
                                     "fields": "foregroundColor,underline,strikethrough"}}
        if action == "accept":
            reqs.append({"deleteContentRange": {"range": rng}} if ty == "deleted" else clear)
        else:  # reject
            reqs.append({"deleteContentRange": {"range": rng}} if ty == "inserted" else clear)

    if reqs:
        batch(doc_id, token, reqs)
    return {"id": doc_id, "tab_id": tid, "action": action, "resolved": len(merged),
            "requests": len(reqs),
            "url": f"https://docs.google.com/document/d/{doc_id}/edit?tab={tid}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("docx", nargs="?")
    ap.add_argument("--account", default="dor.zommer@shakuf.co.il")
    ap.add_argument("--name", default=None)
    ap.add_argument("--folder", default=None)
    ap.add_argument("--update", default=None, metavar="FILE_ID",
                    help="עדכון מסמך קיים במקום יצירת חדש (שומר על אותו קישור)")
    ap.add_argument("--report-tab", default=None, metavar="REPORT_TXT",
                    help=f'יצירת לשונית "{REPORT_TAB_TITLE}" בתוך --doc וכתיבת הדוח אליה')
    ap.add_argument("--enforce-font", action="store_true",
                    help=f"אכיפת {FONT} {BODY_PT} על כל הלשוניות של --doc")
    ap.add_argument("--doc", default=None, metavar="DOC_ID",
                    help="מזהה ה-Google Doc עבור --report-tab / --enforce-font")
    ap.add_argument("--only-tab", default=None, metavar="TAB_ID",
                    help="הגבלת --enforce-font ללשונית אחת (לא לגעת בשאר)")
    ap.add_argument("--mark-headings", default=None, metavar="HEADINGS",
                    help="סימון כותרות הכתבה ב---doc כסגנון אמיתי (ביניים=H2)")
    ap.add_argument("--suggest", default=None, metavar="EDITS_JSON",
                    help="ברירת מחדל: החלת edits.json כהצעות Docs אמיתיות (writeMode SUGGEST) על --doc")
    ap.add_argument("--propose", default=None, metavar="EDITS_JSON",
                    help="אופציה משנית: visual-diff (ירוק/אדום) על --doc מתוך edits.json")
    ap.add_argument("--resolve", default=None, choices=["accept", "reject"],
                    help="ניקוי הסימון על --doc: accept משאיר את החדש, reject מחזיר את הישן")
    ap.add_argument("--tab", default=None, metavar="TAB_ID",
                    help="הגבלת --propose/--resolve ללשונית ספציפית (ברירת מחדל: הראשית)")
    a = ap.parse_args()

    if a.suggest or a.propose or a.resolve:
        if not a.doc:
            sys.exit("--suggest / --propose / --resolve מחייבים --doc <doc_id>")
        if a.suggest:
            ep = Path(a.suggest).expanduser().resolve()
            if not ep.exists():
                sys.exit(f"קובץ edits.json לא נמצא: {ep}")
            info = suggest_edits(a.doc, a.account, ep, a.tab)
        elif a.propose:
            ep = Path(a.propose).expanduser().resolve()
            if not ep.exists():
                sys.exit(f"קובץ edits.json לא נמצא: {ep}")
            info = propose_edits(a.doc, a.account, ep, a.tab)
        else:
            info = resolve_edits(a.doc, a.account, a.resolve, a.tab)
        print(json.dumps(info, ensure_ascii=False))
        return

    if a.mark_headings:
        if not a.doc:
            sys.exit("--mark-headings מחייב --doc <doc_id>")
        hp = Path(a.mark_headings).expanduser().resolve()
        if not hp.exists():
            sys.exit(f"קובץ הכותרות לא נמצא: {hp}")
        print(json.dumps(mark_headings(a.doc, a.account, hp, a.tab), ensure_ascii=False))
        return

    if a.report_tab or a.enforce_font:
        if not a.doc:
            sys.exit("--report-tab / --enforce-font מחייבים --doc <doc_id>")
        if a.report_tab:
            rp = Path(a.report_tab).expanduser().resolve()
            if not rp.exists():
                sys.exit(f"קובץ הדוח לא נמצא: {rp}")
            info = add_report_tab(a.doc, a.account, rp)
        else:
            info = enforce_font(a.doc, a.account, a.only_tab)
        print(json.dumps(info, ensure_ascii=False))
        return

    if not a.docx:
        sys.exit("נדרש נתיב docx (או --report-tab / --enforce-font עם --doc)")
    p = Path(a.docx).expanduser().resolve()
    if not p.exists() or p.suffix != ".docx":
        sys.exit(f"קובץ docx לא נמצא: {p}")
    if a.update:
        info = update(p, a.account, a.update)
    else:
        info = upload(p, a.account, a.name or p.stem, a.folder)
    info["url"] = f"https://docs.google.com/document/d/{info['id']}/edit"
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
