"""Builds sources_manifest.csv for the RBI KYC corpus (step 1).

Evidence levels (how well each row was confirmed in the research session):
  rbi_page        - content of the rbi.org.in page itself was read (via fetch or search snippet)
  secondary       - only seen on third-party sites (taxguru, law-firm notes); RBI URL unconfirmed
  inferred_gap    - known to exist (from RBI listings / law-firm notes) but ref/URL not retrieved
Blank cells mean "not retrieved", never "does not exist".
"""
import csv, sys

RBI_MD = "https://rbi.org.in/scripts/BS_ViewMasDirections.aspx?id={}"
RBI_N = "https://rbi.org.in/scripts/NotificationUser.aspx?Id={}&Mode=0"
PDF = "https://rbidocs.rbi.org.in/rdocs/notification/PDFs/"

COLS = ["doc_key", "entity", "doc_type", "title", "issue_date", "updated_as_on",
        "rbi_ref", "dor_ref", "rbi_page_url", "pdf_urls", "evidence", "lending_priority", "notes"]

def row(**k):
    return {c: k.get(c, "") for c in COLS}

R = []

# ---------------- 2025 entity-specific Directions (current framework) ----------------
R += [
 row(doc_key="md-nbfc-2025", entity="NBFC", doc_type="base",
     title="Reserve Bank of India (Non-Banking Financial Companies – Know Your Customer) Directions, 2025",
     issue_date="2025-11-28", updated_as_on="2025-12-29",
     rbi_ref="RBI/DOR/2025-26/361", dor_ref="DOR.AML.REC.No.280/14.01.003/2025-26",
     rbi_page_url=RBI_MD.format(12943),
     pdf_urls=";".join([PDF+"361MD1E2F8EA063454AD5AFA1D02A1BA5ACA7.PDF",
                        "https://rbidocs.rbi.org.in/rdocs/content/pdfs/361MD28112025_A1.pdf",
                        "https://rbidocs.rbi.org.in/rdocs/content/pdfs/361MD28112025_A2.pdf"]),
     evidence="rbi_page", lending_priority="core",
     notes="Applies to all NBFC categories/layers except NBFCs with no customer interface. Version history: https://rbi.org.in/scripts/NotificationPreVersion.aspx?id=12943. No 2026 NBFC KYC amendment found - CONFIRM on RBI page."),
 row(doc_key="md-commercial-banks-2025", entity="Commercial Banks", doc_type="base",
     title="Reserve Bank of India (Commercial Banks – Know Your Customer) Directions, 2025",
     issue_date="2025-11-28", updated_as_on="2026-10-01 (page header) / 2026-09-18 (latest in version list)",
     rbi_ref="RBI/DOR/2025-26/169", dor_ref="14.01.002 series",
     rbi_page_url="https://www.rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=13141",
     pdf_urls=";".join([PDF+"169MD.PDF",
                        "https://rbidocs.rbi.org.in/rdocs/content/pdfs/169MD12102026_A1.pdf",
                        "https://rbidocs.rbi.org.in/rdocs/content/pdfs/169MD12102026_A2.pdf"]),
     evidence="rbi_page", lending_priority="core",
     notes="DISCREPANCY: page header says 'Updated as on October 1, 2026' but version list shows Nov 28 2025 / Dec 29 2025 / Sep 18 2026, and annex filenames embed 12102026. Resolve by opening the page. Versions: NotificationPreVersion.aspx?id=13141&Histid=26 / 235 / 319."),
 row(doc_key="md-sfb-2025", entity="Small Finance Banks", doc_type="base",
     title="Reserve Bank of India (Small Finance Banks – Know Your Customer) Directions, 2025",
     issue_date="2025-11-28", rbi_ref="", dor_ref="DOR.AML.REC.No.119/14.01.007/2025-26",
     pdf_urls=PDF+"200MD.pdf", evidence="secondary", lending_priority="core",
     notes="RBI page id not retrieved. PDF URL from a secondary site (taxguru) - verify it resolves on rbidocs.rbi.org.in."),
 row(doc_key="md-ucb-2025", entity="Urban Co-operative Banks", doc_type="base",
     title="Reserve Bank of India (Urban Co-operative Banks – Know Your Customer) Directions, 2025",
     issue_date="2025-11-28", rbi_ref="RBI/DOR/2025-26/291", dor_ref="DOR.AML.REC.No.210/14.01.006/2025-26",
     evidence="secondary", lending_priority="core", notes="RBI page id and PDF URL not retrieved."),
 row(doc_key="md-rrb-2025", entity="Regional Rural Banks", doc_type="base",
     title="Reserve Bank of India (Regional Rural Banks – Know Your Customer) Directions, 2025",
     issue_date="2025-11-28", updated_as_on="2026-09-18",
     rbi_ref="RBI/DOR/2025-26/266", dor_ref="DOR.AML.REC.No.185/14.01.004/2025-26",
     rbi_page_url=RBI_MD.format(13040), evidence="rbi_page", lending_priority="core",
     notes="PDF link to be scraped from page."),
 row(doc_key="md-rcb-2025", entity="Rural Co-operative Banks", doc_type="base",
     title="Reserve Bank of India (Rural Co-operative Banks – Know Your Customer) Directions, 2025",
     issue_date="2025-11-28", updated_as_on="2025-12-29 (as last seen; Sep 2026 amendment exists - check)",
     rbi_ref="RBI/DOR/2025-26/316", dor_ref="DOR.AML.REC.No.235/14.01.005/2025-26",
     rbi_page_url=RBI_MD.format(12988),
     pdf_urls=PDF+"316MDC827AC45BD1248DFB272637379D4128C.PDF", evidence="rbi_page", lending_priority="core"),
 row(doc_key="md-aifi-2025", entity="All India Financial Institutions", doc_type="base",
     title="Reserve Bank of India (All India Financial Institutions – Know Your Customer) Directions, 2025",
     issue_date="2025-11-28", updated_as_on="2025-12-29",
     rbi_ref="RBI/DOR/2025-26/335", dor_ref="DOR.AML.REC.No.254/14.01.011/2025-26",
     rbi_page_url=RBI_MD.format(12969),
     pdf_urls="https://website.rbi.org.in/documents/d/rbi/all-india-financial-institutions-know-your-customer",
     evidence="rbi_page", lending_priority="core", notes="Covers EXIM, NABARD, SIDBI, NHB, NaBFID. website.rbi.org.in document URL is a non-PDF-suffixed download link."),
 row(doc_key="md-lab-2025", entity="Local Area Banks", doc_type="base",
     title="Reserve Bank of India (Local Area Banks – Know Your Customer) Directions, 2025",
     issue_date="2025-11-28", updated_as_on="2026-09-18",
     rbi_ref="RBI/DOR/2025-26/243", dor_ref="DOR.AML.REC.No.162/14.01.008/2025-26",
     rbi_page_url=RBI_MD.format(13064), pdf_urls=PDF+"243MD.PDF", evidence="rbi_page", lending_priority="secondary"),
 row(doc_key="md-arc-2025", entity="Asset Reconstruction Companies", doc_type="base",
     title="Reserve Bank of India (Asset Reconstruction Companies – Know Your Customer) Directions, 2025",
     issue_date="2025-11-28", updated_as_on="2025-12-29",
     rbi_ref="RBI/DOR/2025-26/377", dor_ref="DOR.AML.REC.No.296/14.01.010/2025-26",
     rbi_page_url=RBI_MD.format(12927), evidence="rbi_page", lending_priority="low"),
 row(doc_key="md-pb-2025", entity="Payments Banks", doc_type="base",
     title="Reserve Bank of India (Payments Banks – Know Your Customer) Directions, 2025",
     issue_date="2025-11-28", rbi_ref="RBI/DOR/2025-26/218", dor_ref="DOR.AML.REC.No.137/14.01.009/2025-26",
     evidence="secondary", lending_priority="low", notes="Payments banks do not lend; include only if scope widens. Page id/PDF not retrieved."),
]

