"""Currency codes to the symbol people read (Person A).

One place, so Glass-Box, Compare, the Kit and the Council agree.
"""

MONEY = {"SGD": "S$", "USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "AUD": "A$", "CAD": "C$", "S$": "S$"}


def money_symbol(currency: str) -> str:
    """The symbol for a currency code; an unknown code is shown as the code followed by a space ("XYZ 5")."""
    return MONEY.get(currency, f"{currency} ")


def currency_of(population: dict | None, default: str) -> str:
    """The currency a stored population was simulated in (`generation.currency.code`), else `default`.

    A founder's market is simulated in the currency they priced in (see backend/population/localise.py)."""
    generation = (population or {}).get("generation") or {}
    code = (generation.get("currency") or {}).get("code") if isinstance(generation, dict) else None
    return code or default
