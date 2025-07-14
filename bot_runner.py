import asyncio
import logging
import nest_asyncio
from telegram_bot import TelegramBot

logging.basicConfig(level=logging.INFO)

async def main():
    bot = TelegramBot()
    await bot.app.initialize()
    await bot.app.start()
    # Run polling until stopped externally (Ctrl+C)
    await bot.app.updater.start_polling()
    await bot.app.updater.idle()
    await bot.app.stop()
    await bot.app.shutdown()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.run(main())