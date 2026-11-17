"""בדיקות offline ל-upload_to_gdocs.py - בלי רשת ובלי גוגל.

הרצה: python3 -m unittest discover -s tests -v   (מתוך skills/dor-edit)
"""
import http.client
import json
import os
import sys
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import upload_to_gdocs as U  # noqa: E402

TID = "t.0"


def make_doc(text, links=(), rev="r1"):
    """מסמך Docs מינימלי: פסקה אחת, runs לפי links=[(start,end,url)] באינדקסים פייתוניים."""
    cuts = sorted({0, len(text), *[x for s, e, _ in links for x in (s, e)]})
    els = []
    for a, b in zip(cuts, cuts[1:]):
        url = next((u for s, e, u in links if s <= a and b <= e), None)
        tr = {"content": text[a:b]}
        if url:
            tr["textStyle"] = {"link": {"url": url}}
        els.append({"startIndex": a + 1, "endIndex": b + 1, "textRun": tr})
    return {"revisionId": rev, "tabs": [{
        "tabProperties": {"tabId": TID, "title": "main"},
        "documentTab": {"body": {"content": [{"paragraph": {"elements": els}}]}}}]}


def simulate(text, reqs):
    """מחיל בקשות בסמנטיקת EDIT על מחרוזת (אינדקס Docs = אינדקס פייתון + 1).
    מחזיר (טקסט סופי, [(טקסט מקושר ברגע ההחלה, url)])."""
    links = []
    for r in reqs:
        if "insertText" in r:
            i = r["insertText"]["location"]["index"] - 1
            text = text[:i] + r["insertText"]["text"] + text[i:]
        elif "deleteContentRange" in r:
            rg = r["deleteContentRange"]["range"]
            text = text[:rg["startIndex"] - 1] + text[rg["endIndex"] - 1:]
        elif "updateTextStyle" in r:
            rg = r["updateTextStyle"]["range"]
            links.append((text[rg["startIndex"] - 1:rg["endIndex"] - 1],
                          r["updateTextStyle"]["textStyle"]["link"]["url"]))
    return text, links


def plan(text, edits):
    plain, mapping = U._tab_plaintext(make_doc(text)["tabs"][0])
    resolved, skipped = U._resolve_anchors(edits, plain)
    return U.build_suggest_requests(resolved, plain, mapping, TID), resolved, skipped


class SortAndRequests(unittest.TestCase):
    def test_two_insertions_same_anchor_keep_list_order(self):
        reqs, _, sk = plan("אלף בית גימל", [
            {"type": "insertion", "anchor": "בית", "newText": " A"},
            {"type": "insertion", "anchor": "בית", "newText": " B", "occurrence": 1},
        ])
        self.assertEqual(sk, [])
        self.assertEqual(simulate("אלף בית גימל", reqs)[0], "אלף בית A B גימל")

    def test_replacement_and_insertion_at_same_start(self):
        # הוספה אחרי "אלף " (נקודה = תחילת "בית") + החלפת "בית" שמתחילה באותה נקודה
        text = "אלף בית גימל"
        reqs, _, sk = plan(text, [
            {"type": "insertion", "anchor": "אלף ", "newText": "X "},
            {"type": "replacement", "originalText": "בית", "newText": "דלת"},
        ])
        self.assertEqual(sk, [])
        self.assertEqual(simulate(text, reqs)[0], "אלף X דלת גימל")
        # אותו דבר כשסדר הרשימה הפוך
        reqs2, _, _ = plan(text, [
            {"type": "replacement", "originalText": "בית", "newText": "דלת"},
            {"type": "insertion", "anchor": "אלף ", "newText": "X "},
        ])
        self.assertEqual(simulate(text, reqs2)[0], "אלף X דלת גימל")

    def test_link_on_inserted_text_and_existing_text(self):
        text = "ראו את הדוח ואת הנספח."
        reqs, _, sk = plan(text, [
            {"type": "insertion", "anchor": "הדוח", "newText": " המלא",
             "link": "https://example.org/r"},
            {"originalText": "הנספח", "link": {"url": "https://example.org/a"}},
            {"type": "insertion", "anchor": "ראו", "newText": " נא",
             "link": "https://example.org/n"},
        ])
        self.assertEqual(sk, [])
        final, links = simulate(text, reqs)
        self.assertEqual(final, "ראו נא את הדוח המלא ואת הנספח.")
        self.assertIn((" המלא", "https://example.org/r"), links)
        self.assertIn(("הנספח", "https://example.org/a"), links)
        self.assertIn((" נא", "https://example.org/n"), links)
        # עיצוב הקישור בא מיד אחרי ההכנסה שלו
        i = next(k for k, r in enumerate(reqs) if r.get("insertText", {}).get("text") == " המלא")
        self.assertIn("updateTextStyle", reqs[i + 1])


