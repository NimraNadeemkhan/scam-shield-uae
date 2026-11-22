"""Run the golden cases and print per-category precision / recall / F1.

    python -m scamshield.evaluate

Cases flagged ``known_limitation`` are expected to be wrong; they are reported,
not hidden. Any other mismatch makes the command exit 1.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .engine import check_message

DEFAULT_CASES = Path(__file__).resolve().parents[2] / "tests" / "golden" / "cases.jsonl"
CATEGORIES = ["delivery", "banking"]


def load_cases(path: Path) -> list:
    cases = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(json.loads(line))
    return cases


def case_ok(case: dict, result) -> bool:
    return (result.verdict == case["expected_verdict"]
            and set(result.categories) == set(case["expected_categories"]))


def _ratio(num, den):
    return None if den == 0 else num / den


def _fmt(x):
    return "n/a" if x is None else f"{x:.2f}"


def evaluate(cases: list) -> dict:
    stats = {c: {"tp": 0, "fp": 0, "fn": 0, "cases": 0} for c in CATEGORIES}
    rows = []
    for case in cases:
        result = check_message(case["text"])
        pred, gold = set(result.categories), set(case["expected_categories"])
        for c in CATEGORIES:
            if c in gold:
                stats[c]["cases"] += 1
            stats[c]["tp"] += int(c in gold and c in pred)
            stats[c]["fp"] += int(c not in gold and c in pred)
            stats[c]["fn"] += int(c in gold and c not in pred)
        rows.append((case, result, case_ok(case, result)))
    for s in stats.values():
        s["precision"] = _ratio(s["tp"], s["tp"] + s["fp"])
        s["recall"] = _ratio(s["tp"], s["tp"] + s["fn"])
        p, r = s["precision"], s["recall"]
        s["f1"] = None if p is None or r is None or p + r == 0 else 2 * p * r / (p + r)
    return {"stats": stats, "rows": rows}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    out = evaluate(cases)

    print(f"Golden cases: {len(cases)} (all synthetic seed cases; NOT a held-out test set)\n")
    print("| Category | Positive cases | TP | FP | FN | Precision | Recall | F1 |")
    print("|---|---|---|---|---|---|---|---|")
    for c, s in out["stats"].items():
        print(f"| {c} | {s['cases']} | {s['tp']} | {s['fp']} | {s['fn']} | "
              f"{_fmt(s['precision'])} | {_fmt(s['recall'])} | {_fmt(s['f1'])} |")

    unexpected = [(c, r) for c, r, ok in out["rows"] if not ok and not c.get("known_limitation")]
    known = [(c, r) for c, r, ok in out["rows"] if not ok and c.get("known_limitation")]
    fixed = [c for c, _, ok in out["rows"] if ok and c.get("known_limitation")]

    print("\nKnown limitations (reported, expected to be wrong):")
    for c, r in known:
        print(f"  {c['id']}: expected {c['expected_verdict']}/{c['expected_categories']}, "
              f"got {r.verdict}/{r.categories} - {c['known_limitation']}")
    if not known:
        print("  none")
    for c in fixed:
        print(f"NOTE {c['id']} is marked known_limitation but now passes; remove the flag.")
    for c, r in unexpected:
        print(f"UNEXPECTED {c['id']}: expected {c['expected_verdict']}/{c['expected_categories']}, "
              f"got {r.verdict}/{r.categories}")
    return 1 if unexpected else 0


if __name__ == "__main__":
    sys.exit(main())
