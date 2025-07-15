import asyncio
import logging
from datetime import datetime, timedelta
from oanda_client import OandaClient
from trade_closer import TradeCloser
from config import CONFIG

logger = logging.getLogger(__name__)

class TradeExecutor:
    def __init__(self, state):
        self.state = state
        self.client = OandaClient(CONFIG.OANDA_API_KEY, CONFIG.OANDA_ACCOUNT_ID)
        self.trade_closer = TradeCloser(state, self.client)
        self.cooldown_until = None

    def is_cooldown_active(self):
        if not self.cooldown_until:
            return False
        return datetime.utcnow() < self.cooldown_until

    async def execute_trade(self, signal):
        try:
            units = self.calculate_position_size(signal)
            if units <= 0:
                logger.info("Position size zero or negative, skipping trade.")
                return False

            # Pass instrument explicitly for order creation
            order_response = await self.client.create_market_order(signal, units, CONFIG.INSTRUMENT)

            fill_transaction = order_response.get("orderFillTransaction")
            if fill_transaction:
                trade_id = fill_transaction.get("tradeID")
                price = float(fill_transaction.get("price", 0))

                self.state.setdefault("open_trades", {})[trade_id] = {
                    "signal": signal,
                    "units": units,
                    "opened_at": datetime.utcnow().isoformat(),
                    "entry_price": price,
                    "instrument": CONFIG.INSTRUMENT,
                }
                self.cooldown_until = datetime.utcnow() + timedelta(seconds=CONFIG.COOLDOWN_SECONDS)
                logger.info(f"Executed {signal} trade with ID {trade_id} at price {price}")
                return True
            else:
                logger.warning(f"Order not filled: {order_response}")
                return False

        except Exception as e:
            logger.exception(f"Error executing trade: {e}")
            return False

    async def monitor_trades(self):
        closed_trades = []
        try:
            open_trades = self.state.get("open_trades", {})
            for trade_id in list(open_trades.keys()):
                trade_info = open_trades[trade_id]
                should_close = await self.trade_closer.should_close_trade(trade_id, trade_info)
                if should_close:
                    close_result = await self.client.close_trade(trade_id)
                    fill_transaction = close_result.get("orderFillTransaction")
                    if fill_transaction:
                        closed_trades.append(trade_id)
                        del open_trades[trade_id]
                        logger.info(f"Closed trade ID: {trade_id}")
                    else:
                        logger.warning(f"Failed to close trade ID {trade_id}: {close_result}")
        except Exception as e:
            logger.exception(f"Error monitoring trades: {e}")

        return closed_trades

    def calculate_position_size(self, signal):
        # Basic risk management example
        # Could improve by integrating PositionSizer class or more advanced sizing logic
        return CONFIG.DEFAULT_UNITS

    async def close(self):
        await self.client.close()