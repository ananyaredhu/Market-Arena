"""The check that stops the model inventing evidence (Person A).

A finding is kept only if (1) its URL is a source the researcher was actually shown, (2) its quote appears in that
source's text, (3) the number it claims appears in its own quote, and (4) the numbers are sane. Everything else is
dropped with a reason. This is deterministic code, outside the model: the model cannot talk its way past it.

What it does NOT prove: that the source is trustworthy or that the number is right in the real world. A page can
state a wrong number. apply.py limits the damage by clamping every adjustment to a band around the template.
"""
from __future__ import annotations

import re
import unicodedata

from backend.evidence.models import Dropped, Extraction, Finding, TrendNote

MIN_QUOTE_CHARS = 20  # a 5-character "quote" proves nothing
_QUOTE_MAP = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-",
                            " ": " "})
_MARKDOWN = re.compile(r"[*_`#>|]+")
_NUM = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)")


def normalize(text: str) -> str:
    """Case-, spacing-, quote-style- and markdown-insensitive form used to compare a quote with its source."""
    t = unicodedata.normalize("NFKC", text).translate(_QUOTE_MAP)
    t = _MARKDOWN.sub(" ", t.casefold())
    return re.sub(r"\s+", " ", t).strip()


def quote_in_source(quote: str, source_text: str) -> bool:
    q = normalize(quote)
    return len(q) >= MIN_QUOTE_CHARS and q in normalize(source_text)


def numbers_in(text: str) -> list[float]:
    """Numbers written in the text, understanding thousands separators ("1,200" is 1200)."""
    return [float(m.replace(",", "")) for m in _NUM.findall(text)]


def number_in_quote(value: float, quote: str, rel_tol: float = 0.01) -> bool:
    return any(abs(n - value) <= rel_tol * max(1.0, abs(value)) for n in numbers_in(quote))


def check_finding(f: Finding, sources: dict[str, str]) -> str | None:
    """Return None if the finding is faithful to its source, otherwise the reason it was rejected."""
    if f.url not in sources:
        return "the URL is not a source the researcher was shown"
    if not quote_in_source(f.quote, sources[f.url]):
        return "the quote does not appear in the source"
    for name, v in (("value", f.value), ("low", f.low), ("high", f.high)):
        if v is not None:
            if v < 0:
                return f"{name} is negative"
            # a share is stored as a fraction (0.62) but sources print it as a percentage (62%)
            as_percent = f.kind == "free_tool_adoption" and number_in_quote(v * 100, f.quote)
            is_free = v == 0 and re.search(r"\bfree\b", f.quote, re.I) is not None  # "free" stands for a price of 0
            if not (number_in_quote(v, f.quote) or as_percent or is_free):
                return f"the {name} {v:g} does not appear in the quote"
    if f.low is not None and f.high is not None and f.low > f.high:
        return "low is above high"
    if f.kind in ("competitor_price", "segment_budget", "free_tool_adoption") and f.value is None and f.low is None:
        return "a parameter finding needs a number"
    if f.kind == "free_tool_adoption" and not all(0 <= x <= 1 for x in (f.value, f.low, f.high) if x is not None):
        return "an adoption share must be between 0 and 1"
    return None


def check_trend(t: TrendNote, sources: dict[str, str]) -> str | None:
    if t.url not in sources:
        return "the URL is not a source the researcher was shown"
    if not quote_in_source(t.quote, sources[t.url]):
        return "the quote does not appear in the source"
    return None


def verify_extraction(ex: Extraction, sources: dict[str, str]) -> tuple[list[Finding], list[TrendNote], list[Dropped]]:
    """Split an extraction into what survives and what is dropped (with reasons)."""
    findings, trends, dropped = [], [], []
    for f in ex.findings:
        why = check_finding(f, sources)
        if why:
            dropped.append(Dropped(what=f.claim, url=f.url, reason=why))
        else:
            findings.append(f)
    for t in ex.trend_notes:
        why = check_trend(t, sources)
        if why:
            dropped.append(Dropped(what=t.note, url=t.url, reason=why))
        else:
            trends.append(t)
    return findings, trends, dropped
