import logging
from utils import fetch_candles, calculate_atr
from config import CONFIG

logger = logging.getLogger(__name__)

class PositionSizer:
    def __init__(self, state, account_balance=10000):
        self.state = state
        self.account_balance = account_balance  # Should be updated dynamically from OANDA API

    async def update_account_balance(self, client):
        """
        Fetch the latest account balance from OANDA API via client.
        """
        try:
            account_data = await client.get_account_summary()
            balance = float(account_data.get("balance", self.account_balance))
            self.account_balance = balance
            logger.info(f"Updated account balance: {self.account_balance}")
        except Exception as e:
            logger.error(f"Failed to update account balance: {e}")

    async def calculate_units(self, instrument, risk_percent=1.0):
        """
        Calculate position size based on risk % of account balance using ATR stop loss.

        :param instrument: str, e.g., "EUR_USD"
        :param risk_percent: float, percentage of account balance to risk
        :return: int, units to trade
        """
        try:
            # Fetch recent candles for ATR calc
            candles = await fetch_candles(instrument, CONFIG.CANDLE_GRANULARITY, 50)
            if not candles:
                logger.warning("No candle data for ATR calculation. Using default units.")
                return CONFIG.DEFAULT_UNITS

            atr = calculate_atr(candles, period=14)
            if atr == 0:
                logger.warning("ATR calculated as zero, adjusting to minimum risk.")
                atr = 0.0005  # Minimal ATR fallback

            # Position sizing formula: units = (risk_amount / stop_loss_in_price)
            risk_amount = (risk_percent / 100) * self.account_balance

            # Simplified contract size: 100,000 units standard lot
            units = int(risk_amount / (atr * 100000))

            # Enforce minimum units (OANDA minimum is 1 unit, but 1000 safer)
            if units < 1000:
                units = 1000
                logger.debug("Adjusted units to minimum 1000")

            logger.info(f"PositionSizer calculated units: {units} for risk_percent: {risk_percent} and ATR: {atr}")
            return units

        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return CONFIG.DEFAULT_UNITS


# Utils method for ATR calculation (put this in utils.py or here)

def calculate_atr(candles, period=14):
    """
    Calculate Average True Range (ATR) from candle data.
    Each candle dict must have 'high', 'low', 'close' keys.

    Returns float ATR value.
    """
    try:
        highs = [float(candle["high"]) for candle in candles]
        lows = [float(candle["low"]) for candle in candles]
        closes = [float(candle["close"]) for candle in candles]

        trs = []
        for i in range(1, len(candles)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i-1]),
                abs(lows[i] - closes[i-1])
            )
            trs.append(tr)

        atr = sum(trs[-period:]) / period if len(trs) >= period else sum(trs) / len(trs)
        return atr
    except Exception as e:
        logger.error(f"Failed to calculate ATR: {e}")
        return 0.0