#!/usr/bin/env python3
"""לינטר עברית מכני לסקיל dor-edit.

בודק קובץ טקסט או edits.json (שדות newText/text/insert/comment/note,
רקורסיבית) מול הכללים הבינאריים של ספר הסגנון (references/hebrew-style.md):
קו מפריד ארוך, מרכאות ישרות בטקסט עברי, % צמוד לספרה, ש"ח, סימן קריאה,
"בתגובה נמסר", פסיק לפני ש' משלימה (אחרי פועל אמירה/חשיבה), "על-מנת" במקף,
כפל רווחים, וביטויים מהרשימה השחורה. מדפיס JSON של הפרות (סוג, מחרוזת,
הקשר ~40 תווים). exit code 1 אם נמצאו הפרות, 0 אם נקי.

- בלוקי קוד מגודרים (```) ו-URL מוחרגים (ממוסכים ברווחים, כדי ש-%D7 בכתובת
  לא ייתפס כ"אחוז צמוד").
- קדושת הציטוט: הפרות שכולן בתוך ציטוט מדווחות בנפרד תחת in_quote_review
  ואינן מפילות את ה-exit code; חריג - הקו המפריד הארוך תמיד נאכף.
  זיווג המרכאות נעשה לכל פסקה בנפרד (פסקה = בלוק בין שורות ריקות), כך
  שמרכאה יתומה אחת לא משבשת את כל הזוגות שאחריה, וציטוט רשאי לחצות שורה.
- --draft draft.txt: הציטוטים של הטיוטה המקורית מוכרים גם כשה-newText מכיל
  רק שבר של ציטוט (בלי המרכאות שלו), וגם כשהעוגן של הרשומה יושב בתוך ציטוט.
- research_narration ("מטבח המחקר בגוף", SKILL.md שלב 3א): אזהרה בלבד, תחת
  warnings, לא משפיעה על ה-exit code (כמו in_quote_review). כבויה כברירת מחדל
  לקבצים ששמם מתחיל ב-report (שם הניסוחים האלה במקומם); --narration /
  --no-narration עוקפים.

שימוש: lint_hebrew.py <קובץ.txt או edits.json> [--draft draft.txt]
       [--narration | --no-narration]
"""
import argparse
import json
import os
import re
import sys

HEBREW = chr(0x0590) + "-" + chr(0x05FF)
EM_DASH = chr(0x2014)
MAQAF = chr(0x05BE)
GERSHAYIM = chr(0x05F4)

# פעלי אמירה/חשיבה/ידיעה שאחריהם ש' היא משלימה - ופסיק לפניה אסור (2.1).
# פסיק לפני ש' זיקה תיאורית ("החברה, שהוקמה ב-2010, ...") תקין ולא נתפס,
# וגם לא שמות עצם שמתחילים ב-ש ("ירושלים, שני ילדים", "השר, שר האוצר").
SAYING_VERBS = (
    "אמר אמרה אמרו טען טענה טענו הודיע הודיעה הודיעו חשד חשדה חשדו ציין ציינה ציינו "
    "הסביר הסבירה הסבירו כתב כתבה כתבו הוסיף הוסיפה הוסיפו הבהיר הבהירה הבהירו "
    "הודה הודתה הודו גילה גילתה גילו מסר מסרה מסרו השיב השיבה השיבו קבע קבעה קבעו "
    "החליט החליטה החליטו מצא מצאה מצאו ידע ידעה ידעו חשב חשבה חשבו האמין האמינה "
    "טוען טוענת טוענים אומר אומרת אומרים חושב חושבת חושבים יודע יודעת יודעים "
    "מאמין מאמינה מאמינים סבור סבורה סבורים נמסר נטען נקבע הוחלט התברר הסתבר "
    "מסתבר ברור ייתכן הדגיש הדגישה הדגישו הזהיר הזהירה הזהירו התריע התריעה "
    "דיווח דיווחה דיווחו פרסם פרסמה פרסמו"
).split()
_VERB_ALT = "|".join(sorted(SAYING_VERBS, key=len, reverse=True))
# עד 3 מילים בין הפועל לפסיק, בלי פיסוק ביניהן ("אמר לי אתמול, ש...")
COMMA_BEFORE_SHE = re.compile(
    rf"(?<![{HEBREW}])ו?(?:{_VERB_ALT})(?![{HEBREW}])"
    rf"(?:\s+[^\s,.;:!?\"{GERSHAYIM}]+){{0,3}}?(,)\s+ש(?=[{HEBREW}])")

