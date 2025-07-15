# utils.py

import logging
import pandas as pd

logger = logging.getLogger(__name__)

def fetch_candles(instrument, granularity, count):
    """
    Placeholder function to fetch candle data.
    Replace with real OANDA API calls or injected client.
    Returns list of dicts with 'high', 'low', 'close' prices.
    """
    try:
        # Dummy data for testing - generate dummy OHLC candles
        base_price = 1.1000
        candles = []
        for i in range(count):
            close = base_price + i * 0.0001
            high = close + 0.0002
            low = close - 0.0002
            candles.append({"high": high, "low": low, "close": close})
        return candles
    except Exception as e:
        logger.error(f"Failed to fetch candles: {e}")
        return []

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

def calculate_atr(candles, period=14):
    """
    Calculate Average True Range (ATR) from candle data.
    Candles must have 'high', 'low', 'close' keys.
    Returns float ATR value.
    """
    try:
        highs = [float(candle["high"]) for candle in candles]
        lows = [float(candle["low"]) for candle in candles]
        closes = [float(candle["close"]) for candle in candles]

        trs = []
        for i in range(1, len(candles)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            trs.append(tr)

        if len(trs) >= period:
            atr = sum(trs[-period:]) / period
        else:
            atr = sum(trs) / len(trs) if trs else 0.0
        return atr
    except Exception as e:
        logger.error(f"Failed to calculate ATR: {e}")
        return 0.0