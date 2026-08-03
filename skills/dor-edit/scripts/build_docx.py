#!/usr/bin/env python3
"""בונה docx בסיס מטקסט טיוטה (למשל ייצוא של Google Doc).

כל שורה לא-ריקה הופכת לפסקה RTL. תחביר מרקדאון בסיסי:
- **מודגש** נשמר כ-run מודגש
- [טקסט](קישור) הופך ל"טקסט (קישור)" גלוי
- # / ## / ### מקבלות סגנון כותרת (Alef, גדול מ-14, מודגש)

מפרט טיפוגרפי (דרישת דור): כל המסמכים בפונט **Alef**, גוף בגודל **14**.
הפונט והגודל מוגדרים ברמת הסגנון (docDefaults + Normal) ולא ברמת ריצה בודדת,
כדי שיחולו על כל הפסקאות. לעברית (complex script) חובה גם `w:rFonts/@w:cs`
וגם `w:szCs` — בלעדיהם הטקסט העברי נשאר בפונט ובגודל ברירת המחדל.

שימוש: python3 build_docx.py <draft.txt> <out.docx>
"""
import re, sys, zipfile
from xml.sax.saxutils import escape

FONT = "Alef"
BODY_HALF_PT = 28  # 14pt — w:sz/w:szCs נמדדים בחצאי נקודה
HEADING_HALF_PT = {1: 40, 2: 34, 3: 30}  # 20 / 17 / 15 נקודות — נשארות גדולות מהגוף

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

DOC_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""


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


def runs_from_line(line: str, half_pt: int = BODY_HALF_PT) -> str:
    line = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", line)
    out = []
    for part in re.split(r"(\*\*[^*]+\*\*)", line):
        if not part:
            continue
        bold = part.startswith("**") and part.endswith("**")
        text = part[2:-2] if bold else part
        # הפונט והגודל חוזרים גם ברמת ה-run: הממיר של Google Docs לא תמיד
        # יורש docDefaults, ובלי cs/szCs העברית נופלת לברירת המחדל.
        rpr = ("<w:rPr>" + _rfonts() + ("<w:b/><w:bCs/>" if bold else "")
               + _sizes(half_pt) + "<w:rtl/></w:rPr>")
        out.append(f'<w:r>{rpr}<w:t xml:space="preserve">{escape(text)}</w:t></w:r>')
    return "".join(out)


def build(draft_path: str, out_path: str) -> int:
    text = open(draft_path, encoding="utf-8").read()
    paras = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        m = re.match(r"^(#{1,3})\s", line)
        level = len(m.group(1)) if m else 0
        line = re.sub(r"^#{1,3}\s+", "", line)
        if level:
            half = HEADING_HALF_PT[level]
            ppr = f'<w:pPr><w:pStyle w:val="Heading{level}"/><w:bidi/></w:pPr>'
            if not line.startswith("**"):
                line = f"**{line}**"
        else:
            half = BODY_HALF_PT
            ppr = "<w:pPr><w:bidi/></w:pPr>"
        paras.append(f"<w:p>{ppr}{runs_from_line(line, half)}</w:p>")
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body>{''.join(paras)}</w:body></w:document>"
    )
    with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/_rels/document.xml.rels", DOC_RELS)
        z.writestr("word/styles.xml", styles_xml())
        z.writestr("word/document.xml", doc)
    return len(paras)


if __name__ == "__main__":
    n = build(sys.argv[1], sys.argv[2])
    print(f"OK {sys.argv[2]} ({n} פסקאות)")
