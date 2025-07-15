# trade_executor.py

import logging
from datetime import datetime, timedelta
from config import CONFIG
from trade_closer import TradeCloser

logger = logging.getLogger(__name__)


class TradeExecutor:
    def __init__(self, state, client):
        self.state = state
        self.client = client
        self.trade_closer = TradeCloser(state, client)
        self.cooldown_until = None

    def is_cooldown_active(self):
        return self.cooldown_until and datetime.utcnow() < self.cooldown_until

    async def execute_trade(self, signal):
        try:
            units = CONFIG.DEFAULT_UNITS
            if units <= 0:
                logger.warning("Zero units, skipping trade execution.")
                return False

            order = await self.client.create_market_order(
                signal, units, CONFIG.INSTRUMENT
            )
            tx = order.get("orderFillTransaction")
            if tx:
                trade_id = tx["tradeID"]
                price = float(tx["price"])
                self.state.setdefault("open_trades", {})[trade_id] = {
                    "signal": signal,
                    "units": units,
                    "opened_at": datetime.utcnow().isoformat(),
                    "entry_price": price,
                    "instrument": CONFIG.INSTRUMENT,
                }
                self.cooldown_until = datetime.utcnow() + timedelta(
                    seconds=CONFIG.COOLDOWN_SECONDS
                )
                logger.info(f"Executed {signal} trade with ID {trade_id} at {price}")
                return True
            else:
                logger.warning(f"Trade order failed: {order}")
                return False
        except Exception as e:
            logger.exception(f"Error executing trade: {e}")
            return False

    async def monitor_trades(self):
        closed = []
        try:
            open_trades = self.state.get("open_trades", {})
            for trade_id in list(open_trades.keys()):
                trade_info = open_trades[trade_id]
                if await self.trade_closer.should_close_trade(trade_id, trade_info):
                    resp = await self.client.close_trade(trade_id)
                    tx = resp.get("orderFillTransaction")
                    if tx:
                        del open_trades[trade_id]
                        closed.append(trade_id)
                        logger.info(f"Closed trade {trade_id}")
        except Exception as e:
            logger.exception(f"Error monitoring trades: {e}")
        return closed

    async def close(self):
        await self.client.close()
 