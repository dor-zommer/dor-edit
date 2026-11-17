"""בדיקות offline ל-flash90_search.py (HTML סינתטי, בלי רשת)."""
import http.client
import sys
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import flash90_search as F  # noqa: E402

PAGE = """
<div class="item"><img alt="כיתוב ראשון ארוך" src="https://cdn.x/thumbs/Image111.jpg?t=1">
<p class="file_name">F111.jpg</p><p class="caption">כיתוב של 111</p></div>
<div class="item"><img src="https://cdn.x/thumbs/Image222.jpg?t=1">
<p class="file_name">F222.jpg</p></div>
<div class="item"><img alt="alt של 333" src="https://cdn.x/thumbs/Image333.jpg?t=1">
<a href="https://cdn.x/big/Image333.jpg">big</a>
<p class="file_name">F333.jpg</p><p class="caption">כיתוב של 333</p></div>
"""


class Parse(unittest.TestCase):
    def test_no_caption_bleed_and_alt_before_src(self):
        imgs = F.parse_results(PAGE)
        self.assertEqual([i["image_id"] for i in imgs], ["Image111", "Image222", "Image333"])
        self.assertEqual(imgs[0]["caption"], "כיתוב של 111")
        self.assertEqual(imgs[1]["file_name"], "F222.jpg")
        self.assertEqual(imgs[1]["caption"], "")   # לא "כיתוב של 333" / alt של הבא
        self.assertEqual(imgs[2]["file_name"], "F333.jpg")

    def test_alt_fallback_inside_own_tag(self):
        imgs = F.parse_results('<img alt="תיאור התמונה" src="https://c/Image9.jpg">')
        self.assertEqual(imgs[0]["caption"], "תיאור התמונה")


class Fetch(unittest.TestCase):
    def test_incomplete_read_retried(self):
        calls = []

        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                if len(calls) < 2:
                    raise http.client.IncompleteRead(b"<ht")
                return PAGE.encode()

        def fake(req, context=None, timeout=None):
            calls.append(req.get_method())
            return Resp()

        with mock.patch.object(urllib.request, "urlopen", fake), \
                mock.patch.object(F.time, "sleep", lambda s: None):
            self.assertIn("Image111", F._fetch("https://www.flash90.net/x"))
        self.assertEqual(calls, ["GET", "GET"])

    def test_paging_stops_on_no_new(self):
        pages = []

        def fetch(url):
            pages.append(url)
            return PAGE
        with mock.patch.object(F, "_fetch", fetch):
            r = F.search("q", 10)
        self.assertEqual(r["count"], 3)
        self.assertEqual(len(pages), 2)  # עמוד 2 החזיר אותן תמונות - עצירה
        self.assertIn("/en/2/", pages[1])
        with mock.patch.object(F, "_fetch", fetch):
            self.assertEqual(F.search("q", 2)["count"], 2)


if __name__ == "__main__":
    unittest.main()
