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
_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://" + _URL_INNER + r")\)")

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

# רשימות: numId 1 = בולטים, numId 2 = מספור עשרוני
NUMBERING_XML = (
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
    '<w:num w:numId="2"><w:abstractNumId w:val="2"/></w:num>'
    '</w:numbering>'
)

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


def _plain_runs(text: str, half_pt: int, link: bool = False) -> str:
    """בונה runs מטקסט, עם טיפול ב-**מודגש**. link=True מוסיף עיצוב קישור.

    `w:rtl` מוחל רק על runs שמכילים תווים עבריים — run לטיני/מספרי טהור
    נשאר LTR, אחרת מספרים וקיצורים לועזיים מתהפכים בתצוגה.
    """
    out = []
    for part in re.split(r"(\*\*[^*]+\*\*)", text):
        if not part:
            continue
        bold = part.startswith("**") and part.endswith("**")
        body = part[2:-2] if bold else part
        rtl = "<w:rtl/>" if _HEBREW_RE.search(body) else ""
        # הפונט והגודל חוזרים גם ברמת ה-run: הממיר של Google Docs לא תמיד
        # יורש docDefaults, ובלי cs/szCs העברית נופלת לברירת המחדל.
        rpr = ("<w:rPr>" + _rfonts() + ("<w:b/><w:bCs/>" if bold else "")
               + ('<w:color w:val="1155CC"/><w:u w:val="single"/>' if link else "")
               + _sizes(half_pt) + rtl + "</w:rPr>")
        out.append(f'<w:r>{rpr}<w:t xml:space="preserve">{escape(body)}</w:t></w:r>')
    return "".join(out)


def runs_from_line(line: str, half_pt: int = BODY_HALF_PT) -> str:
    """[טקסט](url) הופך ל-w:hyperlink אמיתי — הכתובת לא מוצגת בגוף הטקסט.

    לפני התיקון (02.08.2026) הקישורים רונדרו כ"טקסט (url)", והמסמך שנמסר
    לכתב/ת היה זרוע כתובות גולמיות. עכשיו הקישור יושב על הטקסט עצמו,
    וההמרה ל-Google Docs משמרת אותו כקישור חי. ה-regex מתיר סוגריים
    מקוננים ברמה אחת בתוך ה-URL (10.08.2026) — קישורי ויקיפדיה שורדים.
    """
    out, pos = [], 0
    for m in _LINK_RE.finditer(line):
        if m.start() > pos:
            out.append(_plain_runs(line[pos:m.start()], half_pt))
        rid = _link_rid(m.group(2))
        out.append(f'<w:hyperlink r:id="{rid}">'
                   + _plain_runs(m.group(1), half_pt, link=True)
                   + "</w:hyperlink>")
        pos = m.end()
    if pos < len(line):
        out.append(_plain_runs(line[pos:], half_pt))
    return "".join(out)


def build(draft_path: str, out_path: str) -> int:
    _LINKS.clear()
    text = open(draft_path, encoding="utf-8").read()
    paras = []
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
                num_id, line = 2, re.sub(r"^\d+[.)]\s+", "", line)
        if level:
            half = HEADING_HALF_PT[level]
            ppr = f'<w:pPr><w:pStyle w:val="Heading{level}"/><w:bidi/></w:pPr>'
            if not line.startswith("**"):
                line = f"**{line}**"
        elif num_id:
            half = BODY_HALF_PT
            ppr = (f'<w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="{num_id}"/>'
                   '</w:numPr><w:bidi/></w:pPr>')
        else:
            half = BODY_HALF_PT
            ppr = "<w:pPr><w:bidi/></w:pPr>"
        paras.append(f"<w:p>{ppr}{runs_from_line(line, half)}</w:p>")
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
        z.writestr("word/numbering.xml", NUMBERING_XML)
        z.writestr("word/document.xml", doc)
    return len(paras)


if __name__ == "__main__":
    n = build(sys.argv[1], sys.argv[2])
    print(f"OK {sys.argv[2]} ({n} פסקאות)")
