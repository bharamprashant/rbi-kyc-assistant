import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.search import Index
from core.changes import timeline

IX = Index.load()


class Search(unittest.TestCase):
    def test_ckycr_responsibility(self):
        r = IX.search("Who is responsible for verifying identity when relying on CKYCR records?")
        self.assertEqual(r["status"], "answered")
        top = {(x["entity"], x["para_no"]) for x in r["results"][:3]}
        self.assertTrue({("NBFC", "63"), ("Commercial Banks", "65")} & top)

    def test_periodic_updation(self):
        r = IX.search("periodic updation of KYC for high risk customers", entity="NBFC")
        self.assertEqual(r["status"], "answered")
        self.assertTrue(all(x["entity"] == "NBFC" for x in r["results"]))

    def test_refuses_unrelated(self):
        self.assertEqual(IX.search("best pizza recipe in Mumbai")["status"], "refused")
        self.assertEqual(IX.search("what will the rupee be worth next year")["status"], "refused")

    def test_out_of_scope_entities(self):
        for q in ("KYC for small finance banks", "payments bank KYC limits", "housing finance company KYC"):
            self.assertEqual(IX.search(q)["status"], "out_of_scope", q)

    def test_scope_words_allow_in_scope_question(self):
        self.assertNotEqual(IX.search("does the NBFC KYC direction apply to housing finance companies")["status"], "out_of_scope")

    def test_historical_hidden_by_default_and_labelled(self):
        r = IX.search("periodic updation of KYC")
        self.assertTrue(all(x["status"] != "historical" for x in r["results"]))
        h = IX.search("periodic updation of KYC", include_historical=True, k=20)
        self.assertTrue(any(x["status"] == "historical" for x in h["results"]))

    def test_current_ranks_above_historical(self):
        r = IX.search("periodic updation of KYC", include_historical=True, k=3)
        self.assertNotEqual(r["results"][0]["status"], "historical")

    def test_every_result_cites_source(self):
        for x in IX.search("simplified due diligence")["results"]:
            self.assertTrue(x["source_url"].startswith("https://www.rbi.org.in/"))
            self.assertTrue(x["doc_title"] and x["para_no"])

    def test_timeline_newest_first_and_historical_flag(self):
        t = timeline()
        self.assertEqual([e["date"] for e in t], sorted((e["date"] for e in t), reverse=True))
        self.assertEqual(t[0]["date"], "2026-10-01")
        cur = timeline(include_historical=False)
        self.assertTrue(all(e["status"] != "historical" for e in cur))
