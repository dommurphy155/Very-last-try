import logging
from utils import calculate_atr
from config import CONFIG

logger = logging.getLogger(__name__)


class PositionSizer:
    def __init__(self, state, account_balance=10000):
        self.state = state
        self.account_balance = account_balance

    async def update_account_balance(self, client):
        try:
            account_data = await client.get_account_summary()
            balance = float(account_data.get("balance", self.account_balance))
            self.account_balance = balance
            logger.info(f"Updated account balance: {self.account_balance}")
        except Exception as e:
            logger.error(f"Failed to update account balance: {e}")

    async def calculate_units(self, instrument, risk_percent=1.0):
        try:
            candles = await client.get_candles(
                instrument, CONFIG.CANDLE_GRANULARITY, 50
            )
            if not candles:
                logger.warning(
                    "No candle data for ATR calculation. Using default units."
                )
                return CONFIG.DEFAULT_UNITS

            atr = calculate_atr(candles, period=14)
            if atr == 0:
                logger.warning("ATR calculated as zero, adjusting to minimum risk.")
                atr = 0.0005

            risk_amount = (risk_percent / 100) * self.account_balance
            units = int(risk_amount / (atr * 100000))

            if units < 1000:
                units = 1000
                logger.debug("Adjusted units to minimum 1000")

            logger.info(
                f"PositionSizer calculated units: {units} for risk_percent: {risk_percent} and ATR: {atr}"
            )
            return units

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return CONFIG.DEFAULT_UNITS
