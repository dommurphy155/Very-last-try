# trade_logic.py

import logging
from config import CONFIG

logger = logging.getLogger(__name__)

class TradeLogic:
    def __init__(self, state, client):
        self.state = state
        self.client = client

    async def generate_signal(self):
        try:
            candles = await self.client.get_candles(CONFIG.INSTRUMENT, CONFIG.CANDLE_GRANULARITY, CONFIG.CANDLE_COUNT)
            if not candles:
                logger.warning("No candle data available for signal generation.")
                return None

            closes = [float(c["mid"]["c"]) for c in candles if c.get("mid")]
            if len(closes) < 26:
                logger.warning("Not enough candles for indicators.")
                return None

            rsi = self.calculate_rsi(closes)
            macd, signal_line = self.calculate_macd(closes)

            if rsi[-1] < CONFIG.RSI_OVERSOLD and macd[-1] > signal_line[-1]:
                logger.info("✅ Buy signal generated.")
                return "BUY"
            elif rsi[-1] > CONFIG.RSI_OVERBOUGHT and macd[-1] < signal_line[-1]:
                logger.info("✅ Sell signal generated.")
                return "SELL"

            return None
        except Exception as e:
            logger.exception(f"Error generating trade signal: {e}")
            return None

    def calculate_rsi(self, closes, period=14):
        import pandas as pd
        delta = pd.Series(closes).diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50).tolist()

    def calculate_macd(self, closes, fast=12, slow=26, signal=9):
        import pandas as pd
        series = pd.Series(closes)
        ema_fast = series.ewm(span=fast, adjust=False).mean()
        ema_slow = series.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd.tolist(), signal_line.tolist()