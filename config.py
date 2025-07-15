import os
import sys

class ConfigError(Exception):
    pass

class CONFIG:
    # Load secrets from environment
    OANDA_API_KEY = os.getenv("OANDA_API_KEY")
    OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    # Validate required environment variables
    REQUIRED_VARS = {
        "OANDA_API_KEY": OANDA_API_KEY,
        "OANDA_ACCOUNT_ID": OANDA_ACCOUNT_ID,
        "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
        "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
    }

    for var_name, value in REQUIRED_VARS.items():
        if not value:
            print(f"ERROR: Environment variable {var_name} is not set.", file=sys.stderr)
            sys.exit(1)

    # Trading parameters
    INSTRUMENT = "EUR_USD"
    CANDLE_GRANULARITY = "M5"
    CANDLE_COUNT = 50

    # Risk and trade sizing
    DEFAULT_UNITS = 1000  # Default fixed units; replace with dynamic sizing if needed
    COOLDOWN_SECONDS = 60  # Cooldown period between trades (seconds)

    # Scan interval for trade cycles (seconds)
    SCAN_INTERVAL = 7

    # RSI thresholds for entry signals
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70

    # State file location
    STATE_FILE = "state.json"