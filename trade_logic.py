# trade_logic.py

import logging
import numpy as np
from utils import get_candle_data, analyze_trend, detect_reversal_patterns

logger = logging.getLogger(__name__)


class TradeLogic:
    def __init__(self, state, client):
        self.state = state
        self.client = client

    async def generate_signal(self):
        candles = await get_candle_data(self.client)
        if len(candles) < 20:
            logger.warning("Insufficient candle data for signal generation.")
            return None

        trend = analyze_trend(candles)
        pattern = detect_reversal_patterns(candles)

        if trend == "UP" and pattern == "BEARISH":
            return "SELL"
        elif trend == "DOWN" and pattern == "BULLISH":
            return "BUY"
        else:
            return None