# ---------------- Amendments to the 2025 Directions ----------------
def amend(key, entity, date, ref, dor, pid, title, evidence, notes="", page=None):
    return row(doc_key=key, entity=entity, doc_type="amendment", title=title, issue_date=date,
               rbi_ref=ref, dor_ref=dor, rbi_page_url=(page if page else (RBI_N.format(pid) if pid else "")),
               evidence=evidence, lending_priority="core" if entity in
               ("NBFC","Commercial Banks","Small Finance Banks","Urban Co-operative Banks",
                "Regional Rural Banks","Rural Co-operative Banks","All India Financial Institutions") else "secondary",
               notes=notes)

CK = "CKYCR responsibility: RE that last uploaded/updated the record verifies identity/address (Explanation inserted in CKYCR paragraph); based on Dept of Revenue OM of 18 Sep 2025."
FP = "Certified-copy facility (original certified copy by listed overseas authorities) extended from NRIs/PIOs to Foreign Portfolio Investors."
R += [
 amend("am-nbfc-2025-12-29","NBFC","2025-12-29","RBI/2025-26/160","DOR.AML.REC.364/14.01.003/2025-26",13236,
       "Reserve Bank of India (Non-Banking Financial Companies – Know Your Customer) Amendment Directions, 2025","rbi_page",CK+" Para 63."),
 amend("am-cb-2025-12-29","Commercial Banks","2025-12-29","RBI/2025-26/166","DOR.AML.REC.370/14.01.002/2025-26",13242,
       "Reserve Bank of India (Commercial Banks – Know Your Customer) Amendment Directions, 2025","rbi_page",CK+" Para 65. Page saved to raw_html/ on 2026-11-11."),
 amend("am-sfb-2025-12-29","Small Finance Banks","2025-12-29","","",None,
       "Reserve Bank of India (Small Finance Banks – Know Your Customer) Amendment Directions, 2025","secondary",CK+" Ref number not retrieved."),
 amend("am-ucb-2025-12-29","Urban Co-operative Banks","2025-12-29","RBI/2025-26/165","DOR.AML.REC.369/14.01.006/2025-26",None,
       "Reserve Bank of India (Urban Co-operative Banks – Know Your Customer) Amendment Directions, 2025","secondary",CK+" Para 64."),
 amend("am-rrb-2025-12-29","Regional Rural Banks","2025-12-29","RBI/2025-26/162","DOR.AML.REC.366/14.01.004/2025-26",13238,
       "Reserve Bank of India (Regional Rural Banks – Know Your Customer) Amendment Directions, 2025","rbi_page",CK+" Para 64."),
 amend("am-rcb-2025-12-29","Rural Co-operative Banks","2025-12-29","RBI/2025-26/163","DOR.AML.REC.367/14.01.005/2025-26",13239,
       "Reserve Bank of India (Rural Co-operative Banks – Know Your Customer) Amendment Directions, 2025","rbi_page",CK+" Para 64.",
       page="https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=13239"),
 amend("am-aifi-2025-12-29","All India Financial Institutions","2025-12-29","RBI/2025-26/157","DOR.AML.REC.361/14.01.011/2025-26",13233,
       "Reserve Bank of India (All India Financial Institutions – Know Your Customer) Amendment Directions, 2025","rbi_page",CK+" Para 62.",
       page="https://www.rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=13233"),
 amend("am-lab-2025-12-29","Local Area Banks","2025-12-29","RBI/2025-26/159","DOR.AML.REC.363/14.01.008/2025-26",13235,
       "Reserve Bank of India (Local Area Banks – Know Your Customer) Amendment Directions, 2025","rbi_page",CK),
 amend("am-arc-2025-12-29","Asset Reconstruction Companies","2025-12-29","RBI/2025-26/158","DOR.AML.REC.362/14.01.010/2025-26",None,
       "Reserve Bank of India (Asset Reconstruction Companies – Know Your Customer) Amendment Directions, 2025","secondary",CK+" Para 59.",
       page="https://website.rbi.org.in/web/rbi/-/notifications/reserve-bank-of-india-asset-reconstruction-companies-know-your-customer-amendment-directions-2025"),
 amend("am-pb-2025-12-29","Payments Banks","2025-12-29","","",None,
       "Reserve Bank of India (Payments Banks – Know Your Customer) Amendment Directions, 2025","secondary",CK+" Ref number not retrieved."),
 # 18 Sep 2026: six parallel bank-category amendments
 amend("am-cb-2026-09-18","Commercial Banks","2026-09-18","","",13699,
       "Reserve Bank of India (Commercial Banks – Know Your Customer) Amendment Directions, 2026","rbi_page_footnote",FP+" Footnote on the Commercial Banks Directions page marks para 5 as inserted w.e.f. 18 Sep 2026 (RBI page id 13699). Ref number not yet retrieved."),
 amend("am-cb-2026-10-01-governance","Commercial Banks","2026-10-01","","",13555,
       "Reserve Bank of India (Commercial Banks – Governance) Amendment Directions, 2026 (consequential change in KYC Directions)","rbi_page_footnote","Footnote on the Commercial Banks KYC page: para 11 substituted w.e.f. 1 Oct 2026 consequent to this amendment (RBI page id 13555). Explains the page header 'Updated as on October 1, 2026'."),
 amend("am-sfb-2026-09-18","Small Finance Banks","2026-09-18","RBI/2026-27/258","DOR.AML.REC.224/14.01.007/2026-27",13700,
       "Reserve Bank of India (Small Finance Banks – Know Your Customer) Amendment Directions, 2026","rbi_page",FP+" Substitutes para 5(1)(v)."),
 amend("am-lab-2026-09-18","Local Area Banks","2026-09-18","","",None,
       "Reserve Bank of India (Local Area Banks – Know Your Customer) Amendment Directions, 2026","secondary",FP+" Substitutes para 4(1)(v). Ref not retrieved (base directions page already shows 'updated as on Sep 18, 2026')."),
 amend("am-rrb-2026-09-18","Regional Rural Banks","2026-09-18","RBI/2026-27/260","DOR.AML.REC.222/14.01.004/2026-27",13702,
       "Reserve Bank of India (Regional Rural Banks – Know Your Customer) Amendment Directions, 2026","rbi_page",FP+" Substitutes para 4(1)(v)."),
 amend("am-ucb-2026-09-18","Urban Co-operative Banks","2026-09-18","RBI/2026-27/261","",13703,
       "Reserve Bank of India (Urban Co-operative Banks – Know Your Customer) Amendment Directions, 2026","rbi_page",FP+" Modifies para 4(1)(v)."),
 amend("am-rcb-2026-09-18","Rural Co-operative Banks","2026-09-18","RBI/2026-27/262","DOR.AML.REC.223/14.01.005/2026-27",13704,
       "Reserve Bank of India (Rural Co-operative Banks – Know Your Customer) Amendment Directions, 2026","rbi_page",FP+" Substitutes para 4(1)(v)."),
]

