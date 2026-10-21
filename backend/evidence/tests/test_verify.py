import pytest

from backend.evidence.models import Extraction, Finding, TrendNote
from backend.evidence.verify import (
    check_finding,
    normalize,
    number_in_quote,
    numbers_in,
    quote_in_source,
    verify_extraction,
)

PAGE = (
    "StudyFlow Pricing\n\nThe Premium plan costs $4.99 per month, billed annually at $59.88.\n"
    "Students get a 50% discount. About 62% of surveyed students said they use a free planner."
)
SOURCES = {"https://example.com/pricing": PAGE}


def finding(**kw) -> Finding:
    base = dict(kind="competitor_price", subject="chain_app", claim="Premium costs $4.99 a month", value=4.99,
                unit="per month", currency="USD",
                quote="The Premium plan costs $4.99 per month", url="https://example.com/pricing")
    base.update(kw)
    return Finding(**base)


# ---------------------------------------------------------------- the quote must really be in the source
def test_a_real_quote_passes():
    assert check_finding(finding(), SOURCES) is None


def test_a_fabricated_quote_is_dropped():
    why = check_finding(finding(quote="The Premium plan costs $9.99 per month, a bargain for students"), SOURCES)
    assert why == "the quote does not appear in the source"


def test_a_url_the_researcher_never_saw_is_dropped():
    assert "not a source the researcher was shown" in check_finding(finding(url="https://evil.example/x"), SOURCES)


def test_too_short_a_quote_proves_nothing():
    assert not quote_in_source("$4.99", PAGE)
    assert "does not appear" in check_finding(finding(quote="$4.99"), SOURCES)


def test_matching_ignores_case_spacing_quote_style_and_markdown():
    messy = "the   PREMIUM plan\ncosts **$4.99** per month"
    assert quote_in_source(messy, PAGE)
    assert normalize("It’s “free” – really") == "it's \"free\" - really"


def test_the_claimed_number_must_appear_in_its_own_quote():
    why = check_finding(finding(value=7.0), SOURCES)
    assert why and "does not appear in the quote" in why


def test_numbers_with_thousands_separators_are_understood():
    assert numbers_in("revenue of 1,200,000 and 3.5%") == [1200000.0, 3.5]
    assert number_in_quote(1200, "spends about 1,200 a year")


def test_inverted_ranges_are_rejected():
    page = {"u": "Budgets run from 20 to 5 dollars per month according to the survey of students."}
    bad = finding(url="u", value=None, low=20.0, high=5.0, quote="Budgets run from 20 to 5 dollars per month")
    assert check_finding(bad, page) == "low is above high"


def test_a_parameter_finding_needs_a_number():
    f = finding(value=None, low=None, high=None)
    assert check_finding(f, SOURCES) == "a parameter finding needs a number"


def test_a_share_may_be_a_fraction_of_a_percentage_in_the_quote():
    f = finding(kind="free_tool_adoption", subject=None, value=0.62,
                quote="About 62% of surveyed students said they use a free planner")
    assert check_finding(f, SOURCES) is None
    assert "does not appear" in check_finding(f.model_copy(update={"value": 0.5}), SOURCES)


def test_an_adoption_share_must_be_a_fraction():
    f = finding(kind="free_tool_adoption", subject=None, value=62.0,
                quote="About 62% of surveyed students said they use a free planner")
    assert check_finding(f, SOURCES) == "an adoption share must be between 0 and 1"


def test_context_findings_need_no_number():
    f = finding(kind="regulation", value=None, claim="Students get a discount",
                quote="Students get a 50% discount on every plan")
    page = {"https://example.com/pricing": PAGE + " Students get a 50% discount on every plan"}
    assert check_finding(f, page) is None


# ---------------------------------------------------------------- whole extractions
def test_extraction_is_split_into_kept_and_dropped_with_reasons():
    ex = Extraction(
        findings=[finding(), finding(claim="invented", quote="Premium costs only $1 and includes unicorns today")],
        trend_notes=[TrendNote(note="students discount", quote="Students get a 50% discount",
                               url="https://example.com/pricing", effect="budget_down"),
                     TrendNote(note="made up trend", quote="Students are abandoning planners entirely this year",
                               url="https://example.com/pricing", effect="budget_down")],
    )
    findings, trends, dropped = verify_extraction(ex, SOURCES)
    assert [f.claim for f in findings] == ["Premium costs $4.99 a month"]
    assert [t.note for t in trends] == ["students discount"]
    assert {d.what for d in dropped} == {"invented", "made up trend"}
    assert all(d.reason for d in dropped)


def test_empty_extraction_is_fine():
    assert verify_extraction(Extraction(), SOURCES) == ([], [], [])


@pytest.mark.parametrize("quote", ["The Premium plan costs $4.99 per month", "premium PLAN costs $4.99 per MONTH"])
def test_quote_variants(quote):
    assert quote_in_source(quote, PAGE)


def test_free_counts_as_a_price_of_zero_only_when_the_quote_says_free():
    page = {"u": "Students can use the Basic plan which is free forever, and Pro costs $5 per month."}
    ok = finding(url="u", value=0.0, quote="the Basic plan which is free forever")
    assert check_finding(ok, page) is None
    bad = finding(url="u", value=0.0, quote="Pro costs $5 per month")
    assert "does not appear" in check_finding(bad, page)
