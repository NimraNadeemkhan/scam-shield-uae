"""Validate the rules file. Run in CI: ``python -m scamshield.validate``.

Fails (exit 1) on structural or sourcing errors. Stale review dates only warn
unless ``--strict`` is given, so a repo does not turn red just because time passed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from urllib.parse import urlparse

from jsonschema import Draft202012Validator

from .engine import _read_json

MAX_REVIEW_AGE_DAYS = 180


def validate(doc, schema, templates, primary_domains, today=None):
    today = today or dt.date.today()
    errors, warnings = [], []

    for err in sorted(Draft202012Validator(schema).iter_errors(doc), key=lambda e: list(e.path)):
        where = "/".join(str(p) for p in err.path) or "(root)"
        errors.append(f"schema: {where}: {err.message}")
    if errors:  # semantic checks assume a structurally valid document
        return errors, warnings

    seen = set()
    for rule in doc["rules"]:
        rid = rule["id"]
        if rid in seen:
            errors.append(f"{rid}: duplicate rule id")
        seen.add(rid)

        if rule["template_id"] not in templates:
            errors.append(f"{rid}: template_id '{rule['template_id']}' not found in templates.json")

        host = (urlparse(rule["source"]["url"]).hostname or "").lower()
        if not any(host == d or host.endswith("." + d) for d in primary_domains):
            errors.append(f"{rid}: source host '{host}' is not in primary_domains.json")

        for label, value in (("reviewed", rule["reviewed"]), ("checked", rule["source"]["checked"]),
                             ("published", rule["source"]["published"])):
            if value is None:
                continue
            try:
                d = dt.date.fromisoformat(value)
            except ValueError:
                errors.append(f"{rid}: {label} '{value}' is not a real date")
                continue
            if d > today:
                errors.append(f"{rid}: {label} date {value} is in the future")

        if rule["status"] == "active":
            age = (today - dt.date.fromisoformat(rule["reviewed"])).days
            if age > MAX_REVIEW_AGE_DAYS:
                warnings.append(f"{rid}: last reviewed {age} days ago (limit {MAX_REVIEW_AGE_DAYS})")
            has_text_signal = any("any" in g for g in rule["groups"])
            has_url_signal = bool(rule.get("url_flags_any")) or any("has_url" in g for g in rule["groups"])
            if not (has_text_signal or has_url_signal):
                errors.append(f"{rid}: active rule has no signal")
    return errors, warnings


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true", help="treat warnings as errors")
    args = parser.parse_args(argv)

    errors, warnings = validate(
        _read_json("rules.json"),
        _read_json("rules.schema.json"),
        _read_json("templates.json"),
        _read_json("primary_domains.json")["domains"],
    )
    for w in warnings:
        print(f"WARNING {w}")
    for e in errors:
        print(f"ERROR   {e}")
    failed = bool(errors) or (args.strict and bool(warnings))
    print("rules validation FAILED" if failed else "rules validation passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
