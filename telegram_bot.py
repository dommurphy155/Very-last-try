import asyncio
import logging
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token, chat_id, state, trade_executor):
        self.token = token
        self.chat_id = chat_id
        self.state = state
        self.trade_executor = trade_executor
        self.app = None

    async def start(self):
        self.app = ApplicationBuilder().token(self.token).build()
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("maketrade", self.maketrade))
        self.app.add_handler(CommandHandler("whatyoudoin", self.whatyoudoin))
        logger.info("✅ Telegram bot initialized.")

    async def run(self):
        if not self.app:
            await self.start()
        logger.info("▶️ Telegram bot polling started.")
        try:
            await self.app.run_polling()
        except Exception as e:
            logger.error(f"Telegram bot polling error: {e}")

    async def stop(self):
        if self.app:
            await self.app.shutdown()
            await self.app.stop()
            logger.info("🛑 Telegram bot stopped.")

    async def send_message(self, text):
        if not self.app:
            logger.warning("Telegram app not started yet.")
            return
        try:
            await self.app.bot.send_message(chat_id=self.chat_id, text=text)
        except Exception as e:
            logger.error(f"Telegram send error: {e}")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = f"🤖 Bot Status\n"
        msg += f"Trades: {len(self.state.get('open_trades', {}))}\n"
        msg += f"Cooldown: {self.trade_executor.is_cooldown_active()}\n"
        msg += f"Last Scan: {self.state.get('last_scan')}\n"
        await update.message.reply_text(msg)

    async def maketrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        signal = await self.trade_executor.trade_logic.generate_signal()
        if signal:
            success = await self.trade_executor.execute_trade(signal)
            await update.message.reply_text(f"Manual trade {'✅' if success else '❌'}: {signal}")
        else:
            await update.message.reply_text("No valid signal.")

    async def whatyoudoin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        diag = f"📊 Diagnostics\n"
        diag += f"Open Trades: {len(self.state.get('open_trades', {}))}\n"
        diag += f"State Keys: {list(self.state.keys())}\n"
        await update.message.reply_text(diag)