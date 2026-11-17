#!/usr/bin/env python3
"""בונה docx בסיס מטקסט טיוטה (למשל ייצוא של Google Doc).

כל שורה לא-ריקה הופכת לפסקה RTL. תחביר מרקדאון בסיסי:
- **מודגש** נשמר כ-run מודגש
- [טקסט](קישור) הופך להיפר-קישור אמיתי על הטקסט (הכתובת לא מוצגת);
  ה-URL רשאי להכיל סוגריים מקוננים ברמה אחת (ויקיפדיה בעברית)
- # / ## / ### מקבלות סגנון כותרת (Alef, גדול מ-14, מודגש)
- "- פריט" הופך לרשימת בולטים אמיתית; "1. פריט" לרשימה ממוספרת אמיתית

מפרט טיפוגרפי (דרישת דור): כל המסמכים בפונט **Alef**, גוף בגודל **14**.
הפונט והגודל מוגדרים ברמת הסגנון (docDefaults + Normal) ולא ברמת ריצה בודדת,
כדי שיחולו על כל הפסקאות. לעברית (complex script) חובה גם `w:rFonts/@w:cs`
וגם `w:szCs` — בלעדיהם הטקסט העברי נשאר בפונט ובגודל ברירת המחדל.
`w:rtl` מוחל רק על runs שמכילים עברית — run לטיני טהור נשאר LTR.

שימוש: python3 build_docx.py <draft.txt> <out.docx>
"""
import re, sys, zipfile
from xml.sax.saxutils import escape

FONT = "Alef"
BODY_HALF_PT = 28  # 14pt — w:sz/w:szCs נמדדים בחצאי נקודה
HEADING_HALF_PT = {1: 40, 2: 34, 3: 30}  # 20 / 17 / 15 נקודות — נשארות גדולות מהגוף

# URL עם סוגריים מקוננים ברמה אחת: (he.wikipedia.org/wiki/ניסוי_(מדע)) שורד
_URL_INNER = r"(?:[^()\s]|\([^()\s]*\))+"
# (\*\*)? ... (?(1)\*\*) - קישור עטוף בהדגשה: **[טקסט](url)**
_LINK_RE = re.compile(r"(\*\*)?\[([^\]]+)\]\((https?://" + _URL_INNER + r")\)(?(1)\*\*)")

# תווים שאסורים ב-XML 1.0 (תווי בקרה) + BOM. RLM/LRM נשמרים - הם תווים חוקיים
# ולפעמים מכוונים בטקסט דו-כיווני.
_XML_BAD_RE = re.compile("[" + "".join(chr(c) for c in range(0x00, 0x09)) + chr(0x0B) + chr(0x0C)
                         + "".join(chr(c) for c in range(0x0E, 0x20))
                         + chr(0xFEFF) + chr(0xFFFE) + chr(0xFFFF) + "]")

_HEBREW_RE = re.compile(r"[֐-׿]")

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS_HEAD = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering" Target="numbering.xml"/>"""
DOC_RELS_TAIL = "</Relationships>"
HYPERLINK_TYPE = ("http://schemas.openxmlformats.org/officeDocument/2006/"
                  "relationships/hyperlink")

# רשימות: numId 1 = בולטים. כל רשימה ממוספרת מקבלת numId משלה (2, 3, ...) עם
# startOverride, כדי שהמספור יתחיל מחדש בכל רשימה ולא ימשיך מהרשימה הקודמת.
NUMBERING_HEAD = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:numbering xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
    '<w:abstractNum w:abstractNumId="1">'
    '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/>'
    '<w:lvlText w:val="•"/><w:lvlJc w:val="right"/>'
    '<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl>'
    '</w:abstractNum>'
    '<w:abstractNum w:abstractNumId="2">'
    '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
    '<w:lvlText w:val="%1."/><w:lvlJc w:val="right"/>'
    '<w:pPr><w:ind w:left="720" w:hanging="360"/></w:pPr></w:lvl>'
    '</w:abstractNum>'
    '<w:num w:numId="1"><w:abstractNumId w:val="1"/></w:num>'
)

# numId -> מספר ההתחלה, לכל רשימה ממוספרת במסמך (נאסף בזמן הבנייה)
_NUM_LISTS: list[int] = []


def numbering_xml() -> str:
    nums = []
    for i, start in enumerate(_NUM_LISTS, 2):
        nums.append(f'<w:num w:numId="{i}"><w:abstractNumId w:val="2"/>'
                    f'<w:lvlOverride w:ilvl="0"><w:startOverride w:val="{start}"/>'
                    '</w:lvlOverride></w:num>')
    return NUMBERING_HEAD + "".join(nums) + "</w:numbering>"

