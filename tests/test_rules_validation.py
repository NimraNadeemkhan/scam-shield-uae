import copy
import datetime as dt

from scamshield.engine import _read_json
from scamshield.validate import validate, validate_topics

SCHEMA = _read_json("rules.schema.json")
TEMPLATES = _read_json("templates.json")
DOMAINS = _read_json("primary_domains.json")["domains"]
GOOD = _read_json("rules.json")
TODAY = dt.date(2026, 11, 22)


def run(doc, today=TODAY):
    return validate(doc, SCHEMA, TEMPLATES, DOMAINS, today=today)


def mutated(fn):
    doc = copy.deepcopy(GOOD)
    fn(doc["rules"][0])
    return doc


def test_shipped_rules_are_valid():
    errors, warnings = run(GOOD)
    assert errors == [] and warnings == []


def test_rejects_non_primary_source_level():
    errors, _ = run(mutated(lambda r: r["source"].update(level="secondary")))
    assert errors


def test_rejects_source_on_unlisted_domain():
    errors, _ = run(mutated(lambda r: r["source"].update(url="https://news.example.com/story")))
    assert any("primary_domains" in e for e in errors)


def test_rejects_unknown_template():
    errors, _ = run(mutated(lambda r: r.update(template_id="nope")))
    assert any("template_id" in e for e in errors)


def test_rejects_empty_signal_group():
    errors, _ = run(mutated(lambda r: r.update(groups=[{"name": "x", "any": []}])))
    assert errors


def test_rejects_missing_source_date():
    errors, _ = run(mutated(lambda r: r["source"].pop("checked")))
    assert errors


def test_rejects_duplicate_ids():
    doc = copy.deepcopy(GOOD)
    doc["rules"][1]["id"] = doc["rules"][0]["id"]
    errors, _ = run(doc)
    assert any("duplicate" in e for e in errors)


def test_rejects_future_dates():
    errors, _ = run(GOOD, today=dt.date(2026, 1, 1))
    assert any("future" in e for e in errors)


def test_stale_review_only_warns():
    errors, warnings = run(GOOD, today=dt.date(2027, 11, 22))
    assert errors == []
    assert warnings


def test_shipped_topics_are_valid():
    assert validate_topics(_read_json("topics.json")) == []


def test_topic_with_single_group_is_rejected():
    doc = {"topics": [{"id": "x", "title": "t", "groups": [{"name": "a", "any": ["word"]}]}]}
    assert validate_topics(doc)
