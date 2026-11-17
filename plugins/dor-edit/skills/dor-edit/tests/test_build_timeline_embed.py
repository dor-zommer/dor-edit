"""בדיקות offline ל-hamakom-source-to-item/scripts/build_timeline_embed.py."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = (Path(__file__).resolve().parents[2] / "hamakom-source-to-item" / "scripts"
          / "build_timeline_embed.py")
sys.path.insert(0, str(SCRIPT.parent))
import build_timeline_embed as T  # noqa: E402

TMP = os.environ.get("TMPDIR")


class Escaping(unittest.TestCase):
    def test_event_fields_escaped(self):
        events = [
            {"date": "1.1.2026", "label": "<b>תווית</b>", "title": "A & B",
             "body": "<script>alert(1)</script> גוף"},
            {"date": "2.1.2026", "label": "שנייה", "title": "כותרת", "body": "x < y"},
        ]
        html = T.build(events, "מקור", "#cc785c", "#8a4a30", "hmtl", "רמז")
        self.assertNotIn("<script>", html)
        self.assertNotIn("<b>תווית", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("A &amp; B", html)
        self.assertIn("x &lt; y", html)

    def test_cli_example_and_ascii_quote_rejected(self):
        example = SCRIPT.parents[1] / "assets" / "timeline-events-example.json"
        with tempfile.TemporaryDirectory(dir=TMP) as d:
            out = Path(d) / "e.html"
            r = subprocess.run([sys.executable, str(SCRIPT), str(example), "-o", str(out)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("hmtl-card", out.read_text(encoding="utf-8"))
            bad = Path(d) / "bad.json"
            bad.write_text(json.dumps([{"date": "1", "label": "a", "title": 'x"y', "body": "b"},
                                       {"date": "2", "label": "a", "title": "t", "body": "b"}]),
                           encoding="utf-8")
            r = subprocess.run([sys.executable, str(SCRIPT), str(bad), "-o", str(out)],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
