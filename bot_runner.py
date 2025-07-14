import asyncio
import logging
from telegram_bot import TelegramBot

logging.basicConfig(level=logging.INFO)

async def main():
    bot = TelegramBot()
    await bot.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())