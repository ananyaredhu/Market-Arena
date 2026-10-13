"""Claim grounding tests (Person B)."""
from council.claims import Evidence, cited_numbers, is_grounded, unsupported_numbers


def test_identifiers_are_not_claims():
    text = "See run_8f21 and price_cut_20 for p10 and p90."
    assert cited_numbers(text) == []


def test_supported_and_unsupported():
    ev = Evidence()
    ev.add(0.19, as_percent=True)
    ev.add(-0.05, as_percent=True)
    assert is_grounded("share is 0.19", ev)
    assert is_grounded("share fell 5%", ev)
    assert unsupported_numbers("share is 0.42", ev) == ["0.42"]
    assert not is_grounded("share is 0.42", ev)


def test_precision_matching():
    ev = Evidence()
    ev.add(0.1904)
    assert is_grounded("median share 0.19", ev)
    assert not is_grounded("median share 0.191", ev)
