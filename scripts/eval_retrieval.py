#!/usr/bin/env python3
"""Retrieval quality report: for every phrasing in data/eval_paraphrases.json (and RBI-FAQ probes) check that the facts
a correct answer must contain appear in the top-5 passages, for both entities. Prints hit@5 and MRR@5 by phrasing style.
Usage: eval_retrieval.py [--min-hit 0.90] [--verbose]"""
import json, re, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.search import Index  # noqa: E402

STYLES = ["formal", "casual", "keywords", "descriptive", "typo/short"]


def evaluate(index=None, verbose=False):
    ix = index or Index.load()
    data = json.loads((ROOT / "data" / "eval_paraphrases.json").read_text(encoding="utf-8"))
    n = hit = 0; rr = 0.0; by = {s: [0, 0] for s in STYLES}; fails = []
    for t in data:
        ents = ["Commercial Banks"] if t.get("scope") == "commercial_banks" else ["NBFC", "Commercial Banks"]
        for si, q in enumerate(t["qs"]):
            for ent in ents:
                r = ix.search(q, entity=ent); n += 1; by[STYLES[si]][1] += 1
                ok = False
                if r["status"] == "answered":
                    for rank, x in enumerate(r["results"][:5], 1):
                        pass
                    # a result list passes when all facts appear across top-5 text; rank = first position where cumulative text has all facts
                    cum = ""
                    for rank, x in enumerate(r["results"][:5], 1):
                        cum += " " + x["text"]
                        if all(re.search(f, cum, re.I) for f in t["facts"]):
                            ok = True; rr += 1.0 / rank; break
                if ok:
                    hit += 1; by[STYLES[si]][0] += 1
                else:
                    fails.append((t["topic"], ent, q, r["status"], [x["para_no"] for x in r.get("results", [])[:5]]))
    return {"n": n, "hit": hit / n, "mrr": rr / n, "by_style": {s: (v[0] / v[1] if v[1] else None) for s, v in by.items()}, "fails": fails}


if __name__ == "__main__":
    res = evaluate()
    print(f"queries={res['n']} hit@5={res['hit']:.3f} MRR@5={res['mrr']:.3f}")
    print("by style:", {k: round(v, 2) for k, v in res["by_style"].items() if v is not None})
    if "--verbose" in sys.argv:
        for f in res["fails"]:
            print("FAIL", f)
    mh = float(sys.argv[sys.argv.index("--min-hit") + 1]) if "--min-hit" in sys.argv else 0
    sys.exit(0 if res["hit"] >= mh else 1)