# ---------------- Historical: repealed 2016 Master Direction and its 2025 amendments ----------------
R += [
 row(doc_key="hist-md-kyc-2016", entity="All REs (pre-consolidation)", doc_type="historical_base",
     title="Master Direction – Know Your Customer (KYC) Direction, 2016 (Updated as on August 14, 2025)",
     issue_date="2016-02-25", updated_as_on="2025-08-14", rbi_ref="RBI/DBR/2015-16/18",
     dor_ref="DBR.AML.BC.No.81/14.01.001/2015-16", rbi_page_url=RBI_MD.format(11566), evidence="rbi_page",
     lending_priority="core",
     notes="REPEALED 2025-11-28 (consolidated into entity-specific Directions). Keep for 'what changed' answers and pre-Nov-2025 history. Earlier 'updated as on' dates on the page: 2025-06-12, 2024-11-06, 2024-01-04, 2023-10-17, 2023-05-04, 2023-04-28, 2021-05-10, 2021-04-01, 2021-03-23, 2020-12-18, 2020-04-20 (older snapshots: id=10292 up to 2018-07-12, id=11261 Dec 2016)."),
 row(doc_key="hist-am-2025-06-12", entity="All REs (pre-consolidation)", doc_type="historical_amendment",
     title="Reserve Bank of India (Know Your Customer (KYC)) (Amendment) Directions, 2025",
     issue_date="2025-06-12", rbi_ref="RBI/2025-26/51", dor_ref="DOR.AML.REC.30/14.01.001/2025-26",
     rbi_page_url=RBI_N.format(12866), evidence="rbi_page", lending_priority="core",
     notes="Para 38 periodic updation: low-risk individuals may update up to 1 year after due date or 30 Jun 2026, whichever later; BC-assisted updation."),
 row(doc_key="hist-circ-2025-06-12-banks", entity="Banks", doc_type="historical_amendment",
     title="Updation/Periodic Updation of KYC – Revised Instructions (banks circular)",
     issue_date="2025-06-12", rbi_ref="RBI/2025-26/53", dor_ref="DOR.AML.REC.31/14.01.001/2025-26",
     evidence="secondary", lending_priority="secondary", notes="Seen only via third-party copies (fidcindia.org.in, caalley). Find RBI original."),
 row(doc_key="hist-am-2025-08-14", entity="All REs (pre-consolidation)", doc_type="historical_amendment",
     title="Reserve Bank of India (Know Your Customer (KYC)) (2nd Amendment) Directions, 2025",
     issue_date="2025-08-14", rbi_ref="RBI/2025-26/75", dor_ref="DOR.AML.REC.46/14.01.001/2025-26",
     pdf_urls="https://website.rbi.org.in/documents/d/rbi/mdonkycamendmentscircular", evidence="rbi_page",
     lending_priority="core", notes="Source of the 'three intimations / three reminders' for periodic updation per secondary commentary - verify in text."),
 row(doc_key="hist-withdrawal-2025-11-28", entity="All REs", doc_type="historical_amendment",
     title="Consolidation of Regulations – Withdrawal of circulars (28 Nov 2025) and repeal notice for the 2016 KYC Master Direction",
     issue_date="2025-11-28", evidence="rbi_page", dor_ref="DOR.RRC.REC.302/33-01-010/2025-26", lending_priority="core",
     notes="Repeal of the earlier KYC Directions is stated in RBI's own text: NBFC Directions para 73 and Commercial Banks Directions para 80 cite circular DOR.RRC.REC.302/33-01-010/2025-26 dated 28 Nov 2025. The standalone circular page is not yet retrieved. Related payments circular RBI/2025-26/101 CO.DPSS.POLC.No.S-955/02-30-010/2025-26 at rbi.org.in/Scripts/BS_CircularIndexDisplay.aspx?Id=13171 redirects PPI/PA references to the Commercial Banks Directions."),
]

