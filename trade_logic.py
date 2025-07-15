# trade_logic.py

import logging
from utils import calculate_rsi, calculate_macd, fetch_candles
from config import CONFIG

logger = logging.getLogger(__name__)

class TradeLogic:
    def __init__(self, state):
        self.state = state

    def generate_signal(self):
        try:
            candles = fetch_candles(CONFIG.INSTRUMENT, CONFIG.CANDLE_GRANULARITY, CONFIG.CANDLE_COUNT)
            if not candles:
                logger.warning("No candle data available for signal generation.")
                return None

            rsi = calculate_rsi(candles, period=14)
            macd, signal_line = calculate_macd(candles)

            if rsi[-1] < CONFIG.RSI_OVERSOLD and macd[-1] > signal_line[-1]:
                logger.info("Buy signal generated.")
                return "BUY"
            elif rsi[-1] > CONFIG.RSI_OVERBOUGHT and macd[-1] < signal_line[-1]:
                logger.info("Sell signal generated.")
                return "SELL"

            return None
        except Exception as e:
            logger.exception(f"Error generating trade signal: {e}")
            return None