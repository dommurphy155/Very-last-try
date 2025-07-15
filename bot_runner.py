import asyncio
import logging
import signal

from trading_bot import TradingBot
from telegram_interface import TelegramBot
from state_manager import StateManager
from oanda_client import OandaClient
from config import CONFIG

logger = logging.getLogger(__name__)

class BotRunner:
    def __init__(self):
        self.state_manager = StateManager(CONFIG.STATE_FILE)
        self.state = self.state_manager.load_state()
        self.client = OandaClient(CONFIG.OANDA_API_KEY, CONFIG.OANDA_ACCOUNT_ID)
        self.trading_bot = TradingBot(self.state, self.client)
        self.telegram_bot = TelegramBot(
            CONFIG.TELEGRAM_BOT_TOKEN, CONFIG.TELEGRAM_CHAT_ID, self.state, self.trading_bot.trade_executor
        )
        self.running = True

    async def run(self):
        await self.client.init_session()
        await self.telegram_bot.start()
        await self.trading_bot.start()

        telegram_task = asyncio.create_task(self.telegram_bot.run())

        try:
            while self.running:
                try:
                    await self.trading_bot.trade_cycle()
                    self.state_manager.save_state(self.state)
                    await asyncio.sleep(CONFIG.SCAN_INTERVAL)
                except Exception as e:
                    logger.exception(f"Error in trade cycle: {e}")
                    await self.telegram_bot.send_message(f"⚠️ Error in trade cycle: {e}")
        finally:
            telegram_task.cancel()
            await self.shutdown()

    async def shutdown(self):
        if not self.running:
            return
        self.running = False
        await self.telegram_bot.stop()
        await self.trading_bot.stop()
        self.state_manager.save_state(self.state)
        await self.client.close()
        logger.info("✅ Bot shutdown complete.")

async def main():
    runner = BotRunner()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(runner.shutdown()))
    await runner.run()

if __name__ == "__main__":
    asyncio.run(main())