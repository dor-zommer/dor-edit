#!/usr/bin/env python3
"""לינטר עברית מכני לסקיל dor-edit.

בודק קובץ טקסט או edits.json (כל שדות newText/comment, רקורסיבית) מול
הכללים הבינאריים של ספר הסגנון (references/hebrew-style.md):
קו מפריד ארוך, מרכאות ישרות בטקסט עברי, % צמוד לספרה, ש"ח, סימן קריאה,
"בתגובה נמסר", פסיק לפני ש' מחוברת, "על-מנת" במקף, כפל רווחים,
וביטויים מהרשימה השחורה. מדפיס JSON של הפרות (סוג, מחרוזת, הקשר ~40 תווים).
exit code 1 אם נמצאו הפרות, 0 אם נקי. בלוקי קוד מגודרים (```) מוחרגים.
קדושת הציטוט: הפרות שכולן בתוך ציטוט (״...״ או "...") מדווחות בנפרד
תחת in_quote_review ואינן מפילות את ה-exit code; חריג — em dash תמיד נאכף.

שימוש: lint_hebrew.py <קובץ.txt או edits.json>
"""
import json
import re
import sys

HEBREW = r"֐-׿"

CHECKS = [
    ("em_dash", re.compile("—")),
    ("percent_attached", re.compile(r"\d%")),
    ("shach", re.compile(r"(?:מלש|ש)[\"״]ח")),
    ("exclamation", re.compile("!")),
    ("betguva_nimsar", re.compile(r"בתגובה\s+נמסר")),
    ("comma_before_she", re.compile(rf",\s+ש(?=[{HEBREW}])")),
    ("al_menat_hyphen", re.compile(r"על[-־]מנת")),
    ("double_space", re.compile(r"(?<=\S)  +")),
]

BLACKLIST = [
    "ביצע פנייה", "ביצעה פנייה", "לקח מקום", "לקחה מקום",
    "עשה החלטה", "עשתה החלטה", "בסוף היום",
    "חשוב לציין", "יצוין כי", "ראוי להדגיש",
]

# מרכאות ישרות כפולות בסביבה עברית: תו עברי בטווח 3 תווים לפני או אחרי
STRAIGHT_QUOTE = re.compile(rf'(?:[{HEBREW}][^\n"]{{0,2}}"|"[^\n"]{{0,2}}[{HEBREW}])')

# תווי מרכאות כפולות שיכולים לתחום ציטוט: ישרות, עבריות (״), מסולסלות
QUOTE_DELIMS = re.compile('["״“”„]')


def quote_spans(text):
    """טווחי *תוכן* הציטוט (בין המרכאות, בלעדיהן) לפי זוגות מרכאות כפולות.

    מרכאות בתוך מילה (ש"ח, בג"ץ — תו אות משני הצדדים) אינן תוחמות ציטוט.
    זיווג נאיבי: מרכאה תוחמת אי-זוגית פותחת, זוגית סוגרת. ציטוט לא חוצה שורה.
    המרכאות עצמן אינן חלק מהתוכן המוגן — סימני הציטוט הם פיסוק של הכותב
    ומותר לתקנם (ישרות ← עבריות) בלי לגעת בציטוט עצמו.
    """
    delims = []
    for m in QUOTE_DELIMS.finditer(text):
        i = m.start()
        prev = text[i - 1] if i > 0 else ""
        nxt = text[i + 1] if i + 1 < len(text) else ""
        if prev.isalnum() and nxt.isalnum():
            continue  # גרשיים של ראשי תיבות — לא גבול ציטוט
        delims.append(i)
    spans = []
    for a, b in zip(delims[0::2], delims[1::2]):
        if "\n" not in text[a:b]:
            spans.append((a + 1, b))
    return spans


def in_any_span(spans, start, end):
    return any(start >= a and end <= b for a, b in spans)


def strip_code_blocks(text):
    """מחליף בלוקי קוד מגודרים ברווחים באותו אורך, כדי לשמר אינדקסים."""
    return re.sub(r"```.*?```", lambda m: re.sub(r"\S", " ", m.group(0)),
                  text, flags=re.S)


def context(text, start, end, radius=40):
    return text[max(0, start - radius):min(len(text), end + radius)].replace("\n", " ")


def lint_text(text, source=""):
    """מחזיר הפרות; הפרה שכולה בתוך ציטוט מסומנת in_quote=True.

    קדושת הציטוט: טקסט מצוטט לא מתקנים — הפרות בתוכו מדווחות לבדיקה ידנית
    בלבד ולא מפילות את ה-exit code. חריג: em dash מדווח תמיד כרגיל,
    כי חוק המקפים חל גם בתוך ציטוטים.
    """
    violations = []
    clean = strip_code_blocks(text)
    spans = quote_spans(clean)

    def add(kind, m):
        quoted = kind != "em_dash" and in_any_span(spans, m.start(), m.end())
        violations.append({
            "type": kind,
            "match": m.group(0),
            "context": context(clean, m.start(), m.end()),
            "in_quote": quoted,
            **({"source": source} if source else {}),
        })

    for kind, pattern in CHECKS:
        for m in pattern.finditer(clean):
            add(kind, m)
    for m in STRAIGHT_QUOTE.finditer(clean):
        add("straight_quotes", m)
    for phrase in BLACKLIST:
        for m in re.finditer(re.escape(phrase), clean):
            add("blacklist", m)
    return violations


def iter_edit_strings(node, path=""):
    """שולף רקורסיבית את כל שדות newText ו-comment מתוך מבנה edits.json."""
    if isinstance(node, dict):
        for key, value in node.items():
            child = f"{path}.{key}" if path else key
            if key in ("newText", "comment") and isinstance(value, str):
                yield child, value
            else:
                yield from iter_edit_strings(value, child)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from iter_edit_strings(item, f"{path}[{i}]")


def main():
    if len(sys.argv) != 2:
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    path = sys.argv[1]
    with open(path, encoding="utf-8") as f:
        raw = f.read()

    violations = []
    if path.endswith(".json"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"שגיאת JSON: {e}", file=sys.stderr)
            sys.exit(2)
        for field_path, value in iter_edit_strings(data):
            violations.extend(lint_text(value, source=field_path))
    else:
        violations.extend(lint_text(raw))

    actionable = [v for v in violations if not v["in_quote"]]
    quoted = [v for v in violations if v["in_quote"]]
    print(json.dumps({
        "file": path,
        "violations": actionable,
        "count": len(actionable),
        "in_quote_review": {
            "note": "לבדיקה ידנית - בתוך ציטוט, לא לתקן אוטומטית",
            "violations": quoted,
            "count": len(quoted),
        },
    }, ensure_ascii=False, indent=2))
    sys.exit(1 if actionable else 0)


if __name__ == "__main__":
    main()
