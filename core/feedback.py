"""User feedback ("this is not correct") -> a GitHub issue in a PRIVATE repo, so it can be triaged and turned into tests.

Privacy/security rules (see SECURITY.md):
  * opt-in only: the UI sends feedback only when the user presses the button, and tells them what is sent
  * we store: the question text, the verdict, an optional comment, entity, and the paragraph numbers that were shown.
    We never store IP addresses, headers or anything else about the user.
  * the token lives only in the FEEDBACK_GITHUB_TOKEN environment variable (never in the repo, never sent to the browser)
  * same-origin check, strict validation, tight per-client and global rate limits, text is neutralised
    (no @mentions, no issue/PR cross-links, no markdown/HTML injection) before it reaches GitHub
"""
import json, os, re, time, urllib.request, urllib.error
from collections import defaultdict, deque

VERDICTS = {"incorrect": "Not correct", "not_expected": "Not what I expected", "helpful": "Helpful"}
MAX_BODY = 4096
PER_HOUR = int(os.environ.get("KYC_FEEDBACK_PER_HOUR", "6"))
GLOBAL_DAY = int(os.environ.get("KYC_FEEDBACK_GLOBAL_DAY", "150"))
_hits = defaultdict(deque)
_glob = {"day": None, "n": 0}


def reset_limits():
    _hits.clear(); _glob.update(day=None, n=0)


def limited(client, now=None):
    now = now or time.time()
    day = int(now // 86400)
    if _glob["day"] != day:
        _glob.update(day=day, n=0)
    if _glob["n"] >= GLOBAL_DAY:
        return True
    q = _hits[client]
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= PER_HOUR:
        return True
    q.append(now); _glob["n"] += 1
    if len(_hits) > 5000:
        for k in list(_hits)[:1000]:
            _hits.pop(k, None)
    return False


def clean(text, n):
    """Strip control characters and neutralise anything GitHub would turn into a mention, link or markup."""
    text = re.sub(r"[\x00-\x1f\x7f]", " ", text or "")
    text = re.sub(r"\s+", " ", text).strip()[:n]
    text = text.replace("@", "@​").replace("#", "#​").replace("<", "&lt;").replace(">", "&gt;").replace("`", "'")
    text = re.sub(r"(?i)\b(https?|ftp)://", lambda m: m.group(1) + "[:]//", text)
    return text


def validate(data):
    """Return (clean_payload, error)."""
    if not isinstance(data, dict):
        return None, "Body must be a JSON object."
    q, v = data.get("question"), data.get("verdict")
    if not isinstance(q, str) or not 1 <= len(q.strip()) <= 400:
        return None, "question must be 1-400 characters."
    if v not in VERDICTS:
        return None, "verdict must be one of: " + ", ".join(VERDICTS)
    c = data.get("comment", "")
    if not isinstance(c, str) or len(c) > 500:
        return None, "comment must be at most 500 characters."
    ent = data.get("entity")
    if ent not in (None, "", "nbfc", "commercial_banks"):
        return None, "invalid entity."
    paras = data.get("shown", [])
    if not isinstance(paras, list) or len(paras) > 8 or not all(isinstance(p, str) and re.fullmatch(r"[A-Za-z0-9.\-]{1,12}", p) for p in paras):
        return None, "invalid shown list."
    status = data.get("status", "answered")
    if status not in ("answered", "refused", "out_of_scope"):
        return None, "invalid status."
    return {"question": clean(q, 400), "verdict": v, "comment": clean(c, 500), "entity": ent or "both",
            "shown": paras, "status": status}, None


def build_issue(p):
    title = f"[{p['verdict']}] {p['question'][:70]}"
    body = (f"**Verdict:** {VERDICTS[p['verdict']]}\n\n**Question:** {p['question']}\n\n**Entity filter:** {p['entity']}  \n"
            f"**Assistant status:** {p['status']}  \n**Paragraphs shown (top results):** {', '.join(p['shown']) or 'none'}\n\n"
            f"**What the user expected / comment:** {p['comment'] or '(none)'}\n\n---\n"
            "Triage: if the answer was wrong, add the question and the RBI facts a correct answer needs to `data/eval_paraphrases.json`, "
            "then fix `data/vocabulary.json` or ranking until `scripts/eval_retrieval.py` passes.")
    return {"title": title, "body": body, "labels": ["feedback", p["verdict"]]}


def submit(payload, opener=urllib.request.urlopen):
    token = os.environ.get("FEEDBACK_GITHUB_TOKEN", "")
    repo = os.environ.get("FEEDBACK_REPO", "")
    if not token or not re.fullmatch(r"[\w.-]+/[\w.-]+", repo):
        return 503, {"error": "Feedback is not switched on for this site yet."}
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}/issues", data=json.dumps(build_issue(payload)).encode(),
                                 headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                                          "Content-Type": "application/json", "User-Agent": "rbi-kyc-assistant-feedback",
                                          "X-GitHub-Api-Version": "2022-11-28"}, method="POST")
    try:
        with opener(req, timeout=6) as r:
            return (200, {"ok": True}) if r.status in (200, 201) else (502, {"error": "Could not save feedback."})
    except (urllib.error.URLError, TimeoutError, OSError):
        return 502, {"error": "Could not save feedback right now. Please try again later."}
