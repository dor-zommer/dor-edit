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
    # החלת edits.json כהצעות Docs אמיתיות (writeMode SUGGEST):
    python3 upload_to_gdocs.py --suggest edits.json --doc <doc_id> [--tab <tab_id>]
    # ולידציה מקומית של עוגנים מול קובץ טיוטה — בלי לגעת ב-Google Docs:
    python3 upload_to_gdocs.py --validate edits.json --draft draft.txt

פלט (stdout): JSON עם doc_id ו-url.

מיקום ריפו הטוקנים: משתנה הסביבה GMAIL_MULTI_DIR, עם פולבק ל-
~/Desktop/gmail-multi-account-mcp.

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
- **לעולם אל תסמוך על SUGGEST בלי אימות**: suggest_edits מצלם את מזהי ההצעות
  לפני הכתיבה ובודק שאחריה נוספו מזהים **חדשים**. applied>0 בלי אף הצעה
  חדשה = overwrote.
- `addDocumentTab` ממילא **אינו נתמך** ב-SUGGEST mode (מתועד) — לשונית הדוח נוצרת
  תמיד ב-EDIT, וזה תקין: יצירת לשונית חדשה לא דורסת דבר.

הערות עורך (הוכרע 10.08.2026): type=comment **הוסר**. הערות עורך שייכות לדוח
העורך (report.txt) בלבד — לעולם לא לגוף הכתבה. רשומת comment ב-edits.json
מדולגת עם אזהרה.
"""
import json, os, re, ssl, sys, time, argparse, uuid, urllib.error, urllib.request, urllib.parse
from datetime import datetime
from pathlib import Path

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _CTX = ssl.create_default_context()


def _open(req, retries: int = 3):
    """עטיפת urlopen: מדפיס את גוף שגיאת ה-HTTP מגוגל, ו-retry עם backoff על 429/5xx."""
    last_err = None
    for attempt in range(retries):
        try:
            return urllib.request.urlopen(req, context=_CTX)
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "ignore")
            except Exception:
                pass
            retryable = e.code == 429 or e.code >= 500
            print(f"HTTP {e.code} מגוגל"
                  + (f" (ניסיון {attempt + 1}/{retries})" if retryable else "")
                  + (f": {body[:2000]}" if body else ""), file=sys.stderr)
            if retryable and attempt < retries - 1:
                time.sleep(2 ** attempt)
                last_err = e
                continue
            raise
        except urllib.error.URLError as e:
            print(f"שגיאת רשת (ניסיון {attempt + 1}/{retries}): {e.reason}", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                last_err = e
                continue
            raise
    raise last_err  # pragma: no cover


def _repo() -> Path:
    env = os.environ.get("GMAIL_MULTI_DIR")
    repo = Path(env).expanduser() if env else Path.home() / "Desktop" / "gmail-multi-account-mcp"
    if not repo.exists():
        sys.exit(f"תיקיית gmail-multi-account-mcp לא נמצאה: {repo}\n"
                 "הגדר את משתנה הסביבה GMAIL_MULTI_DIR לנתיב הריפו, "
                 "או ודא שהריפו קיים ב-~/Desktop/gmail-multi-account-mcp")
    return repo


DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
DOCS_API = "https://docs.googleapis.com/v1/documents"
FONT = "Alef"
BODY_PT = 14
# היררכיית הכותרות של הסקיל — מפורשת, כדי שלא יירשו את גדלי ברירת המחדל של Docs
HEADING_PT = {"HEADING_1": 20, "HEADING_2": 17, "HEADING_3": 15, "TITLE": 22}
REPORT_TAB_TITLE = "דוח עורך"
BATCH_CHUNK = 300  # מספר בקשות מקסימלי ב-batchUpdate אחד


def token_path(account: str) -> Path:
    slug = account.replace("@", "_at_").replace(".", "_")
    return _repo() / "tokens" / f"{slug}.json"


def access_token(account: str) -> str:
    repo = _repo()
    tok = json.loads(token_path(account).read_text())
    secret = json.loads((repo / "client_secret.json").read_text())
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


def _batch_raw(doc_id: str, token: str, requests: list, write_control: dict | None = None) -> dict:
    body = {"requests": requests}
    if write_control:
        body["writeControl"] = write_control
    return _docs(f"{DOCS_API}/{doc_id}:batchUpdate", token, "POST", body)


def batch(doc_id: str, token: str, requests: list) -> dict:
    """batchUpdate בצ'אנקים של עד BATCH_CHUNK בקשות — מאמר ארוך לא נופל על באטץ' ענק."""
    if not requests:
        return {}
    replies = []
    for i in range(0, len(requests), BATCH_CHUNK):
        rep = _batch_raw(doc_id, token, requests[i:i + BATCH_CHUNK])
        replies.extend(rep.get("replies", []))
    return {"replies": replies}


def batch_suggest(doc_id: str, token: str, requests: list) -> dict:
    """batchUpdate במצב SUGGEST — כל insertText/deleteContentRange הופך להצעה אמיתית
    של Docs (accept/reject מובנה, מיוחסת למשתמש המאמת), בלי דריסת טקסט קיים.

    דורש שהטוקן יהיה מהפרויקט הרשום ב-Google Workspace Developer Preview
    (dor-gmail-mcp / 719854974771 — אושר 17.07.2026). על פרויקט לא-רשום SUGGEST
    נבלע בשקט והופך לדריסה — לכן suggest_edits תמיד מאמת אחרי הכתיבה.

    הבקשות ממוינות יורד לפי אינדקס, ולכן פיצול לצ'אנקים בטוח: כל צ'אנק נוגע
    באינדקסים נמוכים מקודמו ואינו מוזז על ידיו.
    """
    if not requests:
        return {}
    replies = []
    for i in range(0, len(requests), BATCH_CHUNK):
        rep = _batch_raw(doc_id, token, requests[i:i + BATCH_CHUNK],
                         write_control={"writeMode": "SUGGEST"})
        replies.extend(rep.get("replies", []))
    return {"replies": replies}


def get_doc_view(doc_id: str, token: str, view: str) -> dict:
    """קריאת המסמך במצב תצוגת-הצעות מפורש (SUGGESTIONS_INLINE / PREVIEW_WITHOUT_SUGGESTIONS)."""
    return _docs(f"{DOCS_API}/{doc_id}?includeTabsContent=true&suggestionsViewMode={view}", token)


def _stamp() -> str:
    return datetime.now().strftime("%d.%m.%Y %H:%M")


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

    runs סמוכים עם אותו יעד עיצוב (bold + גודל) מאוחדים לבקשה אחת —
    מקטין דרמטית את מספר הבקשות על מאמר ארוך.
    `only_tab` מגביל את האכיפה ללשונית אחת (ראה הערת חוק-הברזל ב-enforce_font).
    """
    reqs = []
    for tab in doc.get("tabs", []):
        tid = tab["tabProperties"]["tabId"]
        if only_tab and tid != only_tab:
            continue
        # איחוד runs סמוכים: [pt, start, end, bold]
        merged = []
        for style, start, end, bold in _runs(tab):
            if end <= start:
                continue
            pt = HEADING_PT.get(style, BODY_PT if style == "NORMAL_TEXT" else None)
            if merged and merged[-1][3] == bold and merged[-1][0] == pt \
                    and start <= merged[-1][2] + 1:
                merged[-1][2] = max(merged[-1][2], end)
            else:
                merged.append([pt, start, end, bold])
        for pt, start, end, bold in merged:
            rng = {"tabId": tid, "startIndex": start, "endIndex": end}
            reqs.append({"updateTextStyle": {
                "range": rng,
                # weight נגזר מהמצב הקיים — אחרת האכיפה מוחקת bold
                "textStyle": {"weightedFontFamily": {
                    "fontFamily": FONT, "weight": 700 if bold else 400}},
                "fields": "weightedFontFamily"}})
            # גודל מפורש לכל רמה — אחרת כותרות יורשות את גדלי ברירת המחדל של Docs
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

