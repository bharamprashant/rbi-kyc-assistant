# RBI KYC Assistant (NBFCs and Commercial Banks)

A free, public Q&A tool over RBI's KYC Directions for the lending industry. It answers **what RBI says**, **what changed**, and **where to find it**, always with the paragraph, version and a link to the official RBI page. Scope is deliberately limited to **NBFCs** and **Commercial Banks**. Not legal advice; not affiliated with RBI.

## How it works
1. `raw_html/` holds saved copies of the official RBI pages (the evidence).
2. `scripts/parse_directions.py` turns them into numbered paragraphs (`data/chunks.jsonl`), reading RBI's own footnotes and, for the 2016 page, its **colour legend** (each colour = an "Updated as on" date) so every paragraph knows which circular last changed it. `data/changes.jsonl` lists every change; `data/CHANGELOG.md` is the readable version.
3. `core/search.py` finds the best-matching RBI paragraphs (keyword ranking). The newest controlling text wins: current 2025 Directions as amended > amendment circulars > the repealed 2016 Master Direction (only on request, always labelled historical). If nothing relevant is found it says so.
4. `api/` + `public/` serve it on Vercel (free plan). Optional AI summary is off by default.
5. `.github/workflows/refresh.yml` checks the RBI pages weekly and opens a pull request if anything changed. A human reviews and merges; merging redeploys.

## Document set (current)
| Document | Entity | Version on saved page |
|---|---|---|
| RBI (NBFC - KYC) Directions, 2025 (+29 Dec 2025 amendment) | NBFC | 29 Dec 2025 |
| RBI (Commercial Banks - KYC) Directions, 2025 (+29 Dec 2025, 18 Sep 2026, 1 Oct 2026 changes) | Commercial Banks | 1 Oct 2026 |
| Master Direction - KYC, 2016 (repealed by para 73 / para 80 of the 2025 Directions, circular DOR.RRC.REC.302/33-01-010/2025-26, 28 Nov 2025) | history only | colour-coded to 14 Aug 2025 |

Details of what is and is not captured are in `sources_manifest.csv` (evidence level per row). Not yet captured: PDF-only annexes, the 14 Aug 2025 circular text, FAQs.

## Run locally
```
python3 -I -m unittest discover -s tests -v     # 26 tests
python3 -I scripts/parse_directions.py          # rebuild data/ from raw_html/
python3 -I scripts/build_changelog.py
```
Deploy: import the repo in Vercel (no build step). See `SECURITY.md` for settings to enable and `.env.example` for optional variables.


## Questions, detailed answers and FAQs
- `data/question_bank.json`: 84 curated questions, written in our own words from topics in public KYC FAQs (RBI's FAQs of 9 Jun 2025 and lender/bank FAQ pages). Tests require every one to be answered for both NBFCs and Commercial Banks.
- Answers are extractive, never generated: key RBI passages with paragraph references, a **What changed** block (RBI footnotes and amendment circulars on the cited paragraphs), and an **Earlier position** block from the repealed 2016 Direction, clearly labelled historical.
- `scripts/build_faqs.py` writes `data/faqs.json` (verified questions plus auto-generated "What changed" questions from the change registry). `scripts/refresh.py` re-runs it whenever RBI text changes, so the suggestions follow the data. User queries are never logged or used.

## How questions are understood (retrieval v2)
Researched practice for regulatory RAG (hybrid search, query rewriting/expansion for vocabulary mismatch, intent detection, clarification, abstaining when evidence is missing, evaluation with recall@k) and applied the parts that fit a free, no-training, no-secrets setup:
- `data/vocabulary.json`: everyday words and phrases mapped to RBI's wording (selfie -> live photograph, co-borrower -> joint account, NGO -> trust/association ...). Edit this file, not code.
- Typo correction against the RBI text, single BM25 ranker with phrase and section-title bonuses, refusal when key words are not in the Directions.
- Intent label, clarifying options for broad questions (e.g. documents without customer type), and "did you mean" suggestions when nothing answers.
- `scripts/eval_retrieval.py` + `data/eval_paraphrases.json`: 325 differently worded questions; CI fails if quality drops. Result: hit@5 0.80 -> 0.95 (casual wording 0.74 -> 0.92). Reciprocal-rank fusion with extra rankers was tested and scored lower, so it is not used.

## Feedback loop
Every answer has "Was this answer right?". A thumbs-down opens a short note box; it creates an issue in a private feedback repo (`FEEDBACK_REPO`). Triage: add the question and the RBI facts a correct answer needs to `data/eval_paraphrases.json`, fix `data/vocabulary.json` or ranking, and the CI evaluation keeps it fixed.
