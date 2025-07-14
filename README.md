# AI Forex Trading Bot (OANDA Demo + Telegram)

A production-ready, async Python bot for automated Forex trading on an OANDA demo account, with Telegram notifications and command control.

## Features
- Async trading loop with OANDA v3 REST API (demo mode)
- Telegram bot for notifications and commands
- Simple technical analysis (dummy buy signal for demo)
- State and log persistence
- Ubuntu 20.04 + Python 3.8.10 tested

## Requirements
- Ubuntu 20.04+
- Python 3.8.10+
- OANDA demo account (API key + account ID)
- Telegram bot token and chat ID

## Setup

1. **Clone the repo:**
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. **Run the deploy script:**
   ```bash
   bash deploy.sh
   ```
   - This will prompt for your OANDA and Telegram credentials, set up a Python virtual environment, install dependencies, and start the bot.

## Environment Variables
- `OANDA_API_KEY`: Your OANDA v3 API key (demo)
- `OANDA_ACCOUNT_ID`: Your OANDA demo account ID
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `TELEGRAM_CHAT_ID`: Your Telegram chat ID (for notifications)

These are prompted interactively by `deploy.sh` and set for the session.

## Usage
- The bot runs continuously, trading every 20 seconds (demo mode, only logs trades).
- Use Telegram commands:
  - `/start` — Welcome message
  - `/status` — Bot status
  - `/maketrade` — Force a trade
  - `/canceltrade` — Cancel all open trades
  - `/showlog` — (Not implemented)
  - `/pnl` — Show current PnL
  - `/openpositions` — List open trades
  - `/strategystats` — (Not implemented)

## Security
- **Never share your API keys or tokens.**
- This bot is for demo and educational use only. Real trading requires additional risk management and security.

## Customization
- Edit `technical_analysis.py` to implement your own trading logic.
- Extend `trading_bot.py` for more advanced state/log handling.

## License
MIT