CHECKS = [
    ("em_dash", re.compile(EM_DASH)),
    ("percent_attached", re.compile(r"\d%")),
    ("shach", re.compile(rf"(?:מלש|ש)[\"{GERSHAYIM}]ח")),
    ("exclamation", re.compile("!")),
    ("betguva_nimsar", re.compile(r"בתגובה\s+נמסר")),
    ("al_menat_hyphen", re.compile(rf"על[-{MAQAF}]מנת")),
    ("double_space", re.compile(r"(?<=\S)  +")),
]

BLACKLIST = [
    "ביצע פנייה", "ביצעה פנייה", "לקח מקום", "לקחה מקום",
    "עשה החלטה", "עשתה החלטה", "בסוף היום",
    "חשוב לציין", "יצוין כי", "ראוי להדגיש",
]

# מטבח המחקר בגוף (SKILL.md שלב 3א) - אזהרות. "לפי הפרוטוקול" רק מעל מופע אחד.
NARRATION = [
    "הטופס לא מפרט", "לא ידוע אם", "לא מצאנו", "בדקנו", "מעיון ב",
    "במסמך שבידינו", "משלימים את התמונה",
]
NARRATION_REPEATED = {"לפי הפרוטוקול": 1}  # ביטוי -> מספר המופעים המותר

# מרכאות ישרות כפולות בסביבה עברית: תו עברי בטווח 3 תווים לפני או אחרי
STRAIGHT_QUOTE = re.compile(rf'(?:[{HEBREW}][^\n"]{{0,2}}"|"[^\n"]{{0,2}}[{HEBREW}])')

# תווי מרכאות כפולות שיכולים לתחום ציטוט: ישרות, עבריות, מסולסלות
QUOTE_DELIMS = re.compile('["' + GERSHAYIM + chr(0x201C) + chr(0x201D) + chr(0x201E) + ']')

URL_RE = re.compile(r"(?:https?://|www\.)[^\s)\]>\"'" + GERSHAYIM + "]+")

EDIT_TEXT_KEYS = ("newText", "text", "insert", "comment", "note")
EDIT_ANCHOR_KEYS = ("originalText", "find", "anchor")


def _mask(text, pattern, flags=0):
    """מחליף התאמות ברווחים באותו אורך (שורות נשמרות), כדי לשמר אינדקסים."""
    return re.sub(pattern, lambda m: re.sub(r"[^\n]", " ", m.group(0)), text, flags=flags)


def strip_code_blocks(text):
    return _mask(text, r"```.*?```", re.S)


def mask_urls(text):
    # מסכה בקו תחתון ולא ברווחים - אחרת נוצר double_space מלאכותי
    return URL_RE.sub(lambda m: "_" * len(m.group(0)), text)


def quote_spans(text):
    """טווחי *תוכן* הציטוט (בין המרכאות, בלעדיהן) לפי זוגות מרכאות כפולות.

    מרכאות בתוך מילה (ש"ח, בג"ץ - תו אות משני הצדדים) אינן תוחמות ציטוט.
    הזיווג נעשה לכל פסקה בנפרד (בלוק בין שורות ריקות): מרכאה תוחמת אי-זוגית
    פותחת, זוגית סוגרת. ציטוט רשאי לחצות שורה בודדת, לא שורה ריקה.
    המרכאות עצמן אינן חלק מהתוכן המוגן - סימני הציטוט הם פיסוק של הכותב
    ומותר לתקנם (ישרות -> עבריות) בלי לגעת בציטוט עצמו.
    """
    spans = []
    for para in re.finditer(r"(?:[^\n]|\n(?![ \t]*\n))+", text):
        opener = None
        for m in QUOTE_DELIMS.finditer(text, para.start(), para.end()):
            i = m.start()
            prev = text[i - 1] if i > 0 else ""
            nxt = text[i + 1] if i + 1 < len(text) else ""
            if prev.isalnum() and nxt.isalnum():
                continue  # גרשיים של ראשי תיבות - לא גבול ציטוט
            # כיוון המרכאה: פותחת אם לפניה רווח/תחילת שורה/פיסוק פותח ואחריה תו;
            # סוגרת אם לפניה תו. כך מרכאה שבורה אחת לא הופכת פסקאות שלמות לציטוט.
            opens = (prev == "" or prev.isspace() or prev in "([{-:\u05be") and nxt not in ("", " ", "\n")
            if opener is None:
                if opens:
                    opener = i
            elif not opens or nxt in ("", " ", "\n") or not nxt.isalnum():
                spans.append((opener + 1, i))
                opener = None
            elif text.count("\n", opener, i) > 0:
                opener = i  # מרכאה פותחת חדשה בשורה אחרת: הקודמת לא נסגרה
            else:
                spans.append((opener + 1, i))
                opener = None
    return spans


