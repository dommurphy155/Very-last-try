import logging

logger = logging.getLogger("trade_executor")

class TradeExecutor:
    def __init__(self, oanda_client, position_sizer):
        self.oanda_client = oanda_client
        self.position_sizer = position_sizer

    async def place_trade(self, instrument: str, stop_loss_pips: float, direction: str):
        units = await self.position_sizer.calculate_units(instrument, stop_loss_pips)
        if units <= 0:
            logger.error("Units <= 0, abort trade")
            return False

        side = "buy" if direction.lower() == "buy" else "sell" if direction.lower() == "sell" else None
        if not side:
            logger.error(f"Invalid direction: {direction}")
            return False

        result = await self.oanda_client.create_trade(instrument, units, side)
        if result:
            logger.info(f"Trade placed: {side} {units} units on {instrument}")
            return True
        else:
            logger.error("Trade failed")
            return False