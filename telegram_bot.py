import os
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from trading_bot import TradingBot

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
        self.trading_bot = TradingBot()
        self.app = ApplicationBuilder().token(self.token).build()
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("trade", self.trade))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Bot is running. Use /trade to place a trade.")

    async def trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        self.trading_bot.run()
        await update.message.reply_text("Trade command executed.")

    async def run_polling(self):
        await self.app.run_polling()