import logging
import os
import httpx
import asyncio
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, timedelta
from asyncio_throttle import Throttler

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
        self.client = httpx.AsyncClient(
            headers=self.headers,
            timeout=30.0,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
        )
        self.throttler = Throttler(rate_limit=120, period=60)  # 120 requests per minute
        self._price_cache = {}
        self._cache_ttl = 1.0  # 1 second cache

    async def _make_request(self, method: str, url: str, **kwargs) -> Tuple[bool, Any]:
        """Make rate-limited request with retry logic"""
        async with self.throttler:
            for attempt in range(3):
                try:
                    response = await self.client.request(method, url, **kwargs)
                    if response.status_code in [200, 201]:
                        return True, response.json()
                    elif response.status_code == 429:  # Rate limit
                        wait_time = int(response.headers.get('Retry-After', 5))
                        logger.warning(f"Rate limited, waiting {wait_time}s")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"API error {response.status_code}: {response.text}")
                        return False, response.text
                except httpx.TimeoutException:
                    logger.warning(f"Timeout on attempt {attempt + 1}")
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                    continue
                except Exception as e:
                    logger.error(f"Request failed: {e}")
                    return False, str(e)
        return False, "Max retries exceeded"

    async def create_trade(self, instrument: str, units: int, stop_loss_pips: float = None) -> Tuple[bool, Dict]:
        """Create a market order with optional stop loss"""
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
        
        if stop_loss_pips:
            price = await self.get_price(instrument)
            if price:
                pip_size = 0.01 if instrument.endswith("JPY") else 0.0001
                stop_loss_price = price - (stop_loss_pips * pip_size)
                order_data["order"]["stopLossOnFill"] = {
                    "price": str(stop_loss_price),
                    "timeInForce": "GTC"
                }
        
        return await self._make_request("POST", url, json=order_data)

    async def close_trade(self, trade_id: str) -> Tuple[bool, Dict]:
        """Close a specific trade"""
        url = f"{self.base_url}/accounts/{self.account_id}/trades/{trade_id}/close"
        return await self._make_request("PUT", url)

    async def close_all_trades(self, instrument: str = None) -> Tuple[bool, Dict]:
        """Close all trades for an instrument or all instruments"""
        url = f"{self.base_url}/accounts/{self.account_id}/trades/close"
        params = {}
        if instrument:
            params["instrument"] = instrument
        return await self._make_request("PUT", url, params=params)

    async def get_price(self, instrument: str) -> Optional[float]:
        """Get current price with caching"""
        cache_key = f"{instrument}_{datetime.now().timestamp() // self._cache_ttl}"
        if cache_key in self._price_cache:
            return self._price_cache[cache_key]
        
        url = f"{self.base_url}/accounts/{self.account_id}/pricing"
        params = {"instruments": instrument}
        
        success, data = await self._make_request("GET", url, params=params)
        if success and data.get("prices"):
            bid = float(data["prices"][0]["bids"][0]["price"])
            ask = float(data["prices"][0]["asks"][0]["price"])
            mid_price = (bid + ask) / 2
            self._price_cache[cache_key] = mid_price
            return mid_price
        return None

    async def get_candles(self, instrument: str, count: int = 100, granularity: str = "M5") -> List[Dict]:
        """Get historical candles for analysis"""
        url = f"{self.base_url}/instruments/{instrument}/candles"
        params = {
            "count": count,
            "granularity": granularity,
            "price": "M"
        }
        
        success, data = await self._make_request("GET", url, params=params)
        if success:
            return data.get("candles", [])
        return []

    async def get_account_summary(self) -> Optional[Dict]:
        """Get comprehensive account information"""
        url = f"{self.base_url}/accounts/{self.account_id}/summary"
        success, data = await self._make_request("GET", url)
        if success:
            return data.get("account", {})
        return None

    async def get_account_balance(self) -> Optional[float]:
        """Get account balance"""
        summary = await self.get_account_summary()
        if summary:
            return float(summary.get("balance", 0))
        return None

    async def get_margin_available(self) -> Optional[float]:
        """Get available margin"""
        summary = await self.get_account_summary()
        if summary:
            return float(summary.get("marginAvailable", 0))
        return None

    async def get_equity(self) -> Optional[float]:
        """Get current equity"""
        summary = await self.get_account_summary()
        if summary:
            return float(summary.get("NAV", 0))
        return None

    async def get_open_trades(self) -> List[Dict]:
        """Get all open trades"""
        url = f"{self.base_url}/accounts/{self.account_id}/openTrades"
        success, data = await self._make_request("GET", url)
        if success:
            return data.get("trades", [])
        return []

    async def get_trade_history(self, count: int = 50) -> List[Dict]:
        """Get recent trade history"""
        url = f"{self.base_url}/accounts/{self.account_id}/trades"
        params = {"count": count, "state": "CLOSED"}
        success, data = await self._make_request("GET", url, params=params)
        if success:
            return data.get("trades", [])
        return []

    async def get_positions(self) -> List[Dict]:
        """Get current positions"""
        url = f"{self.base_url}/accounts/{self.account_id}/positions"
        success, data = await self._make_request("GET", url)
        if success:
            return data.get("positions", [])
        return []

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()

    def __del__(self):
        """Cleanup on deletion"""
        try:
            asyncio.create_task(self.close())
        except:
            pass