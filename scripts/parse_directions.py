#!/usr/bin/env python3
"""Parse saved RBI HTML snapshots (raw_html/) into structured, citable chunks.

Output (all generated, never hand-edited):
  data/chunks.jsonl    one chunk per numbered paragraph (+ its sub-paragraphs)
  data/changes.jsonl   one row per change event (footnote or colour-coded run)
  data/versions.json   per-document metadata (version, status, snapshot hash)

Rules encoded here:
  * Colour -> amendment date is read from the page's own legend
    ("(<span style='color: X'>Updated as on DATE</span>)"), never hard-coded.
  * Footnotes ("Inserted/Amended/Substituted/Deleted ... vide <circular> dated D")
    are attached to the paragraphs that cite them.
  * status = current | amendment | historical. The newest circular controls:
    each chunk carries last_amended (latest change date). Historical (2016) text
    is only for "what changed" questions and is never presented as current.
Stdlib only. Run:  python3 -I scripts/parse_directions.py
"""
import hashlib, html, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw_html"
OUT = ROOT / "data"

DOCS = [
    # file, doc_key, entity, status, title
    ("nbfc-kyc-2025_id12943.html", "md-nbfc-2025", "NBFC", "current",
     "RBI (NBFC - KYC) Directions, 2025"),
    ("commercial-banks-kyc-2025_id13141.html", "md-commercial-banks-2025", "Commercial Banks", "current",
     "RBI (Commercial Banks - KYC) Directions, 2025"),
    ("md-kyc-2016_id11566.html", "md-kyc-2016", "All REs (pre-consolidation)", "historical",
     "Master Direction - KYC Direction, 2016 (repealed/replaced by the 2025 entity-wise Directions)"),
    ("nbfc-kyc-amendment-2025-12-29_id13236.html", "am-nbfc-2025-12-29", "NBFC", "amendment",
     "RBI (NBFC - KYC) Amendment Directions, 2025 (29 Dec 2025)"),
    ("cb-kyc-amendment-2025-12-29_id13242.html", "am-cb-2025-12-29", "Commercial Banks", "amendment",
     "RBI (Commercial Banks - KYC) Amendment Directions, 2025 (29 Dec 2025)"),
]
MONTHS = {m: i for i, m in enumerate(
    "January February March April May June July August September October November December".split(), 1)}
DATE_RE = re.compile(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})")


def iso(text):
    m = DATE_RE.search(text or "")
    return f"{m.group(3)}-{MONTHS[m.group(1)]:02d}-{int(m.group(2)):02d}" if m else None


def clean(fragment):
    fragment = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    return re.sub(r"\s+", " ", html.unescape(fragment).replace("\xa0", " ")).strip()


def legend(src):
    """colour name -> ISO date, from the page's 'Updated as on' legend."""
    out = {}
    for m in re.finditer(r"<span[^>]*style=\"color:\s*([A-Za-z]+)\"[^>]*>\s*Updated as on ([^<]+?)\s*</span>", src):
        out[m.group(1).lower()] = iso(m.group(2))
    return out


def footnotes(src):
    notes = {}
    for m in re.finditer(r'<p class="footnote">(.*?)</p>', src, re.S):
        body = m.group(1)
        fid = re.search(r'<a id="(F[A-Z]*\d+)"', body)
        if not fid:
            continue
        text = clean(body)
        text = re.sub(r"^\d+\s*", "", text)
        link = re.search(r'href="([^"]+NotificationUser[^"]+)"', body)
        kind = re.match(r"(Inserted|Amended|Substituted|Deleted|Renumbered|Omitted|Added|Updated|Reworded)", text)
        notes[fid.group(1)] = {
            "kind": kind.group(1) if kind else "Noted",
            "text": text,
            "date": iso(text),
            "url": html.unescape(link.group(1)) if link else None,
        }
    return notes


