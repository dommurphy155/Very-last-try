import os
import logging
from oanda_client import OandaClient
from instrument_selector import choose_best_instrument

logger = logging.getLogger("trading_bot")

class TradingBot:
    def __init__(self):
        self.oanda = OandaClient()
        self.instrument = choose_best_instrument()

    def calculate_units(self):
        return 100  # placeholder for now

    async def run(self):
        try:
            units = self.calculate_units()
            side = "buy"
            result = await self.oanda.create_trade(self.instrument, units, side)
            if result:
                logger.info(f"Trade placed: {side} {units} {self.instrument}")
            else:
                logger.warning("Trade not placed.")
        except Exception as e:
            logger.exception(f"Trade execution failed: {e}")

    def send_telegram_message(self, bot, chat_id, message):
        try:
            bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            logger.error(f"Telegram send failed: {e}")