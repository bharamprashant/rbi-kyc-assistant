# Why this exists and how it was built

## The problem
RBI's KYC rules for lenders are spread across a long Master Direction, a repealed 2016 version, a newer 2025 set of Directions (separate for NBFCs and Commercial Banks), and a stream of amendment circulars. Anyone working in lending (compliance, product, operations, risk, programme management) asks the same practical questions again and again:

- *What does RBI actually say about X, and in which paragraph?*
- *Has it changed, and when? Which circular changed it?*
- *Does this apply to NBFCs, to Commercial Banks, or both?*

Today the answer comes from searching a long web page, an old PDF, or a colleague's memory. The risks are real: acting on a repealed rule, mixing up the NBFC and bank texts, or trusting a confident but unsourced answer. General-purpose AI chat makes this worse, because it can state a wrong paragraph with total confidence.

## What this tool does about it
It answers plain-language KYC questions **only from the official RBI text**, and shows the evidence:

| Need | How it is handled |
|---|---|
| Trust the answer | Exact RBI paragraph, document version and a link to RBI's own page on every answer |
| Avoid confident guesses | If nothing relevant is found, it says so and offers close, verified questions instead |
| Know what is current | The newest controlling text wins: 2025 Directions as amended, then amendment circulars. The repealed 2016 Direction appears only as labelled history |
| See what changed | A "What changed" block built from RBI's own footnotes and amendment circulars, with dates |
| Right entity | Scope is limited to NBFCs and Commercial Banks, and each answer says which |
| Stay up to date | A weekly job checks RBI's pages and opens a pull request when text changes; a human reviews before anything goes live |
| Get better over time | A "not correct / not what I expected" button creates a private issue that becomes a regression test |

It is **not** legal advice, not affiliated with RBI, and does not store questions.

## Key design decisions
| Decision | Why |
|---|---|
| Retrieval, not a trained model | Regulation changes. Updating a document store is cheap and auditable; retraining a model is neither. Nothing is answered from memory. |
| Extractive answers (no generated text by default) | The answer is RBI's own words, so it cannot invent a rule. An optional AI summary exists but is off by default and falls back to the extract. |
| Refuse when unsure | A wrong compliance answer is worse than no answer. Unknown-word, coverage and minimum-score guards trigger a refusal. |
| Standard library only, no third-party dependencies | Smaller attack surface, nothing to patch, zero cost to run. |
| Human in the loop for data | Refreshes arrive as pull requests. Merge is the only path to production. |
| Free hosting | GitHub plus Vercel Hobby, with rate limits so it cannot run up a bill. |

## Architecture
```
RBI pages --> raw_html/ (evidence snapshots)
                 |  scripts/parse_directions.py, build_changelog.py, build_faqs.py
                 v
           data/ (numbered paragraphs, change registry, FAQs, vocabulary)
                 |  read-only at runtime
                 v
 core/search.py  ->  core/service.py  ->  api/*.py  ->  public/ (static UI)
 (retrieval)        (answer, changes,    (thin HTTP      (no inline code,
                     clarify, feedback)   handlers)        strict CSP)
```
Weekly: `refresh.yml` re-fetches RBI pages, rebuilds `data/`, runs the tests and opens a pull request. Feedback: `POST /api/feedback` creates an issue in a separate private repository.

## How questions are understood
1. Typo correction against the words actually in the RBI text.
2. Everyday-to-RBI vocabulary mapping in `data/vocabulary.json` (for example "selfie" maps to "live photograph", "co-borrower" to "joint account"). It is data, so it can be fixed without touching code.
3. BM25 keyword ranking with phrase and section-title bonuses, and weights that favour current text over amendments over history.
4. Intent label (change, figure, documents, definition, procedure, applicability) to shape the answer.
5. Guards: out-of-scope entities, unknown words, low coverage and low score all lead to a refusal.
6. Broad questions get clarifying options (for example, documents for which type of customer).

## How it was evaluated
- 325 differently worded questions in five styles (formal, casual, keywords, typos, mixed) in `data/eval_paraphrases.json`. Right paragraph in the top five results: **0.80 to 0.95**. Casual wording: **0.74 to 0.92**.
- 35 probes based on questions in RBI's own FAQ (`data/rbi_faq_eval.json`), including ones the Directions do not cover, which must be declined.
- CI fails if these scores drop. Reciprocal-rank fusion with extra rankers was tried and scored lower, so it was not adopted.

## Build timeline
1. **Evidence first:** saved RBI pages, parsed into numbered paragraphs using RBI's own footnotes and the 2016 page's colour legend to date every change.
2. **Retrieval and refusal:** keyword search, status weighting, answer-or-refuse logic, citations.
3. **Security and separation:** strict headers, input limits, rate limits, no stored queries, repo scan for secrets.
4. **Questions and answers:** question bank (86 verified for both entities), detailed answers, "what changed", FAQ chips, redesign.
5. **Validation against RBI's FAQ:** found and fixed misses (for example the "selfie" question).
6. **Retrieval v2:** vocabulary file, typo correction, intent, clarification, evaluation harness.
7. **Feedback loop:** the "not correct" button feeding a private issue queue.

## Known limits
- About one in twenty differently worded questions still misses the best paragraph.
- Not yet captured: PDF-only annexes, the 14 Aug 2025 circular text, RBI FAQ text.
- Keyword search can miss meaning that shares no words with the RBI text; the vocabulary file and feedback loop address this over time.
- In-memory rate limits are best effort; the Vercel Firewall rule is the hard limit.

## Roadmap
Add the missing annexes and circulars, grow the evaluation set from real feedback, consider semantic search only if it beats keyword search on the evaluation set, and extend to other RBI master directions.

## How this was built
Designed and directed by the maintainer, with Claude Code (Anthropic) used as a coding assistant. Every change goes through a pull request and the automated tests before it is merged.
