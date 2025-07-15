import logging
from datetime import datetime, timedelta
from utils import calculate_atr
from config import CONFIG

logger = logging.getLogger(__name__)

class TradeCloser:
    def __init__(self, state, oanda_client):
        self.state = state
        self.client = oanda_client

    async def should_close_trade(self, trade_id, trade_info):
        """
        Determine if trade should be closed based on:
        - Trailing stop loss (ATR based)
        - Take profit or risk-reward ratio
        - Momentum reversal via RSI/MACD signals
        """

        try:
            # Fetch latest candles for instrument
            instrument = trade_info.get("instrument", CONFIG.INSTRUMENT)
            candles = await self.client.get_candles(instrument, CONFIG.CANDLE_GRANULARITY, CONFIG.CANDLE_COUNT)
            if not candles:
                logger.warning(f"No candles for trade closer on {instrument}")
                return False

            atr = calculate_atr(candles, period=14)
            if atr == 0:
                atr = 0.0005

            # Current price - last candle close
            current_price = float(candles[-1]["close"])

            entry_price = trade_info.get("entry_price")
            if not entry_price:
                logger.warning(f"No entry price for trade {trade_id}, skipping close check.")
                return False

            # Calculate trailing stop: entry_price +/- ATR * factor (3)
            stop_distance = atr * 3
            side = trade_info.get("signal")

            # For BUY trades: trailing stop below current price
            if side == "BUY":
                trailing_stop = max(trade_info.get("trailing_stop", entry_price - stop_distance), current_price - stop_distance)
                trade_info["trailing_stop"] = trailing_stop
                # Close if price <= trailing_stop
                if current_price <= trailing_stop:
                    logger.info(f"Trailing stop hit for trade {trade_id}, closing trade.")
                    return True

                # Add take profit logic here if needed

            # For SELL trades: trailing stop above current price
            elif side == "SELL":
                trailing_stop = min(trade_info.get("trailing_stop", entry_price + stop_distance), current_price + stop_distance)
                trade_info["trailing_stop"] = trailing_stop
                if current_price >= trailing_stop:
                    logger.info(f"Trailing stop hit for trade {trade_id}, closing trade.")
                    return True

                # Add take profit logic here if needed

            # Optional: close if trade open for > max duration (e.g., 2 hours)
            opened_at = trade_info.get("opened_at")
            if opened_at:
                open_time = datetime.fromisoformat(opened_at)
                if datetime.utcnow() - open_time > timedelta(hours=2):
                    logger.info(f"Trade {trade_id} open over 2 hours, closing.")
                    return True

            # TODO: Add momentum indicator based closing here (RSI, MACD)

            return False

        except Exception as e:
            logger.error(f"Error in should_close_trade for {trade_id}: {e}")
            return False