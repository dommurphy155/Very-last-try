import logging

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
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1])
            )
            trs.append(tr)

        atr = sum(trs[-period:]) / period if len(trs) >= period else sum(trs) / len(trs)
        return atr
    except Exception as e:
        logger.error(f"Failed to calculate ATR: {e}")
        return 0.0


def calculate_rsi(candles, period=14):
    try:
        closes = [float(c["close"]) for c in candles]
        if len(closes) < period + 1:
            return [50] * len(closes)

        rsi_values = []
        for i in range(period, len(closes)):
            gains = []
            losses = []
            for j in range(i - period, i):
                delta = closes[j + 1] - closes[j]
                if delta > 0:
                    gains.append(delta)
                    losses.append(0)
                else:
                    gains.append(0)
                    losses.append(-delta)
            avg_gain = sum(gains) / period
            avg_loss = sum(losses) / period
            rs = avg_gain / avg_loss if avg_loss != 0 else 0
            rsi = 100 - (100 / (1 + rs)) if avg_loss != 0 else 100
            rsi_values.append(round(rsi, 2))

        return [50] * (len(closes) - len(rsi_values)) + rsi_values
    except Exception as e:
        logger.error(f"Failed to calculate RSI: {e}")
        return [50] * len(candles)


def calculate_macd(candles, fast=12, slow=26, signal=9):
    try:
        closes = [float(c["close"]) for c in candles]

        def ema(data, span):
            alpha = 2 / (span + 1)
            result = [data[0]]
            for price in data[1:]:
                result.append((price - result[-1]) * alpha + result[-1])
            return result

        if len(closes) < slow:
            return [0] * len(closes), [0] * len(closes)

        ema_fast = ema(closes, fast)
        ema_slow = ema(closes, slow)
        macd = [f - s for f, s in zip(ema_fast[-len(ema_slow):], ema_slow)]
        signal_line = ema(macd, signal)
        macd = macd[-len(signal_line):]

        return macd, signal_line
    except Exception as e:
        logger.error(f"Failed to calculate MACD: {e}")
        return [0] * len(candles), [0] * len(candles)
 