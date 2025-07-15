import logging
import pandas as pd

logger = logging.getLogger(__name__)

def calculate_atr(candles, period=14):
    try:
        highs = [float(c["high"]) for c in candles]
        lows = [float(c["low"]) for c in candles]
        closes = [float(c["close"]) for c in candles]

        trs = []
        for i in range(1, len(candles)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            trs.append(tr)

        atr = sum(trs[-period:]) / period if len(trs) >= period else sum(trs) / len(trs)
        return atr
    except Exception as e:
        logger.error(f"Failed to calculate ATR: {e}")
        return 0.0

def calculate_rsi(candles, period=14):
    try:
        closes = pd.Series([c['close'] for c in candles])
        delta = closes.diff()
        gain = delta.where(delta > 0, 0.0)
        loss = -delta.where(delta < 0, 0.0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50).tolist()
    except Exception as e:
        logger.error(f"Failed to calculate RSI: {e}")
        return [50] * len(candles)

def calculate_macd(candles, fast=12, slow=26, signal=9):
    try:
        closes = pd.Series([c['close'] for c in candles])
        ema_fast = closes.ewm(span=fast, adjust=False).mean()
        ema_slow = closes.ewm(span=slow, adjust=False).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal, adjust=False).mean()
        return macd.tolist(), signal_line.tolist()
    except Exception as e:
        logger.error(f"Failed to calculate MACD: {e}")
        length = len(candles)
        return [0] * length, [0] * length