def quote_texts(text):
    """תוכן הציטוטים בטקסט (לשימוש --draft)."""
    clean = strip_code_blocks(text)
    return [clean[a:b] for a, b in quote_spans(clean)]


def in_any_span(spans, start, end):
    return any(start >= a and end <= b for a, b in spans)


def _in_draft_quote(text, start, end, draft_quotes, radius=12):
    """האם ההפרה יושבת בשבר ציטוט מהטיוטה: החלון סביבה (בגבולות המחרוזת)
    מופיע כמחרוזת-משנה בתוך אחד מציטוטי הטיוטה."""
    if not draft_quotes:
        return False
    window = text[max(0, start - radius):min(len(text), end + radius)].strip()
    if not window:
        return False
    return any(window in q for q in draft_quotes)


def context(text, start, end, radius=40):
    return text[max(0, start - radius):min(len(text), end + radius)].replace("\n", " ")


def lint_text(text, source="", draft_quotes=None, force_in_quote=False, narration=True,
              repeat_counter=None):
    """מחזיר (violations, warnings); הפרה שכולה בתוך ציטוט מסומנת in_quote=True.

    קדושת הציטוט: טקסט מצוטט לא מתקנים - הפרות בתוכו מדווחות לבדיקה ידנית
    בלבד ולא מפילות את ה-exit code. חריג: הקו המפריד הארוך מדווח תמיד כרגיל,
    כי חוק המקפים חל גם בתוך ציטוטים.
    force_in_quote: העוגן של הרשומה יושב בתוך ציטוט בטיוטה.
    repeat_counter: dict משותף לכל השדות בקובץ - כך "לפי הפרוטוקול" נספר
    לקובץ כולו ולא לכל newText בנפרד.
    """
    if repeat_counter is None:
        repeat_counter = {}
    violations, warnings = [], []
    clean = mask_urls(strip_code_blocks(text))
    spans = quote_spans(clean)

    def quoted(start, end):
        return (force_in_quote or in_any_span(spans, start, end)
                or _in_draft_quote(clean, start, end, draft_quotes))

    def add(kind, start, end, bucket=None):
        q = kind != "em_dash" and quoted(start, end)
        (violations if bucket is None else bucket).append({
            "type": kind,
            "match": clean[start:end],
            "context": context(clean, start, end),
            "in_quote": q,
            **({"source": source} if source else {}),
        })

    for kind, pattern in CHECKS:
        for m in pattern.finditer(clean):
            add(kind, m.start(), m.end())
    for m in COMMA_BEFORE_SHE.finditer(clean):
        add("comma_before_she", m.start(1), m.end())
    for m in STRAIGHT_QUOTE.finditer(clean):
        add("straight_quotes", m.start(), m.end())
    for phrase in BLACKLIST:
        for m in re.finditer(re.escape(phrase), clean):
            add("blacklist", m.start(), m.end())

    if narration:
        for phrase in NARRATION:
            for m in re.finditer(re.escape(phrase), clean):
                if not quoted(m.start(), m.end()):
                    add("research_narration", m.start(), m.end(), warnings)
        for phrase, allowed in NARRATION_REPEATED.items():
            for m in re.finditer(re.escape(phrase), clean):
                if quoted(m.start(), m.end()):
                    continue
                repeat_counter[phrase] = repeat_counter.get(phrase, 0) + 1
                if repeat_counter[phrase] > allowed:
                    add("research_narration", m.start(), m.end(), warnings)
    return violations, warnings


