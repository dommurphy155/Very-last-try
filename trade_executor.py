import logging
from datetime import datetime, timedelta
from config import CONFIG
from trade_closer import TradeCloser

logger = logging.getLogger(__name__)


class TradeExecutor:
    def __init__(self, state, client):
        self.state = state
        self.client = client
        self.trade_closer = TradeCloser(state, client)
        self.cooldown_until = None

    def is_cooldown_active(self):
        return self.cooldown_until and datetime.utcnow() < self.cooldown_until

    async def execute_trade(self, signal):
        try:
            units = CONFIG.DEFAULT_UNITS
            if units <= 0:
                logger.warning("Zero units, skipping trade execution.")
 