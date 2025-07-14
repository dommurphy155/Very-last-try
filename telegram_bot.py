from telegram.ext import ApplicationBuilder, CommandHandler
import os

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

class TelegramAppWrapper:
    def __init__(self, app, bot):
        self.app = app
        self.bot = bot
    async def run_polling(self):
        await self.app.run_polling()
    async def stop(self):
        await self.app.stop()

def build_telegram_app(trading_bot):
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", trading_bot.cmd_start))
    app.add_handler(CommandHandler("status", trading_bot.cmd_status))
    app.add_handler(CommandHandler("maketrade", trading_bot.cmd_maketrade))
    app.add_handler(CommandHandler("canceltrade", trading_bot.cmd_canceltrade))
    app.add_handler(CommandHandler("showlog", trading_bot.cmd_showlog))
    app.add_handler(CommandHandler("pnl", trading_bot.cmd_pnl))
    app.add_handler(CommandHandler("openpositions", trading_bot.cmd_openpositions))
    app.add_handler(CommandHandler("strategystats", trading_bot.cmd_strategystats))
    return TelegramAppWrapper(app, app.bot)