import asyncio
import logging
from config import CONFIG
from state_manager import StateManager
from oanda_client import OandaClient
from trading_bot import TradingBot
from telegram_interface import TelegramBot

logger = logging.getLogger(__name__)

async def main():
    state = StateManager()
    client = OandaClient(CONFIG.OANDA_API_KEY, CONFIG.OANDA_ACCOUNT_ID)
    await client.init_session()

    trading_bot = TradingBot(state.state, client)
    telegram_bot = TelegramBot(CONFIG.TELEGRAM_BOT_TOKEN, CONFIG.TELEGRAM_CHAT_ID, trading_bot)

    await trading_bot.start()

    # Start telegram bot polling in background
    telegram_task = asyncio.create_task(telegram_bot.run())

    try:
        while True:
            await trading_bot.trade_cycle()
            await asyncio.sleep(CONFIG.COOLDOWN_SECONDS)
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received, shutting down.")
    finally:
        await trading_bot.stop()
        await client.close()
        telegram_task.cancel()
        try:
            await telegram_task
        except asyncio.CancelledError:
            pass

if __name__ == "__main__":
    logging.basicConfig(level=CONFIG.LOGGING_LEVEL)
    asyncio.run(main())
 