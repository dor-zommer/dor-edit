"""בדיקות offline ל-build_docx.py."""
import os
import re
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.dom import minidom

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import build_docx as B  # noqa: E402

TMP = os.environ.get("TMPDIR")


def build(text):
    with tempfile.TemporaryDirectory(dir=TMP) as d:
        src, out = Path(d) / "draft.txt", Path(d) / "out.docx"
        src.write_text(text, encoding="utf-8")
        B.build(str(src), str(out))
        with zipfile.ZipFile(out) as z:
            return {n: z.read(n).decode("utf-8") for n in z.namelist()}


def visible_text(doc_xml):
    return "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", doc_xml))


class Headings(unittest.TestCase):
    def test_heading_with_link_has_no_literal_stars(self):
        f = build("## כותרת עם [קישור](https://example.org/a) בסוף\n"
                  "# **כבר מודגש**\n"
                  "גוף **[מודגש-מקושר](https://example.org/b)** ו-**לפני [ק](https://e.org) אחרי**")
        doc = f["word/document.xml"]
        self.assertNotIn("**", visible_text(doc))
        self.assertIn("w:hyperlink", doc)
        self.assertEqual(visible_text(doc),
                         "כותרת עם קישור בסוףכבר מודגשגוף מודגש-מקושר ו-לפני ק אחרי")
        minidom.parseString(doc)

    def test_heading_runs_are_bold(self):
        doc = build("## כותרת [קישור](https://e.org)")["word/document.xml"]
        runs = re.findall(r"<w:r>(.*?)</w:r>", doc)
        self.assertTrue(runs and all("<w:b/>" in r for r in runs))

    def test_unpaired_stars_stay_literal(self):
        doc = build("מחיר 5**2 נשאר")["word/document.xml"]
        self.assertEqual(visible_text(doc), "מחיר 5**2 נשאר")


class ControlChars(unittest.TestCase):
    def test_bom_and_control_chars_stripped(self):
        text = chr(0xFEFF) + "שורה" + chr(0x01) + chr(0x0B) + " עם" + chr(0x200F) + " RLM\r\nשנייה"
        f = build(text)
        doc = f["word/document.xml"]
        minidom.parseString(doc)  # XML תקין
        self.assertNotIn(chr(0xFEFF), doc)
        self.assertIn(chr(0x200F), doc)  # RLM נשמר
        self.assertEqual(visible_text(doc), "שורה עם" + chr(0x200F) + " RLMשנייה")


class Numbering(unittest.TestCase):
    def test_restart_per_list(self):
        f = build("1. א\n2. ב\nפסקה\n1. ג\n2. ד\n\n3. ה\n- בולט\n1. ו")
        doc, num = f["word/document.xml"], f["word/numbering.xml"]
        ids = re.findall(r'<w:numId w:val="(\d+)"/>', doc)
        self.assertEqual(ids, ["2", "2", "3", "3", "3", "1", "4"])
        self.assertEqual(len(re.findall(r"<w:startOverride", num)), 3)
        minidom.parseString(num)


if __name__ == "__main__":
    unittest.main()
