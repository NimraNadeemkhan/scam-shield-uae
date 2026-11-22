"""Passive URL analysis. Nothing here ever fetches or opens a link."""
from __future__ import annotations

import ipaddress
import json
import re
from dataclasses import dataclass, field
from importlib import resources
from urllib.parse import urlparse

SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "cutt.ly", "is.gd", "rb.gy",
    "shorturl.at", "ow.ly", "tiny.cc", "goo.gl", "rebrand.ly",
}
SUSPICIOUS_TLDS = {"top", "xyz", "icu", "click", "cfd", "sbs", "cyou", "buzz", "tk"}
# Minimal stand-in for the Public Suffix List (no network/deps needed).
MULTI_LABEL_SUFFIXES = {
    "co.ae", "gov.ae", "com.ae", "net.ae", "org.ae", "ac.ae", "sch.ae",
    "co.uk", "org.uk", "com.au", "com.sa", "co.in", "com.pk",
}
_BARE_TLDS = (
    "com|net|org|info|ae|top|xyz|icu|click|shop|live|vip|online|site|link|co|me|"
    "ly|gl|to|cc|ru|cn|tk|support|help|cfd|sbs|cyou|buzz|store|app|pro|biz|in"
)
_URL_RE = re.compile(
    r"(?i)(?:\b(?:https?://|www\.)[^\s<>\"']+)"
    r"|(?:(?<![\w@.\-])(?:[a-z0-9](?:[a-z0-9\-]{0,61}[a-z0-9])?\.)+(?:" + _BARE_TLDS + r")"
    r"(?![a-z0-9\-])(?:[/?#][^\s<>\"']*)?)"
)
_TRAILING = ".,;:!?)]}>»،؛؟\"'"


@dataclass
class UrlInfo:
    url: str
    host: str
    registrable: str
    flags: list = field(default_factory=list)
    official_brand: str | None = None

    @property
    def display(self) -> str:
        """Defanged form: safe to show, cannot be clicked."""
        return self.url.replace("http", "hxxp", 1).replace(".", "[.]")


def _load_brands() -> dict:
    raw = resources.files("scamshield").joinpath("data/brands.json").read_text("utf-8")
    return json.loads(raw)


_BRANDS = _load_brands()


def _registrable(host: str) -> str:
    labels = host.split(".")
    if len(labels) >= 3 and ".".join(labels[-2:]) in MULTI_LABEL_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def _is_official(registrable: str, brand: dict) -> bool:
    if registrable in brand["official_domains"]:
        return True
    label, _, tld = registrable.partition(".")
    cc_label = brand.get("country_domain_label")
    return bool(cc_label and label == cc_label and len(tld) == 2 and tld.isalpha())


def analyze_url(raw: str) -> UrlInfo | None:
    cleaned = raw.rstrip(_TRAILING)
    candidate = cleaned if "://" in cleaned else "http://" + cleaned
    try:
        parsed = urlparse(candidate)
        host = (parsed.hostname or "").lower().rstrip(".")
    except ValueError:
        return None
    if not host:
        return None

    flags: list = []
    registrable = host
    try:
        ipaddress.ip_address(host)
        flags.append("ip_host")
    except ValueError:
        registrable = _registrable(host)
        if registrable in SHORTENERS:
            flags.append("shortener")
        if host.rsplit(".", 1)[-1] in SUSPICIOUS_TLDS:
            flags.append("suspicious_tld")
        if "xn--" in host:
            flags.append("punycode")
    if "@" in parsed.netloc:
        flags.append("userinfo_trick")

    official = None
    if "ip_host" not in flags:
        for name, brand in _BRANDS.items():
            if _is_official(registrable, brand):
                official = name
                break
            if any(k in host for k in brand["keywords"]):
                flags.append(f"lookalike_brand:{name}")
    return UrlInfo(cleaned, host, registrable, flags, official)


def find_urls(text: str) -> list:
    out = []
    for m in _URL_RE.finditer(text):
        info = analyze_url(m.group(0))
        if info:
            out.append((m.start(), m.end(), info))
    return out


def analyze_urls(text: str) -> list:
    return [info for _, _, info in find_urls(text)]


def strip_urls(text: str) -> str:
    """Replace URLs with a space so words inside a domain are not read as prose."""
    pieces, last = [], 0
    for start, end, _ in find_urls(text):
        pieces.append(text[last:start])
        pieces.append(" ")
        last = end
    pieces.append(text[last:])
    return "".join(pieces)
