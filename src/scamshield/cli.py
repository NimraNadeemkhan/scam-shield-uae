"""Command line: ``python -m scamshield "message text"`` (or pipe text on stdin)."""
from __future__ import annotations

import argparse
import json
import sys

from .engine import check_message


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="scamshield", description=__doc__)
    parser.add_argument("message", nargs="?", help="message text (reads stdin if omitted)")
    parser.add_argument("--json", action="store_true", help="print the full JSON result")
    args = parser.parse_args(argv)

    text = args.message if args.message is not None else sys.stdin.read()
    try:
        result = check_message(text)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
        return 0

    print(f"Result: {result.verdict_label}")
    print(result.summary)
    for m in result.matches:
        terms = ", ".join(f"{i['group']}={i['term']!r}" for i in m.matched_indicators)
        print(f"\n[{m.rule_id}] {m.title}\n  Why: {m.why}\n  Matched: {terms}")
        print(f"  Source: {m.source['publisher']} - {m.source['url']} (checked {m.source['checked']})")
    for u in result.url_indicators:
        if u["flags"]:
            print(f"\nLink {u['url']}: {', '.join(u['flags'])}")
    print("\nWhat to do:")
    for a in result.recommended_actions:
        print(f"  - {a}")
    print(f"\n{result.official_route}\n{result.disclaimer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
