"""Shared, testable request logic for the serverless endpoints (moved from api/ so the runtime can always import it) (no framework, stdlib only).

Security properties implemented here (see SECURITY.md):
  * strict input validation: method, content type, body size, length, control chars, whitelists
  * per-client and global rate limits (in-memory, best effort per serverless instance)
  * no secrets here; the optional LLM key is read from the environment inside core/llm.py only
  * no query text or client IP is logged
  * responses never echo raw user input; clients must render with textContent
"""
import json, os, re, time
from collections import defaultdict, deque

from core.search import Index
from core import changes as changes_mod
from core import llm

MAX_BODY = 2048
MAX_QUERY = 400
ENTITIES = {"nbfc": "NBFC", "commercial_banks": "Commercial Banks"}
PER_MIN = int(os.environ.get("KYC_RATE_PER_MIN", "12"))
PER_DAY = int(os.environ.get("KYC_RATE_PER_DAY", "150"))
GLOBAL_DAY = int(os.environ.get("KYC_RATE_GLOBAL_DAY", "3000"))
DISCLAIMER = ("Information from RBI's published Directions, not legal advice. Always check the linked RBI source "
              "and your regulated entity's compliance team before acting.")

_INDEX = None
_hits = defaultdict(deque)
_global = {"day": None, "n": 0}


def index():
    global _INDEX
    if _INDEX is None:
        _INDEX = Index.load()
    return _INDEX


def reset_limits():
    _hits.clear(); _global.update(day=None, n=0)


def rate_limited(client, now=None):
    """True if the request must be rejected. Sliding minute window + daily caps."""
    now = now or time.time()
    day = int(now // 86400)
    if _global["day"] != day:
        _global.update(day=day, n=0)
    if _global["n"] >= GLOBAL_DAY:
        return True
    q = _hits[client]
    while q and now - q[0] > 86400:
        q.popleft()
    if len(q) >= PER_DAY or sum(1 for t in q if now - t <= 60) >= PER_MIN:
        return True
    q.append(now); _global["n"] += 1
    if len(_hits) > 5000:                       # bound memory
        for k in list(_hits)[:1000]:
            _hits.pop(k, None)
    return False


def client_id(headers):
    xff = headers.get("x-forwarded-for", "")
    return (xff.split(",")[-1].strip() or headers.get("x-real-ip", "") or "unknown")[:64]


def _resp(status, payload, extra=None):
    h = {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
    h.update(extra or {})
    return status, h, json.dumps(payload, ensure_ascii=False).encode("utf-8")


def handle_ask(method, headers, body, now=None):
    headers = {k.lower(): v for k, v in headers.items()}
    if method != "POST":
        return _resp(405, {"error": "Use POST."}, {"Allow": "POST"})
    if "application/json" not in headers.get("content-type", ""):
        return _resp(415, {"error": "Content-Type must be application/json."})
    if len(body) > MAX_BODY:
        return _resp(413, {"error": "Request too large."})
    if rate_limited(client_id(headers), now):
        return _resp(429, {"error": "Too many requests. Please try again later."}, {"Retry-After": "60"})
    try:
        data = json.loads(body.decode("utf-8"))
        q = data["question"]; ent = data.get("entity") or None; hist = data.get("include_historical", False)
    except (ValueError, KeyError, TypeError, UnicodeDecodeError, AttributeError):
        return _resp(400, {"error": "Body must be JSON with a 'question' string."})
    if not isinstance(q, str) or not isinstance(hist, bool) or (ent is not None and ent not in ENTITIES):
        return _resp(400, {"error": "Invalid field types or entity."})
    q = re.sub(r"[\x00-\x1f\x7f]", " ", q).strip()
    if not q or len(q) > MAX_QUERY:
        return _resp(400, {"error": f"Question must be 1-{MAX_QUERY} characters."})
    res = index().search(q, entity=ENTITIES.get(ent), include_historical=hist)
    res["disclaimer"] = DISCLAIMER
    res["answer"] = summarise(res)
    if res["status"] == "answered":
        gen = llm.summarise(q, res["results"])
        if gen:
            res["summary"] = gen; res["summary_is_ai_generated"] = True
    return _resp(200, res)


def summarise(res):
    """Extractive answer: the top RBI passage, trimmed at a sentence boundary. No generated text."""
    if res["status"] != "answered":
        return res.get("reason", "")
    top = res["results"][0]
    text = re.sub(r"\s+", " ", top["text"]).strip()
    if len(text) > 700:
        cut = text[:700]; cut = cut[: max(cut.rfind(". "), 400) + 1]; text = cut + " …"
    return f"RBI says ({top['doc_title']}, paragraph {top['para_no']}): {text}"


def handle_changes(method, headers, query_string):
    if method != "GET":
        return _resp(405, {"error": "Use GET."}, {"Allow": "GET"})
    headers = {k.lower(): v for k, v in headers.items()}
    if rate_limited(client_id(headers)):
        return _resp(429, {"error": "Too many requests. Please try again later."}, {"Retry-After": "60"})
    from urllib.parse import parse_qs
    qs = parse_qs(query_string or "", max_num_fields=5)
    ent = (qs.get("entity") or [None])[0]; since = (qs.get("since") or [None])[0]
    hist = (qs.get("include_historical") or ["false"])[0] == "true"
    if ent is not None and ent not in ENTITIES:
        return _resp(400, {"error": "Invalid entity."})
    if since is not None and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", since):
        return _resp(400, {"error": "since must be YYYY-MM-DD."})
    return _resp(200, {"changes": changes_mod.timeline(ENTITIES.get(ent), since, hist), "disclaimer": DISCLAIMER})
