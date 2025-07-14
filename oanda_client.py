import os
import httpx
import logging

logger = logging.getLogger("oanda_client")

class OandaClient:
    def __init__(self):
        self.api_key = os.getenv("OANDA_API_KEY")
        self.account_id = os.getenv("OANDA_ACCOUNT_ID")
        self.base_url = "https://api-fxpractice.oanda.com/v3"
        if not self.api_key or not self.account_id:
            raise ValueError("OANDA_API_KEY and OANDA_ACCOUNT_ID must be set as environment variables")
        self.headers = {"Authorization": f"Bearer {self.api_key}"}
        self.demo_mode = True  # toggle for demo/live

    async def get_account_balance(self):
        url = f"{self.base_url}/accounts/{self.account_id}/summary"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self.headers)
            if resp.status_code != 200:
                logger.error(f"Failed to fetch account balance: {resp.text}")
                return None
            data = resp.json()
            balance = float(data["account"]["balance"])
            logger.info(f"Account balance: {balance}")
            return balance

    async def create_trade(self, instrument: str, units: int, side: str):
        if self.demo_mode:
            logger.info(f"DEMO_MODE: create_trade {side} {units} {instrument} skipped")
            return {"tradeOpened": {"units": str(units), "instrument": instrument}}

        url = f"{self.base_url}/accounts/{self.account_id}/orders"
        order_data = {
            "order": {
                "units": str(units if side == "buy" else -units),
                "instrument": instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT",
            }
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=order_data, headers=self.headers)
            if resp.status_code != 201:
                logger.error(f"Trade creation failed: {resp.text}")
                return None
            logger.info(f"Trade created: {resp.json()}")
            return resp.json()