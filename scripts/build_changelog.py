#!/usr/bin/env python3
"""Write data/CHANGELOG.md (human review aid) from the change registry. Run after parse_directions.py."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from core.changes import timeline

vers = json.loads((ROOT / "data" / "versions.json").read_text())
lines = ["# RBI KYC change log (generated, do not edit)", "",
         "Newest first. The newest RBI circular controls; 2016 Master Direction entries are historical context only.", "",
         "## Document versions", ""]
for v in vers:
    lines.append(f"- **{v['title']}**: version {v['version']} ({v['status']}); snapshot saved {v['snapshot_saved_at']}; sha256 `{v['snapshot_sha256'][:12]}`")
leg = next((v["colour_legend"] for v in vers if v["colour_legend"]), {})
lines += ["", "## 2016 page colour legend (read from the RBI page)", ""] + [f"- {c}: {d}" for c, d in sorted(leg.items(), key=lambda x: x[1], reverse=True)]
lines += ["", "## Changes by date", ""]
for e in timeline():
    tag = "HISTORICAL (2016, repealed)" if e["status"] == "historical" else "CURRENT"
    paras = ", ".join(f"{p['para_no']} ({p['kind'].split(' ')[0]})" for p in e["paragraphs"])
    lines.append(f"- **{e['date']}** · {tag} · {e['doc_title']} · paragraphs {paras}")
    for i in e["instruments"][:2]:
        lines.append(f"    - {i}")
(ROOT / "data" / "CHANGELOG.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("wrote data/CHANGELOG.md", len(lines), "lines")
