"""Text normalisation shared by rule terms and incoming messages.

Both sides go through the same function, so a rule term written naturally
("شحنة", "تأكيد") matches the variants people actually type.
"""
from __future__ import annotations

import re
import unicodedata

# Arabic harakat, superscript alef, tatweel.
_ARABIC_MARKS = re.compile("[ً-ْٰـ]")
# Zero-width and bidi control characters, a common obfuscation trick.
_INVISIBLE = re.compile("[​-‏‪-‮⁠-⁤﻿]")
_ALEF_VARIANTS = re.compile("[أإآٱ]")  # أ إ آ ٱ
_DIGITS = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)
_QUOTES = str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'})
_SPACES = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Return a canonical, lower-case form of ``text`` for matching."""
    t = unicodedata.normalize("NFKC", text)
    t = _INVISIBLE.sub("", t)
    t = _ARABIC_MARKS.sub("", t)
    t = t.translate(_DIGITS).translate(_QUOTES)
    t = _ALEF_VARIANTS.sub("ا", t)  # -> ا
    t = t.replace("ى", "ي")  # ى -> ي
    t = t.replace("ة", "ه")  # ة -> ه
    t = t.casefold()
    return _SPACES.sub(" ", t).strip()
