import aiohttp
import asyncio
import logging

logger = logging.getLogger(__name__)

class OandaClient:
    BASE_URL = "https://api-fxpractice.oanda.com/v3"

    def __init__(self, api_key, account_id):
        self.api_key = api_key
        self.account_id = account_id
        self.session = None
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def init_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(headers=self.headers)
            logger.info("✅ OandaClient HTTP session initialized.")

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("🛑 OandaClient HTTP session closed.")
            self.session = None

    async def _request(self, method, endpoint, **kwargs):
        if not self.session or self.session.closed:
            await self.init_session()

        url = f"{self.BASE_URL}{endpoint}"
        try:
            async with self.session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                data = await response.json()
                return data
        except aiohttp.ClientResponseError as e:
            logger.error(f"OANDA API error {e.status}: {e.message}")
            raise
        except Exception as e:
            logger.error(f"OANDA request error: {e}")
            raise

    async def get_candles(self, instrument, granularity="M1", count=100):
        """
        Fetch candlestick data for an instrument.
        granularity: M1, M5, M15, etc.
        count: number of candles
        """
        endpoint = f"/instruments/{instrument}/candles"
        params = {
            "granularity": granularity,
            "count": count,
            "price": "M"  # Midpoint prices only
        }
        return await self._request("GET", endpoint, params=params)

    async def get_prices(self, instruments):
        """
        Get current prices for one or more instruments (comma-separated string).
        """
        endpoint = f"/accounts/{self.account_id}/pricing"
        params = {
            "instruments": instruments
        }
        return await self._request("GET", endpoint, params=params)

    async def create_order(self, instrument, units, order_type="MARKET", price=None):
        """
        Place an order on the market.
        units: positive for buy, negative for sell.
        order_type: "MARKET", "LIMIT", etc.
        price: required for LIMIT orders.
        """
        endpoint = f"/accounts/{self.account_id}/orders"
        order_data = {
            "order": {
                "instrument": instrument,
                "units": str(units),
                "type": order_type,
                "positionFill": "DEFAULT"
            }
        }
        if order_type == "LIMIT" and price is not None:
            order_data["order"]["price"] = str(price)

        return await self._request("POST", endpoint, json=order_data)

    async def get_open_trades(self):
        endpoint = f"/accounts/{self.account_id}/openTrades"
        return await self._request("GET", endpoint)

    async def close_trade(self, trade_id):
        endpoint = f"/accounts/{self.account_id}/trades/{trade_id}/close"
        return await self._request("PUT", endpoint)

    # Add more specialized methods as needed for your strategies...