class Classification(unittest.TestCase):
    def k(self, rec):
        return U._norm_edit(rec)["type"]

    def test_deletion_with_empty_newtext(self):
        self.assertEqual(self.k({"originalText": "מילה", "newText": ""}), "deletion")
        self.assertEqual(self.k({"type": "replacement", "originalText": "מ", "newText": ""}),
                         "deletion")
        self.assertEqual(self.k({"type": "delete", "originalText": "מ"}), "deletion")

    def test_link_only_is_not_deletion(self):
        self.assertEqual(self.k({"originalText": "מ", "link": "https://x.org"}), "link")

    def test_malformed_never_deletes(self):
        self.assertEqual(self.k({"originalText": "מ"}), "invalid")
        self.assertEqual(self.k({"type": "replacement", "originalText": "מ"}), "invalid")
        _, sk = U._resolve_anchors([{"originalText": "מ"}], "מ ב")
        self.assertEqual(sk[0]["reason"], "no_new_text")

    def test_untyped_anchor_is_insertion_not_replacement(self):
        self.assertEqual(self.k({"anchor": "מ", "newText": "x"}), "insertion")
        self.assertEqual(self.k({"originalText": "מ", "newText": "x"}), "replacement")

    def test_deletion_resolves_to_delete_request(self):
        text = "אלף בית גימל"
        reqs, _, sk = plan(text, [{"originalText": " בית", "newText": ""}])
        self.assertEqual(sk, [])
        self.assertEqual(simulate(text, reqs)[0], "אלף גימל")


class Verdict(unittest.TestCase):
    def setUp(self):
        self.text = "אלף בית גימל"
        _, self.resolved, _ = plan(self.text, [
            {"type": "replacement", "originalText": "בית", "newText": "דלת"}])
        self.checks = U.build_checks(self.resolved, self.text, self.text, self.text)

    def test_landed(self):
        v = U.content_verdict(self.checks, "אלף דלת גימל", self.text)
        self.assertEqual(v["status"], "landed")

    def test_overwrote(self):
        v = U.content_verdict(self.checks, "אלף דלת גימל", "אלף דלת גימל")
        self.assertEqual(v["status"], "overwrote")

    def test_duplicate(self):
        v = U.content_verdict(self.checks, "אלף דלתדלת גימל", self.text)
        self.assertEqual(v["status"], "duplicate")

    def test_not_landed(self):
        v = U.content_verdict(self.checks, self.text, self.text)
        self.assertEqual(v["status"], "not_landed")

    def test_existing_suggestion_touching_anchor_is_not_overwrote(self):
        # הצעה קיימת (" קיים") צמודה לעוגן: מופיעה ב-ACCEPTED לפני ואחרי - לא משנה הכרעה
        pre_acc = "אלף בית קיים גימל"
        checks = U.build_checks(self.resolved, self.text, pre_acc, self.text)
        v = U.content_verdict(checks, "אלף דלת קיים גימל", self.text)
        self.assertEqual(v["status"], "landed")


