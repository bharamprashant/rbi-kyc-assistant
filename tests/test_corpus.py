import json, re, sys, unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
CH = [json.loads(l) for l in open(ROOT / "data" / "chunks.jsonl", encoding="utf-8")]
VER = {v["doc_key"]: v for v in json.load(open(ROOT / "data" / "versions.json"))}


def one(doc, para):
    return [c for c in CH if c["doc_key"] == doc and c["para_no"] == para]


class Corpus(unittest.TestCase):
    def test_all_documents_present(self):
        self.assertEqual(set(VER), {"md-nbfc-2025", "md-commercial-banks-2025", "md-kyc-2016", "am-nbfc-2025-12-29", "am-cb-2025-12-29"})
        for d in VER.values():
            self.assertGreater(d["chunks"], 4)

    def test_colour_legend_read_from_rbi_page(self):
        leg = VER["md-kyc-2016"]["colour_legend"]
        self.assertEqual(len(leg), 15)
        self.assertEqual(leg["darkcyan"], "2025-08-14")
        self.assertEqual(leg["darkorange"], "2023-04-28")

    def test_2016_colour_changes_tracked_per_date(self):
        dates = {d for c in CH if c["doc_key"] == "md-kyc-2016" for d in c["change_dates"]}
        for d in ("2025-08-14", "2023-04-28", "2023-10-17", "2024-11-06", "2020-01-09"):
            self.assertIn(d, dates)

    def test_dec_2025_ckycr_amendment_attached_to_paragraph(self):
        n = [c for c in one("md-nbfc-2025", "63") if c["amendments"]]
        b = [c for c in one("md-commercial-banks-2025", "65") if c["amendments"]]
        for found in (n, b):
            self.assertTrue(found)
            self.assertEqual(found[0]["last_amended"], "2025-12-29")
            self.assertEqual(found[0]["amendments"][0]["kind"], "Inserted")

    def test_commercial_bank_2026_changes_tracked(self):
        a = {c["last_amended"] for c in CH if c["doc_key"] == "md-commercial-banks-2025" and c["amendments"]}
        self.assertIn("2026-09-18", a)
        self.assertIn("2026-10-01", a)
        self.assertEqual(VER["md-commercial-banks-2025"]["version_iso"], "2026-10-01")

    def test_every_chapter_detected(self):
        for d in ("md-nbfc-2025", "md-commercial-banks-2025"):
            chapters = {c["chapter"].split(" ")[0] + " " + re.split(r"[\s-]+", c["chapter"])[1] for c in CH if c["doc_key"] == d and c["chapter"]}
            self.assertEqual(len(chapters), 11, (d, sorted(chapters)))

    def test_status_and_scope(self):
        self.assertEqual({c["entity"] for c in CH if c["status"] == "current"}, {"NBFC", "Commercial Banks"})
        self.assertTrue(all(c["status"] == "historical" for c in CH if c["doc_key"] == "md-kyc-2016"))

    def test_chunks_have_citation_fields(self):
        for c in CH:
            for k in ("id", "doc_title", "para_no", "source_url", "snapshot_sha256", "status"):
                self.assertTrue(c.get(k), (c["id"], k))
            self.assertTrue(c["source_url"].startswith("https://www.rbi.org.in/"))
            self.assertLessEqual(len(c["text"]), 2600)

    def test_text_matches_snapshot(self):
        """Every chunk's opening words appear verbatim in the saved RBI page (no invented text)."""
        import html as h
        raw = {}
        for d in VER.values():
            s = (ROOT / "raw_html" / d["snapshot_file"]).read_text(encoding="utf-8")
            s = re.sub(r"<[^>]+>", "", re.sub(r"<br\s*/?>", " ", s, flags=re.I)); raw[d["doc_key"]] = re.sub(r"\s+", " ", h.unescape(s).replace("\xa0", " "))
        for c in CH[::3]:
            if c["para_no"] == "table":      # table rows are joined with " | " by the parser
                continue
            probe = re.sub(r"\s+", " ", c["text"].split("\n")[0][:60]).strip()
            self.assertTrue(probe in raw[c["doc_key"]], c["id"])