def blocks(src):
    """Yield (kind, inner_html, css_class) in document order for the content area."""
    start = src.find("In order to prevent")
    if start < 0:
        start = src.find("Reserve Bank of India")
    end = src.rfind("lblGetLastUpdateDate")
    region = src[start:end if end > 0 else len(src)]
    items = []
    for m in re.finditer(r"<p\b([^>]*)>(.*?)</p>", region, re.S):
        cls = re.search(r'class="([^"]*)"', m.group(1))
        items.append((m.start(), m.end(), "p", m.group(2), cls.group(1) if cls else ""))
    for m in re.finditer(r"<tr\b[^>]*>(.*?)</tr>", region, re.S):
        if "<p" in m.group(1) or "<tr" in m.group(1) or len(re.findall(r"<td", m.group(1))) < 2:
            continue
        cells = [clean(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", m.group(1), re.S)]
        items.append((m.start(), m.end(), "tr", " | ".join(c for c in cells if c), ""))
    items.sort()
    for _, _, kind, inner, cls in items:
        yield kind, inner, cls


NUM_RE = re.compile(r"^\[?\s*(\d{1,3})\.\s")
CHAPTER_RE = re.compile(r"^(chapter[\s-]*[ivxl]+)\b\s*[–-]?\s*(.*)$", re.I)
MAX_CHARS = 2400


def parse(fname, doc_key, entity, status, title):
    src = (RAW / fname).read_text(encoding="utf-8")
    sha = hashlib.sha256(src.encode("utf-8")).hexdigest()
    saved = re.match(r"<!-- source: (\S+) saved (\S+) -->", src)
    upd = re.search(r"\(Updated as on ([A-Za-z]+ \d{1,2}, \d{4})\)", clean(src[:src.find('Table of Contents')] if 'Table of Contents' in src else src))
    leg = legend(src)
    notes = footnotes(src)
    chunks, changes = [], []
    chapter = section = ""
    cur = None
    last_num = "intro"

    def flush():
        nonlocal cur
        if cur and cur["text"].strip():
            lines = cur["text"].strip().split("\n")
            groups, buf, start = [], [], 0
            for idx, ln in enumerate(lines):
                if buf and sum(len(x) for x in buf) + len(ln) > MAX_CHARS:
                    groups.append((start, idx)); buf, start = [], idx
                buf.append(ln)
            groups.append((start, len(lines)))
            for n, (a, b) in enumerate(groups, 1):
                c = {k: v for k, v in cur.items() if k not in ("_am", "_col")}
                c.update(text="\n".join(lines[a:b]), part=n, parts=len(groups),
                         amendments=[ev for i, ev in cur["_am"] if a <= i < b],
                         colour_dates=sorted({d for i, d in cur["_col"] if a <= i < b}))
                chunks.append(c)
        cur = None

    for kind, inner, cls in blocks(src):
        text = clean(inner)
        if not text:
            continue
        if kind == "p" and "footnote" in cls:
            continue
        if kind == "p" and "head" in cls:
            m = CHAPTER_RE.match(text)
            hn = NUM_RE.match(text)
            if m:
                flush(); chapter = text; section = ""
            elif hn:   # numbered paragraph titles are heads on the RBI pages
                flush(); last_num = hn.group(1)
                cur = {"para_no": last_num, "chapter": chapter, "section": text, "text": text,
                       "_am": [], "_col": []}
            else:
                flush(); section = text
            continue
        # paragraph-level change evidence
        refs = []
        for m in re.finditer(r'<sup[^>]*title="([^"]*)"[^>]*>\s*<a[^>]*href="#(F[A-Z]*\d+)"', inner):
            refs.append((m.group(2), html.unescape(m.group(1))))
        for m in re.finditer(r'<a[^>]*href="#(F[A-Z]*\d+)"[^>]*>\s*(?:<sup>)?\d+', inner):
            if m.group(1) not in [r[0] for r in refs]:
                refs.append((m.group(1), ""))
        colours = sorted({c.lower() for c in re.findall(r'<span[^>]*style="color:\s*([A-Za-z]+)"', inner)
                          if c.lower() in leg})
        num = NUM_RE.match(text) if kind == "p" else None
        if num or cur is None or kind == "tr" and (cur is None or cur.get("para_no") != "table"):
            flush()
            if num:
                last_num = num.group(1)
            cur = {"para_no": last_num if (num or kind == "p") else "table",
                   "chapter": chapter, "section": section, "text": "", "_am": [], "_col": []}
        line_idx = cur["text"].count("\n") + 1 if cur["text"] else 0
        cur["text"] += ("\n" if cur["text"] else "") + text
        cur["continuation"] = not bool(num) and cur["text"] != text
        for fid, tip in refs:
            n = notes.get(fid, {})
            ev = {"footnote": fid, "kind": n.get("kind") or (tip.split(" ")[0] if tip else "Noted"),
                  "date": n.get("date") or iso(tip), "instrument": n.get("text") or tip, "url": n.get("url")}
            if (line_idx, ev) not in cur["_am"]:
                cur["_am"].append((line_idx, ev))
        for c in colours:
            d = leg[c]
            cur["_col"].append((line_idx, d))
    flush()

    version = upd.group(1) if upd else None
    if status == "historical" and leg:
        version = max(leg.values())
    out = []
    for i, c in enumerate(chunks, 1):
        dates = [a["date"] for a in c["amendments"] if a["date"]] + c["colour_dates"]
        c["last_amended"] = max(dates) if dates else (iso(title) if status == "amendment" else None)
        c["change_dates"] = sorted(set(dates))
        c.update({
            "id": f"{doc_key}:{i:04d}", "doc_key": doc_key, "doc_title": title, "entity": entity,
            "status": status, "version": version,
            "source_url": f"https://www.rbi.org.in/Scripts/{src_page(src)}",
            "snapshot_sha256": sha, "version_iso": (iso(upd.group(1)) if upd else None),
        })
        out.append(c)
        for a in c["amendments"]:
            changes.append({"doc_key": doc_key, "chunk": c["id"], "para_no": c["para_no"], "date": a["date"],
                            "kind": a["kind"], "instrument": a["instrument"], "evidence": "rbi_footnote"})
        for d in c["colour_dates"]:
            changes.append({"doc_key": doc_key, "chunk": c["id"], "para_no": c["para_no"], "date": d,
                            "kind": "Amended (colour-coded on RBI page)", "instrument": f"Updated as on {d}",
                            "evidence": "rbi_page_colour_legend"})
    meta = {"doc_key": doc_key, "title": title, "entity": entity, "status": status,
            "version": version, "snapshot_file": fname, "snapshot_sha256": sha, "version_iso": (iso(upd.group(1)) if upd else None),
            "snapshot_saved_at": saved.group(2) if saved else None, "source_url": f"https://www.rbi.org.in/Scripts/{src_page(src)}",
            "colour_legend": leg, "footnotes": len(notes), "chunks": len(out)}
    return out, changes, meta


def src_page(src):
    m = re.match(r"<!-- source: (\S+) saved", src)
    return m.group(1) if m else ""


def main():
    OUT.mkdir(exist_ok=True)
    all_chunks, all_changes, metas = [], [], []
    for d in DOCS:
        if not (RAW / d[0]).exists():
            print("missing", d[0], file=sys.stderr); continue
        c, ch, m = parse(*d)
        all_chunks += c; all_changes += ch; metas.append(m)
        print(f"{d[1]:28s} chunks={m['chunks']:4d} footnotes={m['footnotes']:3d} version={m['version']}")
    (OUT / "chunks.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in all_chunks) + "\n", encoding="utf-8")
    (OUT / "changes.jsonl").write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in all_changes) + "\n", encoding="utf-8")
    (OUT / "versions.json").write_text(json.dumps(metas, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
