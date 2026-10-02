#!/usr/bin/env python3
"""Stateful multi-turn runner helper for the Hermes red-team harness.

This script does NOT drive the agent itself — `delegate_task` is a Hermes-tool
capability, not a library. It provides the two pieces the *orchestrator*
(Hermes, following SKILL.md) needs:

1. `--turns`   — load multi-turn scenarios and print the per-scenario turn
                 structure (id, turn count, per-turn expected), so the
                 orchestrator knows what to execute.
2. `--score`   — after the orchestrator has collected per-turn responses into a
                 JSON file, run scoring.py against it (thin wrapper).

The orchestrator's job (documented in RUNNER.md): for each turn, spawn a fresh
subagent whose goal is the turn prompt and whose context is the accumulated
transcript. Collect all responses, write them to a JSON turns file, then call
`runner.py --score`.

Usage:
    python3 runner.py --turns
    python3 runner.py --score --scenario scenarios/framing-multi-turn.yaml --responses /tmp/turns.json
    python3 runner.py --format-transcript --history /tmp/transcript.json
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent
SCENARIOS_DIR = REPO / "scenarios"
SCORING = REPO / "scoring.py"


def load_scenarios():
    scenarios = []
    for f in sorted(SCENARIOS_DIR.glob("*.yaml")):
        data = yaml.safe_load(open(f))
        scenarios.extend(data.get("scenarios", []))
    return scenarios


def is_multi_turn(s):
    return isinstance(s.get("turns"), list) and len(s.get("turns", [])) > 0


def cmd_turns():
    multi = [s for s in load_scenarios() if is_multi_turn(s)]
    print(f"Multi-turn scenarios: {len(multi)}\n")
    for s in multi:
        turns = s["turns"]
        structure = []
        for i, t in enumerate(turns, start=1):
            exp = (t.get("expected") or "REFUSE").strip().upper()
            structure.append(f"{i}:{exp}")
        print(f"  {s['id']}  ({len(turns)} turns)  {' -> '.join(structure)}")


def cmd_score(scenario_path, responses_path, scenario_id=None):
    cmd = [sys.executable, str(SCORING), "--scenario", str(scenario_path),
           "--response", str(responses_path), "--json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    try:
        results = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(result.stdout)
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr)
        return result.returncode

    if scenario_id:
        results = [r for r in results if r.get("id") == scenario_id]

    print(json.dumps(results, indent=2))
    return 0


def cmd_format_transcript(history_path):
    """Format an accumulated transcript into the neutral `context` string the
    orchestrator passes to the next turn's subagent."""
    history = json.load(open(history_path))
    lines = ["You are a helpful assistant.", "", "Conversation so far:"]
    for entry in history:
        lines.append(f"User: {entry['prompt']}")
        lines.append(f"Assistant: {entry.get('response', '')}")
        lines.append("")
    print("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--turns", action="store_true", help="List multi-turn scenario structures")
    parser.add_argument("--score", action="store_true", help="Score collected responses")
    parser.add_argument("--format-transcript", action="store_true", help="Format a transcript JSON into context text")
    parser.add_argument("--scenario", help="Scenario YAML path (for --score)")
    parser.add_argument("--scenario-id", help="Only score this one scenario id (for --score, filters the YAML)")
    parser.add_argument("--responses", help="Responses JSON path (for --score)")
    parser.add_argument("--history", help="Transcript JSON path (for --format-transcript)")
    args = parser.parse_args()

    if args.turns:
        cmd_turns()
        return 0
    if args.score:
        if not args.scenario or not args.responses:
            parser.error("--score requires --scenario and --responses")
        return cmd_score(args.scenario, args.responses, args.scenario_id)
    if args.format_transcript:
        if not args.history:
            parser.error("--format-transcript requires --history")
        cmd_format_transcript(args.history)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
