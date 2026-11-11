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
