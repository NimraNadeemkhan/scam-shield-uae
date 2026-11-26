"""Every golden case is a regression test.

Cases marked ``known_limitation`` are xfail(strict): they document a real
weakness, and the suite tells you when a change accidentally fixes one.
"""
import pytest

from scamshield import check_message
from scamshield.evaluate import DEFAULT_CASES, case_ok, load_cases

CASES = load_cases(DEFAULT_CASES)


def _param(case):
    marks = []
    if case.get("known_limitation"):
        marks.append(pytest.mark.xfail(strict=True, reason=case["known_limitation"]))
    return pytest.param(case, id=case["id"], marks=marks)


@pytest.mark.parametrize("case", [_param(c) for c in CASES])
def test_golden_case(case):
    assert case_ok(case, check_message(case["text"]))


def test_case_ids_are_unique_and_labelled():
    ids = [c["id"] for c in CASES]
    assert len(ids) == len(set(ids))
    for c in CASES:
        assert c["origin"] in {"synthetic", "real"}
        assert c["split"] in {"seed", "heldout"}


def test_every_category_has_positive_and_negative_cases():
    for category in ("delivery", "banking", "job_visa"):
        assert any(category in c["expected_categories"] for c in CASES)
    assert any(not c["expected_categories"] and c["expected_verdict"] == "no_match" for c in CASES)
