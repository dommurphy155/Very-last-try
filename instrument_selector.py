import random

CURRENCY_PAIRS = [
    "EUR_USD", "USD_JPY", "GBP_USD", "AUD_USD", "USD_CAD",
    "NZD_USD", "USD_CHF", "EUR_GBP", "EUR_JPY", "GBP_JPY"
]

def choose_best_instrument():
    # Placeholder logic: random selection (upgrade with real analysis later)
    return random.choice(CURRENCY_PAIRS)