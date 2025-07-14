import os
import aiohttp
import logging

OANDA_API_KEY = os.getenv("OANDA_API_KEY")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
DEMO_MODE = True

logger = logging.getLogger(__name__)

class OandaClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.api_key = OANDA_API_KEY
        self.account_id = OANDA_ACCOUNT_ID
        self.session = session
        self.base_url = "https://api-fxpractice.oanda.com/v3"

    async def _request(self, method, endpoint, **kwargs):
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = self.base_url + endpoint
        try:
            async with self.session.request(method, url, headers=headers, **kwargs) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    logger.warning(f"OANDA API {method} {endpoint} failed {resp.status}: {text}")
                    return None
                return await resp.json()
        except Exception as e:
            logger.error(f"OANDA API request error: {e}")
            return None

    async def get_open_trades(self):
        return await self._request("GET", f"/accounts/{self.account_id}/openTrades")

    async def create_trade(self, instrument: str, units: int, side: str):
        if DEMO_MODE:
            logger.info(f"DEMO_MODE: create_trade {side} {units} {instrument} skipped")
            return {"demo": True, "instrument": instrument, "units": units, "side": side}
        data = {
            "order": {
                "instrument": instrument,
                "units": str(units if side == "buy" else -units),
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }
        return await self._request("POST", f"/accounts/{self.account_id}/orders", json=data)

    async def close_trade(self, trade_id: str):
        if DEMO_MODE:
            logger.info(f"DEMO_MODE: close_trade {trade_id} skipped")
            return {"demo": True, "trade_id": trade_id}
        return await self._request("PUT", f"/accounts/{self.account_id}/trades/{trade_id}/close")