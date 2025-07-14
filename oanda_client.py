import logging
import httpx

logger = logging.getLogger("oanda_client")

class OandaClient:
    def __init__(self, api_key: str, account_id: str):
        self.api_key = api_key
        self.account_id = account_id
        self.base_url = "https://api-fxpractice.oanda.com/v3"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.client = httpx.AsyncClient(headers=self.headers)

    async def create_trade(self, instrument: str, units: int):
        """
        Places a market order for the specified instrument and units.
        Returns (success: bool, response: dict or str)
        """
        url = f"{self.base_url}/accounts/{self.account_id}/orders"
        order_data = {
            "order": {
                "units": str(units),
                "instrument": instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }
        try:
            response = await self.client.post(url, json=order_data)
            if response.status_code == 201:
                data = response.json()
                logger.info(f"Trade created successfully: {data}")
                return True, data
            else:
                error = response.json()
                logger.error(f"Failed to create trade: {error}")
                return False, error
        except Exception as e:
            logger.error(f"Exception while creating trade: {e}")
            return False, str(e)

    async def close_trade(self, trade_id: str):
        """
        Closes an open trade by trade_id.
        Returns (success: bool, response: dict or str)
        """
        url = f"{self.base_url}/accounts/{self.account_id}/trades/{trade_id}/close"
        try:
            response = await self.client.put(url)
            if response.status_code == 200:
                data = response.json()
                logger.info(f"Trade closed successfully: {data}")
                return True, data
            else:
                error = response.json()
                logger.error(f"Failed to close trade: {error}")
                return False, error
        except Exception as e:
            logger.error(f"Exception while closing trade: {e}")
            return False, str(e)

    async def get_price(self, instrument: str):
        """
        Fetches the latest price for the instrument.
        Returns float price or None.
        """
        url = f"{self.base_url}/instruments/{instrument}/pricing"
        params = {"instruments": instrument}
        try:
            response = await self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                prices = data.get("prices")
                if prices and len(prices) > 0:
                    # Use the mid price between bid and ask
                    bid = float(prices[0]["bids"][0]["price"])
                    ask = float(prices[0]["asks"][0]["price"])
                    mid_price = (bid + ask) / 2
                    return mid_price
            logger.error(f"Failed to fetch price for {instrument}: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Exception while fetching price: {e}")
            return None

    async def get_account_balance(self):
        """
        Fetches account balance.
        Returns float balance or None.
        """
        url = f"{self.base_url}/accounts/{self.account_id}/summary"
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                balance = float(data["account"]["balance"])
                return balance
            logger.error(f"Failed to fetch account balance: {response.text}")
            return None
        except Exception as e:
            logger.error(f"Exception while fetching account balance: {e}")
            return None

    async def get_open_trades(self):
        """
        Fetches list of open trades.
        Returns list of trades or empty list.
        """
        url = f"{self.base_url}/accounts/{self.account_id}/openTrades"
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("trades", [])
            logger.error(f"Failed to fetch open trades: {response.text}")
            return []
        except Exception as e:
            logger.error(f"Exception while fetching open trades: {e}")
            return []