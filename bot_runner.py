import asyncio
import logging
import nest_asyncio
import signal
import sys
from telegram_bot import TelegramBot
from trading_bot import TradingBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('trading_bot.log')
    ]
)

logger = logging.getLogger(__name__)

class BotRunner:
    def __init__(self):
        self.telegram_bot = None
        self.trading_bot = None
        self.is_running = False
        self.tasks = []

    async def start(self):
        """Start both the trading bot and Telegram bot"""
        try:
            logger.info("🚀 Starting AI Forex Trading Bot...")
            
            # Initialize bots
            self.telegram_bot = TelegramBot()
            self.trading_bot = TradingBot()
            
            self.is_running = True
            
            # Start trading bot in background
            trading_task = asyncio.create_task(self._run_trading_bot())
            self.tasks.append(trading_task)
            
            # Start Telegram bot
            telegram_task = asyncio.create_task(self._run_telegram_bot())
            self.tasks.append(telegram_task)
            
            logger.info("✅ Both bots started successfully")
            
            # Wait for both tasks
            await asyncio.gather(*self.tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"❌ Error starting bots: {e}")
            raise
        finally:
            await self.stop()

    async def _run_trading_bot(self):
        """Run the trading bot with continuous scanning"""
        try:
            logger.info("🤖 Starting trading bot...")
            await self.trading_bot.start()
        except Exception as e:
            logger.error(f"❌ Trading bot error: {e}")
            self.is_running = False

    async def _run_telegram_bot(self):
        """Run the Telegram bot"""
        try:
            logger.info("📱 Starting Telegram bot...")
            await self.telegram_bot.run_polling()
        except Exception as e:
            logger.error(f"❌ Telegram bot error: {e}")
            self.is_running = False

    async def stop(self):
        """Stop both bots gracefully"""
        logger.info("🛑 Stopping bots...")
        self.is_running = False
        
        # Stop trading bot
        if self.trading_bot:
            try:
                await self.trading_bot.stop()
                logger.info("✅ Trading bot stopped")
            except Exception as e:
                logger.error(f"❌ Error stopping trading bot: {e}")
        
        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("✅ All bots stopped")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"📡 Received signal {signum}, shutting down...")
    sys.exit(0)

async def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and start bot runner
    runner = BotRunner()
    
    try:
        await runner.start()
    except KeyboardInterrupt:
        logger.info("🛑 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
    finally:
        await runner.stop()

if __name__ == "__main__":
    # Apply nest_asyncio for Jupyter compatibility
    nest_asyncio.apply()
    
    # Run the main function
    asyncio.run(main())