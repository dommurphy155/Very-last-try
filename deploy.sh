#!/bin/bash
set -e

echo "Starting deployment..."

# Update and install python3-venv if missing
sudo apt update
sudo apt install -y python3-venv

# Create venv if missing
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Prompt for env vars
read -p "Enter your OANDA_API_KEY: " OANDA_API_KEY
read -p "Enter your OANDA_ACCOUNT_ID: " OANDA_ACCOUNT_ID
read -p "Enter your TELEGRAM_BOT_TOKEN: " TELEGRAM_BOT_TOKEN
read -p "Enter your TELEGRAM_CHAT_ID: " TELEGRAM_CHAT_ID

# Export environment variables for current session
export OANDA_API_KEY=$OANDA_API_KEY
export OANDA_ACCOUNT_ID=$OANDA_ACCOUNT_ID
export TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
export TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID

# Cleanup old processes and files
pkill -f bot_runner.py || true
rm -f bot_state.json bot_state.json.tmp trading_log.json trading_log.json.tmp nohup.out || true

echo "Deployment complete. Starting bot..."

# Start bot_runner.py with environment
python3 bot_runner.py