_LINK_RE = re.compile(r"(\*\*)?\[([^\]]+)\]\(([^)\s]+)\)(?(1)\*\*)")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")


def _u16(s: str) -> int:
    """אורך מחרוזת ביחידות UTF-16 — אינדקסי Google Docs נמדדים ב-code units,
    ולכן תו מחוץ ל-BMP (אמוג'י) תופס 2 יחידות ולא אחת."""
    return len(s.encode("utf-16-le")) // 2


def _md_spans(text: str) -> list:
    """מפרק שורה ל-spans עם bold/link. מסיר את תווי המארקדאון עצמם."""
    spans, pos = [], 0
    # קודם קישורים (כולל **[..](..)** מודגש-עוטף), ואז הדגשה בתוך מה שנשאר
    for m in _LINK_RE.finditer(text):
        if m.start() > pos:
            spans.extend(_md_bold_spans(text[pos:m.start()]))
        label, bold = m.group(2), bool(m.group(1))
        inner = _BOLD_RE.fullmatch(label)
        if inner:  # [**טקסט**](url) — הדגשה בתוך טקסט הקישור
            label, bold = inner.group(1), True
        else:
            label = label.replace("**", "")
        spans.append({"t": label, "bold": bold, "link": m.group(3)})
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
        elif s.startswith(">"):
            # blockquote — הסימן `>` מוסר, הפסקה תרונדר עם הזחה
            inner = re.sub(r"^(?:>\s?)+", "", s)
            blocks.append({"kind": "quote", "spans": _md_spans(inner)})
        elif s:
            blocks.append({"kind": "para", "spans": _md_spans(s)})
        elif blocks and blocks[-1]["kind"] != "blank":
            # שורה ריקה אחת נשמרת כמרווח; רצף שורות ריקות לא מייצר רעש
            blocks.append({"kind": "blank", "spans": []})
        i += 1
    while blocks and blocks[-1]["kind"] == "blank":
        blocks.pop()
    return blocks


