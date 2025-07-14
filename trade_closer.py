import logging
from datetime import datetime, timedelta

logger = logging.getLogger("trade_closer")

class TradeCloser:
    def __init__(self, oanda_client, position_sizer):
        self.oanda = oanda_client
        self.position_sizer = position_sizer
        self.trailing_stop_pips = 15
        self.min_profit_threshold = 3.0  # in pips
        self.max_trade_duration = timedelta(hours=2)
        self.min_risk_reward = 1.2

    async def monitor_trades(self):
        open_trades = await self.oanda.get_open_trades()
        for trade in open_trades:
            await self._evaluate_trade(trade)

    async def _evaluate_trade(self, trade):
        trade_id = trade["id"]
        instrument = trade["instrument"]
        open_time_str = trade["openTime"].replace("Z", "+00:00")

        # Fix fractional seconds length for isoformat parsing
        if '.' in open_time_str:
            date_part, frac_part = open_time_str.split('.', 1)
            frac_digits = ''.join(filter(str.isdigit, frac_part))
            tz_part = frac_part[len(frac_digits):]
            frac_digits = frac_digits[:6]  
            open_time_str = f"{date_part}.{frac_digits}{tz_part}"

        open_time = datetime.fromisoformat(open_time_str)
        current_price = await self.oanda.get_price(instrument)

        unrealized_pl = float(trade.get("unrealizedPL", 0))
        initial_margin = float(trade.get("initialMarginRequired", 1))  # Avoid div by zero
        duration = datetime.utcnow() - open_time

        if duration > self.max_trade_duration:
            logger.info(f"Trade {trade_id} held too long, closing")
            await self._close_trade(trade_id, instrument)
            return

        rr_ratio = (unrealized_pl / initial_margin) if initial_margin > 0 else 0

        if unrealized_pl >= self.min_profit_threshold and rr_ratio >= self.min_risk_reward:
            logger.info(f"Trade {trade_id} meets profit threshold (PL: {unrealized_pl}, RR: {rr_ratio}), closing")
            await self._close_trade(trade_id, instrument)
            return

        # Trailing stop logic
        entry_price = float(trade["price"])
        is_short = trade