import asyncio
import logging
import nest_asyncio
from telegram_bot import TelegramBot

logging.basicConfig(level=logging.INFO)

nest_asyncio.apply()

async def main():
    bot = TelegramBot()
    await bot.run_polling()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        pass