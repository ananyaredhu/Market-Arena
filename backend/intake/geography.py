"""Find the market's country in a founder's idea (Person A). No model, no network: a fixed list of country names, common
aliases and large cities, each mapped to an ISO 3166 alpha-2 code.

The country decides which official data the evidence step can use (income level for any country, consumer prices for
Singapore, Europe and the US), so a wrong guess would quietly price the market wrongly. It therefore only answers when a
name is actually in the text, takes the first one mentioned, and otherwise returns None so intake can keep asking.
"""
from __future__ import annotations

import re

COUNTRIES = {
    "Singapore": "SG", "United States": "US", "United States of America": "US", "America": "US", "United Kingdom": "GB",
    "Britain": "GB", "England": "GB", "Scotland": "GB", "Wales": "GB", "Canada": "CA", "Australia": "AU",
    "New Zealand": "NZ", "Ireland": "IE", "Germany": "DE", "France": "FR", "Spain": "ES", "Italy": "IT",
    "Portugal": "PT", "Netherlands": "NL", "Holland": "NL", "Belgium": "BE", "Luxembourg": "LU", "Austria": "AT",
    "Switzerland": "CH", "Denmark": "DK", "Sweden": "SE", "Norway": "NO", "Finland": "FI", "Iceland": "IS",
    "Poland": "PL", "Czechia": "CZ", "Czech Republic": "CZ", "Slovakia": "SK", "Hungary": "HU", "Romania": "RO",
    "Bulgaria": "BG", "Greece": "GR", "Croatia": "HR", "Slovenia": "SI", "Estonia": "EE", "Latvia": "LV",
    "Lithuania": "LT", "Cyprus": "CY", "Malta": "MT", "Russia": "RU", "Ukraine": "UA", "Turkey": "TR",
    "India": "IN", "Pakistan": "PK", "Bangladesh": "BD", "Sri Lanka": "LK", "Nepal": "NP", "China": "CN",
    "Hong Kong": "HK", "Taiwan": "TW", "Japan": "JP", "South Korea": "KR", "Korea": "KR", "Malaysia": "MY",
    "Indonesia": "ID", "Thailand": "TH", "Vietnam": "VN", "Philippines": "PH", "Cambodia": "KH",
    "United Arab Emirates": "AE", "UAE": "AE", "Dubai": "AE", "Saudi Arabia": "SA", "Qatar": "QA", "Kuwait": "KW",
    "Israel": "IL", "Egypt": "EG", "Morocco": "MA", "Nigeria": "NG", "Kenya": "KE", "Ghana": "GH",
    "South Africa": "ZA", "Ethiopia": "ET", "Brazil": "BR", "Argentina": "AR", "Chile": "CL", "Colombia": "CO",
    "Peru": "PE", "Mexico": "MX", "Uruguay": "UY",
}
CITIES = {
    "London": "GB", "Manchester": "GB", "Edinburgh": "GB", "Paris": "FR", "Berlin": "DE", "Munich": "DE",
    "Hamburg": "DE", "Frankfurt": "DE", "Madrid": "ES", "Barcelona": "ES", "Rome": "IT", "Milan": "IT",
    "Amsterdam": "NL", "Brussels": "BE", "Vienna": "AT", "Zurich": "CH", "Stockholm": "SE", "Copenhagen": "DK",
    "Oslo": "NO", "Helsinki": "FI", "Dublin": "IE", "Lisbon": "PT", "Warsaw": "PL", "Prague": "CZ",
    "Budapest": "HU", "Athens": "GR", "Istanbul": "TR", "Moscow": "RU", "New York": "US", "Los Angeles": "US",
    "San Francisco": "US", "Chicago": "US", "Boston": "US", "Seattle": "US", "Austin": "US", "Toronto": "CA",
    "Vancouver": "CA", "Montreal": "CA", "Sydney": "AU", "Melbourne": "AU", "Auckland": "NZ", "Mumbai": "IN",
    "Delhi": "IN", "New Delhi": "IN", "Bangalore": "IN", "Bengaluru": "IN", "Hyderabad": "IN", "Chennai": "IN",
    "Karachi": "PK", "Dhaka": "BD", "Beijing": "CN", "Shanghai": "CN", "Shenzhen": "CN", "Guangzhou": "CN",
    "Tokyo": "JP", "Osaka": "JP", "Seoul": "KR", "Taipei": "TW", "Kuala Lumpur": "MY", "Jakarta": "ID",
    "Bangkok": "TH", "Hanoi": "VN", "Ho Chi Minh City": "VN", "Manila": "PH", "Abu Dhabi": "AE", "Riyadh": "SA",
    "Tel Aviv": "IL", "Cairo": "EG", "Lagos": "NG", "Nairobi": "KE", "Johannesburg": "ZA", "Cape Town": "ZA",
    "Sao Paulo": "BR", "São Paulo": "BR", "Buenos Aires": "AR", "Santiago": "CL", "Bogota": "CO", "Bogotá": "CO",
    "Lima": "PE", "Mexico City": "MX",
}
# Words that are also ordinary English, so they count only when written with a capital letter ("Turkey", not "turkey").
CAPITAL_ONLY = {"Turkey", "Chile", "Wales", "Austin", "Lima", "Santiago", "Holland", "Cyprus", "Korea"}
# Short forms that count only as written (the word "us" is not the United States).
CODES = {"US": "US", "USA": "US", "UK": "GB", "UAE": "AE"}


def _pattern(names) -> re.Pattern:
    ordered = sorted(names, key=len, reverse=True)
    return re.compile(r"(?<![A-Za-z])(" + "|".join(re.escape(n) for n in ordered) + r")(?![A-Za-z])")


_ALL = {**COUNTRIES, **CITIES}
_LOWER = {n.lower(): c for n, c in _ALL.items()}
_FREE = _pattern([n for n in _ALL if n not in CAPITAL_ONLY])
_CAPITAL = _pattern([n for n in _ALL if n in CAPITAL_ONLY])
_CODE = _pattern(list(CODES))


def detect_geography(text: str) -> str | None:
    """The ISO alpha-2 code of the first country or city named in `text`, or None."""
    hits: list[tuple[int, str]] = []
    for m in re.finditer(_FREE.pattern, text, re.IGNORECASE):
        hits.append((m.start(), _LOWER[m.group(1).lower()]))
    hits += [(m.start(), _LOWER[m.group(1).lower()]) for m in _CAPITAL.finditer(text)]
    hits += [(m.start(), CODES[m.group(1)]) for m in _CODE.finditer(text)]
    return min(hits)[1] if hits else None


def normalise_geography(value: str | None) -> str | None:
    """A code (SG, DE, USA) is kept as given; a country or city written out (Germany, Berlin) becomes its code."""
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if re.fullmatch(r"[A-Za-z]{2,3}", value):
        return CODES.get(value.upper(), value.upper())
    return detect_geography(value) or value.upper()
