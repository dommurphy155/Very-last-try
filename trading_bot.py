import logging
from oanda_client import OandaClient
from position_sizer import PositionSizer
from trade_executor import TradeExecutor

logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self):
        self.oanda = OandaClient()
        self.position_sizer = PositionSizer(self.oanda)
        self.trade_executor = TradeExecutor(self.oanda, self.position_sizer)
        self.instrument = "EUR_USD"  # default

    async def select_instrument(self):
        # Minimal logic example: rotate between EUR_USD and GBP_USD
        import random
        self.instrument = random.choice(["EUR_USD", "GBP_USD"])
        logger.info(f"Selected instrument: {self.instrument}")

    async def run(self):
        await self.select_instrument()
        stop_loss_pips = 10  # fixed stop loss for now
        direction = "buy"    # minimal buy logic, replace with algo later
        success = await self.trade_executor.place_trade(self.instrument, stop_loss_pips, direction)
        if success:
            logger.info(f"Trade placed successfully on {self.instrument}")
        else:
            logger.error(f"Trade failed on {self.instrument}")