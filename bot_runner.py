import asyncio
import logging
from telegram_bot import TelegramBot
import nest_asyncio

logging.basicConfig(level=logging.INFO)

async def main():
    bot = TelegramBot()
    await bot.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())