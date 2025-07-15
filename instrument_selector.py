# instrument_selector.py

import logging

logger = logging.getLogger(__name__)

class InstrumentSelector:
    def __init__(self, instruments=None):
        # Default to major forex pairs if none provided
        self.instruments = instruments or [
            "EUR_USD", "USD_JPY", "GBP_USD", "USD_CHF",
            "AUD_USD", "USD_CAD", "NZD_USD"
        ]

    def get_best_instrument(self, market_data):
        """
        Select best instrument to trade based on volatility, volume, or AI signals.
        Placeholder: returns instrument with highest recent volatility.
        """
        if not market_data:
            logger.warning("No market data available for instrument selection.")
            return self.instruments[0]

        volatilities = {}
        for instrument in self.instruments:
            data = market_data.get(instrument)
            if data:
                volatilities[instrument] = self.calculate_volatility(data)
            else:
                volatilities[instrument] = 0

        best_instrument = max(volatilities, key=volatilities.get)
        logger.info(f"Selected best instrument: {best_instrument} with volatility {volatilities[best_instrument]:.5f}")
        return best_instrument

    def calculate_volatility(self, candles):
        # Simple volatility calculation: standard deviation of close prices
        closes = [candle['close'] for candle in candles]
        if len(closes) < 2:
            return 0
        mean = sum(closes) / len(closes)
        variance = sum((x - mean) ** 2 for x in closes) / (len(closes) - 1)
        return variance ** 0.5