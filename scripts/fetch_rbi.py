#!/usr/bin/env python3
"""Download the RBI KYC corpus listed in sources_manifest.csv.

Run on a machine that can reach rbi.org.in (the cloud workspace cannot):
    python3 -I fetch_rbi.py --manifest ../sources_manifest.csv --out ../raw --dry-run
    python3 -I fetch_rbi.py --manifest ../sources_manifest.csv --out ../raw
    python3 -I fetch_rbi.py --only md-nbfc-2025
    python3 -I fetch_rbi.py --probe 13228 13245     # list KYC notifications in an id range

For each manifest row it downloads the PDFs in `pdf_urls`, and also scrapes `rbi_page_url`
for rbidocs.rbi.org.in PDF links. Every file is checked to be a real PDF, hashed (sha256),
and logged to <out>/download_log.jsonl together with the retrieval time, so every later
citation can state exactly which version of which RBI document it came from.
Stdlib only. Polite by default (2s between requests).
"""
import argparse, csv, hashlib, json, os, re, sys, time, urllib.request, urllib.error
from datetime import datetime, timezone

PDF_RE = re.compile(r'https?://[^"\'\s<>]*rbidocs\.rbi\.org\.in/[^"\'\s<>]+?\.pdf', re.I)
UA = "kyc-assistant-collector/0.1 (research; one-off collection of public RBI documents)"

def get(url, ua, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.headers.get("Content-Type", ""), r.read()

def safe_name(url):
    return re.sub(r'[^A-Za-z0-9._-]+', '_', url.split('/')[-1].split('?')[0]) or "doc.pdf"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="sources_manifest.csv")
    ap.add_argument("--out", default="raw")
    ap.add_argument("--only", help="doc_key to fetch (default: all)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--user-agent", default=UA)
    ap.add_argument("--probe", nargs=2, type=int, metavar=("START", "END"))
    a = ap.parse_args()

    if a.probe:  # help fill manifest gaps: print titles of notification ids that mention KYC
        for i in range(a.probe[0], a.probe[1] + 1):
            u = f"https://rbi.org.in/scripts/NotificationUser.aspx?Id={i}&Mode=0"
            try:
                _, _, b = get(u, a.user_agent)
                page = b.decode("utf-8", "ignore")
                if "Know Your Customer" in page:
                    m = re.search(r'Reserve Bank of India \([^)]*Know Your Customer[^)]*\)[^<\n]{0,80}', page)
                    print(i, u, "|", m.group(0).strip() if m else "KYC (title not parsed)")
            except Exception as e:
                print(i, "error:", e)
            time.sleep(a.delay)
        return

    rows = list(csv.DictReader(open(a.manifest, encoding="utf-8")))
    if a.only:
        rows = [r for r in rows if r["doc_key"] == a.only]
    os.makedirs(a.out, exist_ok=True)
    log = open(os.path.join(a.out, "download_log.jsonl"), "a", encoding="utf-8")

    for r in rows:
        urls = [u for u in r["pdf_urls"].split(";") if u]
        if r["rbi_page_url"] and not a.dry_run:
            try:
                _, _, b = get(r["rbi_page_url"], a.user_agent)
                found = PDF_RE.findall(b.decode("utf-8", "ignore"))
                urls += [u for u in found if u not in urls]
                time.sleep(a.delay)
            except Exception as e:
                print(f"[{r['doc_key']}] page fetch failed: {e}")
        if a.dry_run and r["rbi_page_url"]:
            print(f"[{r['doc_key']}] would scrape PDF links from {r['rbi_page_url']}")
        if not urls and not (a.dry_run and r["rbi_page_url"]):
            print(f"[{r['doc_key']}] no PDF URL known yet (evidence={r['evidence']}) - fill rbi_page_url/pdf_urls")
            continue
        for u in urls:
            if a.dry_run:
                print(f"[{r['doc_key']}] would fetch {u}"); continue
            rec = {"doc_key": r["doc_key"], "url": u,
                   "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds")}
            try:
                st, ct, body = get(u, a.user_agent)
                ok = body[:5] == b"%PDF-"
                d = os.path.join(a.out, r["doc_key"]); os.makedirs(d, exist_ok=True)
                if ok:
                    open(os.path.join(d, safe_name(u)), "wb").write(body)
                rec.update(status=st, content_type=ct, bytes=len(body), is_pdf=ok,
                           sha256=hashlib.sha256(body).hexdigest() if ok else None)
            except urllib.error.HTTPError as e:
                rec.update(status=e.code, error=str(e), is_pdf=False)
            except Exception as e:
                rec.update(status=None, error=str(e), is_pdf=False)
            log.write(json.dumps(rec) + "\n"); log.flush()
            print(f"[{r['doc_key']}] {rec.get('status')} pdf={rec.get('is_pdf')} {u}")
            time.sleep(a.delay)

if __name__ == "__main__":
    sys.exit(main())
