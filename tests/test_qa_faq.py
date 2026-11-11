import json, os, sys, unittest
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


class RbiFaqEval(unittest.TestCase):
    """RBI's own FAQ (9 Jun 2025, 35 questions). Each probe lists facts RBI's answer states; the facts must appear
    in the top-5 retrieved paragraphs of the current Directions. Bank-only or out-of-corpus items must not answer for NBFC / at all."""
    def test_rbi_faq_facts_found_in_retrieved_text(self):
        import re
        ev = json.loads((ROOT / "data" / "rbi_faq_eval.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(ev), 35); bad = []
        for e in ev:
            for ent in ("NBFC", "Commercial Banks"):
                r = IX.search(e["q"], entity=ent); sc = e.get("scope")
                if sc == "not_in_directions" or (sc == "commercial_banks_only" and ent == "NBFC"):
                    if sc == "not_in_directions" and r["status"] == "answered":
                        bad.append((e["n"], ent, "should refuse"))
                    continue
                if r["status"] != "answered":
                    bad.append((e["n"], ent, "refused")); continue
                txt = " ".join(x["text"] for x in r["results"][:5])
                lost = [f for f in e["facts"] if not re.search(f, txt, re.I)]
                if lost:
                    bad.append((e["n"], ent, lost))
        self.assertEqual(bad, [])


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


class Understanding(unittest.TestCase):
    def setUp(self):
        c.reset_limits()

    def test_retrieval_quality_does_not_regress(self):
        """scripts/eval_retrieval.py over differently worded questions (formal, casual, keywords, descriptive, typos)."""
        sys.path.insert(0, str(ROOT / "scripts"))
        import eval_retrieval
        r = eval_retrieval.evaluate(IX)
        self.assertGreaterEqual(r["hit"], 0.93, r["by_style"])
        self.assertGreaterEqual(r["by_style"]["formal"], 0.99)
        for style in ("casual", "keywords", "typo/short"):
            self.assertGreaterEqual(r["by_style"][style], 0.88, style)

    def test_broad_question_gets_clarifying_options(self):
        s, j = ask("what documents are required for kyc")
        self.assertEqual(j["status"], "answered"); self.assertTrue(j["clarify"]["options"])
        s, j = ask("what documents are needed for a company customer")
        self.assertIsNone(j["clarify"])

    def test_typos_and_lay_words(self):
        for q in ("re-kyc frequecy for high risk custmer", "wire transfr rules", "ubo threshold", "kyc by dsa or agent"):
            self.assertEqual(ask(q)[1]["status"], "answered", q)

    def test_words_not_in_the_directions_are_refused_not_guessed(self):
        self.assertEqual(ask("inoperative account reactivation kyc")[1]["status"], "refused")
        self.assertEqual(ask("What is the best biryani recipe?")[1]["status"], "refused")

    def test_intent_labels(self):
        self.assertEqual(c.classify_intent("how many years to keep records"), "figure")
        self.assertEqual(c.classify_intent("what changed in 2025"), "change")
        self.assertEqual(c.classify_intent("what is a walk-in customer"), "definition")

    def test_suggestions_for_unanswerable_but_related(self):
        j = ask("kyc rules for crypto wallets")[1]
        self.assertIn(j["status"], ("refused",)); self.assertIn("suggestions", j)


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


class FeedbackTests(unittest.TestCase):
    OK = {"content-type": "application/json", "origin": "https://site.example", "host": "site.example", "x-forwarded-for": "7.7.7.7"}

    def setUp(self):
        import core.feedback as fb
        fb.reset_limits(); c.reset_limits(); self.fb = fb
        for k in ("FEEDBACK_GITHUB_TOKEN", "FEEDBACK_REPO"):
            os.environ.pop(k, None)

    def post(self, body, headers=None, opener=None):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        return c.handle_feedback("POST", headers or self.OK, b, opener=opener)

    GOOD = {"question": "what is a selfie rule?", "verdict": "incorrect", "comment": "expected para 24", "shown": ["24", "27"], "status": "answered"}

    def test_not_enabled_without_token(self):
        self.assertEqual(self.post(self.GOOD)[0], 503)

    def test_creates_issue_with_sanitised_text(self):
        os.environ["FEEDBACK_GITHUB_TOKEN"] = "tok"; os.environ["FEEDBACK_REPO"] = "owner/private-feedback"
        seen = {}

        class R:
            status = 201
            def __enter__(s): return s
            def __exit__(s, *a): return False

        def opener(req, timeout=0):
            seen["url"] = req.full_url; seen["body"] = json.loads(req.data); seen["h"] = dict(req.header_items()); return R()
        bad = dict(self.GOOD, comment="ping @octocat see #12 <script>x</script> https://evil.example `x`")
        self.assertEqual(self.post(bad, opener=opener)[0], 200)
        body = seen["body"]["body"]
        self.assertEqual(seen["url"], "https://api.github.com/repos/owner/private-feedback/issues")
        self.assertNotIn("@octocat", body); self.assertNotIn("<script>", body); self.assertNotIn("https://evil", body); self.assertNotIn("#12", body)
        self.assertIn("feedback", seen["body"]["labels"])
        self.assertNotIn("7.7.7.7", json.dumps(seen["body"]))        # no IP stored
        self.assertNotIn("tok", json.dumps(seen["body"]))

    def test_validation_and_origin(self):
        self.assertEqual(self.post(dict(self.GOOD, verdict="meh"))[0], 400)
        self.assertEqual(self.post(dict(self.GOOD, question=""))[0], 400)
        self.assertEqual(self.post(dict(self.GOOD, comment="x" * 501))[0], 400)
        self.assertEqual(self.post(dict(self.GOOD, shown=["<b>"]))[0], 400)
        self.assertEqual(self.post(b"not json")[0], 400)
        self.assertEqual(self.post(self.GOOD, headers=dict(self.OK, origin="https://evil.example"))[0], 403)
        no_origin = {k: v for k, v in self.OK.items() if k != "origin"}
        self.assertEqual(self.post(self.GOOD, headers=no_origin)[0], 403)
        self.assertEqual(c.handle_feedback("GET", self.OK, b"")[0], 405)
        self.assertEqual(self.post(b"x" * 5000)[0], 413)

    def test_rate_limited(self):
        codes = [self.post(self.GOOD)[0] for _ in range(8)]
        self.assertEqual(codes[-1], 429)

    def test_ui_wires_feedback(self):
        js = (ROOT / "public" / "app.js").read_text()
        self.assertIn("/api/feedback", js); self.assertIn("Not correct", js)
