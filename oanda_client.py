import os
import logging
import httpx

logger = logging.getLogger(__name__)

class OandaClient:
    def __init__(self):
        self.api_key = os.getenv("OANDA_API_KEY")
        self.account_id = os.getenv("OANDA_ACCOUNT_ID")
        self.base_url = "https://api-fxpractice.oanda.com/v3"
        self.demo_mode = True if not self.api_key or not self.account_id else False
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def create_trade(self, instrument: str, units: int, side: str):
        if self.demo_mode:
            logger.info(f"DEMO_MODE: create_trade {side} {units} {instrument} skipped")
            return None
        data = {
            "order": {
                "instrument": instrument,
                "units": str(units if side == "buy" else -units),
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }
        try:
            resp = httpx.post(
                f"{self.base_url}/accounts/{self.account_id}/orders",
                headers=self.headers,
                json=data,
                timeout=10
            )
            resp.raise_for_status()
            logger.info(f"Trade executed: {side} {units} {instrument}")
            return resp.json()
        except Exception as e:
            logger.error(f"Error placing trade: {e}")
            return None