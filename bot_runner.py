import asyncio
import aiohttp
import signal
import sys
import logging
from trading_bot import TradingBot
from oanda_client import OandaClient
from telegram_bot import build_telegram_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    async with aiohttp.ClientSession() as session:
        oanda = OandaClient(session)
        bot = TradingBot(oanda)
        telegram_app = build_telegram_app(bot)
        await bot.set_telegram_bot(telegram_app.bot)

        async def trade_loop():
            while True:
                try:
                    await bot.check_and_trade()
                except Exception as e:
                    logger.error(f"Trade loop error: {e}")
                    await bot.send_telegram_message(f"⚠️ Trade loop error: {e}")
                await asyncio.sleep(20)

        trade_task = asyncio.create_task(trade_loop())

        # Graceful shutdown handling
        def shutdown():
            trade_task.cancel()
            asyncio.create_task(telegram_app.stop())
            logger.info("Shutdown initiated")

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, shutdown)

        await telegram_app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())