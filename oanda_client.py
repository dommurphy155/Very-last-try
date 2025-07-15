import aiohttp
import asyncio
import logging

logger = logging.getLogger(__name__)

class OandaClient:
    BASE_URL = "https://api-fxpractice.oanda.com/v3"

    def __init__(self, api_key, account_id):
        self.api_key = api_key
        self.account_id = account_id
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.session = aiohttp.ClientSession(headers=self.headers)

    async def create_market_order(self, side, units, instrument):
        """
        side: "BUY" or "SELL"
        units: int (positive integer)
        instrument: str, e.g., "EUR_USD"
        """
        data = {
            "order": {
                "units": str(units if side == "BUY" else -units),
                "instrument": instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }
        url = f"{self.BASE_URL}/accounts/{self.account_id}/orders"

        try:
            async with self.session.post(url, json=data) as resp:
                response = await resp.json()
                if resp.status == 201:
                    logger.info(f"Market order created: {response}")
                else:
                    logger.warning(f"Order creation failed ({resp.status}): {response}")
                return response
        except Exception as e:
            logger.error(f"Exception creating market order: {e}")
            return {}

    async def close_trade(self, trade_id):
        url = f"{self.BASE_URL}/accounts/{self.account_id}/trades/{trade_id}/close"
        try:
            async with self.session.put(url) as resp:
                response = await resp.json()
                if resp.status == 200:
                    logger.info(f"Trade closed: {trade_id}")
                else:
                    logger.warning(f"Failed to close trade {trade_id} ({resp.status}): {response}")
                return response
        except Exception as e:
            logger.error(f"Exception closing trade {trade_id}: {e}")
            return {}

    async def get_candles(self, instrument, granularity, count):
        params = {
            "granularity": granularity,
            "count": count,
            "price": "M"
        }
        url = f"{self.BASE_URL}/instruments/{instrument}/candles"
        try:
            async with self.session.get(url, params=params) as resp:
                response = await resp.json()
                if resp.status == 200:
                    return response.get("candles", [])
                else:
                    logger.warning(f"Failed to fetch candles ({resp.status}): {response}")
                    return []
        except Exception as e:
            logger.error(f"Exception fetching candles: {e}")
            return []

    async def close(self):
        await self.session.close()