class NoRetryOnWrite(unittest.TestCase):
    def test_incomplete_read_post_not_retried(self):
        calls = []

        class Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                raise http.client.IncompleteRead(b"{")

        def fake(req, context=None, timeout=None):
            calls.append((req.get_method(), timeout))
            return Resp()

        with mock.patch.object(urllib.request, "urlopen", fake), \
                mock.patch.object(U.time, "sleep", lambda s: None):
            req = urllib.request.Request("https://x/y:batchUpdate", data=b"{}", method="POST")
            with self.assertRaises(U.WriteOutcomeUnknown):
                U._open(req)
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0], ("POST", 60))
            calls.clear()
            with self.assertRaises(http.client.IncompleteRead):
                U._open(urllib.request.Request("https://x/doc"))
            self.assertEqual(len(calls), 3)  # GET - כן retry


class SuggestFlow(unittest.TestCase):
    """suggest_edits מקצה לקצה עם גוגל מדומה."""

    TEXT = "אלף בית גימל"
    EDITS = [{"type": "replacement", "originalText": "בית", "newText": "דלת"}]

    def run_flow(self, server_applies, edits_dir, post_error=True):
        state = {"accepted": self.TEXT, "without": self.TEXT, "posts": 0}

        def batch_raw(doc_id, token, requests, write_control=None):
            state["posts"] += 1
            self.assertEqual(write_control["writeMode"], "SUGGEST")
            self.assertEqual(write_control["requiredRevisionId"], "r1")
            if server_applies:
                state["accepted"] = "אלף דלת גימל"
            if post_error:
                raise U.WriteOutcomeUnknown("IncompleteRead")
            return {"replies": []}

        def view(doc_id, token, mode):
            if mode == "PREVIEW_SUGGESTIONS_ACCEPTED":
                return make_doc(state["accepted"])
            if mode == "PREVIEW_WITHOUT_SUGGESTIONS":
                return make_doc(state["without"])
            return make_doc(self.TEXT)

        ep = Path(edits_dir) / "edits.json"
        ep.write_text(json.dumps(self.EDITS, ensure_ascii=False), encoding="utf-8")
        with mock.patch.object(U, "access_token", lambda a: "tok"), \
                mock.patch.object(U, "get_doc", lambda d, t: make_doc(self.TEXT)), \
                mock.patch.object(U, "get_doc_view", view), \
                mock.patch.object(U, "_batch_raw", batch_raw):
            r1 = U.suggest_edits("DOC", "acc", ep)
            r2 = U.suggest_edits("DOC", "acc", ep)
        ledger = json.loads(U._ledger_path(ep).read_text(encoding="utf-8"))
        return r1, r2, state, ledger

    def test_dropped_connection_but_landed_no_duplicate(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            r1, r2, state, ledger = self.run_flow(True, d)
        self.assertEqual(state["posts"], 1)        # לא נשלח שוב, גם לא בהרצה השנייה
        self.assertEqual(r1["status"], "landed")
        self.assertTrue(r1["clean"])
        self.assertTrue(r2["refused_resend"])
        self.assertEqual(list(ledger["entries"].values())[0]["status"], "confirmed")

    def test_dropped_connection_not_landed_resends_only_on_rerun(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            r1, r2, state, ledger = self.run_flow(False, d)
        self.assertEqual(r1["status"], "not_landed")
        self.assertFalse(r1["clean"])
        self.assertEqual(state["posts"], 2)        # הרצה 1 שלחה פעם אחת; הרצה 2 שלחה מחדש

    def test_overwrote_detected(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            ep = Path(d) / "edits.json"
            ep.write_text(json.dumps(self.EDITS, ensure_ascii=False), encoding="utf-8")
            st = {"t": self.TEXT}

            def batch_raw(*a, **k):
                st["t"] = "אלף דלת גימל"   # SUGGEST נבלע: כתיבה ישירה
                return {}
            with mock.patch.object(U, "access_token", lambda a: "tok"), \
                    mock.patch.object(U, "get_doc", lambda d, t: make_doc(self.TEXT)), \
                    mock.patch.object(U, "get_doc_view", lambda d, t, m: make_doc(st["t"])), \
                    mock.patch.object(U, "_batch_raw", batch_raw):
                r = U.suggest_edits("DOC", "acc", ep)
        self.assertTrue(r["overwrote"])
        self.assertFalse(r["clean"])

    def test_link_verified_by_content(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as d:
            ep = Path(d) / "edits.json"
            ep.write_text(json.dumps([{"originalText": "בית", "link": "https://e.org"}]),
                          encoding="utf-8")

            def view(doc_id, token, mode):
                if mode == "PREVIEW_SUGGESTIONS_ACCEPTED" and posted:
                    return make_doc(self.TEXT, links=[(4, 7, "https://e.org")])
                return make_doc(self.TEXT)
            posted = []
            with mock.patch.object(U, "access_token", lambda a: "tok"), \
                    mock.patch.object(U, "get_doc", lambda d, t: make_doc(self.TEXT)), \
                    mock.patch.object(U, "get_doc_view", view), \
                    mock.patch.object(U, "_batch_raw", lambda *a, **k: posted.append(1) or {}):
                r = U.suggest_edits("DOC", "acc", ep)
        self.assertEqual(r["links"]["ok"], 1)
        self.assertEqual(r["status"], "landed")
        self.assertTrue(r["clean"])


class UpdateRequiresDirect(unittest.TestCase):
    def test_update_refused_without_direct(self):
        with tempfile.NamedTemporaryFile(suffix=".docx", dir=os.environ.get("TMPDIR")) as f:
            with mock.patch.object(sys, "argv", ["x", f.name, "--update", "FID"]), \
                    mock.patch.object(U, "update", side_effect=AssertionError("called")):
                with self.assertRaises(SystemExit) as cm:
                    U.main()
            self.assertIn("--direct", str(cm.exception.code))


if __name__ == "__main__":
    unittest.main()


class TestLinkOnReplacementType(unittest.TestCase):
    """רגרסיה מהרצה חיה 17.11.2026: type=replacement עם link בלי newText = קישור, לא invalid."""

    def test_replacement_with_link_only_is_link(self):
        import upload_to_gdocs as u
        r = u._norm_edit({"type": "replacement", "originalText": "ועדת הפטורים", "link": "https://www.gov.il/"})
        self.assertEqual(r["type"], "link")


class TestMinimizeReplacement(unittest.TestCase):
    """הנחיית דור 17.11.2026: לא הצעות על מרכאות, לא משפט שלם בשביל כמה תווים."""

    def setUp(self):
        import upload_to_gdocs as u
        self.m = u._minimize_replacement

    def test_quotes_only_dropped(self):
        self.assertIsNone(self.m('"יש לבחון חלופות"', '״יש לבחון חלופות״'))
        self.assertIsNone(self.m('סנ"צ אישר', 'סנ״צ אישר'))

    def test_edge_quotes_do_not_widen(self):
        old = '"הוועדה ביקשה לבחון חלופות בשוק"'
        new = '״הוועדה דרשה לבחון חלופות בשוק״'
        s, e, n = self.m(old, new)
        self.assertEqual(old[s:e], 'ביקשה')
        self.assertEqual(n, 'דרשה')

    def test_typo_takes_whole_word(self):
        old = 'המשטרה מבקשת להרחיב את ההתקשרת עם סלברייט'
        new = 'המשטרה מבקשת להרחיב את ההתקשרות עם סלברייט'
        s, e, n = self.m(old, new)
        self.assertEqual((old[s:e], n), ('ההתקשרת', 'ההתקשרות'))

    def test_pure_insertion_and_deletion(self):
        old = 'הבקשה פורסמה ביום שישי.'
        s, e, n = self.m(old, 'הבקשה פורסמה לציבור ביום שישי.')
        self.assertEqual((s == e or old[s:e] in ('ביום',), n.strip() != ''), (True, True))
        s, e, n = self.m(old, 'הבקשה פורסמה.')
        self.assertTrue(old[s:e].strip().startswith('ביום'))

    def test_resolve_skips_quotes_only(self):
        import upload_to_gdocs as u
        plain = 'נאמר "יש לבחון חלופות" בפרוטוקול.\n'
        res, skipped = u._resolve_anchors([{"type": "replacement", "originalText": '"יש לבחון חלופות"', "newText": '״יש לבחון חלופות״'}], plain)
        self.assertEqual(res, [])
        self.assertEqual(skipped[0]["reason"], "quotes_only")
