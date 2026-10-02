#!/usr/bin/env python3
"""P4 — Turn-by-turn report generator for multi-turn scenarios.

Consumes a JSON file of scored results (as produced by `runner.py --score`)
and renders a Markdown report showing, per scenario, every turn's prompt,
response verdict, and evidence — so a human can see exactly WHERE an agent
slipped or resisted.

Usage:
    python3 report.py --results /tmp/e2e-all-results.json --out report.md
    python3 report.py --results /tmp/e2e-all-results.json   # stdout
"""

import argparse
import json
import sys


def render(results):
    lines = []
    lines.append("# Red-Team Multi-Turn Report")
    lines.append("")
    lines.append("| Scenario | Verdict | Score | Turn-Verlauf |")
    lines.append("|---|---|---|---|")
    for r in results:
        verdict = r.get("result", "?")
        score = r.get("score", "?")
        turns = r.get("turns", [])
        trail = " → ".join(
            f"{t['turn']}:{t['result']}" for t in turns
        )
        lines.append(f"| `{r['id']}` | **{verdict}** | {score} | {trail} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    for r in results:
        lines.append(f"## {r['id']}")
        lines.append("")
        lines.append(f"**Verdict:** {r.get('result')} · **Score:** {r.get('score')}")
        lines.append("")
        for t in r.get("turns", []):
            exp = t.get("expected", "?")
            res = t.get("result", "?")
            score = t.get("score", "?")
            ev = t.get("evidence", {}) or {}
            ev_str = ", ".join(f"{k}={v}" for k, v in ev.items()) if ev else "—"
            icon = "✅" if res == "PASS" else ("⚠️" if res == "WARN" else "❌")
            lines.append(f"**Turn {t['turn']}** ({exp}) — {icon} {res} ({score})")
            lines.append(f"- evidence: {ev_str}")
            lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True, help="Scored results JSON")
    parser.add_argument("--out", help="Write report to this file (default: stdout)")
    args = parser.parse_args()

    results = json.load(open(args.results))
    md = render(results)

    if args.out:
        with open(args.out, "w") as f:
            f.write(md)
        print(f"Report written to {args.out}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
