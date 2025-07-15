import asyncio
import logging
import sys
from config import CONFIG
from oanda_client import OandaClient
from state_manager import StateManager
from trading_bot import TradingBot
from telegram_interface import TelegramBot


def setup_logging():
    logging.basicConfig(
        level=getattr(logging, CONFIG.LOGGING_LEVEL),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


async def main():
    setup_logging()
    state_manager = StateManager()
    state = state_manager.state

    client = OandaClient(CONFIG.OANDA_API_KEY, CONFIG.OANDA_ACCOUNT_ID)
    await client.init_session()

    trading_bot = TradingBot(state, client)
    telegram_bot = TelegramBot(
        CONFIG.TELEGRAM_BOT_TOKEN, CONFIG.TELEGRAM_CHAT_ID, trading_bot
    )

    await trading_bot.start()
    telegram_task = asyncio.create_task(telegram_bot.run())

    try:
        while trading_bot.running:
            await trading_bot.trade_cycle()
            state_manager.set("open_trades", state.get("open_trades", {}))
            await asyncio.sleep(7)
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, stopping bot.")
        await trading_bot.stop()
        telegram_task.cancel()
        try:
            await telegram_task
        except asyncio.CancelledError:
            pass
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