def _style_reqs_for_spans(tid: str, spans: list, start: int) -> list:
    """updateTextStyle לכל span שיש לו bold/link. מחזיר גם את האינדקס הסופי."""
    reqs, idx = [], start
    for sp in spans:
        e = idx + _u16(sp["t"])
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
        start, end = idx, idx + _u16(line) + 1
        ps, fields = {"direction": "RIGHT_TO_LEFT"}, "direction"
        if b["kind"] == "heading":
            ps["namedStyleType"] = f"HEADING_{b['level']}"
            fields += ",namedStyleType"
        elif b["kind"] == "quote":
            # blockquote — הזחה מצד הפתיחה (ימין ב-RTL) במקום `>` גולמי
            ps["indentStart"] = {"magnitude": 36, "unit": "PT"}
            ps["indentFirstLine"] = {"magnitude": 36, "unit": "PT"}
            fields += ",indentStart,indentFirstLine"
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
            "range": {"tabId": tid, "startIndex": idx, "endIndex": idx + _u16(txt)},
            "paragraphStyle": {"direction": "RIGHT_TO_LEFT"}, "fields": "direction"}})
        if is_header:
            reqs.append({"updateTextStyle": {
                "range": {"tabId": tid, "startIndex": idx, "endIndex": idx + _u16(txt)},
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


# -------------------------------------------------- הצעות עריכה (suggest)

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


def _find_tab(doc: dict, tab_id: str) -> dict | None:
    for t in doc.get("tabs", []):
        if t["tabProperties"]["tabId"] == tab_id:
            return t
    return None


def _u16len(ch: str) -> int:
    """אורך התו ביחידות UTF-16 — אינדקסי Google Docs נמדדים ב-code units."""
    return len(ch.encode("utf-16-le")) // 2


def _tab_plaintext(tab: dict):
    """(plainText, indexMapping) ללשונית.

    indexMapping ממפה אינדקס תו פייתוני ב-plainText לאינדקס Google Docs.
    אינדקסי Docs נמדדים ב-UTF-16 code units, ולכן תו מחוץ ל-BMP (אמוג'י)
    מקדם את המונה ב-2 — בלי זה אמוג'י אחד מזיז את כל האינדקסים שאחריו.
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
                        offset = pe.get("startIndex", 0)
                        for ch in s:
                            plain.append(ch)
                            mapping.append(offset)
                            offset += _u16len(ch)
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
        if find and new:
            t = "replacement"
        elif comment and not new:
            t = "comment"
        else:
            t = "insertion"
    return {"type": t, "find": find, "new": new, "occurrence": occ,
            "explicit_occurrence": "occurrence" in rec, "comment": comment}


# --- נרמול עוגנים: גרשיים מסולסלים/עבריים, מקפים, NBSP, רווחים כפולים ---
# הנרמול דו-צדדי (רץ גם על ה-plaintext וגם על העוגן), עם מיפוי אינדקסים
# שמשמר את המיקום המקורי — כך עוגן עם גרשיים ישרים מוצא טקסט עם ״ עבריים.

_NORM_CHAR = {
    "\u201c": '"', "\u201d": '"', "\u201e": '"',  # מרכאות מסולסלות
    "\u05f4": '"',                              # גרשיים עבריים
    "\u2018": "'", "\u2019": "'",              # גרש מסולסל
    "\u05f3": "'",                              # גרש עברי
    "\u05be": "-",                              # מקף עברי
    "\u2013": "-", "\u2014": "-",              # en/em dash
    "\u00a0": " ",                              # NBSP
}


def _normalize_with_map(s: str) -> tuple:
    """(מחרוזת מנורמלת, מיפוי אינדקס-מנורמל → אינדקס-מקור).

    רווחים כפולים (אחרי המרת NBSP) מכווצים לרווח יחיד; המיפוי מצביע על
    התו הראשון בקבוצה, כך שהמיקום במקור נשמר.
    """
    out, idx_map = [], []
    for i, ch in enumerate(s):
        c = _NORM_CHAR.get(ch, ch)
        if c == " " and out and out[-1] == " ":
            continue  # כיווץ רווחים כפולים
        out.append(c)
        idx_map.append(i)
    return "".join(out), idx_map


def _find_occurrences(plain: str, needle: str) -> list:
    out, i = [], plain.find(needle)
    while i != -1:
        out.append(i)
        i = plain.find(needle, i + 1)
    return out


def _resolve_anchors(raw_edits: list, plain: str) -> tuple:
    """רזולוציית עוגנים משותפת (suggest + validate) על אינדקסים פייתוניים ב-plain.

    מחזיר (resolved, skipped):
      resolved: [{"pstart", "pend", "new", "anchor", "exact"}]  (pstart==pend = הוספה)
      skipped:  [{"reason", ...}] — כולל not_found / ambiguous / no_anchor /
                overlap / comment_type_removed.

    כללים:
    - התאמה מדויקת קודמת; אם אין — התאמה מנורמלת (גרשיים/מקפים/NBSP/רווחים).
    - יותר ממופע אחד בלי occurrence מפורש = ambiguous (לא בוחרים בשקט).
    - insertion בלי עוגן = no_anchor (לא דוחפים לראש המסמך).
    - type=comment הוסר (10.08.2026): הערות עורך שייכות ל-report.txt — מדולג עם אזהרה.
    - עריכות חופפות: המאוחרת ברשימה נדחית עם reason=overlap.
    """
    norm_plain, norm_map = _normalize_with_map(plain)
    resolved, skipped = [], []
    for rec in raw_edits:
        e = _norm_edit(rec)
        if e["type"] == "comment":
            print("אזהרה: type=comment הוסר מהסקיל — הערות עורך שייכות לדוח העורך "
                  f"(report.txt) בלבד. ההערה דולגה: {e['comment'][:60]}", file=sys.stderr)
            skipped.append({"reason": "comment_type_removed", "comment": e["comment"][:60]})
            continue
        find, new = e["find"], e["new"]
        if not find:
            skipped.append({"reason": "no_anchor", "new": new[:40]})
            continue

        exact = True
        matches = [(mp, mp + len(find)) for mp in _find_occurrences(plain, find)]
        if not matches:
            norm_find, _ = _normalize_with_map(find)
            if norm_find:
                for mp in _find_occurrences(norm_plain, norm_find):
                    s0 = norm_map[mp]
                    e0 = norm_map[mp + len(norm_find) - 1] + 1
                    matches.append((s0, e0))
                exact = False
        if not matches:
            skipped.append({"reason": "not_found", "text": find[:60]})
            continue
        if len(matches) > 1 and not e["explicit_occurrence"]:
            skipped.append({"reason": "ambiguous", "occurrences": len(matches),
                            "text": find[:60]})
            continue
        occ = e["occurrence"]
        if occ > len(matches):
            skipped.append({"reason": f"occurrence {occ}>{len(matches)}", "text": find[:60]})
            continue
        s0, e0 = matches[occ - 1]
        if e["type"] == "insertion":
            resolved.append({"pstart": e0, "pend": e0, "new": new,
                             "anchor": find[:60], "exact": exact})
        else:
            resolved.append({"pstart": s0, "pend": e0, "new": new,
                             "anchor": find[:60], "exact": exact})

    # זיהוי חפיפות: העריכה המאוחרת ברשימה שחופפת טווח שכבר התקבל — נדחית.
    accepted_ranges, final = [], []
    for ed in resolved:
        s, ee = ed["pstart"], ed["pend"]
        conflict = any(
            (s < ae and ee > as_) or (s == ee and as_ < s < ae)
            for as_, ae in accepted_ranges)
        if conflict:
            skipped.append({"reason": "overlap", "text": ed["anchor"]})
            continue
        accepted_ranges.append((s, ee))
        final.append(ed)
    return final, skipped


def _suggestion_ids(node) -> tuple:
    """אוסף מזהי suggestedInsertionIds / suggestedDeletionIds מכל עומק המבנה."""
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

    walk(node)
    return ins, dele


def suggest_edits(doc_id: str, account: str, edits_path: Path, tab_id: str | None = None) -> dict:
    """מחיל את edits.json כהצעות Docs אמיתיות (writeMode: SUGGEST).

    כל החלפה = הצעת-מחיקה של הישן + הצעת-הוספה של החדש; כל תוספת = הצעת-הוספה.
    הישן לא נמחק בפועל — הוא הצעת-מחיקה שדור יכול לדחות (חוק הברזל נשמר: אין
    batchUpdate שדורס טקסט; הכל הפיך דרך accept/reject המובנה של גוגל).

    אימות אחרי הכתיבה: מזהי ההצעות מצולמים **לפני** הכתיבה (בלשונית הרלוונטית),
    ורק מזהים חדשים נספרים. overwrote=true אם היו עריכות פעילות ואפס הצעות
    חדשות — גם על מסמך שכבר יש בו הצעות פתוחות מסבב קודם.
    """
    token = access_token(account)
    doc = get_doc(doc_id, token)
    tab = _pick_tab(doc, tab_id)
    tid = tab["tabProperties"]["tabId"]
    plain, mapping = _tab_plaintext(tab)

    raw = json.loads(Path(edits_path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("edits") or raw.get("changes") or []

    # צילום מצב הצעות לפני הכתיבה — מוגבל ללשונית הרלוונטית
    pre_view = get_doc_view(doc_id, token, "SUGGESTIONS_INLINE")
    pre_node = _find_tab(pre_view, tid) or pre_view
    pre_ins, pre_del = _suggestion_ids(pre_node)
    pre_ids = pre_ins | pre_del

    resolved, skipped = _resolve_anchors(raw, plain)

    reqs = []
    # מיון יורד לפי startIndex — הכנסה במצב SUGGEST מזיזה אינדקסים ≥ נקודת ההכנסה,
    # ולכן מעבדים גבוה→נמוך כדי שהעריכות הנמוכות יישארו תקפות.
    for ed in sorted(resolved, key=lambda x: x["pstart"], reverse=True):
        ps, pe, new = ed["pstart"], ed["pend"], ed["new"]
        # מיפוי אינדקס פייתוני → אינדקס Docs (UTF-16)
        if ps < pe:  # החלפה/מחיקה
            s = mapping[ps]
            e = mapping[pe - 1] + _u16len(plain[pe - 1])
            if new:
                reqs.append({"insertText": {"text": new, "location": {"tabId": tid, "index": e}}})
            reqs.append({"deleteContentRange": {
                "range": {"tabId": tid, "startIndex": s, "endIndex": e}}})
        else:  # הוספה טהורה אחרי העוגן
            e = mapping[ps - 1] + _u16len(plain[ps - 1]) if ps > 0 else 1
            if new:
                reqs.append({"insertText": {"text": new, "location": {"tabId": tid, "index": e}}})

    if reqs:
        batch_suggest(doc_id, token, reqs)

    # אימות חובה — רק הצעות **חדשות** נספרות (הפרש מול הצילום שלפני הכתיבה)
    post_view = get_doc_view(doc_id, token, "SUGGESTIONS_INLINE")
    post_node = _find_tab(post_view, tid) or post_view
    post_ins, post_del = _suggestion_ids(post_node)
    new_ins = post_ins - pre_ids
    new_del = post_del - pre_ids
    new_ids = new_ins | new_del
    tagged = [i for i in new_ids if "import" in i.lower()]
    counts = {"insertions": len(new_ins), "deletions": len(new_del),
              "total": len(new_ids), "tagged": len(tagged),
              "pre_existing": len(pre_ids)}
    overwrote = bool(reqs) and len(new_ids) == 0

    return {"id": doc_id, "tab_id": tid, "mode": "suggest", "applied": len(resolved),
            "requests": len(reqs), "suggestions": counts,
            "clean": counts["tagged"] == 0 and not overwrote,
            "overwrote": overwrote,
            "skipped": skipped,
            "url": f"https://docs.google.com/document/d/{doc_id}/edit?tab={tid}"}


def validate_edits(edits_path: Path, draft_path: Path) -> dict:
    """ולידציה מקומית של כל העוגנים ב-edits.json מול קובץ טקסט — בלי לגעת ב-Docs.

    מדפיס דוח JSON: found / ambiguous / missing (+ skipped אחרים).
    מריצים לפני ההעלאה — עוגן שנופל כאן ייפול גם בענן.
    """
    plain = draft_path.read_text(encoding="utf-8")
    raw = json.loads(edits_path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("edits") or raw.get("changes") or []

    resolved, skipped = _resolve_anchors(raw, plain)
    ambiguous = [s for s in skipped if s.get("reason") == "ambiguous"]
    missing = [s for s in skipped if s.get("reason") == "not_found"]
    other = [s for s in skipped if s.get("reason") not in ("ambiguous", "not_found")]
    return {
        "mode": "validate", "draft": str(draft_path), "edits": len(raw),
        "found": [{"anchor": r["anchor"], "exact": r["exact"]} for r in resolved],
        "ambiguous": ambiguous,
        "missing": missing,
        "skipped_other": other,
        "ok": not ambiguous and not missing and not other,
    }


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
                    help="מזהה ה-Google Doc עבור --report-tab / --enforce-font / --suggest")
    ap.add_argument("--only-tab", default=None, metavar="TAB_ID",
                    help="הגבלת --enforce-font ללשונית אחת (לא לגעת בשאר)")
    ap.add_argument("--mark-headings", default=None, metavar="HEADINGS",
                    help="סימון כותרות הכתבה ב---doc כסגנון אמיתי (ביניים=H2)")
    ap.add_argument("--suggest", default=None, metavar="EDITS_JSON",
                    help="החלת edits.json כהצעות Docs אמיתיות (writeMode SUGGEST) על --doc")
    ap.add_argument("--validate", default=None, metavar="EDITS_JSON",
                    help="ולידציה מקומית של עוגני edits.json מול --draft (בלי לגעת ב-Docs)")
    ap.add_argument("--draft", default=None, metavar="DRAFT_TXT",
                    help="קובץ הטיוטה עבור --validate")
    ap.add_argument("--tab", default=None, metavar="TAB_ID",
                    help="הגבלת --suggest ללשונית ספציפית (ברירת מחדל: הראשית)")
    a = ap.parse_args()

    if a.validate:
        if not a.draft:
            sys.exit("--validate מחייב --draft <draft.txt>")
        ep = Path(a.validate).expanduser().resolve()
        dp = Path(a.draft).expanduser().resolve()
        if not ep.exists():
            sys.exit(f"קובץ edits.json לא נמצא: {ep}")
        if not dp.exists():
            sys.exit(f"קובץ הטיוטה לא נמצא: {dp}")
        print(json.dumps(validate_edits(ep, dp), ensure_ascii=False))
        return

    if a.suggest:
        if not a.doc:
            sys.exit("--suggest מחייב --doc <doc_id>")
        ep = Path(a.suggest).expanduser().resolve()
        if not ep.exists():
            sys.exit(f"קובץ edits.json לא נמצא: {ep}")
        info = suggest_edits(a.doc, a.account, ep, a.tab)
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
        sys.exit("נדרש נתיב docx (או --report-tab / --enforce-font / --suggest / --validate)")
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
