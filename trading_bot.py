import os
import logging
from oanda_client import OandaClient

logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.oanda = OandaClient()
        self.instrument = "EUR_USD"

    def calculate_units(self):
        # Minimal dynamic sizing: fixed 100 units
        return 100

    def run(self):
        units = self.calculate_units()
        side = "buy"  # minimal demo mode always buy
        result = self.oanda.create_trade(self.instrument, units, side)
        if result:
            logger.info(f"Trade placed: {side} {units} {self.instrument}")
        else:
            logger.warning("Trade not placed.")

    def send_telegram_message(self, bot, chat_id, message):
        try:
            bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")