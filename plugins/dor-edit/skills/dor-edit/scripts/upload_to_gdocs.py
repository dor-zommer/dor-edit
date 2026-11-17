#!/usr/bin/env python3
"""העלאת .docx ל-Drive עם המרה ל-Google Docs, ולשונית "דוח עורך" בתוך המסמך.

Track changes בקובץ הופכים ל"הצעות עריכה" (suggestions) במסמך שנוצר.
משתמש בטוקנים של gmail-multi-account-mcp. ה-scope `auth/drive` שבטוקנים
מספיק גם ל-Docs API — אין צורך ב-scope `documents` נפרד (אומת 17.07.2026).

שימוש:
    python3 upload_to_gdocs.py <path.docx> [--account dor.zommer@shakuf.co.il] \
        [--name "שם המסמך"] [--folder <folder_id>]
    python3 upload_to_gdocs.py <path.docx> --update <file_id> --direct   # דריסה מלאה! מסורב בלי --direct
    # לשונית דוח עורך בתוך מסמך קיים (קיימת כבר? מוסיף בסופה, לא דורס):
    python3 upload_to_gdocs.py --report-tab report.txt --doc <doc_id>
    # אכיפת פונט Alef 14 על מסמך קיים, כהצעות עיצוב (אפשר להגביל ללשונית אחת;
    # --direct = כתיבה ישירה עם אזהרה):
    python3 upload_to_gdocs.py --enforce-font --doc <doc_id> [--only-tab <tab_id>] [--direct]
    # החלת edits.json כהצעות Docs אמיתיות (writeMode SUGGEST), כולל קישורים
    # (שדה link). ledger נכתב ליד edits.json; exit 1 אם לא clean:
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
- **לעולם אל תסמוך על SUGGEST בלי אימות**: suggest_edits מאמת **לפי תוכן**
  (19.11.2026): PREVIEW_WITHOUT_SUGGESTIONS חייב להישאר זהה (אחרת overwrote),
  ו-PREVIEW_SUGGESTIONS_ACCEPTED חייב להכיל כל טקסט חדש בדיוק פעם אחת לכל
  עריכה (פעמיים = duplicate). מזהי ההצעות נספרים כמידע משני בלבד - עוגן
  שנוגע בהצעה קיימת מתמזג אליה בלי מזהה חדש, וזה לא דריסה.
- `addDocumentTab` ממילא **אינו נתמך** ב-SUGGEST mode (מתועד) — לשונית הדוח נוצרת
  תמיד ב-EDIT, וזה תקין: יצירת לשונית חדשה לא דורסת דבר.

הערות עורך (הוכרע 10.08.2026): type=comment **הוסר**. הערות עורך שייכות לדוח
העורך (report.txt) בלבד — לעולם לא לגוף הכתבה. רשומת comment ב-edits.json
מדולגת עם אזהרה.
"""
import hashlib, http.client, json, os, re, ssl, sys, time, argparse, uuid
import urllib.error, urllib.request, urllib.parse
from datetime import datetime
from pathlib import Path

try:
    import certifi
    _CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _CTX = ssl.create_default_context()

HTTP_TIMEOUT = 60  # שניות; בלי timeout חיבור תקוע נתלה לנצח


class WriteOutcomeUnknown(Exception):
    """בקשת כתיבה (POST/PATCH) נשלחה, אבל התשובה לא הגיעה במלואה.

    ייתכן שהשרת **ביצע** אותה. אסור לשלוח שוב בעיוורון - צריך לקרוא את
    המסמך מחדש ולבדוק לפי תוכן אם השינוי נחת.
    """


def _open(req, retries: int = 3, idempotent: bool | None = None) -> bytes:
    """urlopen + read בתוך אותו try, עם timeout. מחזיר את גוף התשובה כ-bytes.

    מדיניות retry:
    - בקשה אידמפוטנטית (GET, או רענון טוקן OAuth שמסומן idempotent=True):
      retry עם backoff על 429/5xx, שגיאות רשת ו-IncompleteRead, גם בשלב הקריאה.
    - כל POST/PATCH אחר (batchUpdate, העלאה ל-Drive): **אפס retry**. שליחה
      חוזרת אחרי חיבור שנפל יכולה לשכפל הצעות או קבצים. שגיאת רשת או תשובה
      חלקית אחרי השליחה מורמות כ-WriteOutcomeUnknown; שגיאת HTTP (השרת
      ענה ודחה) מורמת כ-HTTPError כרגיל.
    """
    if idempotent is None:
        idempotent = req.get_method() in ("GET", "HEAD")
    attempts = retries if idempotent else 1
    last_err = None
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, context=_CTX, timeout=HTTP_TIMEOUT) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "ignore")
            except Exception:
                pass
            retryable = idempotent and (e.code == 429 or e.code >= 500)
            print(f"HTTP {e.code} מגוגל"
                  + (f" (ניסיון {attempt + 1}/{attempts})" if retryable else "")
                  + (f": {body[:2000]}" if body else ""), file=sys.stderr)
            if retryable and attempt < attempts - 1:
                time.sleep(2 ** attempt)
                last_err = e
                continue
            raise
        except (urllib.error.URLError, http.client.HTTPException, OSError) as e:
            reason = getattr(e, "reason", None) or repr(e)
            print(f"שגיאת רשת (ניסיון {attempt + 1}/{attempts}): {reason}", file=sys.stderr)
            if not idempotent:
                raise WriteOutcomeUnknown(str(reason)) from e
            if attempt < attempts - 1:
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
    # רענון טוקן הוא POST אבל אידמפוטנטי - מותר retry
    return json.loads(_open(req, idempotent=True))["access_token"]


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
    # POST יצירה: בלי retry (שליחה חוזרת = קובץ כפול ב-Drive)
    return json.loads(_open(req))


