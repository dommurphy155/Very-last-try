import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError
from trading_bot import TradingBot

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        self.token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = int(os.getenv("TELEGRAM_CHAT_ID", "0"))
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN must be set in environment variables")
        
        self.trading_bot = TradingBot()
        self.last_trade_info = None
        self.bot_start_time = datetime.utcnow()

        # Initialize Telegram application
        self.app = Application.builder().token(self.token).build()

        # Add command handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(CommandHandler("maketrade", self.trade))
        self.app.add_handler(CommandHandler("whatyoudoin", self.diagnostics))
        self.app.add_handler(CommandHandler("opentrades", self.open_trades))
        self.app.add_handler(CommandHandler("daily", self.daily_report))
        self.app.add_handler(CommandHandler("weekly", self.weekly_report))
        self.app.add_handler(CommandHandler("stop", self.stop_bot))
        self.app.add_handler(CommandHandler("closeall", self.close_all_trades))
        
        # Add error handler
        self.app.add_error_handler(self.error_handler)

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        try:
            welcome_msg = (
                "🤖 *AI Forex Trading Bot Started*\n\n"
                "📊 *Available Commands:*\n"
                "• `/start` - Show this message\n"
                "• `/status` - Bot status and health\n"
                "• `/maketrade` - Execute manual trade\n"
                "• `/whatyoudoin` - Run diagnostics\n"
                "• `/opentrades` - Show open trades\n"
                "• `/daily` - Daily trading report\n"
                "• `/weekly` - Weekly trading report\n"
                "• `/stop` - Stop the bot\n"
                "• `/closeall` - Close all trades\n\n"
                "🔄 Bot scans every 7 seconds for opportunities\n"
                "⚡ Auto-trades with 60%+ win rate target\n"
                "🛡️ Risk management: 1-3% per trade, 10% max drawdown"
            )
            
            await update.message.reply_text(welcome_msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("❌ Error processing start command")

    async def trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /maketrade command"""
        try:
            await update.message.reply_text("🔄 Executing trading cycle...")
            
            result = await self.trading_bot.run()
            
            if not result['success']:
                await update.message.reply_text(f"⚠️ No trade executed: {result['reason']}")
                return
            
            # Format trade results
            trades_executed = result['trades_executed']
            trades_closed = result['trades_closed']
            
            if trades_executed == 0 and trades_closed == 0:
                await update.message.reply_text("ℹ️ No trades executed or closed in this cycle")
                return
            
            # Build response message
            msg = "📈 *Trading Cycle Results*\n\n"
            
            if trades_executed > 0:
                msg += f"✅ *Trades Executed:* {trades_executed}\n"
            
            if trades_closed > 0:
                msg += f"📉 *Trades Closed:* {trades_closed}\n"
            
            # Add risk summary
            risk_summary = result.get('risk_summary', {})
            if risk_summary:
                msg += f"\n🛡️ *Risk Status:*\n"
                msg += f"• Drawdown: {risk_summary.get('current_drawdown', 0):.2%}\n"
                msg += f"• Open Trades: {risk_summary.get('open_trades', 0)}\n"
                msg += f"• Can Trade: {'✅' if risk_summary.get('can_trade', False) else '❌'}\n"
            
            # Add errors if any
            if result.get('errors'):
                msg += f"\n⚠️ *Errors:* {len(result['errors'])}"
                for error in result['errors'][:3]:  # Show first 3 errors
                    msg += f"\n• {error}"
            
            await update.message.reply_text(msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in trade command: {e}")
            await update.message.reply_text("❌ Error executing trade")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        try:
            # Get session stats
            session_stats = self.trading_bot.get_session_stats()
            
            # Calculate uptime
            uptime = datetime.utcnow() - self.bot_start_time
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds
            
            # Get account info
            balance = await self.trading_bot.oanda.get_account_balance()
            equity = await self.trading_bot.oanda.get_equity()
            
            # Get risk summary
            risk_summary = self.trading_bot.position_sizer.get_risk_summary()
            
            # Build status message
            msg = "📊 *Bot Status Report*\n\n"
            
            # System status
            msg += "🖥️ *System:*\n"
            msg += f"• Uptime: {uptime_str}\n"
            msg += f"• Scans Completed: {session_stats['scans_completed']}\n"
            msg += f"• Errors: {session_stats['errors']}\n"
            
            # Account status
            msg += "\n💰 *Account:*\n"
            if balance is not None:
                msg += f"• Balance: £{balance:,.2f}\n"
            if equity is not None:
                msg += f"• Equity: £{equity:,.2f}\n"
                if balance is not None:
                    pnl = equity - balance
                    msg += f"• P&L: £{pnl:,.2f} ({pnl/balance*100:.2f}%)\n"
            
            # Trading status
            msg += "\n📈 *Trading:*\n"
            msg += f"• Trades Executed: {session_stats['trades_executed']}\n"
            msg += f"• Trades Closed: {session_stats['trades_closed']}\n"
            msg += f"• Open Trades: {risk_summary.get('open_trades', 0)}\n"
            msg += f"• Drawdown: {risk_summary.get('current_drawdown', 0):.2%}\n"
            msg += f"• Can Trade: {'✅' if risk_summary.get('can_trade', False) else '❌'}\n"
            
            await update.message.reply_text(msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in status command: {e}")
            await update.message.reply_text("❌ Error getting status")

    async def open_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /opentrades command"""
        try:
            trades = await self.trading_bot.get_open_trades()
            
            if not trades:
                await update.message.reply_text("📭 No open trades at the moment.")
                return
            
            msg = f"📂 *Open Trades ({len(trades)})*\n\n"
            
            for i, trade in enumerate(trades, 1):
                instrument = trade.get('instrument', 'Unknown')
                units = trade.get('units', 0)
                entry_price = trade.get('entry_price', 0)
                unrealized_pl = trade.get('unrealized_pl', 0)
                duration = trade.get('duration', 'Unknown')
                confidence = trade.get('confidence', 0)
                
                # Format P&L
                pl_str = f"£{unrealized_pl:,.2f}" if unrealized_pl != 0 else "£0.00"
                pl_emoji = "🟢" if unrealized_pl > 0 else "🔴" if unrealized_pl < 0 else "⚪"
                
                msg += f"{i}. *{instrument}*\n"
                msg += f"   • Units: {units:,}\n"
                msg += f"   • Entry: {entry_price:.5f}\n"
                msg += f"   • P&L: {pl_emoji} {pl_str}\n"
                msg += f"   • Duration: {duration}\n"
                msg += f"   • Confidence: {confidence:.2f}\n\n"
            
            msg += "🔔 Monitor positions carefully and adjust risk accordingly."
            
            await update.message.reply_text(msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in open_trades command: {e}")
            await update.message.reply_text("❌ Error getting open trades")

    async def daily_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /daily command"""
        try:
            await update.message.reply_text("📅 Generating daily report...")
            
            report = await self.trading_bot.get_daily_report()
            
            if 'error' in report:
                await update.message.reply_text(f"❌ Error generating report: {report['error']}")
                return
            
            # Build daily report message
            msg = "📅 *Daily Trading Report*\n\n"
            
            # Account section
            account = report.get('account', {})
            if account:
                msg += "💰 *Account Summary:*\n"
                if account.get('balance'):
                    msg += f"• Balance: £{account['balance']:,.2f}\n"
                if account.get('equity'):
                    msg += f"• Equity: £{account['equity']:,.2f}\n"
                if account.get('daily_pnl'):
                    pnl = account['daily_pnl']
                    msg += f"• Daily P&L: £{pnl:,.2f} ({pnl/account['balance']*100:.2f}%)\n"
            
            # Trading section
            trading = report.get('trading', {})
            if trading:
                msg += "\n📈 *Trading Activity:*\n"
                msg += f"• Open Trades: {trading.get('open_trades', 0)}\n"
                
                session_stats = trading.get('session_stats', {})
                if session_stats:
                    msg += f"• Trades Executed: {session_stats.get('trades_executed', 0)}\n"
                    msg += f"• Trades Closed: {session_stats.get('trades_closed', 0)}\n"
                    msg += f"• Scans Completed: {session_stats.get('scans_completed', 0)}\n"
                
                # Risk summary
                risk_summary = trading.get('risk_summary', {})
                if risk_summary:
                    msg += f"• Drawdown: {risk_summary.get('current_drawdown', 0):.2%}\n"
                    msg += f"• Consecutive Losses: {risk_summary.get('consecutive_losses', 0)}\n"
            
            # Performance summary
            performance = trading.get('performance_summary', {})
            if performance:
                msg += "\n📊 *Performance Summary:*\n"
                for instrument, perf in list(performance.items())[:5]:  # Top 5 instruments
                    win_rate = perf.get('win_rate', 0)
                    total_trades = perf.get('total_trades', 0)
                    if total_trades > 0:
                        msg += f"• {instrument}: {win_rate:.1%} ({total_trades} trades)\n"
            
            await update.message.reply_text(msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in daily_report command: {e}")
            await update.message.reply_text("❌ Error generating daily report")

    async def weekly_report(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /weekly command"""
        try:
            await update.message.reply_text("📆 Generating weekly report...")
            
            report = await self.trading_bot.get_weekly_report()
            
            if 'error' in report:
                await update.message.reply_text(f"❌ Error generating report: {report['error']}")
                return
            
            # Build weekly report message
            msg = "📆 *Weekly Trading Report*\n\n"
            
            msg += f"📊 *Summary:*\n"
            msg += f"• Total Trades: {report.get('trades', 0)}\n"
            msg += f"• Winning Trades: {report.get('winning_trades', 0)}\n"
            msg += f"• Win Rate: {report.get('win_rate', 0):.1%}\n"
            msg += f"• Total P&L: £{report.get('total_pnl', 0):,.2f}\n"
            msg += f"• Avg Trade P&L: £{report.get('avg_trade_pnl', 0):,.2f}\n"
            msg += f"• Best Trade: £{report.get('best_trade', 0):,.2f}\n"
            msg += f"• Worst Trade: £{report.get('worst_trade', 0):,.2f}\n"
            
            await update.message.reply_text(msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in weekly_report command: {e}")
            await update.message.reply_text("❌ Error generating weekly report")

    async def diagnostics(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /whatyoudoin command"""
        try:
            await update.message.reply_text("🔍 Running comprehensive diagnostics...")
            
            diagnostics = await self.trading_bot.run_diagnostics()
            
            if diagnostics['system_status'] == 'CRITICAL_ERROR':
                await update.message.reply_text(f"❌ Critical system error: {diagnostics.get('error', 'Unknown')}")
                return
            
            # Build diagnostics message
            msg = "🔍 *System Diagnostics*\n\n"
            
            # Overall status
            status_emoji = "✅" if diagnostics['system_status'] == 'OK' else "⚠️"
            msg += f"{status_emoji} *Overall Status:* {diagnostics['system_status']}\n\n"
            
            # Component status
            msg += "🔧 *Components:*\n"
            msg += f"• OANDA Connection: {diagnostics.get('oanda_connection', 'UNKNOWN')}\n"
            msg += f"• Instrument Analysis: {diagnostics.get('instrument_analysis', 'UNKNOWN')}\n"
            msg += f"• Risk Management: {diagnostics.get('risk_management', 'UNKNOWN')}\n"
            msg += f"• Open Trades: {diagnostics.get('open_trades', 'UNKNOWN')}\n"
            
            # Risk summary if available
            risk_summary = diagnostics.get('risk_summary', {})
            if risk_summary:
                msg += f"\n🛡️ *Risk Status:*\n"
                msg += f"• Drawdown: {risk_summary.get('current_drawdown', 0):.2%}\n"
                msg += f"• Can Trade: {'✅' if risk_summary.get('can_trade', False) else '❌'}\n"
            
            # Errors if any
            errors = diagnostics.get('errors', [])
            if errors:
                msg += f"\n⚠️ *Errors ({len(errors)}):*\n"
                for error in errors[:3]:  # Show first 3 errors
                    msg += f"• {error}\n"
            
            await update.message.reply_text(msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in diagnostics command: {e}")
            await update.message.reply_text("❌ Error running diagnostics")

    async def stop_bot(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command"""
        try:
            await update.message.reply_text("🛑 Stopping trading bot...")
            await self.trading_bot.stop()
            await update.message.reply_text("✅ Trading bot stopped successfully")
            
        except Exception as e:
            logger.error(f"Error in stop_bot command: {e}")
            await update.message.reply_text("❌ Error stopping bot")

    async def close_all_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /closeall command"""
        try:
            await update.message.reply_text("🔄 Closing all open trades...")
            
            result = await self.trading_bot.force_close_all_trades("Manual close via Telegram")
            
            msg = f"📉 *Close All Results*\n\n"
            msg += f"• Trades Closed: {result['trades_closed']}\n"
            
            if result['errors']:
                msg += f"• Errors: {len(result['errors'])}\n"
                for error in result['errors'][:2]:  # Show first 2 errors
                    msg += f"  - {error}\n"
            
            await update.message.reply_text(msg, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in close_all_trades command: {e}")
            await update.message.reply_text("❌ Error closing trades")

    async def error_handler(self, update, context):
        """Handle Telegram errors"""
        logger.error(f"Telegram error: {context.error}")
        try:
            if update and update.message:
                await update.message.reply_text("⚠️ An error occurred while processing your command.")
        except:
            pass

    async def run_polling(self):
        """Start the Telegram bot polling"""
        try:
            logger.info("🤖 Starting Telegram bot...")
            await self.app.initialize()
            await self.app.start()
            await self.app.run_polling(drop_pending_updates=True)
        except Exception as e:
            logger.error(f"Error starting Telegram bot: {e}")
            raise