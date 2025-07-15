import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from trading_bot import TradingBot

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self, token, chat_id, trading_bot):
        self.token = token
        self.chat_id = chat_id
        self.trading_bot = trading_bot
        self.app = ApplicationBuilder().token(self.token).build()

        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("maketrade", self.make_trade))
        self.app.add_handler(CommandHandler("stop", self.stop))
        self.app.add_handler(CommandHandler("closeall", self.close_all))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="🤖 AI Forex Bot started. Use /status to check bot status.")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        open_trades = self.trading_bot.state.get("open_trades", {})
        msg = f"Bot running: {self.trading_bot.running}\nOpen trades: {len(open_trades)}"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

    async def make_trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.trading_bot.running:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Bot is not running.")
            return
        await self.trading_bot.trade_cycle()
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Trade cycle executed.")

    async def stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.trading_bot.stop()
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Bot stopped.")

    async def close_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        trades = list(self.trading_bot.state.get("open_trades", {}).keys())
        for trade_id in trades:
            await self.trading_bot.client.close_trade(trade_id)
            self.trading_bot.state["open_trades"].pop(trade_id, None)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="All trades closed.")

    def run(self):
        self.app.run_polling()