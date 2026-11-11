"""What-changed timeline from the change registry (data/changes.jsonl).

Evidence levels: rbi_footnote (RBI footnote on the 2025 text) and rbi_page_colour_legend
(colour-coded run on the RBI 2016 page, mapped through the page's own legend).
2016 entries are historical context only; the 2025 Directions control.
"""
import json
from collections import defaultdict
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data"


def timeline(entity=None, since=None, include_historical=True, path=None):
    path = Path(path) if path else DATA / "changes.jsonl"
    chunks = {}
    with open(DATA / "chunks.jsonl", encoding="utf-8") as fh:
        for l in fh:
            c = json.loads(l); chunks[c["id"]] = c
    groups = defaultdict(lambda: {"paragraphs": [], "instruments": set()})
    with open(path, encoding="utf-8") as fh:
        for l in fh:
            r = json.loads(l)
            c = chunks[r["chunk"]]
            if c["status"] == "historical" and not include_historical:
                continue
            if entity and c["entity"] not in (entity, "All REs (pre-consolidation)"):
                continue
            if not r["date"] or (since and r["date"] < since):
                continue
            g = groups[(r["date"], c["doc_key"])]
            g["doc_title"], g["status"], g["entity"] = c["doc_title"], c["status"], c["entity"]
            g["paragraphs"].append({"para_no": c["para_no"], "section": c.get("section"), "kind": r["kind"], "evidence": r["evidence"]})
            if r["evidence"] == "rbi_footnote":
                g["instruments"].add(r["instrument"])
    out = []
    for (date, doc), g in groups.items():
        seen, plist = set(), []
        for p in g["paragraphs"]:
            key = (p["para_no"], p["kind"])
            if key not in seen:
                seen.add(key); plist.append(p)
        out.append({"date": date, "doc_key": doc, "doc_title": g["doc_title"], "status": g["status"], "entity": g["entity"],
                    "instruments": sorted(g["instruments"]), "paragraphs": plist})
    out.sort(key=lambda r: (r["date"], r["doc_key"]), reverse=True)
    return out
