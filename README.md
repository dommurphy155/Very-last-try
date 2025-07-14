# 🤖 AI Forex Trading Bot

A production-ready, AI-powered Forex trading bot for OANDA demo accounts with Telegram integration, advanced risk management, and 24/7 automated trading capabilities.

## 🎯 Features

### Core Trading Features
- **7-second market scanning** for optimal trade opportunities
- **Advanced instrument analysis** with momentum, volatility, and trend detection
- **Intelligent position sizing** using Kelly Criterion and risk management
- **Multi-strategy approach** combining momentum and mean-reversion
- **Trailing stops** and dynamic exit strategies
- **Performance tracking** with confidence scoring per instrument

### Risk Management
- **1-3% risk per trade** (adjustable based on confidence)
- **10% maximum drawdown** protection
- **2% daily loss limit** with automatic trading halt
- **Consecutive loss protection** (stops after 5 losses)
- **Margin and balance validation** before each trade
- **Cooldown periods** between trades (6 seconds minimum)

### Telegram Integration
- **Real-time commands** for manual control
- **Comprehensive reporting** (daily/weekly summaries)
- **Live status monitoring** with account metrics
- **Trade execution** via `/maketrade` command
- **Emergency controls** (stop bot, close all trades)

### Technical Features
- **Fully async architecture** with no blocking operations
- **Rate limiting** and retry logic for API calls
- **Comprehensive error handling** and logging
- **State persistence** with JSON file storage
- **Production-grade logging** with file rotation

## 📋 Requirements

### Environment Variables
```bash
# OANDA API Configuration
OANDA_API_KEY=your_oanda_api_key_here
OANDA_ACCOUNT_ID=your_oanda_account_id_here

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

### Python Dependencies
- Python 3.10.18+
- httpx>=0.24.0
- python-telegram-bot==20.3
- pandas>=1.5.0
- numpy>=1.21.0
- asyncio-throttle>=1.0.0
- python-dateutil>=2.8.0
- nest_asyncio

## 🚀 Installation & Setup

### 1. Clone the Repository
```bash
git clone <repository-url>
cd ai-forex-trading-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables
```bash
export OANDA_API_KEY="your_api_key"
export OANDA_ACCOUNT_ID="your_account_id"
export TELEGRAM_BOT_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
```

### 4. Run the Bot
```bash
python bot_runner.py
```

## 📊 Trading Strategy

### Market Analysis
The bot analyzes 10 major currency pairs:
- EUR/USD, GBP/USD, USD/JPY, AUD/USD, USD/CHF
- USD/CAD, NZD/USD, EUR/GBP, EUR/JPY, GBP/JPY

### Technical Indicators
- **RSI & MACD** for momentum analysis
- **Moving Averages** (20 & 50 period) for trend detection
- **ATR** for volatility-based stop losses
- **Support/Resistance** levels for entry/exit points
- **Volume analysis** for market participation

### Entry Conditions
- **Confidence score > 0.5** (based on historical performance)
- **Risk management checks** passed
- **Market regime detection** (trending/ranging/volatile)
- **Margin availability** confirmed

### Exit Conditions
- **Profit target reached** (3+ pips with 1.2+ R:R ratio)
- **Trailing stop hit** (15 pips trailing distance)
- **Time-based exit** (4 hours maximum)
- **Momentum reversal** detected
- **Maximum loss** exceeded (30 pips)

## 📱 Telegram Commands

### Basic Commands
- `/start` - Show welcome message and available commands
- `/status` - Display bot status, account info, and trading metrics
- `/maketrade` - Execute a manual trading cycle

### Monitoring Commands
- `/opentrades` - Show all currently open trades with details
- `/whatyoudoin` - Run comprehensive system diagnostics
- `/daily` - Generate detailed daily trading report
- `/weekly` - Generate weekly performance summary

### Control Commands
- `/stop` - Stop the trading bot gracefully
- `/closeall` - Force close all open trades

## 📈 Performance Metrics

