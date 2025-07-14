import httpx
import os
import logging

logger = logging.getLogger("oanda_client")

class OandaClient:
    def __init__(self):
        self.account_id = os.getenv("OANDA_ACCOUNT_ID")
        self.api_key = os.getenv("OANDA_API_KEY")
        self.base_url = "https://api-fxpractice.oanda.com/v3"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def get_account_balance(self):
        url = f"{self.base_url}/accounts/{self.account_id}/summary"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code == 200:
                return float(response.json()["account"]["balance"])
            else:
                logger.error(f"Failed to fetch account balance: {response.text}")
                return None

    async def get_price(self, instrument):
        url = f"{self.base_url}/pricing?instruments={instrument}"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code == 200:
                prices = response.json()["prices"][0]
                return float(prices["bids"][0]["price"])
            else:
                logger.error(f"Failed to get price for {instrument}: {response.text}")
                return None

    async def get_open_trades(self):
        url = f"{self.base_url}/accounts/{self.account_id}/openTrades"
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()["trades"]
            else:
                logger.error(f"Failed to get open trades: {response.text}")
                return []

    async def close_trade(self, trade_id, instrument):
        url = f"{self.base_url}/accounts/{self.account_id}/trades/{trade_id}/close"
        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=self.headers)
            if response.status_code == 200:
                logger.info(f"Closed trade {trade_id} on {instrument}")
                return True
            else:
                logger.error(f"Failed to close trade {trade_id}: {response.text}")
                return False