import logging
from datetime import datetime, timedelta
from utils import calculate_atr
from config import CONFIG

logger = logging.getLogger(__name__)

class TradeCloser:
    def __init__(self, state, client):
        self.state = state
        self.client = client

    async def should_close_trade(self, trade_id, trade_info):
        try:
            instrument = trade_info.get("instrument", CONFIG.INSTRUMENT)
            raw_candles = await self.client.get_candles(
                instrument, CONFIG.CANDLE_GRANULARITY, CONFIG.CANDLE_COUNT
            )
            candles = (
                raw_candles.get("candles")
                if isinstance(raw_candles, dict)
                else raw_candles
            )
            if not candles:
                logger.warning(f"No candles data for trade closer on {instrument}")
                return False

            atr = calculate_atr(candles, period=14)
            if atr == 0:
                atr = 0.0005

            current_price = (
                float(candles[-1]["mid"]["c"])
                if "mid" in candles[-1]
                else float(candles[-1]["close"])
            )

            entry_price = trade_info.get("entry_price")
            if entry_price is None:
                logger.warning(f"No entry price for trade {trade_id}, skipping close check.")
                return False

            stop_distance = atr * 3
            side = trade_info.get("signal")

            if side == "BUY":
                trailing_stop = max(
                    trade_info.get("trailing_stop", entry_price - stop_distance),
                    current_price - stop_distance,
                )
                trade_info["trailing_stop"] = trailing_stop
                if current_price <= trailing_stop:
                    logger.info(f"Trailing stop hit for trade {trade_id}, closing trade.")
                    return True
            elif side == "SELL":
                trailing_stop = min(
                    trade_info.get("trailing_stop", entry_price + stop_distance),
                    current_price + stop_distance,
                )
                trade_info["trailing_stop"] = trailing_stop
                if current_price >= trailing_stop:
                    logger.info(f"Trailing stop hit for trade {trade_id}, closing trade.")
                    return True

            opened_at = trade_info.get("opened_at")
            if opened_at:
                open_time = datetime.fromisoformat(opened_at)
                if datetime.utcnow() - open_time > timedelta(hours=4):
                    logger.info(f"Trade {trade_id} open over 4 hours, closing.")
                    return True

            return False
        except Exception as e:
            logger.error(f"Error in should_close_trade for {trade_id}: {e}")
            return False
 