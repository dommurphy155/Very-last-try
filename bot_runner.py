import asyncio
import logging
import signal
from trading_bot import TradingBot
from telegram_bot import TelegramBot
from state_manager import StateManager
from config import CONFIG

logger = logging.getLogger(__name__)

class BotRunner:
    def __init__(self):
        self.state_manager = StateManager(CONFIG.STATE_FILE)
        self.state = self.state_manager.load_state()
        self.trading_bot = TradingBot(self.state)
        self.telegram_bot = TelegramBot(
            CONFIG.TELEGRAM_BOT_TOKEN, CONFIG.TELEGRAM_CHAT_ID, self.state, self.trading_bot.trade_executor
        )
        self.running = True
        self.loop = asyncio.get_event_loop()
        self.main_task = None

    async def run(self):
        await self.telegram_bot.start()
        await self.trading_bot.start()

        while self.running:
            try:
                await self.trading_bot.trade_cycle()
                self.state_manager.save_state(self.state)
                await asyncio.sleep(CONFIG.SCAN_INTERVAL)
            except Exception as e:
                logger.exception(f"Error in main loop: {e}")
                await self.telegram_bot.send_message(f"⚠️ Error in main loop: {e}")

        await self.shutdown()

    async def shutdown(self):
        if not self.running:
            return
        logger.info("Shutting down bot...")
        self.running = False
        await self.telegram_bot.stop()
        await self.trading_bot.stop()
        self.state_manager.save_state(self.state)
        await self.trading_bot.close()  # Correct client close here
        logger.info("Shutdown complete.")

    def start(self):
        self.main_task = self.loop.create_task(self.run())

        for sig in (signal.SIGINT, signal.SIGTERM):
            self.loop.add_signal_handler(sig, lambda: asyncio.create_task(self.shutdown()))

        try:
            self.loop.run_until_complete(self.main_task)
        finally:
            self.loop.close()

def main():
    runner = BotRunner()
    runner.start()

if __name__ == "__main__":
    main()