def iter_edit_records(node, path=""):
    """שולף רקורסיבית (path, record) לכל dict שיש בו שדה טקסט של עריכה."""
    if isinstance(node, dict):
        if any(isinstance(node.get(k), str) for k in EDIT_TEXT_KEYS):
            yield path, node
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                yield from iter_edit_records(value, f"{path}.{key}" if path else key)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from iter_edit_records(item, f"{path}[{i}]")


def iter_edit_strings(node, path=""):
    """תאימות לאחור: (field_path, value) לכל שדה טקסט של עריכה."""
    for rec_path, rec in iter_edit_records(node, path):
        for k in EDIT_TEXT_KEYS:
            if isinstance(rec.get(k), str):
                yield (f"{rec_path}.{k}" if rec_path else k), rec[k]


def _anchor_in_draft_quote(rec, draft_text, draft_spans):
    """העוגן של הרשומה נמצא (מופע ראשון) בתוך ציטוט בטיוטה."""
    if draft_text is None:
        return False
    anchor = next((rec[k] for k in EDIT_ANCHOR_KEYS
                   if isinstance(rec.get(k), str) and rec[k]), "")
    if not anchor:
        return False
    i = draft_text.find(anchor)
    return i != -1 and in_any_span(draft_spans, i, i + len(anchor))


def lint_path(path, draft=None, narration=None):
    with open(path, encoding="utf-8") as f:
        raw = f.read()
    if narration is None:
        narration = not os.path.basename(path).lower().startswith("report")

    draft_text, draft_spans, draft_quotes = None, [], None
    if draft:
        with open(draft, encoding="utf-8") as f:
            draft_text = strip_code_blocks(f.read())
        draft_spans = quote_spans(draft_text)
        draft_quotes = [draft_text[a:b] for a, b in draft_spans]

    violations, warnings, counter = [], [], {}
    if path.endswith(".json"):
        data = json.loads(raw)
        for rec_path, rec in iter_edit_records(data):
            force = _anchor_in_draft_quote(rec, draft_text, draft_spans)
            for k in EDIT_TEXT_KEYS:
                if not isinstance(rec.get(k), str):
                    continue
                src = f"{rec_path}.{k}" if rec_path else k
                # הערה (comment/note) אינה גוף - לא נבדקת למטבח מחקר
                v, w = lint_text(rec[k], source=src, draft_quotes=draft_quotes,
                                 force_in_quote=force,
                                 narration=narration and k not in ("comment", "note"),
                                 repeat_counter=counter)
                violations.extend(v)
                warnings.extend(w)
    else:
        v, w = lint_text(raw, draft_quotes=draft_quotes, narration=narration)
        violations.extend(v)
        warnings.extend(w)
    return violations, warnings


def main(argv=None):
    ap = argparse.ArgumentParser(description="לינטר עברית מכני ל-dor-edit")
    ap.add_argument("path", help="קובץ .txt או edits.json")
    ap.add_argument("--draft", default=None,
                    help="draft.txt המקורי - לזיהוי שברי ציטוטים ועוגנים בתוך ציטוט")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--narration", dest="narration", action="store_true", default=None,
                   help="להפעיל research_narration גם על report*")
    g.add_argument("--no-narration", dest="narration", action="store_false",
                   help="לכבות research_narration")
    a = ap.parse_args(argv)

    try:
        violations, warnings = lint_path(a.path, a.draft, a.narration)
    except json.JSONDecodeError as e:
        print(f"שגיאת JSON: {e}", file=sys.stderr)
        sys.exit(2)

    actionable = [v for v in violations if not v["in_quote"]]
    quoted = [v for v in violations if v["in_quote"]]
    print(json.dumps({
        "file": a.path,
        "violations": actionable,
        "count": len(actionable),
        "in_quote_review": {
            "note": "לבדיקה ידנית - בתוך ציטוט, לא לתקן אוטומטית",
            "violations": quoted,
            "count": len(quoted),
        },
        "warnings": {
            "note": "מטבח המחקר בגוף (research_narration) - לשכתב לממצא או להעביר "
                    "לדוח. אזהרה בלבד, לא משפיעה על ה-exit code",
            "violations": warnings,
            "count": len(warnings),
        },
    }, ensure_ascii=False, indent=2))
    sys.exit(1 if actionable else 0)


if __name__ == "__main__":
    main()
