import logging
from trade_logic import TradeLogic
from trade_executor import TradeExecutor

logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, state, client):
        self.state = state
        self.client = client
        self.trade_executor = TradeExecutor(state, client)
        self.trade_logic = TradeLogic(state, client)
        self.running = False

    async def start(self):
        self.running = True
        logger.info("✅ Trading bot started.")

    async def stop(self):
        self.running = False
        logger.info("🛑 Trading bot stopped.")

    async def trade_cycle(self):
        if not self.running or self.trade_executor.is_cooldown_active():
            return

        signal = await self.trade_logic.generate_signal()
        if signal in ("BUY", "SELL"):
            success = await self.trade_executor.execute_trade(signal)
            if success:
                logger.info(f"✅ Trade executed: {signal}")
        else:
            logger.debug("No valid trade signal.")

        closed_trades = await self.trade_executor.monitor_trades()
        if closed_trades:
            logger.info(f"📉 Closed trades: {closed_trades}")