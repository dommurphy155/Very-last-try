import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError
from trading_bot import TradingBot

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
        self.trading_bot = TradingBot()
        self.last_trade_info = None

        self.app = Application.builder().token(self.token).build()

        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("maketrade", self.trade))
        self.app.add_handler(CommandHandler("whatyoudoin", self.diagnostics))
        self.app.add_error_handler(self.error_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🤖 Bot is live. Use /maketrade to place a trade.")

    async def trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.trading_bot.run()
        self.last_trade_info = f"Instrument: {self.trading_bot.instrument}"
        await update.message.reply_text("📈 Trade command executed.")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        status_msg = f"📊 Instrument: {self.trading_bot.instrument}\n"
        status_msg += f"📌 Last trade: {self.last_trade_info or 'No trades yet'}"
        await update.message.reply_text(status_msg)

    async def diagnostics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("🔍 Running diagnostics...")
        # Placeholder: extend this with actual diagnostic logic from your bot
        await update.message.reply_text("✅ All systems operational.")

    async def error_handler(self, update, context):
        logger.error(f"Telegram error: {context.error}")
        if update and update.message:
            await update.message.reply_text("⚠️ An error occurred while processing your command.")

    async def run_polling(self):
        await self.app.run_polling()