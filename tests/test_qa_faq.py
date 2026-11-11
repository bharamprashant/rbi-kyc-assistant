import json, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import core.service as c
from core.search import Index

H = {"content-type": "application/json", "x-forwarded-for": "9.9.9.9"}
BANK = json.loads((ROOT / "data" / "question_bank.json").read_text(encoding="utf-8"))
IX = Index.load()


def ask(q, ent=None):
    s, _, b = c.handle_ask("POST", H, json.dumps({"question": q, "entity": ent}).encode())
    return s, json.loads(b)


class Bank(unittest.TestCase):
    def test_every_bank_question_answered_for_both_entities(self):
        bad = [(q, e) for _, q in BANK for e in ("NBFC", "Commercial Banks") if IX.search(q, entity=e)["status"] != "answered"]
        self.assertEqual(bad, [])

    def test_bank_size_and_unique(self):
        qs = [q for _, q in BANK]
        self.assertGreaterEqual(len(qs), 80); self.assertEqual(len(qs), len(set(qs)))

    def test_expected_paragraphs(self):
        """Spot checks that the right RBI paragraph is among the top results."""
        want = [("Who is the designated director and principal officer for KYC?", "NBFC", {"14", "15"}),
                ("What is the beneficial ownership threshold for a partnership firm?", "NBFC", {"5"}),
                ("What documents are needed for a sole proprietorship?", "Commercial Banks", {"30", "31", "32"}),
                ("What is a politically exposed person rule?", "NBFC", {"45"}),
                ("How long are transaction records to be preserved?", "NBFC", {"47"}),
                ("What is required for wire transfers?", "NBFC", {"69"})]
        for q, e, paras in want:
            got = {r["para_no"] for r in IX.search(q, entity=e)["results"][:5]}
            self.assertTrue(got & paras, (q, got))

    def test_everyday_wording_maps_to_rbi_terms(self):
        """Regression: 'selfie' is not RBI's word (it says live photograph / liveness)."""
        for q in ("what are regulations for SELFIE in kyc", "selfie kyc", "Is face liveness needed in video kyc?"):
            r = IX.search(q); self.assertEqual(r["status"], "answered", q)
            self.assertTrue({"24", "27"} & {x["para_no"] for x in r["results"][:4]}, q)

    def test_off_topic_still_refused(self):
        for q in ("What is the best biryani recipe?", "How do I file my GST return?", "Who won the cricket match?"):
            self.assertNotEqual(ask(q)[1]["status"], "answered", q)


class Detail(unittest.TestCase):
    def setUp(self):
        c.reset_limits()

    def test_detail_structure(self):
        s, j = ask("How often must KYC be updated for high, medium and low risk customers?", "commercial_banks")
        self.assertEqual(s, 200); d = j["detail"]
        self.assertTrue(d["key_points"]); self.assertIn("source_url", d["key_points"][0]); self.assertIn("reference", d["key_points"][0])
        self.assertIn("what_changed_note", d); self.assertIn("what_changed", d)

    def test_what_changed_reports_amendment(self):
        s, j = ask("What was inserted in the NBFC KYC Directions on 29 December 2025?", "nbfc")
        dates = {a["date"] for a in j["detail"]["what_changed"]}
        self.assertIn("2025-12-29", dates)

    def test_history_is_labelled_historical(self):
        s, j = ask("What is periodic updation of KYC?", "commercial_banks")
        e = j["detail"]["earlier_position"]
        if e:
            self.assertIn("historical", e["note"]); self.assertIn("repealed", e["note"])

    def test_detail_text_is_verbatim_rbi(self):
        import re
        s, j = ask("What is the beneficial ownership threshold for a partnership firm?", "nbfc")
        norm = lambda t: re.sub(r"\s+", " ", t.replace("…", "")).strip()
        full = " ".join(norm(r["text"]) for r in j["results"])
        for p in j["detail"]["key_points"]:
            for part in norm(p["text"]).split("  "):
                self.assertIn(part[:120], full)


class Faqs(unittest.TestCase):
    def setUp(self):
        c.reset_limits()

    def test_faq_endpoint(self):
        s, h, b = c.handle_faqs("GET", H); j = json.loads(b)
        self.assertEqual(s, 200); self.assertGreaterEqual(sum(len(t["items"]) for t in j["topics"]), 80)
        self.assertEqual(c.handle_faqs("POST", H)[0], 405)

    def test_faq_file_is_current(self):
        """data/faqs.json must be regenerated whenever the corpus or bank changes (scripts/build_faqs.py)."""
        import subprocess
        before = (ROOT / "data" / "faqs.json").read_text(encoding="utf-8")
        subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / "build_faqs.py")], check=True, capture_output=True)
        after = (ROOT / "data" / "faqs.json").read_text(encoding="utf-8")
        self.assertEqual(before, after)

    def test_whats_new_is_answerable(self):
        _, _, b = c.handle_faqs("GET", H)
        for w in json.loads(b)["whats_new"]:
            s, j = ask(w["q"], w["entity"]); self.assertEqual(j["status"], "answered", w["q"])

    def test_every_faq_answerable_via_api(self):
        _, _, b = c.handle_faqs("GET", H)
        for t in json.loads(b)["topics"]:
            for it in t["items"]:
                c.reset_limits(); self.assertEqual(ask(it["q"])[1]["status"], "answered", it["q"])


class Ui(unittest.TestCase):
    def test_ui_has_no_inline_code_and_uses_faq_api(self):
        html = (ROOT / "public" / "index.html").read_text(); js = (ROOT / "public" / "app.js").read_text()
        self.assertNotIn("style=", html); self.assertNotIn("onclick=", html)
        self.assertNotRegex(html, r"<script(?![^>]*src=)")
        self.assertIn("/api/faqs", js); self.assertNotIn("innerHTML", js)

if __name__ == "__main__":
    unittest.main()
