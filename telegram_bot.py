import logging
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import asyncio

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

        # Run polling in a background task
        asyncio.create_task(self.app.run_polling())
        logger.info("Telegram bot started.")

    async def stop(self):
        if self.app:
            await self.app.shutdown()
            await self.app.stop()
            logger.info("Telegram bot stopped.")

    async def send_message(self, text):
        if not self.app:
            logger.warning("Telegram app not started yet.")
            return
        bot: Bot = self.app.bot
        try:
            await bot.send_message(chat_id=self.chat_id, text=text)
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        open_trades = self.state.get("open_trades", {})
        message = f"🤖 Bot Status:\nOpen Trades: {len(open_trades)}\n"
        message += f"Cooldown Active: {self.trade_executor.is_cooldown_active()}\n"
        message += f"Last Scan: {self.state.get('last_scan')}\n"
        await update.message.reply_text(message)

    async def maketrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        signal = await self.trade_executor.trade_logic.generate_signal()
        if signal in ("BUY", "SELL"):
            success = await self.trade_executor.execute_trade(signal)
            msg = f"Manual trade {'executed' if success else 'failed'}: {signal}"
        else:
            msg = "No valid trade signal to execute."
        await update.message.reply_text(msg)

    async def whatyoudoin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        diagnostics = (
            f"📊 Diagnostics:\n"
            f"Open Trades: {len(self.state.get('open_trades', {}))}\n"
            f"Cooldown Active: {self.trade_executor.is_cooldown_active()}\n"
            f"State Keys: {list(self.state.keys())}\n"
        )
        await update.message.reply_text(diagnostics)