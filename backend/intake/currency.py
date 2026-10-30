"""Which currency a project is in (Person A). Never a conversion: the founder's own currency is kept as written.

Order: the currency the founder wrote with the price (S$, EUR, 500 rupees); else the currency of the country the market
is in; else the industry pack's. A bare dollar sign is the market's own dollar when the market uses one (Singapore,
Australia, Canada, New Zealand, Hong Kong, the US), otherwise US dollars.
"""
from __future__ import annotations

EURO = ("AT BE CY DE EE ES FI FR GR HR IE IT LT LU LV MT NL PT SI SK").split()
COUNTRY_CURRENCY = {
    "SG": "SGD", "US": "USD", "GB": "GBP", "CA": "CAD", "AU": "AUD", "NZ": "NZD", "HK": "HKD", "IN": "INR",
    "CN": "CNY", "JP": "JPY", "KR": "KRW", "TW": "TWD", "MY": "MYR", "ID": "IDR", "TH": "THB", "VN": "VND",
    "PH": "PHP", "PK": "PKR", "BD": "BDT", "LK": "LKR", "NP": "NPR", "KH": "KHR", "AE": "AED", "SA": "SAR",
    "QA": "QAR", "KW": "KWD", "IL": "ILS", "EG": "EGP", "MA": "MAD", "NG": "NGN", "KE": "KES", "GH": "GHS",
    "ZA": "ZAR", "ET": "ETB", "BR": "BRL", "AR": "ARS", "CL": "CLP", "CO": "COP", "PE": "PEN", "MX": "MXN",
    "UY": "UYU", "CH": "CHF", "DK": "DKK", "SE": "SEK", "NO": "NOK", "IS": "ISK", "PL": "PLN", "CZ": "CZK",
    "HU": "HUF", "RO": "RON", "BG": "BGN", "RU": "RUB", "UA": "UAH", "TR": "TRY",
    **dict.fromkeys(EURO, "EUR"),
}
DOLLAR_CURRENCIES = {"USD", "SGD", "AUD", "CAD", "NZD", "HKD"}
# The country whose price level a currency is measured in, when the market is elsewhere (a US-dollar price in India).
HOME_COUNTRY = {"USD": "US", "EUR": "DE", "GBP": "GB", "SGD": "SG", "INR": "IN", "AUD": "AU", "CAD": "CA", "NZD": "NZ",
                "HKD": "HK", "JPY": "JP", "CNY": "CN", "CHF": "CH"}
_ISO3_TO_ISO2 = {"USA": "US", "SGP": "SG", "GBR": "GB", "DEU": "DE", "FRA": "FR", "IND": "IN", "CHN": "CN", "JPN": "JP",
                 "AUS": "AU", "CAN": "CA"}


def country_code(geography: str | None) -> str | None:
    if not geography:
        return None
    g = geography.strip().upper()
    return _ISO3_TO_ISO2.get(g, g if len(g) == 2 else None)


def currency_of_country(geography: str | None) -> str | None:
    return COUNTRY_CURRENCY.get(country_code(geography) or "")


def bare_dollar(geography: str | None) -> str | None:
    """The currency a bare `$` means in this market, or None when the market has no dollar of its own."""
    own = currency_of_country(geography)
    return own if own in DOLLAR_CURRENCIES else ("USD" if own else None)


def reference_country(currency: str, geography: str | None) -> str | None:
    """The country whose purchasing power the currency is measured in: the market's own country when it uses that
    currency, else the currency's home country."""
    country = country_code(geography)
    if country and currency_of_country(country) == currency:
        return country
    return HOME_COUNTRY.get(currency)
