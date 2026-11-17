"""בדיקות offline ל-lint_hebrew.py."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import lint_hebrew as L  # noqa: E402

TMP = os.environ.get("TMPDIR")


def kinds(text, **kw):
    v, w = L.lint_text(text, **kw)
    return [x["type"] for x in v if not x["in_quote"]], v, w


class CommaBeforeShe(unittest.TestCase):
    def test_flags_completive_after_saying_verb(self):
        k, _, _ = kinds("צה״ל חשד, שיש חטופים במבנה.")
        self.assertIn("comma_before_she", k)
        k, _, _ = kinds("הוא אמר לי אתמול, שהמצב חמור.")
        self.assertIn("comma_before_she", k)

    def test_no_false_positives(self):
        for t in ("בירושלים, שני ילדים נפצעו.",
                  "החברה, שהוקמה ב-2010, זכתה במכרז.",
                  "הוא נפגש עם השר, שר האוצר.",
                  "ביום ראשון, שבוע לפני הבחירות.",
                  "האיש, שלום כהן, הגיע."):
            k, _, _ = kinds(t)
            self.assertNotIn("comma_before_she", k, t)


class Quotes(unittest.TestCase):
    def test_pairing_per_paragraph(self):
        # מרכאה יתומה בפסקה 1 לא משבשת את הציטוט בפסקה 2
        text = 'הוא כתב 5" ואז הלך.\n\nהיא אמרה: "זה מדהים!" וזהו.'
        k, v, _ = kinds(text)
        excl = [x for x in v if x["type"] == "exclamation"]
        self.assertTrue(excl and excl[0]["in_quote"])

    def test_quote_across_single_newline(self):
        text = 'היא אמרה: "זה\nמדהים!" וזהו.'
        _, v, _ = kinds(text)
        self.assertTrue([x for x in v if x["type"] == "exclamation"][0]["in_quote"])

    def test_split_fragment_with_draft(self):
        draft_quotes = L.quote_texts('השר אמר: "המצב חמור מאוד! אין מה לעשות" ויצא.')
        # newText מכיל שבר ציטוט בלי המרכאות
        k, v, _ = kinds("חמור מאוד! אין", draft_quotes=draft_quotes)
        self.assertNotIn("exclamation", k)
        self.assertTrue(v[0]["in_quote"])
        k, _, _ = kinds("חמור מאוד! אין")
        self.assertIn("exclamation", k)

    def test_em_dash_always_enforced(self):
        k, _, _ = kinds('היא אמרה: "זה ' + chr(0x2014) + ' זה"')
        self.assertIn("em_dash", k)


class Urls(unittest.TestCase):
    def test_url_masked(self):
        k, _, _ = kinds("ראו https://he.wikipedia.org/wiki/%D7%A9%D7%9C%D7%95%D7%9D כאן")
        self.assertEqual(k, [])


class Narration(unittest.TestCase):
    def test_warning_not_violation(self):
        k, v, w = kinds("בדקנו את הנתונים. הטופס לא מפרט את הסכום.")
        self.assertEqual(k, [])
        self.assertEqual(len(w), 2)
        self.assertTrue(all(x["type"] == "research_narration" for x in w))

    def test_protocol_repeated(self):
        _, _, w = kinds("לפי הפרוטוקול א. ")
        self.assertEqual(w, [])
        _, _, w = kinds("לפי הפרוטוקול א. לפי הפרוטוקול ב.")
        self.assertEqual(len(w), 1)

    def test_protocol_repeated_across_records(self):
        edits = [{"type": "insertion", "anchor": "a", "newText": "לפי הפרוטוקול א"},
                 {"type": "insertion", "anchor": "b", "newText": "לפי הפרוטוקול ב"}]
        code, out = self.run_cli("edits.json", json.dumps(edits, ensure_ascii=False))
        self.assertEqual(out["warnings"]["count"], 1)
        self.assertEqual(code, 0)

    def test_quoted_not_flagged(self):
        _, _, w = kinds('הוא אמר: "בדקנו הכל"')
        self.assertEqual(w, [])

    def run_cli(self, name, content, *args):
        with tempfile.TemporaryDirectory(dir=TMP) as d:
            p = Path(d) / name
            p.write_text(content, encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPTS / "lint_hebrew.py"), str(p), *args],
                               capture_output=True, text=True)
        return r.returncode, json.loads(r.stdout)

    def test_cli_exit_code_and_report_default_off(self):
        code, out = self.run_cli("edited.txt", "בדקנו את זה.")
        self.assertEqual(code, 0)
        self.assertEqual(out["warnings"]["count"], 1)
        code, out = self.run_cli("report.txt", "בדקנו את זה.")
        self.assertEqual(out["warnings"]["count"], 0)
        code, out = self.run_cli("report.txt", "בדקנו את זה.", "--narration")
        self.assertEqual(out["warnings"]["count"], 1)

    def test_cli_json_aliases_and_draft(self):
        edits = [{"type": "insertion", "anchor": "x", "text": "זה נהדר!"},
                 {"type": "replacement", "originalText": "מאוד חמור",
                  "newText": "חמור מאוד!"}]
        with tempfile.TemporaryDirectory(dir=TMP) as d:
            ep = Path(d) / "edits.json"
            ep.write_text(json.dumps(edits, ensure_ascii=False), encoding="utf-8")
            dp = Path(d) / "draft.txt"
            dp.write_text('השר אמר: "המצב מאוד חמור" ויצא.', encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPTS / "lint_hebrew.py"), str(ep),
                                "--draft", str(dp)], capture_output=True, text=True)
        out = json.loads(r.stdout)
        self.assertEqual(r.returncode, 1)  # alias "text" נבדק
        self.assertEqual(out["count"], 1)
        self.assertEqual(out["violations"][0]["source"], "[0].text")
        self.assertEqual(out["in_quote_review"]["count"], 1)  # עוגן בתוך ציטוט בטיוטה


if __name__ == "__main__":
    unittest.main()


class TestOneLineParagraphs(unittest.TestCase):
    """רגרסיה: טיוטה שבה כל פסקה היא שורה אחת, בלי שורות ריקות (סלברייט 17.11.2026)."""

    def test_narration_outside_quotes_across_lines(self):
        import lint_hebrew as lh
        text = ('הנימוק נכנס בפסקה אחת. "למשטרה התקשרות בפטור". תום סנ"צ אישר.\n'
                'אילו יחידות יוקמו - הטופס לא מפרט.\n'
                'בהמשך נאמר "על הבקשה" בלבד.\n')
        _, warnings = lh.lint_text(text)
        self.assertTrue(any(w["match"] == "הטופס לא מפרט" for w in warnings))