# sectPr מינימלי: A4 עם שוליים סטנדרטיים — בלעדיו יש ממירים שמתלוננים
SECT_PR = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
           '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
           'w:header="720" w:footer="720" w:gutter="0"/>'
           '<w:bidi/></w:sectPr>')

# הקישורים נאספים תוך כדי בניית הפסקאות, כי כל אחד צריך rId משלו ב-rels.
_LINKS: list[str] = []


def _link_rid(url: str) -> str:
    """מחזיר rId לקישור, ומוסיף אותו לרשימה אם הוא חדש."""
    if url not in _LINKS:
        _LINKS.append(url)
    return f"rIdL{_LINKS.index(url) + 1}"


def doc_rels_xml() -> str:
    rels = [DOC_RELS_HEAD]
    for i, url in enumerate(_LINKS, 1):
        rels.append(f'<Relationship Id="rIdL{i}" Type="{HYPERLINK_TYPE}" '
                    f'Target="{escape(url, {chr(34): "&quot;"})}" TargetMode="External"/>')
    rels.append(DOC_RELS_TAIL)
    return "".join(rels)


def _rfonts() -> str:
    """ascii/hAnsi ללטינית, cs לעברית (complex script), eastAsia להשלמה."""
    return (f'<w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" '
            f'w:cs="{FONT}" w:eastAsia="{FONT}"/>')


def _sizes(half_pt: int) -> str:
    """w:sz לטקסט רגיל, w:szCs לטקסט מורכב — העברית נשלטת ע\"י szCs."""
    return f'<w:sz w:val="{half_pt}"/><w:szCs w:val="{half_pt}"/>'


def styles_xml() -> str:
    heads = []
    for lvl, half in HEADING_HALF_PT.items():
        heads.append(
            f'<w:style w:type="paragraph" w:styleId="Heading{lvl}">'
            f'<w:name w:val="heading {lvl}"/><w:basedOn w:val="Normal"/>'
            f'<w:pPr><w:bidi/><w:outlineLvl w:val="{lvl - 1}"/></w:pPr>'
            f'<w:rPr>{_rfonts()}<w:b/><w:bCs/>{_sizes(half)}</w:rPr></w:style>'
        )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        '<w:docDefaults><w:rPrDefault><w:rPr>'
        f'{_rfonts()}{_sizes(BODY_HALF_PT)}'
        '</w:rPr></w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:bidi/></w:pPr></w:pPrDefault></w:docDefaults>'
        '<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        '<w:name w:val="Normal"/><w:pPr><w:bidi/></w:pPr>'
        f'<w:rPr>{_rfonts()}{_sizes(BODY_HALF_PT)}</w:rPr></w:style>'
        + "".join(heads) +
        '</w:styles>'
    )


def _run(body: str, half_pt: int, bold: bool, link: bool) -> str:
    """run בודד. `w:rtl` רק אם יש בו עברית - run לטיני/מספרי טהור נשאר LTR,
    אחרת מספרים וקיצורים לועזיים מתהפכים בתצוגה."""
    if not body:
        return ""
    rtl = "<w:rtl/>" if _HEBREW_RE.search(body) else ""
    # הפונט והגודל חוזרים גם ברמת ה-run: הממיר של Google Docs לא תמיד
    # יורש docDefaults, ובלי cs/szCs העברית נופלת לברירת המחדל.
    rpr = ("<w:rPr>" + _rfonts() + ("<w:b/><w:bCs/>" if bold else "")
           + ('<w:color w:val="1155CC"/><w:u w:val="single"/>' if link else "")
           + _sizes(half_pt) + rtl + "</w:rPr>")
    return f'<w:r>{rpr}<w:t xml:space="preserve">{escape(body)}</w:t></w:r>'


def _plain_runs(text: str, half_pt: int, link: bool = False, bold: bool = False) -> str:
    """runs מטקסט עם **מודגש** (זוגות סגורים בתוך הקטע). bold=True = כל הקטע מודגש
    (כותרת, או קישור שעטוף ב-**). ** בלי זוג נשאר כטקסט."""
    out = []
    for part in re.split(r"(\*\*[^*]+\*\*)", text):
        if not part:
            continue
        inner = part.startswith("**") and part.endswith("**") and len(part) > 4
        out.append(_run(part[2:-2] if inner else part, half_pt, bold or inner, link))
    return "".join(out)


