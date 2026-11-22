from scamshield.normalize import normalize


def test_lowercases_and_collapses_whitespace():
    assert normalize("  Your   PARCEL \n is held ") == "your parcel is held"


def test_strips_zero_width_characters():
    assert normalize("sh​ip‌ment") == "shipment"


def test_arabic_variants_collapse():
    # hamza on alef, ta marbuta, diacritics and tatweel all normalise away
    assert normalize("تأكيـد") == normalize("تاكيد")
    assert normalize("شحنة") == normalize("شحنه")
    assert normalize("حدّث") == "حدث"


def test_arabic_indic_digits_become_ascii():
    assert normalize("٧٨٤") == "784"


def test_curly_apostrophe_matches_straight():
    assert normalize("don’t share") == "don't share"
