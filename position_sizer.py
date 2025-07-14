import logging

logger = logging.getLogger("position_sizer")

class PositionSizer:
    def __init__(self, oanda_client, risk_per_trade=0.01):
        self.oanda_client = oanda_client
        self.risk_per_trade = risk_per_trade

    async def calculate_units(self, instrument: str, stop_loss_pips: float):
        balance = await self.oanda_client.get_account_balance()
        if balance is None:
            logger.error("Cannot calculate units without balance")
            return 0

        pip_value = 0.0001
        risk_amount = balance * self.risk_per_trade
        units = risk_amount / (stop_loss_pips * pip_value)
        units = int(units)

        if units < 1:
            logger.warning(f"Units too low ({units}), set to 1")
            units = 1

        logger.info(f"Calculated units for {instrument}: {units} at {self.risk_per_trade*100}% risk")
        return units