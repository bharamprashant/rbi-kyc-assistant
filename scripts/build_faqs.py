#!/usr/bin/env python3
"""Build data/faqs.json: quick-question suggestions that are verified against the current corpus.

Sources of questions (no user queries are ever logged or used, for privacy):
  1. data/question_bank.json  - curated questions written from topics in public KYC FAQs (RBI FAQs of 9 Jun 2025,
     lender/bank FAQ pages). A question is published only if the search answers it for BOTH NBFCs and Commercial Banks.
  2. "What's new" questions generated from the change registry (data/changes.jsonl): one per recent 2025+ amendment.
     Published only if the amended paragraph is among the top results for that question.
Re-run automatically by scripts/refresh.py whenever the RBI text changes, so suggestions follow the data.
"""
import json, re, sys
from datetime import datetime
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.search import Index  # noqa: E402

TOPICS = {"basics": "KYC basics", "documents": "Documents & identity", "onboarding": "Onboarding (V-CIP, e-KYC, digital)",
          "ckyc": "CKYC registry", "updation": "Periodic updation", "risk": "Risk & due diligence",
          "entities": "Companies, firms & trusts", "records": "Record keeping", "reporting": "Reporting (STR/CTR/FIU)",
          "nbfc": "NBFC lending", "change": "What changed"}
ENT = {"NBFC": "nbfc", "Commercial Banks": "commercial_banks"}


def main():
    ix = Index.load()
    bank = json.loads((ROOT / "data" / "question_bank.json").read_text(encoding="utf-8"))
    topics, dropped = defaultdict(list), []
    for topic, q in bank:
        tops = {}
        for ent in ENT:
            r = ix.search(q, entity=ent)
            if r["status"] != "answered":
                break
            tops[ent] = r["results"][0]
        else:
            top = tops["NBFC"]
            topics[topic].append({"q": q, "ref": f"para {top['para_no']}", "amended": bool(top.get("amendments")),
                                  "last_amended": top.get("last_amended")})
            continue
        dropped.append(q)
    chunks = {c["id"]: c for c in ix.chunks}
    whats_new = []
    for l in (ROOT / "data" / "changes.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(l)
        c = chunks.get(r["chunk"])
        if not c or c["status"] == "historical" or not r.get("date") or r["evidence"] != "rbi_footnote":
            continue
        ent = c["entity"]
        if ent not in ENT:
            continue
        sec = re.sub(r"^([A-Z]\.|\d+\.)\s*", "", c.get("section") or "").strip(": ") or "this provision"
        pretty = datetime.strptime(r["date"], "%Y-%m-%d").strftime("%d %B %Y").lstrip("0")
        q = f"What changed in paragraph {c['para_no']} ({sec.strip(': ')}) of the {ent} KYC Directions on {pretty}?"
        res = ix.search(q, entity=ent)
        hit = res["status"] == "answered" and any(x["id"] == c["id"] or x["para_no"] == c["para_no"] for x in res["results"][:5])
        whats_new.append({"q": q, "entity": ENT[ent], "date": r["date"], "kind": r["kind"], "para_no": c["para_no"], "verified": hit})
    whats_new = [w for w in whats_new if w["verified"]]
    whats_new.sort(key=lambda w: w["date"], reverse=True)
    versions = sorted({c["version"] for c in ix.chunks if c.get("version") and c["status"] != "historical"})
    out = {"corpus_versions": versions,
           "topics": [{"key": k, "title": TOPICS[k], "items": topics[k]} for k in TOPICS if topics[k]],
           "whats_new": whats_new[:8]}
    (ROOT / "data" / "faqs.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    n = sum(len(t["items"]) for t in out["topics"])
    print(f"faqs: {n} verified questions, {len(out['whats_new'])} what's-new, {len(dropped)} dropped")
    for q in dropped:
        print("DROPPED:", q, file=sys.stderr)


if __name__ == "__main__":
    main()
