import asyncio
import logging
import nest_asyncio
from telegram_bot import TelegramBot

logging.basicConfig(level=logging.INFO)

async def main():
    bot = TelegramBot()
    await bot.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    finally:
        pass  # Avoid closing the loop to prevent runtime errors