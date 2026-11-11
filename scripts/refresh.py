#!/usr/bin/env python3
"""Check the official RBI pages for changes; write new snapshots; never publish anything itself.

Run by the scheduled GitHub Action, which opens a pull request. A human reviews and merges the PR
(that merge is the only thing that redeploys the site). Exit codes: 0 no change, 10 changed, 2 fetch failure.
Safety: a response is only accepted if it looks like the real RBI page (size and markers); block pages,
captchas or HTML error pages are rejected so a bad fetch can never overwrite good data.
Stdlib only.
"""
import hashlib, html, json, re, subprocess, sys, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = "rbi-kyc-assistant-refresh/0.1 (+https://github.com/bharamprashant/rbi-kyc-assistant)"
MARKERS = ("Official Website of Reserve Bank of India", "Reserve Bank of India")


def fingerprint(page):
    """Hash of the visible content only, so dynamic page furniture does not cause false changes."""
    start = page.find("In order to prevent")
    end = page.rfind("lblGetLastUpdateDate")
    body = page[start if start > 0 else 0: end if end > 0 else len(page)]
    body = re.sub(r"<script.*?</script>|<style.*?</style>", "", body, flags=re.S)
    text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", body)))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read().decode("utf-8", errors="replace")


def main():
    pages = json.loads((ROOT / "sources_pages.json").read_text())
    changed, failed = [], []
    for p in pages:
        dest = ROOT / "raw_html" / p["file"]
        try:
            new = fetch(p["url"])
        except Exception as e:
            failed.append((p["file"], str(e)[:100])); continue
        if len(new) < 50_000 or not any(m in new for m in MARKERS) or "captcha" in new.lower()[:5000]:
            failed.append((p["file"], "response does not look like the RBI page")); continue
        old = dest.read_text(encoding="utf-8") if dest.exists() else ""
        if old and fingerprint(old) == fingerprint(new):
            continue
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        dest.write_text(f"<!-- source: {p['url'].rsplit('/', 1)[-1]} saved {stamp} -->\n{new}", encoding="utf-8")
        changed.append(p["file"])
    print(f"checked {len(pages)} pages: {len(changed)} changed, {len(failed)} failed, {len(pages) - len(changed) - len(failed)} unchanged")
    for f, why in failed:
        print(f"FAILED {f}: {why}", file=sys.stderr)
    if changed:
        for s in ("parse_directions.py", "build_changelog.py", "build_faqs.py"):
            subprocess.run([sys.executable, "-I", str(ROOT / "scripts" / s)], check=True)
        print("CHANGED: " + ", ".join(changed))
    if failed and not changed:
        return 2
    return 10 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
