import logging
from config import CONFIG
from utils import calculate_rsi, calculate_macd

logger = logging.getLogger(__name__)


class TradeLogic:
    def __init__(self, state, client):
        self.state = state
        self.client = client

    async def generate_signal(self):
        try:
            raw_candles = await self.client.get_candles(
                CONFIG.INSTRUMENT, CONFIG.CANDLE_GRANULARITY,
    CONFIG.CANDLE_COUNT
            )
            candles = (
                raw_candles.get("candles")
                if isinstance(raw_candles, dict)
                else raw_candles
            )
            if not candles or len(candles) < 30:
                logger.warning("Insufficient candle data for signal
    generation.")
                return None

            closes = [float(c["mid"]["c"]) for c in candles if c.get("mid")]
            if len(closes) < 26:
                logger.warning("Not enough closes for indicators calculation.")
                return None

            rsi = calculate_rsi([{"close": c} for c in closes], period=14)
            macd, signal_line = calculate_macd([{"close": c} for c in closes])

            if rsi[-1] < CONFIG.RSI_OVERSOLD and macd[-1] > signal_line[-1]:
                logger.info("✅ Buy signal generated.")
                return "BUY"
            elif rsi[-1] > CONFIG.RSI_OVERBOUGHT and macd[-1] <
    signal_line[-1]:
                logger.info("✅ Sell signal generated.")
                return "SELL"
            return None
        except Exception as e:
            logger.exception(f"Error generating trade signal: {e}")
            return None
