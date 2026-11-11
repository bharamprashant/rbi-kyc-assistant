"""Retrieval over the parsed RBI KYC corpus. Pure stdlib, no network, no secrets.

Design rules (also enforced by tests):
  * Answer only from retrieved RBI text; refuse when nothing relevant is found.
  * Scope: NBFCs and Commercial Banks only. Other entity types are refused as out of scope.
  * Newest controlling text wins: current (2025 Directions as amended) > amendment
    circulars > historical (2016 Master Direction, repealed). Historical text is only
    returned when asked for ("what changed" / include_historical) and is always labelled.
"""
import json, math, re
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"

STOP = set("""a an the of to in on for and or is are be by with as at from that this it its if any shall
what which who whom how does do can may must should would not no per under into than then there their
these those such other also all about i we you your our me my""".split())
SYN = {"vcip": ["videobased", "video"], "videokyc": ["vcip", "video"], "aadhar": ["aadhaar"],
       "ckyc": ["ckycr"], "kyc": ["kyc"], "ubo": ["beneficial", "owner"], "pep": ["politically", "exposed"],
       "edd": ["enhanced", "due", "diligence"], "sdd": ["simplified", "due", "diligence"],
       "cdd": ["customer", "due", "diligence"], "str": ["suspicious", "transaction"], "fiu": ["financial", "intelligence"]}
OUT_OF_SCOPE = [  # entity types the project deliberately does not cover
    (r"small\s+finance\s+bank|\bsfb\b", "Small Finance Banks"),
    (r"payments?\s+bank", "Payments Banks"),
    (r"local\s+area\s+bank", "Local Area Banks"),
    (r"regional\s+rural\s+bank|\brrb\b", "Regional Rural Banks"),
    (r"co-?operative\s+bank|\bucb\b", "Co-operative Banks"),
    (r"housing\s+finance|\bhfc\b", "Housing Finance Companies"),
    (r"asset\s+reconstruction|\barc\b", "Asset Reconstruction Companies"),
    (r"all\s+india\s+financial\s+institution|\baifi\b", "All India Financial Institutions"),
]
STATUS_WEIGHT = {"current": 1.0, "amendment": 0.95, "historical": 0.55}
MIN_SCORE = 4.0       # below this top score => refuse
MIN_COVERAGE = 0.5    # share of query terms that must appear in the best chunk


def stem(w):
    for suf in ("ations", "ation", "ings", "ing", "ies", "ied", "es", "ed", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)] + ("y" if suf in ("ies", "ied") else "")
    return w


def tokens(text, keep_stop=False):
    text = text.lower().replace("v-cip", "vcip").replace("e-kyc", "ekyc").replace("video kyc", "vcip")
    out = []
    for w in re.findall(r"[a-z0-9]+", text):
        if not keep_stop and (w in STOP or len(w) < 2):
            continue
        out.append(stem(w))
    return out


def expand(q_tokens):
    out = list(q_tokens)
    for t in q_tokens:
        out += [stem(x) for x in SYN.get(t, [])]
    return out


class Index:
    def __init__(self, chunks):
        self.chunks = chunks
        self.docs = []
        for c in chunks:
            body = tokens(c["text"]) + 2 * tokens(c.get("section", "")) + tokens(c.get("chapter", ""))
            self.docs.append(Counter(body))
        self.len = [sum(d.values()) for d in self.docs]
        self.avg = sum(self.len) / max(1, len(self.len))
        df = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    @classmethod
    def load(cls, path=None):
        path = Path(path) if path else DATA / "chunks.jsonl"
        with open(path, encoding="utf-8") as fh:
            return cls([json.loads(l) for l in fh if l.strip()])

    def score(self, i, q, k1=1.5, b=0.75):
        d, dl, s = self.docs[i], self.len[i], 0.0
        for t in q:
            f = d.get(t, 0)
            if f:
                s += self.idf.get(t, 0) * f * (k1 + 1) / (f + k1 * (1 - b + b * dl / self.avg))
        return s

    def search(self, query, entity=None, include_historical=False, k=5):
        """Return dict: status answered|refused|out_of_scope, results [...]."""
        ql = query.lower()
        for pat, name in OUT_OF_SCOPE:
            if re.search(pat, ql) and not re.search(r"nbfc|non-?banking|commercial\s+bank", ql):
                return {"status": "out_of_scope", "reason": f"This assistant covers NBFCs and Commercial Banks only; {name} are not covered.", "results": []}
        q_raw = tokens(query)
        if not q_raw:
            return {"status": "refused", "reason": "Please ask a question about RBI KYC requirements.", "results": []}
        q = list(dict.fromkeys(expand(q_raw)))
        scored = []
        for i, c in enumerate(self.chunks):
            if c["status"] == "historical" and not include_historical:
                continue
            if entity and c["entity"] not in (entity, "All REs (pre-consolidation)"):
                continue
            s = self.score(i, q) * STATUS_WEIGHT[c["status"]]
            if s > 0:
                scored.append((s, c.get("last_amended") or "", i))
        scored.sort(key=lambda x: (-round(x[0], 6), x[1]), reverse=False)
        if not scored:
            return {"status": "refused", "reason": "No relevant RBI text found for this question.", "results": []}
        top = scored[0]
        top_terms = set(self.docs[top[2]])
        coverage = sum(1 for t in set(q_raw) if t in top_terms) / len(set(q_raw))
        if top[0] < MIN_SCORE or coverage < MIN_COVERAGE:
            return {"status": "refused", "reason": "I could not find text in the RBI KYC Directions that answers this. Try rephrasing, or check the Directions directly.", "results": []}
        return {"status": "answered", "coverage": round(coverage, 2), "results": [self.cite(self.chunks[i], s) for s, _, i in scored[:k]]}

    @staticmethod
    def cite(c, score):
        return {
            "score": round(score, 2), "id": c["id"], "doc_key": c["doc_key"], "doc_title": c["doc_title"],
            "entity": c["entity"], "status": c["status"], "chapter": c.get("chapter"), "section": c.get("section"),
            "para_no": c["para_no"], "version": c.get("version"), "last_amended": c.get("last_amended"),
            "change_dates": c.get("change_dates", []),
            "amendments": [{"kind": a["kind"], "date": a["date"], "instrument": a["instrument"], "url": a["url"]} for a in c.get("amendments", [])],
            "source_url": c["source_url"], "text": c["text"],
        }
