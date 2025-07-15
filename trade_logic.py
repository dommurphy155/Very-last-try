import logging
from utils import calculate_rsi, calculate_macd
from config import CONFIG

logger = logging.getLogger(__name__)


class TradeLogic:
    def __init__(self, state, client):
        self.state = state
        self.client = client

    async def generate_signal(self):
        candles_response = await self.client.get_candles(
            CONFIG.INSTRUMENT, CONFIG.CANDLE_GRANULARITY, CONFIG.CANDLE_COUNT
        )
        candles = candles_response.get("candles", []) if isinstance(candles_response, dict) else []

        if len(candles) < 30:
            logger.warning("Not enough candle data to generate signal.")
            return None

        rsi_values = calculate_rsi(candles, period=14)
        macd, signal_line = calculate_macd(candles, fast=12, slow=26, signal=9)

        if not rsi_values or not macd or not signal_line:
            logger.warning("Indicators not available for signal generation.")
            return None

        current_rsi = rsi_values[-1]
        current_macd = macd[-1]
        current_signal = signal_line[-1]

        # Simple RSI + MACD strategy for trade signals:
        if current_rsi < CONFIG.RSI_OVERSOLD and current_macd > current_signal:
            logger.info("TradeLogic generated BUY signal.")
            return "BUY"
        elif current_rsi > CONFIG.RSI_OVERBOUGHT and current_macd < current_signal:
            logger.info("TradeLogic generated SELL signal.")
            return "SELL"

        logger.debug("TradeLogic found no trade signal.")
        return None
 