# Individual amendment circulars to the 2016 Direction, taken from the footnotes and colour legend of
# rbi.org.in/Scripts/BS_ViewMasDirections.aspx?id=11566. RBI page URLs not yet located (evidence=rbi_page_footnote).
HIST = [
 ("2025-08-14","DOR.AML.REC.46/14.01.001/2025-26","Already listed above (RBI/2025-26/75)."),
 ("2024-11-06","DOR.AML.REC.49/14.01.001/2024-25","CKYCR use in updation, KYC Identifier retrieval, 7-day update of new info (from text samples); corrigendum dated 2024-04-22 mentioned on page."),
 ("2024-01-04","DOR.AML.REC.66/14.01.001/2023-24","Small: one item deleted, PEP explanation edited."),
 ("2023-10-17","DOR.AML.REC.44/14.01.001/2023-24","Large; FATF-aligned CDD wording: beneficial ownership and control, 10 percent thresholds."),
 ("2023-05-04","DOR.AML.REC.13/14.01.001/2023-24","Small."),
 ("2023-04-28","DOR.AML.REC.111/14.01.001/2023-24","Large; Introduction and statutory powers rewritten, Group and correspondent banking text."),
 ("2021-05-10","DOR.AML.REC.No.15/14.01.001/2021-22",""),
 ("2021-04-01","DOR.AML.BC.No.1/14.01.001/2021-22",""),
 ("2021-03-23","DOR.AML.REC.48/14.01.001/2020-21",""),
 ("2020-12-18","DOR.AML.BC.No.31/14.01.001/2020-21",""),
 ("2020-04-20","DOR.AML.BC.No.66/14.01.001/2019-20",""),
 ("2020-01-09","DOR.AML.BC.No.27/14.01.001/2019-20","Large; Aadhaar, Certified Copy, Digital KYC, Digital Signature, Equivalent e-document, KYC Identifier definitions."),
 ("2019-05-29","DBR.AML.BC.No.39/14.01.001/2018-19",""),
]
for d, ref, note in HIST[1:]:
    R.append(row(doc_key=f"hist-am-{d}-md2016", entity="All REs (pre-consolidation)", doc_type="historical_amendment",
                 title=f"Amendment circular to KYC Master Direction 2016 ({ref})", issue_date=d, dor_ref=ref,
                 evidence="rbi_page_footnote", lending_priority="secondary",
                 notes="RBI circular page/PDF URL not located. "+note))

# Scope decision (2026-11-11): NBFCs and commercial banks only. Other bank categories, AIFIs, ARCs and
# payments banks were researched but are excluded. Historical rows that applied to all REs are kept.
KEEP = {"NBFC", "Commercial Banks", "Banks", "All REs", "All REs (pre-consolidation)"}
R = [r for r in R if r["entity"] in KEEP]

if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "sources_manifest.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader(); w.writerows(R)
    print(f"wrote {len(R)} rows to {out}")
