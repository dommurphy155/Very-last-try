# trading_bot.py

import asyncio
import logging
from trade_logic import TradeLogic
from trade_executor import TradeExecutor

logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, state):
        self.state = state
        self.trade_executor = TradeExecutor(state)
        self.trade_logic = TradeLogic(state)
        self.running = False

    async def start(self):
        self.running = True
        logger.info("Trading bot started.")

    async def stop(self):
        self.running = False
        logger.info("Trading bot stopped.")

    async def trade_cycle(self):
        if not self.running:
            return

        if self.trade_executor.is_cooldown_active():
            logger.info("Cooldown active, skipping trade cycle.")
            return

        signal = self.trade_logic.generate_signal()
        if signal in ("BUY", "SELL"):
            success = await self.trade_executor.execute_trade(signal)
            if success:
                logger.info(f"Executed trade: {signal}")
            else:
                logger.warning(f"Failed to execute trade: {signal}")
        else:
            logger.debug("No trade signal generated this cycle.")

        closed_trades = await self.trade_executor.monitor_trades()
        if closed_trades:
            logger.info(f"Closed trades: {closed_trades}")