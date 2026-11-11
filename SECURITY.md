# Security and separation

## Separation of concerns (one folder, one job)
| Folder | Job | Runtime access |
|---|---|---|
| `raw_html/` | Untouched snapshots of official RBI pages (evidence). Never edited by hand | offline only |
| `data/` | Generated corpus (`chunks.jsonl`, `changes.jsonl`, `versions.json`, `CHANGELOG.md`). Regenerate with `scripts/parse_directions.py` | read-only at runtime |
| `core/` | Retrieval, refusal, change timeline. Pure functions, no network, no secrets (`llm.py` is optional and off by default) | imported by `api/` |
| `api/` | Thin HTTP handlers only; request validation and rate limits live in `core/service.py` | public internet |
| `public/` | Static UI. No inline scripts, no `innerHTML`, no third-party scripts | public internet |
| `scripts/` | Offline tools: parse, refresh, changelog. Not deployed behavior | CI / maintainer only |
| `.github/workflows/` | CI (read-only token) and weekly refresh (opens a PR, never deploys) | GitHub only |

Secrets exist only as environment variables (`.env.example` lists names, no values). `.env` is git-ignored and a test scans the repo for key patterns.

## Controls
- **Answers only from RBI text.** Retrieval-only by default (no AI generation, zero cost). Refuses when nothing relevant is found; refuses out-of-scope entities.
- **Optional AI summary** (`KYC_LLM_ENABLED=1`): excerpts sent as untrusted data, 350-token cap, daily call budget, falls back to the extracted RBI text. Also set a hard monthly spend limit in the provider console; the in-process budget is best effort.
- **Input validation:** POST only, JSON only, 2 KB body, 400-char question, control characters stripped, entity whitelist, strict types.
- **Rate limits:** per-client per-minute and per-day, plus a global daily cap (`KYC_RATE_*`). In-memory per serverless instance, so best effort; add a Vercel Firewall rate-limit rule in the dashboard for a hard limit.
- **Browser hardening (vercel.json):** CSP `default-src 'none'` with self-only scripts, no inline code, `frame-ancestors 'none'`, HSTS, nosniff, no-referrer, minimal Permissions-Policy. No CORS headers (same-origin only).
- **Privacy:** no query text or IP is logged or stored; no cookies; no accounts.
- **Supply chain:** the app has zero third-party dependencies (stdlib only). Workflows use only official `actions/*`. Recommended: pin them to commit SHAs and turn on Dependabot for Actions.
- **Refresh safety:** a fetched page is rejected unless it looks like the real RBI page, so a block page can never overwrite good data. Changes arrive as a pull request; merging (human review) is the only path to production.

## Repository settings to turn on (cannot be set from code)
1. Branch protection on `main`: require pull request and passing `ci`; no force pushes.
2. Settings > Actions > General > "Allow GitHub Actions to create and approve pull requests" (so the weekly refresh can open its PR).
3. Secret scanning and push protection; Dependabot alerts.
4. Vercel: Firewall rate-limit rule on `/api/*`; set `KYC_LLM_ENABLED` only if you add a key.

## Reporting
Open a private security advisory on the GitHub repository.
