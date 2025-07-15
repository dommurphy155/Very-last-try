# trade_logic.py

import logging
import numpy as np

logger = logging.getLogger(__name__)

class TradeLogic:
    def __init__(self, state, client):
        self.state = state
        self.client = client

    async def generate_signal(self):
        response = await self.client.get_candles("EUR_USD", "M5", 50)
        candles = response.get("candles", []) if isinstance(response, dict) else []
        if len(candles) < 35:
            logger.warning("Insufficient candle data for signal generation.")
            return None

        closes = np.array([float(c["mid"]["c"]) if "mid" in c else float(c["close"]) for c in candles])
        highs = np.array([float(c["mid"]["h"]) if "mid" in c else float(c["high"]) for c in candles])
        lows = np.array([float(c["mid"]["l"]) if "mid" in c else float(c["low"]) for c in candles])

        # RSI
        rsi = self.calculate_rsi(closes, 14)
        current_rsi = rsi[-1]

        # MACD and Signal line
        macd, signal_line = self.calculate_macd(closes)
        macd_current = macd[-1]
        signal_current = signal_line[-1]
        macd_prev = macd[-2]
        signal_prev = signal_line[-2]

        # EMA Trend confirmation
        ema_fast = self.ema(closes, 12)
        ema_slow = self.ema(closes, 26)
        ema_fast_current = ema_fast[-1]
        ema_slow_current = ema_slow[-1]

        # Candlestick pattern detection on last 3 candles
        pattern = self.detect_candlestick_pattern(candles[-3:])

        # Buy signal conditions
        if (
            current_rsi < 30
            and macd_prev < signal_prev
            and macd_current > signal_current
            and ema_fast_current > ema_slow_current
            and pattern in ("BULLISH_ENGULFING", "HAMMER", "DOJI")
        ):
            logger.info("TradeLogic: BUY signal generated.")
            return "BUY"

        # Sell signal conditions
        if (
            current_rsi > 70
            and macd_prev > signal_prev
            and macd_current < signal_current
            and ema_fast_current < ema_slow_current
            and pattern in ("BEARISH_ENGULFING", "SHOOTING_STAR", "DOJI")
        ):
            logger.info("TradeLogic: SELL signal generated.")
            return "SELL"

        return None

    def calculate_rsi(self, prices, period=14):
        deltas = np.diff(prices)
        seed = deltas[:period]
        up = seed[seed >= 0].sum() / period
        down = -seed[seed < 0].sum() / period
        rs = up / down if down != 0 else 0
        rsi = np.zeros_like(prices)
        rsi[:period] = 100 - 100 / (1 + rs)

        for i in range(period, len(prices)):
            delta = deltas[i - 1]
            upval = max(delta, 0)
            downval = -min(delta, 0)
            up = (up * (period - 1) + upval) / period
            down = (down * (period - 1) + downval) / period
            rs = up / down if down != 0 else 0
            rsi[i] = 100 - 100 / (1 + rs)
        return rsi

    def calculate_macd(self, prices, fast=12, slow=26, signal=9):
        ema_fast = self.ema(prices, fast)
        ema_slow = self.ema(prices, slow)
        macd = ema_fast - ema_slow
        signal_line = self.ema(macd, signal)
        return macd, signal_line

    def ema(self, data, period):
        alpha = 2 / (period + 1)
        ema = np.zeros_like(data)
        ema[0] = data[0]
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
        return ema

    def detect_candlestick_pattern(self, candles):
        last = candles[-1]
        open_p = float(last["mid"]["o"] if "mid" in last else last["open"])
        close_p = float(last["mid"]["c"] if "mid" in last else last["close"])
        high_p = float(last["mid"]["h"] if "mid" in last else last["high"])
        low_p = float(last["mid"]["l"] if "mid" in last else last["low"])

        body = abs(close_p - open_p)
        candle_range = high_p - low_p
        upper_shadow = high_p - max(close_p, open_p)
        lower_shadow = min(close_p, open_p) - low_p

        if len(candles) >= 2:
            prev = candles[-2]
            prev_open = float(prev["mid"]["o"] if "mid" in prev else prev["open"])
            prev_close = float(prev["mid"]["c"] if "mid" in prev else prev["close"])

            if prev_close < prev_open and open_p < close_p and open_p < prev_close and close_p > prev_open:
                return "BULLISH_ENGULFING"

            if prev_close > prev_open and open_p > close_p and open_p > prev_close and close_p < prev_open:
                return "BEARISH_ENGULFING"

        if body / candle_range < 0.3 and lower_shadow > 2 * body and upper_shadow < body:
            return "HAMMER"

        if body / candle_range < 0.3 and upper_shadow > 2 * body and lower_shadow < body:
            return "SHOOTING_STAR"

        if body / candle_range < 0.1:
            return "DOJI"

        return None
 