### Target Performance
- **60%+ win rate** across all instruments
- **10-15 positive trades per day**
- **Maximum 10% drawdown**
- **2% daily loss limit**

### Risk Parameters
- **Position sizing**: 1-3% of account balance per trade
- **Stop loss**: 10-50 pips (ATR-based)
- **Trailing stop**: 15 pips
- **Maximum trade duration**: 4 hours
- **Cooldown**: 6 seconds between trades

## 🔧 Configuration

### Risk Management Settings
```python
# In position_sizer.py
min_risk = 0.01      # 1% minimum risk per trade
max_risk = 0.03      # 3% maximum risk per trade
max_drawdown = 0.10  # 10% maximum drawdown
max_daily_loss = 0.02  # 2% daily loss limit
```

### Trading Parameters
```python
# In trading_bot.py
scan_interval = 7     # seconds between market scans
max_trades_per_scan = 2  # maximum trades per scan cycle
```

### Exit Parameters
```python
# In trade_closer.py
trailing_stop_pips = 15.0    # trailing stop distance
min_profit_threshold = 3.0   # minimum profit in pips
max_trade_duration = 4       # hours
max_loss_pips = 30.0         # maximum loss in pips
```

## 📁 File Structure

```
ai-forex-trading-bot/
├── bot_runner.py          # Main entry point
├── trading_bot.py         # Core trading logic
├── oanda_client.py        # OANDA API client
├── instrument_selector.py # Market analysis & selection
├── position_sizer.py      # Risk management & sizing
├── trade_executor.py      # Trade execution logic
├── trade_closer.py        # Trade monitoring & closure
├── telegram_bot.py        # Telegram integration
├── requirements.txt       # Python dependencies
├── trade_state.json       # Persistent state storage
├── trading_bot.log        # Application logs
└── README.md             # This file
```

## 🛡️ Safety Features

### Risk Controls
- **Automatic trading halt** when drawdown exceeds 10%
- **Daily loss limits** with automatic stop
- **Consecutive loss protection**
- **Margin validation** before each trade
- **Position size limits** based on account balance

### Error Handling
- **Comprehensive exception handling** throughout
- **API rate limiting** and retry logic
- **Graceful degradation** on API failures
- **State persistence** for crash recovery
- **Detailed logging** for debugging

### Monitoring
- **Real-time status monitoring** via Telegram
- **Performance tracking** per instrument
- **Risk metrics** tracking and alerts
- **System diagnostics** on demand

## 🚨 Important Notes

### Demo Account Only
This bot is designed for **OANDA demo accounts only**. Never use with live accounts without extensive testing.

### Risk Disclaimer
- Forex trading involves substantial risk
- Past performance does not guarantee future results
- Always test thoroughly before live deployment
- Monitor the bot continuously during operation

### Environment Setup
- Ensure stable internet connection
- Use dedicated server/VPS for 24/7 operation
- Set up proper logging and monitoring
- Regular backup of trade state files

## 🔍 Troubleshooting

### Common Issues

1. **API Connection Errors**
   - Verify OANDA API credentials
   - Check internet connectivity
   - Ensure account is active

2. **Telegram Bot Not Responding**
   - Verify bot token and chat ID
   - Check bot permissions
   - Restart the application

3. **No Trades Executing**
   - Check risk management settings
   - Verify account balance
   - Review confidence thresholds

4. **Performance Issues**
   - Monitor system resources
   - Check API rate limits
   - Review log files for errors

### Log Files
- **trading_bot.log**: Main application logs
- **trade_state.json**: Persistent state data
- Check logs for detailed error information

## 📞 Support

For issues and questions:
1. Check the log files for error details
2. Review the troubleshooting section
3. Verify all environment variables are set
4. Test with small position sizes first

## 📄 License

This project is for educational and research purposes. Use at your own risk.

---

**⚠️ Warning**: This is a sophisticated trading system. Always test thoroughly in demo environments before any live deployment. The authors are not responsible for any financial losses.