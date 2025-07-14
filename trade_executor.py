import logging
from oanda_client import OandaClient

logger = logging.getLogger("trade_executor")

class TradeExecutor:
    def __init__(self, oanda_client: OandaClient, position_sizer: PositionSizer):
        self.oanda_client = oanda_client
        self.position_sizer = position_sizer

    async def place_trade(self, instrument: str, stop_loss_pips: float, direction: str):
        units = await self.position_sizer.calculate_units(instrument, stop_loss_pips)
        if units <= 0:
            logger.error("Units <= 0 or trade blocked by cooldown/max trades, abort trade")
            return False

        side = "buy" if direction.lower() == "buy" else "sell" if direction.lower() == "sell" else None
        if not side:
            logger.error(f"Invalid trade direction: {direction}")
            return False

        result = await self.oanda_client.create_trade(instrument, units, side)
        if result:
            logger.info(f"Trade placed: {side} {units} units on {instrument}")
            self.position_sizer.record_trade(instrument)
            # Outcome tracking requires external logic -- placeholder:
            # You should call update_performance() after trade closes with actual win/loss
            return True
        else:
            logger.error("Trade failed")
            return False

    def close_trade(self, instrument: str, won: bool):
        # Call this externally when trade closes
        self.position_sizer.close_trade(instrument)
        self.position_sizer.update_performance(instrument, won)