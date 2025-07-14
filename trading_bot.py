import os
import time
import json
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from technical_analysis import TechnicalAnalyzer

logger = logging.getLogger(__name__)

STATE_FILE = "bot_state.json"
LOG_FILE = "trading_log.json"
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {"open_trades": {}, "pnl": 0.0, "trade_count": 0}

def save_state(state):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    import os
    os.replace(tmp, STATE_FILE)

def load_log():
    try:
        with open(LOG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_log(log):
    tmp = LOG_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(log, f)
    import os
    os.replace(tmp, LOG_FILE)

class TradingBot:
    def __init__(self, oanda_client):
        self.oanda = oanda_client
        self.state = load_state()
        self.log = load_log()
        self.technical_analyzer = TechnicalAnalyzer()
        self.last_trade_time = 0
        self.trade_cooldown = 15
        self.telegram_bot = None

    async def set_telegram_bot(self, telegram_bot):
        self.telegram_bot = telegram_bot

    async def check_and_trade(self):
        now = time.time()
        if now - self.last_trade_time < self.trade_cooldown:
            logger.debug("Trade cooldown active, skipping")
            return
        analysis = self.technical_analyzer.analyze()
        signal = analysis.get("signal")
        confidence = analysis.get("confidence", 0)
        if confidence < 0.6:
            await self.send_telegram_message(f"Signal confidence too low ({confidence:.2f}), skipping trade.")
            return
        if signal == "buy":
            trade_resp = await self.oanda.create_trade("EUR_USD", 100, "buy")
            self.state["trade_count"] += 1
            self.state["open_trades"][str(self.state["trade_count"])] = {
                "instrument": "EUR_USD",
                "units": 100,
                "side": "buy",
                "timestamp": datetime.utcnow().isoformat()
            }
            save_state(self.state)
            await self.send_telegram_message(f"Executed BUY trade on EUR_USD with 100 units (confidence {confidence:.2f})")
            self.last_trade_time = now

    async def send_telegram_message(self, text):
        if not self.telegram_bot:
            logger.warning("Telegram bot not set, cannot send message")
            return
        try:
            await self.telegram_bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Telegram send message failed: {e}")

    async def get_status(self):
        pnl = self.state.get("pnl", 0.0)
        trades = len(self.state.get("open_trades", {}))
        return f" 916 *Demo Trading Bot Status*\nOpen Trades: {trades}\nTotal PnL: {pnl:.2f}"

    async def cancel_all_trades(self):
        trades = self.state.get("open_trades", {})
        for trade_id in list(trades.keys()):
            if getattr(self.oanda, 'DEMO_MODE', True):
                logger.info(f"DEMO_MODE: pretend close trade {trade_id}")
                del trades[trade_id]
                continue
            resp = await self.oanda.close_trade(trade_id)
            if resp:
                del trades[trade_id]
        save_state(self.state)
        await self.send_telegram_message("Cancelled all open trades.")

    # Command handlers

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Welcome! Demo Forex Bot is running. Use /status to check status.")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        status = await self.get_status()
        await update.message.reply_text(status, parse_mode="Markdown")

    async def cmd_maketrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.check_and_trade()
        await update.message.reply_text("Trade command executed.")

    async def cmd_canceltrade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await self.cancel_all_trades()
        await update.message.reply_text("Cancelled all trades.")

    async def cmd_showlog(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Logs feature not implemented yet.")

    async def cmd_pnl(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        pnl = self.state.get("pnl", 0.0)
        await update.message.reply_text(f"Current PnL: {pnl:.2f}")

    async def cmd_openpositions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        trades = self.state.get("open_trades", {})
        if not trades:
            await update.message.reply_text("No open trades.")
            return
        msg = "Open Trades:\n"
        for tid, info in trades.items():
            msg += f"Trade ID {tid}: {info['instrument']} {info['side']} {info['units']} units\n"
        await update.message.reply_text(msg)

    async def cmd_strategystats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("Strategy stats feature not implemented yet.")