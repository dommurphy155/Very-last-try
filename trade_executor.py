import logging

logger = logging.getLogger("trade_executor")

class TradeExecutor:
    def __init__(self, oanda_client):
        self.oanda_client = oanda_client

    async def execute_trade(self, instrument: str, units: int):
        if units <= 0:
            logger.error("Units <= 0 or trade blocked by cooldown/max trades, abort trade")
            return False

        # Place trade
        success, response = await self.oanda_client.create_trade(instrument, units)
        if not success:
            logger.error(f"Trade failed for {instrument}: {response}")
            return False

        logger.info(f"Trade placed: buy {units} units on {instrument}")
        return True

    async def close_trade(self, trade_id: str):
        success, response = await self.oanda_client.close_trade(trade_id)
        if success:
            logger.info(f"Trade closed successfully: {trade_id}")
            return True
        else:
            logger.error(f"Failed to close trade {trade_id}: {response}")
            return False