def _segments(line: str) -> list:
    """מפרק שורה ל-[(text, bold, url)]: קישורים ([טקסט](url), **[טקסט](url)**,
    [**טקסט**](url)) והדגשה שמכסה גם קישורים ("**לפני [קישור](u) אחרי**").

    מצב ההדגשה עובר בין קטעי הטקסט שמסביב לקישורים, כך ש-** לא נשאר כטקסט
    מילולי בפלט. ** אי-זוגי בשורה - האחרון נשאר כטקסט (לא נבלע בשקט).
    התוכן הטקסטואלי זהה לשורה בלי סימני המארקדאון - העוגנים נשארים תקפים.
    """
    tokens, pos = [], 0
    for m in _LINK_RE.finditer(line):
        if m.start() > pos:
            tokens.append(("text", line[pos:m.start()], None, False))
        tokens.append(("link", m.group(2), m.group(3), bool(m.group(1))))
        pos = m.end()
    if pos < len(line):
        tokens.append(("text", line[pos:], None, False))

    toggles = sum(t[1].count("**") for t in tokens if t[0] == "text")
    literal_last = toggles % 2 == 1
    seen, bold, segs = 0, False, []
    for kind, txt, url, wrapped in tokens:
        if kind == "link":
            label = txt
            lb = bold or wrapped
            if label.startswith("**") and label.endswith("**") and len(label) > 4:
                label, lb = label[2:-2], True
            segs.append((label.replace("**", ""), lb, url))
            continue
        parts = txt.split("**")
        for i, part in enumerate(parts):
            if i > 0:
                seen += 1
                if literal_last and seen == toggles:
                    segs.append(("**", bold, None))
                else:
                    bold = not bold
            if part:
                segs.append((part, bold, None))
    return segs


def runs_from_line(line: str, half_pt: int = BODY_HALF_PT, bold: bool = False) -> str:
    """[טקסט](url) הופך ל-w:hyperlink אמיתי - הכתובת לא מוצגת בגוף הטקסט.

    לפני התיקון (02.08.2026) הקישורים רונדרו כ"טקסט (url)", והמסמך שנמסר
    לכתב/ת היה זרוע כתובות גולמיות. עכשיו הקישור יושב על הטקסט עצמו,
    וההמרה ל-Google Docs משמרת אותו כקישור חי. ה-regex מתיר סוגריים
    מקוננים ברמה אחת בתוך ה-URL (10.08.2026) - קישורי ויקיפדיה שורדים.
    bold=True (כותרות): כל השורה מודגשת דרך דגל, לא דרך עטיפה ב-** - עטיפה
    שברה כותרת עם קישור והשאירה ** מילולי בפלט.
    """
    out = []
    for txt, b, url in _segments(line):
        if url:
            out.append(f'<w:hyperlink r:id="{_link_rid(url)}">'
                       + _run(txt, half_pt, bold or b, True) + "</w:hyperlink>")
        else:
            out.append(_run(txt, half_pt, bold or b, False))
    return "".join(out)


def build(draft_path: str, out_path: str) -> int:
    _LINKS.clear()
    _NUM_LISTS.clear()
    with open(draft_path, encoding="utf-8") as f:
        text = f.read()
    text = _XML_BAD_RE.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    paras = []
    prev_num = False  # האם הפסקה הקודמת שנפלטה הייתה פריט ממוספר
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(#{1,3})\s", line)
        level = len(m.group(1)) if m else 0
        line = re.sub(r"^#{1,3}\s+", "", line)
        num_id = 0  # 1 = בולט, 2 = ממוספר
        if not level:
            if re.match(r"^[-*+]\s+", line):
                num_id, line = 1, re.sub(r"^[-*+]\s+", "", line)
            elif re.match(r"^\d+[.)]\s+", line):
                n = int(re.match(r"^(\d+)", line).group(1))
                # רשימה חדשה: הפסקה הקודמת לא הייתה ממוספרת, או שהפריט הוא 1
                if not prev_num or n == 1:
                    _NUM_LISTS.append(n)
                num_id, line = 1 + len(_NUM_LISTS), re.sub(r"^\d+[.)]\s+", "", line)
        if level:
            half = HEADING_HALF_PT[level]
            ppr = f'<w:pPr><w:pStyle w:val="Heading{level}"/><w:bidi/></w:pPr>'
        elif num_id:
            half = BODY_HALF_PT
            ppr = (f'<w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num_id}"/>'
                   '</w:numPr><w:bidi/></w:pPr>')
        else:
            half = BODY_HALF_PT
            ppr = "<w:pPr><w:bidi/></w:pPr>"
        prev_num = num_id >= 2
        paras.append(f"<w:p>{ppr}{runs_from_line(line, half, bold=bool(level))}</w:p>")
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<w:body>{''.join(paras)}{SECT_PR}</w:body></w:document>"
    )
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/_rels/document.xml.rels", doc_rels_xml())
        z.writestr("word/styles.xml", styles_xml())
        z.writestr("word/numbering.xml", numbering_xml())
        z.writestr("word/document.xml", doc)
    return len(paras)


if __name__ == "__main__":
    n = build(sys.argv[1], sys.argv[2])
    print(f"OK {sys.argv[2]} ({n} פסקאות)")
