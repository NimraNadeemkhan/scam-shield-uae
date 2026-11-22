"""Rules engine: message in, cautious structured result out.

The engine never says "this is a scam". It says a message matches a documented
warning pattern, or that nothing matched (which is not proof of safety).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from importlib import resources

from .normalize import normalize
from .urls import UrlInfo, analyze_urls, strip_urls

ENGINE_VERSION = "0.1.0"
MAX_MESSAGE_LENGTH = 2000
DISCLAIMER = (
    "Informational guidance only. This is not an official fraud report and not a "
    "guarantee that a message is or is not fraudulent."
)
VERDICT_LABELS = {
    "verify": "Verify before taking action",
    "caution": "Treat the link with caution",
    "no_match": "No documented pattern matched",
}
# URL flags strong enough to raise a caution when no rule matched.
_CAUTION_FLAGS = ("lookalike_brand", "ip_host", "userinfo_trick", "punycode")


def _read_json(name: str):
    return json.loads(resources.files("scamshield").joinpath(f"data/{name}").read_text("utf-8"))


@lru_cache(maxsize=None)
def load_rules() -> dict:
    return _read_json("rules.json")


@lru_cache(maxsize=None)
def load_templates() -> dict:
    return _read_json("templates.json")


@lru_cache(maxsize=None)
def _term_pattern(term: str):
    n = normalize(term)
    if n.isascii():  # Latin terms match whole words; Arabic matches substrings
        body = r"\s+".join(re.escape(p) for p in n.split(" "))
        return re.compile(rf"(?<![a-z0-9]){body}(?![a-z0-9])")
    return re.compile(re.escape(n))


def _first_term(terms, norm_text):
    for term in terms:
        if _term_pattern(term).search(norm_text):
            return term
    return None


def _url_flag_hit(urls, wanted) -> bool:
    return any(f == w or f.startswith(w + ":") for u in urls for f in u.flags for w in wanted)


@dataclass
class Match:
    rule_id: str
    category: str
    title: str
    why: str
    matched_indicators: list
    source: dict


@dataclass
class CheckResult:
    verdict: str
    categories: list
    matches: list
    url_indicators: list
    recommended_actions: list
    official_route: str
    summary: str
    disclaimer: str = DISCLAIMER
    rules_version: str = ""
    engine_version: str = ENGINE_VERSION
    verdict_label: str = field(init=False)

    def __post_init__(self):
        self.verdict_label = VERDICT_LABELS[self.verdict]

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "verdict_label": self.verdict_label,
            "summary": self.summary,
            "categories": self.categories,
            "matches": [m.__dict__ for m in self.matches],
            "url_indicators": self.url_indicators,
            "recommended_actions": self.recommended_actions,
            "official_route": self.official_route,
            "disclaimer": self.disclaimer,
            "rules_version": self.rules_version,
            "engine_version": self.engine_version,
        }


def _rule_matches(rule: dict, norm_text: str, urls: list):
    """Return a list of matched indicators, or None if the rule does not fire."""
    if rule.get("suppress_if_any") and _first_term(rule["suppress_if_any"], norm_text):
        return None
    if rule.get("suppress_if_all_urls_official") and urls and all(u.official_brand for u in urls):
        return None
    if rule.get("url_flags_any") and not _url_flag_hit(urls, rule["url_flags_any"]):
        return None
    indicators = []
    for group in rule["groups"]:
        if group.get("has_url"):
            if not urls:
                return None
            indicators.append({"group": group["name"], "term": "(link present)"})
            continue
        term = _first_term(group["any"], norm_text)
        if term is None:
            return None
        indicators.append({"group": group["name"], "term": term})
    return indicators


def check_message(message: str) -> CheckResult:
    if not isinstance(message, str):
        raise TypeError("message must be a string")
    if not message.strip():
        raise ValueError("message is empty")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"message exceeds {MAX_MESSAGE_LENGTH} characters")

    urls: list[UrlInfo] = analyze_urls(message)
    norm_text = normalize(strip_urls(message))
    doc = load_rules()

    matches = []
    for rule in doc["rules"]:
        if rule["status"] != "active":
            continue
        indicators = _rule_matches(rule, norm_text, urls)
        if indicators is not None:
            matches.append(
                Match(rule["id"], rule["category"], rule["title"], rule["description"],
                      indicators, rule["source"])
            )

    url_indicators = [{"url": u.display, "host": u.host, "flags": u.flags,
                       "official_brand": u.official_brand} for u in urls]
    categories = sorted({m.category for m in matches})
    templates = load_templates()

    if matches:
        verdict, keys = "verify", categories
    elif _url_flag_hit(urls, _CAUTION_FLAGS):
        verdict, keys = "caution", ["url_caution"]
    else:
        verdict, keys = "no_match", ["no_match"]

    actions, routes = [], []
    for key in keys:
        tpl = templates[key]
        actions += [a for a in tpl["actions"] if a not in actions]
        routes.append(tpl["official_route"])

    return CheckResult(
        verdict=verdict,
        categories=categories,
        matches=matches,
        url_indicators=url_indicators,
        recommended_actions=actions,
        official_route=" ".join(routes),
        summary=templates[keys[0]]["summary"],
        rules_version=doc["version"],
    )
