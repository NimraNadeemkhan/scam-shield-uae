import pytest

from scamshield import check_message
from scamshield.engine import MAX_MESSAGE_LENGTH, DISCLAIMER


def test_match_returns_cautious_structured_result():
    r = check_message("Pay a redelivery fee of AED 4 for your parcel: https://bit.ly/abc")
    assert r.verdict == "verify"
    assert r.verdict_label == "Verify before taking action"
    assert r.categories == ["delivery"]
    assert r.matches and r.matches[0].source["level"] == "primary"
    assert r.disclaimer == DISCLAIMER
    assert any("official" in a.lower() for a in r.recommended_actions)


def test_no_match_is_never_called_safe():
    r = check_message("Lunch at 1?")
    assert r.verdict == "no_match"
    assert "does not mean the message is safe" in r.summary
    assert r.matches == []


def test_result_never_contains_clickable_links():
    r = check_message("Update your parcel details at https://dhl-track.top/a")
    indicators = r.to_dict()["url_indicators"]
    assert indicators
    for u in indicators:
        assert u["url"].startswith("hxxp") and "://" in u["url"] and "[.]" in u["url"]


def test_official_link_suppresses_link_rules():
    r = check_message("Confirm your delivery for your parcel: https://www.dhl.com/ae-en/")
    assert r.verdict == "no_match"


def test_mixed_official_and_unknown_link_still_matches():
    r = check_message("Confirm your parcel delivery https://www.dhl.com/ae-en/ or https://track-now.top/x")
    assert r.verdict == "verify"


def test_negation_suppresses_educational_bank_message():
    r = check_message("We will never ask you to share your PIN or card number.")
    assert r.verdict == "no_match"


def test_arabic_message_matches():
    r = check_message("تعذر توصيل شحنتك. يرجى تحديث بياناتك https://uae-post-track.top/x")
    assert "delivery" in r.categories


def test_caution_when_only_link_is_suspicious():
    r = check_message("See http://192.168.4.12/login")
    assert r.verdict == "caution"
    assert r.categories == []


def test_input_validation():
    with pytest.raises(ValueError):
        check_message("   ")
    with pytest.raises(ValueError):
        check_message("x" * (MAX_MESSAGE_LENGTH + 1))
    with pytest.raises(TypeError):
        check_message(None)  # type: ignore[arg-type]


def test_boundary_length_accepted():
    check_message("a" * MAX_MESSAGE_LENGTH)