def update(path: Path, account: str, file_id: str) -> dict:
    """מחליף את תוכן ה-Google Doc הקיים (אותו קישור) בתוכן ה-docx."""
    req = urllib.request.Request(
        f"https://www.googleapis.com/upload/drive/v3/files/{file_id}?uploadType=media&fields=id,name&supportsAllDrives=true",
        data=path.read_bytes(),
        headers={"Authorization": f"Bearer {access_token(account)}", "Content-Type": DOCX_MIME},
        method="PATCH",
    )
    return json.loads(_open(req))


# ---------------------------------------------------------------- Docs API

def _docs(url: str, token: str, method: str = "GET", body: dict | None = None) -> dict:
    req = urllib.request.Request(
        url, method=method,
        data=json.dumps(body, ensure_ascii=False).encode() if body else None,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    return json.loads(_open(req))


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


SUGGEST_MAX_REQUESTS = 1000  # POST אחד לכל הרצה; מעבר לזה - לפצל את edits.json


def batch_suggest(doc_id: str, token: str, requests: list,
                  required_revision_id: str | None = None) -> dict:
    """batchUpdate במצב SUGGEST - כל insertText/deleteContentRange/updateTextStyle
    הופך להצעה של Docs (accept/reject מובנה), בלי דריסת טקסט קיים.

    דורש שהטוקן יהיה מהפרויקט הרשום ב-Google Workspace Developer Preview
    (dor-gmail-mcp / 719854974771 - אושר 17.07.2026). על פרויקט לא-רשום SUGGEST
    נבלע בשקט והופך לדריסה - לכן כל קורא מאמת אחרי הכתיבה.

    **POST אחד בלבד, בלי פיצול לצ'אנקים ובלי retry**: אחרי הצ'אנק הראשון
    ה-revision משתנה, ו-requiredRevisionId היה דוחה את השני; ושליחה חוזרת אחרי
    חיבור שנפל עלולה לשכפל הצעות. requiredRevisionId (מהקריאה שממנה נגזרו
    האינדקסים) מבטיח שהבקשה לא תוחל על מסמך שהשתנה בינתיים.
    """
    if not requests:
        return {}
    if len(requests) > SUGGEST_MAX_REQUESTS:
        sys.exit(f"{len(requests)} בקשות - מעל {SUGGEST_MAX_REQUESTS} ב-POST אחד. "
                 "פצל את edits.json לשני קבצים והרץ כל אחד בנפרד.")
    wc = {"writeMode": "SUGGEST"}
    if required_revision_id:
        wc["requiredRevisionId"] = required_revision_id
    return _batch_raw(doc_id, token, requests, write_control=wc)


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


def font_requests(doc: dict, only_tab: str | None = None, min_index: int = 0) -> list:
    """Alef על כל הטקסט; גודל לפי רמת הכותרת — והדגשה קיימת נשמרת.

    runs סמוכים עם אותו יעד עיצוב (bold + גודל) מאוחדים לבקשה אחת —
    מקטין דרמטית את מספר הבקשות על מאמר ארוך.
    `only_tab` מגביל את האכיפה ללשונית אחת (ראה הערת חוק-הברזל ב-enforce_font).
    `min_index` מגביל לטקסט שמתחיל מהאינדקס הזה (למשל רק מה שנוסף עכשיו בסוף
    לשונית הדוח - בלי לגעת בתוכן שכבר היה בה).
    """
    reqs = []
    for tab in doc.get("tabs", []):
        tid = tab["tabProperties"]["tabId"]
        if only_tab and tid != only_tab:
            continue
        # איחוד runs סמוכים: [pt, start, end, bold]
        merged = []
        for style, start, end, bold in _runs(tab):
            start = max(start, min_index)
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


def enforce_font(doc_id: str, account: str, only_tab: str | None = None,
                 direct: bool = False) -> dict:
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

    עדכון (חוק הברזל - הרחבה 22.7.2026: "הכל בהצעות" חל על כל מסמך שנמסר):
    ברירת המחדל היא עכשיו הצעות עיצוב (SUGGEST) עם אימות; כתיבה ישירה רק
    עם --direct מפורש, ועם אזהרה.
    """
    token = access_token(account)
    doc = get_doc(doc_id, token)
    reqs = font_requests(doc, only_tab)
    info = apply_style_requests(doc_id, token, reqs, doc.get("revisionId"), direct,
                                "enforce-font")
    return {"id": doc_id, "font_requests": len(reqs), "only_tab": only_tab, **info}


def apply_style_requests(doc_id: str, token: str, reqs: list, revision: str | None,
                         direct: bool, what: str) -> dict:
    """מחיל בקשות עיצוב (updateTextStyle / updateParagraphStyle).

    ברירת מחדל: כהצעות (SUGGEST) עם אימות - נדרשים מזהי suggestedTextStyleChanges /
    suggestedParagraphStyleChanges **חדשים** אחרי הכתיבה. אם אין - ייתכן ש-SUGGEST
    נבלע וההחלה הייתה ישירה: overwrote=true ואזהרה.
    לא נבדק מול ה-API בפועל (19.11.2026): ייתכן ש-SUGGEST אינו תומך בשינויי
    סגנון פסקה. במקרה כזה הבקשה תיכשל או תסומן overwrote - ואז אפשר לבחור
    במודע ב---direct (כתיבה ישירה, עם אזהרה).
    """
    if not reqs:
        return {"mode": "direct" if direct else "suggest", "requests": 0}
    if direct:
        print(f"אזהרה: {what} עם --direct - עיצוב נכתב ישירות למסמך, לא כהצעה. "
              "דור לא יוכל לדחות אותו דרך accept/reject.", file=sys.stderr)
        batch(doc_id, token, reqs)
        return {"mode": "direct", "requests": len(reqs)}
    pre = _all_ids(_suggestion_ids(get_doc_view(doc_id, token, "SUGGESTIONS_INLINE")))
    try:
        batch_suggest(doc_id, token, reqs, revision)
    except WriteOutcomeUnknown as e:
        print(f"החיבור נפל אחרי השליחה ({e}). לא שולח שוב - בודק.", file=sys.stderr)
    except urllib.error.HTTPError as e:
        sys.exit(f"{what} נדחה במצב SUGGEST (HTTP {e.code}; פירוט ב-stderr). לא הוחל דבר. "
                 "ייתכן שה-API לא תומך בשינוי הזה כהצעה. כתיבה ישירה מודעת: --direct.")
    post = _suggestion_ids(get_doc_view(doc_id, token, "SUGGESTIONS_INLINE"))
    new_style = (post["text_style"] | post["para_style"]) - pre
    overwrote = not new_style
    if overwrote:
        print(f"אזהרה: {what} במצב SUGGEST לא יצר אף הצעת עיצוב חדשה. ייתכן שהעיצוב "
              "הוחל ישירות (SUGGEST נבלע). בדוק את המסמך ידנית.", file=sys.stderr)
    return {"mode": "suggest", "requests": len(reqs),
            "style_suggestions": len(new_style), "overwrote": overwrote}


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
                  tab_id: str | None = None, direct: bool = False) -> dict:
    """מסמן כותרות בכתבה עצמה בסגנון אמיתי: ראשית=H1, ביניים=H2.

    קלט: JSON (רשימת מחרוזות או [{"text":..,"level":2}]) או טקסט שורה-לכותרת
    (אפשר עם קידומת `#`/`##` שקובעת רמה; ברירת מחדל H2 = כותרת ביניים).

    זו פעולת **עיצוב**, לא תוכן: היא לא מוחקת ולא משנה אף מילה — רק מחילה
    namedStyleType על פסקה שכבר קיימת. בכל זאת - "הכל בהצעות": ברירת המחדל
    היא SUGGEST עם אימות (apply_style_requests); כתיבה ישירה רק עם --direct.
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
    # התאמה סובלנית: קודם התאמה מדויקת, ואם אין — התאמה מנורמלת
    # (_normalize_with_map: גרשיים/מקפים/NBSP/רווחים כפולים), כמו ברזולוציית עוגנים.
    norm_paras = [(_normalize_with_map(p[0])[0], p) for p in paras]
    reqs, matched, missed = [], [], []
    for h in norm:
        if not h["text"]:
            continue
        hit = next((p for p in paras if p[0] == h["text"]), None)
        if not hit:
            ht = _normalize_with_map(h["text"])[0]
            hit = next((p for nt, p in norm_paras if nt == ht), None)
        if not hit:
            missed.append(h["text"][:60])
            continue
        _, s, e = hit
        rng = {"tabId": tid, "startIndex": s, "endIndex": e}
        reqs.append({"updateParagraphStyle": {
            "range": rng,
            "paragraphStyle": {"namedStyleType": f"HEADING_{h['level']}",
                               "direction": "RIGHT_TO_LEFT"},
            "fields": "namedStyleType,direction"}})
        # עיצוב נקודתי של הפסקה שסומנה בלבד — פונט הסקיל וגודל לפי הרמה.
        # אין אכיפת פונט גורפת על הלשונית: שאר המסמך של דור לא נוגעים בו.
        pt = HEADING_PT.get(f"HEADING_{h['level']}", BODY_PT)
        reqs.append({"updateTextStyle": {
            "range": rng,
            "textStyle": {
                "weightedFontFamily": {"fontFamily": FONT, "weight": 700},
                "fontSize": {"magnitude": pt, "unit": "PT"}},
            "fields": "weightedFontFamily,fontSize"}})
        matched.append({"text": h["text"][:60], "level": h["level"]})

    info = apply_style_requests(doc_id, token, reqs, doc.get("revisionId"), direct,
                                "mark-headings")

    return {"id": doc_id, "tab_id": tid, "marked": len(matched), **info,
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
        # חוק המקפים: מקף רגיל עם רווחים, לעולם לא קו מפריד ארוך במסמך עברי.
        md = f"\n- עדכון דוח ({_stamp()}) -\n\n" + md
    # רנדור אמיתי: טבלאות Docs, קישורים על הטקסט, הדגשה, בולטים, כותרות בהיררכיה.
    render_markdown(doc_id, token, tid, md, at)

    # אכיפת הפונט אחרי שהפסקאות קיבלו את הסגנון הנקוב שלהן —
    # רק על לשונית הדוח. הלשונית הראשית היא של דור; לא נוגעים בעיצוב שלה.
    # בלשונית קיימת: רק על הטווח שנוסף עכשיו (מ-at), לא על מה שכבר היה בה.
    batch(doc_id, token, font_requests(get_doc(doc_id, token), only_tab=tid,
                                       min_index=at if appending else 0))
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


_DELETE_TYPES = {"delete", "deletion", "remove"}
_REPLACE_TYPES = {"replace", "replacement"}
_INSERT_TYPES = {"insert", "insertion", "add"}
_LINK_TYPES = {"link"}


def _norm_edit(rec: dict) -> dict:
    """מנרמל רשומת edits.json לפורמט אחיד, עם כינויים גמישים לשמות שדות.

    סיווג (type מפורש גובר תמיד):
    - deletion: type=deletion/delete, או originalText + newText **שקיים ושווה ""**.
      (`"newText" in rec` ולא `rec.get(...) or ...` - שרשרת or מסתירה מחרוזת ריקה.)
    - replacement: עוגן + newText לא ריק.
    - insertion: עוגן מסוג `anchor` (ולא originalText) + newText; או type מפורש.
    - link: originalText + link בלי newText - קישור על טקסט קיים, בלי שינוי טקסט.
    - invalid: originalText בלי newText ובלי link - **לעולם לא נמחק** רשומה פגומה.
    שדה `link` (מחרוזת URL או {"url": ...}) אופציונלי: על newText שנוסף הוא מוחל
    כהצעת עיצוב (updateTextStyle במצב SUGGEST) מיד אחרי ההכנסה.
    """
    t = (rec.get("type") or "").lower().strip()
    find = rec.get("originalText") or rec.get("find") or rec.get("anchor") or ""
    new_key = next((k for k in ("newText", "text", "insert")
                    if k in rec and rec[k] is not None), None)
    new = rec[new_key] if new_key and isinstance(rec[new_key], str) else ""
    link = rec.get("link") or ""
    if isinstance(link, dict):
        link = link.get("url") or ""
    link = str(link).strip()
    comment = rec.get("comment") or rec.get("note") or ""
    occ = int(rec.get("occurrence", 1))
    anchor_only = bool(rec.get("anchor")) and not (rec.get("originalText") or rec.get("find"))

    if t in _DELETE_TYPES:
        t = "deletion"
    elif t in _REPLACE_TYPES:
        t = "replacement"
        if new_key is None and link:
            t = "link"              # replacement בלי newText אבל עם link = קישור על טקסט קיים
        elif new_key is None:
            t = "invalid"           # replacement בלי newText - לא מנחשים מחיקה
        elif new == "":
            t = "deletion"          # newText="" מפורש = מחיקה
    elif t in _INSERT_TYPES:
        t = "insertion"
    elif t in _LINK_TYPES:
        t = "link"
    elif t == "comment":
        pass
    elif t:
        t = "unknown:" + t
    else:
        if comment and new_key is None and not link:
            t = "comment"
        elif find and new:
            t = "insertion" if anchor_only else "replacement"
        elif find and new_key is not None and new == "":
            t = "invalid" if link else "deletion"
        elif find and new_key is None and link:
            t = "link"
        elif find and new_key is None:
            t = "invalid"
        else:
            t = "insertion"
    return {"type": t, "find": find, "new": new, "link": link, "occurrence": occ,
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


_QUOTE_EQ = {
    "“": '"', "”": '"', "„": '"', "״": '"',
    "‘": "'", "’": "'", "׳": "'",
}


def _qeq(ch: str) -> str:
    return _QUOTE_EQ.get(ch, ch)


def _minimize_replacement(old: str, new: str):
    """מצמצם החלפה לטווח המילים שבאמת השתנה (הנחיית דור 17.11.2026).

    מרכאות וגרשיים מכל סוג נחשבים זהים: שינוי שכולו מרכאות לא נשלח (None),
    ומרכאות בקצוות של משפט מוחלף לא מגדילות את ההצעה למשפט שלם - הטקסט במסמך
    שומר את המרכאות שלו. החיתוך נעשה בגבולות מילה, כדי שתיקון הקלדה יציע את
    המילה כולה ולא חצי מילה.
    מחזיר (start, end, new_min) יחסית ל-old, או None אם אין שינוי ענייני.
    """
    if "".join(map(_qeq, old)) == "".join(map(_qeq, new)):
        return None
    def bnd(x, i):  # גבול מילה: לא באמצע רצף אותיות/ספרות
        return i <= 0 or i >= len(x) or not (x[i - 1].isalnum() and x[i].isalnum())

    p, lim = 0, min(len(old), len(new))
    while p < lim and _qeq(old[p]) == _qeq(new[p]):
        p += 1
    while p > 0 and not (bnd(old, p) and bnd(new, p)):
        p -= 1
    s, lim2 = 0, min(len(old), len(new)) - p
    while s < lim2 and _qeq(old[-1 - s]) == _qeq(new[-1 - s]):
        s += 1
    while s > 0 and not (bnd(old, len(old) - s) and bnd(new, len(new) - s)):
        s -= 1
    o_mid, n_mid = old[p:len(old) - s], new[p:len(new) - s]
    if "".join(map(_qeq, o_mid)) == "".join(map(_qeq, n_mid)):
        return None
    return p, len(old) - s, n_mid


def _find_occurrences(plain: str, needle: str) -> list:
    out, i = [], plain.find(needle)
    while i != -1:
        out.append(i)
        i = plain.find(needle, i + 1)
    return out


def _resolve_anchors(raw_edits: list, plain: str) -> tuple:
    """רזולוציית עוגנים משותפת (suggest + validate) על אינדקסים פייתוניים ב-plain.

    מחזיר (resolved, skipped):
      resolved: [{"pstart", "pend", "new", "link", "kind", "idx", "anchor", "exact"}]
                (pstart==pend = הוספה; idx = המיקום ברשימה המקורית)
      skipped:  [{"reason", ...}] - כולל not_found / ambiguous / no_anchor /
                overlap / comment_type_removed / no_new_text / empty_insertion /
                bad_link / unknown_type.

    כללים:
    - התאמה מדויקת קודמת; אם אין - התאמה מנורמלת (גרשיים/מקפים/NBSP/רווחים).
    - יותר ממופע אחד בלי occurrence מפורש = ambiguous (לא בוחרים בשקט).
    - insertion בלי עוגן = no_anchor (לא דוחפים לראש המסמך).
    - type=comment הוסר (10.08.2026): הערות עורך שייכות ל-report.txt - מדולג עם אזהרה.
    - עריכות חופפות: המאוחרת ברשימה נדחית עם reason=overlap.
    """
    norm_plain, norm_map = _normalize_with_map(plain)
    resolved, skipped = [], []
    for idx, rec in enumerate(raw_edits):
        e = _norm_edit(rec)
        if e["type"] == "comment":
            print("אזהרה: type=comment הוסר מהסקיל - הערות עורך שייכות לדוח העורך "
                  f"(report.txt) בלבד. ההערה דולגה: {e['comment'][:60]}", file=sys.stderr)
            skipped.append({"reason": "comment_type_removed", "comment": e["comment"][:60]})
            continue
        find, new, link, kind = e["find"], e["new"], e["link"], e["type"]
        if kind.startswith("unknown:"):
            skipped.append({"reason": "unknown_type", "type": kind[8:], "text": find[:60]})
            continue
        if kind == "invalid":
            skipped.append({"reason": "no_new_text", "text": find[:60]})
            continue
        if kind == "insertion" and not new:
            skipped.append({"reason": "empty_insertion", "text": find[:60]})
            continue
        if link and not re.match(r"^https?://\S+$", link):
            skipped.append({"reason": "bad_link", "link": link[:80], "text": find[:60]})
            continue
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
        if occ < 1 or occ > len(matches):
            skipped.append({"reason": f"occurrence {occ}>{len(matches)}", "text": find[:60]})
            continue
        s0, e0 = matches[occ - 1]
        base = {"new": new, "link": link, "kind": kind, "idx": idx,
                "anchor": find[:60], "exact": exact}
        if kind == "insertion":
            resolved.append({"pstart": e0, "pend": e0, **base})
        else:
            if kind == "deletion":
                base["new"] = ""
            elif kind == "replacement" and not link:
                # הנחיית דור 17.11.2026: הצעה ענינית או כירורגית בלבד. מצמצמים
                # לטווח שבאמת השתנה, ומדלגים על הצעה שכל ההבדל בה הוא מרכאות/גרשיים.
                m = _minimize_replacement(plain[s0:e0], new)
                if m is None:
                    skipped.append({"reason": "quotes_only", "text": find[:60]})
                    continue
                ds, de, new_min = m
                s0, e0 = s0 + ds, s0 + de
                base["new"] = new_min
                if s0 == e0:
                    base["kind"] = "insertion"
                elif not new_min:
                    base["kind"] = "deletion"
            resolved.append({"pstart": s0, "pend": e0, **base})

    # זיהוי חפיפות: העריכה המאוחרת ברשימה שחופפת טווח שכבר התקבל - נדחית.
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


def _link_req(tid: str, start: int, end: int, url: str) -> dict:
    return {"updateTextStyle": {
        "range": {"tabId": tid, "startIndex": start, "endIndex": end},
        "textStyle": {"link": {"url": url}}, "fields": "link"}}


def build_suggest_requests(resolved: list, plain: str, mapping: list, tid: str) -> list:
    """בונה את רשימת הבקשות ל-batchUpdate מתוך resolved.

    סדר: יורד לפי (pstart, pend, idx). הכנסה מזיזה אינדקסים >= נקודת ההכנסה,
    ולכן מעבדים גבוה->נמוך. שובר-שוויון: כששתי עריכות מתחילות באותו מקום,
    הארוכה (החלפה) לפני ההוספה, ושתי הוספות באותה נקודה מעובדות מהמאוחרת
    ברשימה למוקדמת - כך שבמסמך הן יוצאות בסדר הרשימה. (מיון יציב עם
    key=pstart בלבד היה הופך את סדרן.)

    קישור (`link`) מוחל ב-updateTextStyle **מיד אחרי ה-insertText שלו**, על
    הטווח [e, e+len(new)) - הבקשות רצות לפי הסדר, ולכן העיצוב נצמד לטקסט לפני
    שהכנסות נמוכות יותר מזיזות אותו.
    """
    reqs = []
    order = sorted(resolved, key=lambda x: (x["pstart"], x["pend"], x.get("idx", 0)),
                   reverse=True)
    for ed in order:
        ps, pe, new, link = ed["pstart"], ed["pend"], ed["new"], ed.get("link")
        kind = ed.get("kind", "replacement")
        if ps < pe:  # החלפה / מחיקה / קישור על טקסט קיים
            s = mapping[ps]
            e = mapping[pe - 1] + _u16len(plain[pe - 1])
            if kind == "link":
                if link:
                    reqs.append(_link_req(tid, s, e, link))
                continue
            if new:
                reqs.append({"insertText": {"text": new, "location": {"tabId": tid, "index": e}}})
                if link:
                    reqs.append(_link_req(tid, e, e + _u16(new), link))
            reqs.append({"deleteContentRange": {
                "range": {"tabId": tid, "startIndex": s, "endIndex": e}}})
        else:  # הוספה טהורה אחרי העוגן
            e = mapping[ps - 1] + _u16len(plain[ps - 1]) if ps > 0 else 1
            if new:
                reqs.append({"insertText": {"text": new, "location": {"tabId": tid, "index": e}}})
                if link:
                    reqs.append(_link_req(tid, e, e + _u16(new), link))
    return reqs


def _suggestion_ids(node) -> dict:
    """אוסף מזהי הצעות מכל עומק המבנה.

    insertions / deletions: ערכי suggestedInsertionIds / suggestedDeletionIds (רשימות).
    text_style / para_style: **המפתחות** של suggestedTextStyleChanges /
    suggestedParagraphStyleChanges (מפות שממופתחות לפי מזהה הצעה).
    """
    out = {"insertions": set(), "deletions": set(), "text_style": set(), "para_style": set()}

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "suggestedInsertionIds" and isinstance(v, list):
                    out["insertions"].update(v)
                elif k == "suggestedDeletionIds" and isinstance(v, list):
                    out["deletions"].update(v)
                elif k == "suggestedTextStyleChanges" and isinstance(v, dict):
                    out["text_style"].update(v.keys())
                elif k == "suggestedParagraphStyleChanges" and isinstance(v, dict):
                    out["para_style"].update(v.keys())
                else:
                    walk(v)
        elif isinstance(o, list):
            for i in o:
                walk(i)

    walk(node)
    return out


def _all_ids(ids: dict) -> set:
    return set().union(*ids.values())


# ------------------------------------------- אימות לפי תוכן (לא לפי מזהים)
# מזהי הצעות לבדם מטעים: עוגן שנוגע בהצעה קיימת מתמזג אליה ולא יוצר מזהה
# חדש (false "overwrote"), ו-SUGGEST שנבלע לדריסה לא משאיר מזהים בכלל.
# לכן ההכרעה נעשית לפי תוכן בשתי תצוגות:
#   PREVIEW_WITHOUT_SUGGESTIONS - הטקסט המאושר. חייב להישאר זהה: מקור שנעלם
#     או טקסט חדש שהופיע בו = כתיבה ישירה = overwrote.
#   PREVIEW_SUGGESTIONS_ACCEPTED - הטקסט אם דור יקבל הכל. הטקסט החדש חייב
#     להופיע בו בדיוק פעם אחת לכל עריכה; פעמיים = הצעה כפולה.

def expected_deltas(resolved: list, plain: str) -> dict:
    """לכל מחרוזת רלוונטית: בכמה אמורה ספירת המופעים שלה להשתנות בתצוגת ACCEPTED."""
    news = [ed["new"] for ed in resolved if ed["new"]]
    origs = [plain[ed["pstart"]:ed["pend"]] for ed in resolved
             if ed["pstart"] < ed["pend"] and ed.get("kind") != "link"]
    keys = {s for s in news + origs if s.strip()}
    return {k: sum(n.count(k) for n in news) - sum(o.count(k) for o in origs)
            for k in keys}


def build_checks(resolved: list, plain: str, pre_accepted: str, pre_without: str) -> dict:
    return {k: {"expected": d, "pre_accepted": pre_accepted.count(k),
                "pre_without": pre_without.count(k)}
            for k, d in expected_deltas(resolved, plain).items()}


def content_verdict(checks: dict, post_accepted: str, post_without: str) -> dict:
    """הכרעה טהורה (בלי רשת) האם ההצעות נחתו, ובאיזה אופן.

    status:
      overwrote  - הטקסט המאושר (WITHOUT) השתנה: SUGGEST נבלע לכתיבה ישירה.
      landed     - כל השינויים הצפויים מופיעים ב-ACCEPTED, ו-WITHOUT ללא שינוי.
      duplicate  - שינוי כפול מהצפוי (הבקשה הוחלה פעמיים).
      not_landed - שום שינוי צפוי לא הופיע.
      partial    - חלק כן וחלק לא (או שינוי מקביל במסמך) - לבדיקה ידנית.
    """
    direct, ok, missing, dup, mismatch = [], [], [], [], []
    for text, c in checks.items():
        dw = post_without.count(text) - c["pre_without"]
        if dw:
            direct.append({"text": text[:60], "delta_without": dw})
        da = post_accepted.count(text) - c["pre_accepted"]
        exp = c["expected"]
        if exp == 0:
            continue
        if da == exp:
            ok.append(text[:60])
        elif da == 0:
            missing.append(text[:60])
        elif exp > 0 and da >= 2 * exp:
            dup.append({"text": text[:60], "expected": exp, "actual": da})
        else:
            mismatch.append({"text": text[:60], "expected": exp, "actual": da})
    if direct:
        status = "overwrote"
    elif dup:
        status = "duplicate"
    elif not missing and not mismatch:
        status = "landed"
    elif not ok and not mismatch:
        status = "not_landed"
    else:
        status = "partial"
    return {"status": status, "ok": len(ok), "missing": missing, "duplicate": dup,
            "mismatch": mismatch, "direct_write": direct}


def _linked_texts(tab: dict) -> list:
    """[(url, text)] - runs רצופים עם אותו קישור מאוחדים לטקסט אחד."""
    out = []

    def walk(content):
        for el in content:
            p = el.get("paragraph")
            if p:
                for pe in p.get("elements", []):
                    tr = pe.get("textRun")
                    if not tr:
                        continue
                    url = (tr.get("textStyle", {}).get("link") or {}).get("url")
                    txt = tr.get("content", "")
                    if url and out and out[-1][0] == url and out[-1][2]:
                        out[-1] = (url, out[-1][1] + txt, True)
                    elif url:
                        out.append((url, txt, True))
                    else:
                        out.append((None, "", False))
            elif el.get("table"):
                for row in el["table"].get("tableRows", []):
                    for cell in row.get("tableCells", []):
                        walk(cell.get("content", []))

    walk(tab["documentTab"]["body"]["content"])
    return [(u, t) for u, t, _ in out if u]


def _is_linked(links: list, url: str, text: str) -> bool:
    return any(u == url and text in t for u, t in links)


def build_link_checks(resolved: list, plain: str, pre_without_links: list) -> list:
    checks = []
    for ed in resolved:
        if not ed.get("link"):
            continue
        text = ed["new"] if ed["new"] else plain[ed["pstart"]:ed["pend"]]
        checks.append({"url": ed["link"], "text": text,
                       "pre_without": _is_linked(pre_without_links, ed["link"], text)})
    return checks


def link_verdict(link_checks: list, accepted_links: list, without_links: list) -> dict:
    ok, missing, direct = [], [], []
    for c in link_checks:
        if _is_linked(without_links, c["url"], c["text"]) and not c["pre_without"]:
            direct.append({"url": c["url"], "text": c["text"][:60]})
        elif _is_linked(accepted_links, c["url"], c["text"]):
            ok.append({"url": c["url"], "text": c["text"][:60]})
        else:
            missing.append({"url": c["url"], "text": c["text"][:60]})
    return {"total": len(link_checks), "ok": len(ok), "missing": missing,
            "direct_write": direct}


# ------------------------------------------------------------- ledger מקומי

def _ledger_path(edits_path: Path) -> Path:
    return edits_path.with_name(edits_path.stem + ".suggest-ledger.json")


def _ledger_load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"entries": {}}


def _ledger_save(path: Path, ledger: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(ledger, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(tmp, path)


def _edits_key(doc_id: str, tab_id: str | None, raw: list) -> str:
    blob = json.dumps({"doc": doc_id, "tab": tab_id or "", "edits": raw},
                      ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:24]


# ledger statuses: pending/unknown = נשלח, התוצאה לא ידועה (בדיקה לפני כל שליחה);
# rejected/not_landed = בטוח לשלוח שוב; כל השאר = כבר נחת, לא שולחים שוב.
_RESEND_OK = {"rejected", "not_landed"}
_NEEDS_CHECK = {"pending", "unknown"}


def _read_views(doc_id: str, token: str, tid: str) -> tuple:
    acc = _find_tab(get_doc_view(doc_id, token, "PREVIEW_SUGGESTIONS_ACCEPTED"), tid)
    wo = _find_tab(get_doc_view(doc_id, token, "PREVIEW_WITHOUT_SUGGESTIONS"), tid)
    if not acc or not wo:
        sys.exit(f"הלשונית {tid} לא נמצאה בקריאת האימות")
    return acc, wo


def _verify_entry(doc_id: str, token: str, entry: dict) -> dict:
    tid = entry["tab_id"]
    acc, wo = _read_views(doc_id, token, tid)
    v = content_verdict(entry["checks"], _tab_plaintext(acc)[0], _tab_plaintext(wo)[0])
    lv = link_verdict(entry.get("link_checks", []), _linked_texts(acc), _linked_texts(wo))
    has_text = any(c["expected"] for c in entry["checks"].values())
    if lv["direct_write"]:
        v["status"] = "overwrote"
    elif not has_text and lv["total"]:
        # רק קישורים על טקסט קיים - ההכרעה לפי הקישורים בלבד
        v["status"] = ("landed" if lv["ok"] == lv["total"]
                       else "not_landed" if lv["ok"] == 0 else "partial")
    elif v["status"] == "landed" and lv["missing"]:
        v["status"] = "partial"
    elif v["status"] == "not_landed" and lv["ok"]:
        v["status"] = "partial"
    return {"content": v, "links": lv}


def suggest_edits(doc_id: str, account: str, edits_path: Path, tab_id: str | None = None) -> dict:
    """מחיל את edits.json כהצעות Docs אמיתיות (writeMode: SUGGEST).

    כל החלפה = הצעת-מחיקה של הישן + הצעת-הוספה של החדש; כל תוספת = הצעת-הוספה;
    `link` = הצעת-עיצוב (updateTextStyle) על הטקסט שנוסף או על הטקסט הקיים.

    בטיחות מפני כפילות (חיבור שנפל אחרי ה-POST):
    - POST אחד לכל הרצה, בלי retry, עם requiredRevisionId מהקריאה שממנה נגזרו
      האינדקסים.
    - ledger מקומי ליד edits.json (`<stem>.suggest-ledger.json`) נכתב **לפני**
      השליחה (status=pending) ומתעדכן אחריה. שגיאת רשת = status=unknown: קוראים
      את המסמך מחדש ובודקים לפי תוכן אם ההצעות נחתו - ולא שולחים שוב.
    - הרצה חוזרת על אותו edits.json לאותו מסמך: אם הקודמת אושרה - מסרבים;
      אם תוצאתה לא ידועה - בודקים קודם לפי תוכן.

    אימות (חובה) לפי תוכן - ראה content_verdict. מזהי ההצעות נספרים כמידע משני.
    """
    token = access_token(account)
    raw = json.loads(Path(edits_path).read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        raw = raw.get("edits") or raw.get("changes") or []
    url = f"https://docs.google.com/document/d/{doc_id}/edit"
    lpath = _ledger_path(Path(edits_path))
    ledger = _ledger_load(lpath)
    key = _edits_key(doc_id, tab_id, raw)
    prev = ledger["entries"].get(key)

    def finish(entry, verdict, reqs_n, resolved_n, skipped, counts, refused=False):
        st = verdict["content"]["status"]
        overwrote = st == "overwrote"
        clean = (st == "landed" and counts.get("tagged", 0) == 0
                 and not verdict["links"]["missing"] and not refused)
        return {"id": doc_id, "tab_id": entry["tab_id"], "mode": "suggest",
                "applied": resolved_n, "requests": reqs_n, "suggestions": counts,
                "status": st, "clean": clean, "overwrote": overwrote,
                "refused_resend": refused, "verification": verdict["content"],
                "links": verdict["links"], "skipped": skipped,
                "ledger": str(lpath), "url": f"{url}?tab={entry['tab_id']}"}

    if prev and prev["status"] in _NEEDS_CHECK:
        print(f"ledger: הרצה קודמת ({prev['submitted_at']}) במצב {prev['status']} - "
              "בודק לפי תוכן אם נחתה, לפני כל שליחה.", file=sys.stderr)
        verdict = _verify_entry(doc_id, token, prev)
        st = verdict["content"]["status"]
        prev["status"] = "confirmed" if st == "landed" else st
        prev["checked_at"] = _stamp()
        _ledger_save(lpath, ledger)
        if prev["status"] != "not_landed":
            return finish(prev, verdict, prev["requests"], prev.get("applied", 0),
                          [], {}, refused=True)
    elif prev and prev["status"] not in _RESEND_OK:
        print(f"ledger: edits.json הזה כבר הוגש למסמך ({prev['submitted_at']}, "
              f"status={prev['status']}). לא שולח שוב. לשליחה מכוונת - מחק את {lpath}.",
              file=sys.stderr)
        verdict = _verify_entry(doc_id, token, prev)
        return finish(prev, verdict, prev["requests"], prev.get("applied", 0),
                      [], {}, refused=True)

    doc = get_doc(doc_id, token)
    revision = doc.get("revisionId")
    tab = _pick_tab(doc, tab_id)
    tid = tab["tabProperties"]["tabId"]
    plain, mapping = _tab_plaintext(tab)

    resolved, skipped = _resolve_anchors(raw, plain)
    reqs = build_suggest_requests(resolved, plain, mapping, tid)

    # צילום מצב לפני הכתיבה: תוכן בשתי התצוגות + מזהי הצעות (משני)
    pre_acc, pre_wo = _read_views(doc_id, token, tid)
    pre_inline = _find_tab(get_doc_view(doc_id, token, "SUGGESTIONS_INLINE"), tid) or {}
    pre_ids = _all_ids(_suggestion_ids(pre_inline))
    entry = {
        "status": "pending", "doc_id": doc_id, "tab_id": tid, "base_revision": revision,
        "requests": len(reqs), "applied": len(resolved), "submitted_at": _stamp(),
        "checks": build_checks(resolved, plain, _tab_plaintext(pre_acc)[0],
                               _tab_plaintext(pre_wo)[0]),
        "link_checks": build_link_checks(resolved, plain, _linked_texts(pre_wo)),
    }

    if reqs:
        ledger["entries"][key] = entry
        _ledger_save(lpath, ledger)  # נכתב לפני ה-POST
        try:
            batch_suggest(doc_id, token, reqs, revision)
            entry["status"] = "sent"
        except urllib.error.HTTPError as e:
            if e.code < 500:
                entry["status"] = "rejected"  # השרת ענה ודחה - לא הוחל דבר
                _ledger_save(lpath, ledger)
                sys.exit(f"batchUpdate נדחה (HTTP {e.code}). לא הוחל דבר. הסיבה בגוף "
                         "השגיאה שהודפס ל-stderr; הרצה חוזרת עוזרת רק אם המסמך השתנה "
                         "בין הקריאה לכתיבה (revision mismatch).")
            entry["status"] = "unknown"
        except WriteOutcomeUnknown as e:
            entry["status"] = "unknown"
            print(f"החיבור נפל אחרי השליחה ({e}). לא שולח שוב - בודק לפי תוכן.",
                  file=sys.stderr)
        _ledger_save(lpath, ledger)

    verdict = _verify_entry(doc_id, token, entry)
    post_inline = _find_tab(get_doc_view(doc_id, token, "SUGGESTIONS_INLINE"), tid) or {}
    post_ids = _suggestion_ids(post_inline)
    new = {k: v - pre_ids for k, v in post_ids.items()}
    new_all = _all_ids(new)
    counts = {"insertions": len(new["insertions"]), "deletions": len(new["deletions"]),
              "text_style": len(new["text_style"]), "total": len(new_all),
              "tagged": len([i for i in new_all if "import" in i.lower()]),
              "pre_existing": len(pre_ids)}
    if reqs:
        st = verdict["content"]["status"]
        entry["status"] = "confirmed" if st == "landed" else st
        entry["checked_at"] = _stamp()
        _ledger_save(lpath, ledger)
    else:
        verdict["content"]["status"] = "landed"  # אין מה להחיל
    return finish(entry, verdict, len(reqs), len(resolved), skipped, counts)


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
    ap.add_argument("--direct", action="store_true",
                    help="מאפשר כתיבה ישירה (לא כהצעה) ל---update / --mark-headings / "
                         "--enforce-font. בלעדיו: --update מסורב, והעיצוב מוחל כהצעות.")
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
        if not info.get("clean"):
            sys.exit(1)
        return

    if a.mark_headings:
        if not a.doc:
            sys.exit("--mark-headings מחייב --doc <doc_id>")
        hp = Path(a.mark_headings).expanduser().resolve()
        if not hp.exists():
            sys.exit(f"קובץ הכותרות לא נמצא: {hp}")
        print(json.dumps(mark_headings(a.doc, a.account, hp, a.tab, a.direct),
                         ensure_ascii=False))
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
            info = enforce_font(a.doc, a.account, a.only_tab, a.direct)
        print(json.dumps(info, ensure_ascii=False))
        return

    if not a.docx:
        sys.exit("נדרש נתיב docx (או --report-tab / --enforce-font / --suggest / --validate)")
    p = Path(a.docx).expanduser().resolve()
    if not p.exists() or p.suffix != ".docx":
        sys.exit(f"קובץ docx לא נמצא: {p}")
    if a.update:
        # --update מחליף את כל תוכן המסמך דרך Drive. אין לזה צורת הצעה - זו בדיוק
        # "הדריסה המוחלטת דרך ה-API" שחוק הברזל אוסר. רק עם --direct מפורש.
        if not a.direct:
            sys.exit("--update מחליף את כל תוכן ה-Google Doc הקיים (כולל כל ההצעות "
                     "והעריכות של דור) ואין לו צורת הצעה. מסורב לפי חוק הברזל. "
                     "להעלאת גרסה חדשה - העלה מסמך חדש בלי --update. "
                     "דריסה מכוונת בלבד: הוסף --direct.")
        print("אזהרה: --update --direct - כל תוכן המסמך יוחלף. אין accept/reject.",
              file=sys.stderr)
        info = update(p, a.account, a.update)
    else:
        info = upload(p, a.account, a.name or p.stem, a.folder)
    info["url"] = f"https://docs.google.com/document/d/{info['id']}/edit"
    print(json.dumps(info, ensure_ascii=False))


if __name__ == "__main__":
    main()
