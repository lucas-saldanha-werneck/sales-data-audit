from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter

from .checks import REQUIRED, run_all
from .sample import make_sample


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in REQUIRED if c not in (reader.fieldnames or [])]
        if missing:
            raise SystemExit(f"Missing columns: {', '.join(missing)}")
        rows = []
        for i, r in enumerate(reader, start=2):  # line 1 is the header
            r["_line"] = i
            rows.append(r)
    return rows


def render_markdown(rows, findings):
    sev = Counter(f["severity"] for f in findings)
    score = max(0, 100 - 10 * sev["high"] - 3 * sev["medium"] - sev["low"])
    lines = ["# Sell-out data audit", "",
             f"Rows read: {len(rows)}  ",
             f"Findings: {len(findings)} (high {sev['high']}, medium {sev['medium']}, low {sev['low']})  ",
             f"Quality score: {score}/100 (simple rule: 100 - 10 per high - 3 per medium - 1 per low)", ""]
    for level in ("high", "medium", "low"):
        group = [f for f in findings if f["severity"] == level]
        if not group:
            continue
        lines.append(f"## {level.capitalize()}")
        for f in group:
            where = f" (file lines {', '.join(map(str, f['rows'][:8]))}{'...' if len(f['rows']) > 8 else ''})" if f["rows"] else ""
            lines.append(f"- **{f['check']}**: {f['message']}{where}")
        lines.append("")
    return "\n".join(lines)


def main(argv=None):
    p = argparse.ArgumentParser(prog="sales-data-audit")
    p.add_argument("csv", nargs="?", help="sell-out CSV: date,store,sku,product,units,price")
    p.add_argument("--make-sample", metavar="PATH", help="write invented example data with planted problems")
    p.add_argument("--json", action="store_true", help="print findings as JSON")
    a = p.parse_args(argv)
    if a.make_sample:
        n = make_sample(a.make_sample)
        print(f"Wrote {n} example rows to {a.make_sample}")
        return 0
    if not a.csv:
        p.error("give a CSV path or --make-sample PATH")
    rows = load(a.csv)
    findings = run_all(rows)
    print(json.dumps(findings, indent=2) if a.json else render_markdown(rows, findings))
    return 1 if any(f["severity"] == "high" for f in findings) else 0


if __name__ == "__main__":
    sys.exit(main())
