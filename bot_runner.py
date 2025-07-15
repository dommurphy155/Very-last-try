import asyncio
from trading_bot import TradingBot
from telegram_interface import TelegramBot

async def main():
    trading_bot = TradingBot()
    telegram_bot = TelegramBot(trading_bot)

    await asyncio.gather(
        trading_bot.run(),
        telegram_bot.run()
    )

if __name__ == "__main__":
    asyncio.run(main())
