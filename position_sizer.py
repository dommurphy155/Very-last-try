import asyncio
import json
import os
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from oanda_client import OandaClient

logger = logging.getLogger("position_sizer")

# File to persist cooldowns and trade performance
STATE_FILE = "trade_state.json"

class PositionSizer:
    def __init__(self, oanda_client: OandaClient, risk_per_trade=0.01, max_open_trades=100):
        self.oanda_client = oanda_client
        self.risk_per_trade = risk_per_trade  # max % of balance per trade
        self.max_open_trades = max_open_trades
        self.trade_cooldown_minutes = 0.1  # cooldown per instrument in minutes
        self.min_confidence = 0.5  # minimum confidence to trade
        self.trade_state = {
            "last_trade_time": {},  # instrument -> datetime ISO string
            "open_trades": 0,
            "performance": defaultdict(lambda: {"wins": 0, "losses": 0, "confidence": 0.7}),
        }
        self._load_state()

    def _load_state(self):
        if os.path.isfile(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    data = json.load(f)
                    self.trade_state.update(data)
                    # convert times back to datetime
                    for inst, t_str in self.trade_state["last_trade_time"].items():
                        self.trade_state["last_trade_time"][inst] = datetime.fromisoformat(t_str)
                    logger.info("Trade state loaded")
            except Exception as e:
                logger.warning(f"Failed to load trade state: {e}")

    def _save_state(self):
        try:
            data = self.trade_state.copy()
            # convert datetime to string for JSON
            data["last_trade_time"] = {k: v.isoformat() if isinstance(v, datetime) else v
                                       for k, v in self.trade_state["last_trade_time"].items()}
            with open(STATE_FILE, "w") as f:
                json.dump(data, f)
            logger.debug("Trade state saved")
        except Exception as e:
            logger.warning(f"Failed to save trade state: {e}")

    def update_performance(self, instrument: str, won: bool):
        perf = self.trade_state["performance"][instrument]
        if won:
            perf["wins"] += 1
            perf["confidence"] = min(1.0, perf["confidence"] + 0.05)  # increase confidence on win
        else:
            perf["losses"] += 1
            perf["confidence"] = max(0.1, perf["confidence"] - 0.1)  # decrease confidence on loss
        self._save_state()

    def get_confidence(self, instrument: str):
        return self.trade_state["performance"].get(instrument, {}).get("confidence", 0.5)

    def can_trade(self, instrument: str):
        # Check cooldown
        last_time = self.trade_state["last_trade_time"].get(instrument)
        if last_time and datetime.utcnow() - last_time < timedelta(minutes=self.trade_cooldown_minutes):
            logger.info(f"Cooldown active for {instrument}, skipping trade")
            return False
        # Check max open trades
        if self.trade_state["open_trades"] >= self.max_open_trades:
            logger.info(f"Max open trades reached ({self.max_open_trades}), skipping trade")
            return False
        return True

    def record_trade(self, instrument: str):
        self.trade_state["last_trade_time"][instrument] = datetime.utcnow()
        self.trade_state["open_trades"] += 1
        self._save_state()

    def close_trade(self, instrument: str):
        # Call when trade closes to free slot
        self.trade_state["open_trades"] = max(0, self.trade_state["open_trades"] - 1)
        self._save_state()

    async def calculate_units(self, instrument: str, stop_loss_pips: float):
        balance = await self.oanda_client.get_account_balance()
        if balance is None:
            logger.error("Cannot calculate units without balance")
            return 0

        if not self.can_trade(instrument):
            return 0

        confidence = self.get_confidence(instrument)
        if confidence < self.min_confidence:
            logger.info(f"Confidence {confidence:.2f} below threshold {self.min_confidence}, skipping trade")
            return 0

        # Adjust risk per trade by confidence but cap at 5%
        adjusted_risk = min(self.risk_per_trade * (confidence * 2), 0.05)  # cap max 5%
        
        # Basic volatility adjustment: widen stop loss by 50% if confidence < 0.6
        volatility_adjustment = 1.5 if confidence < 0.6 else 1.0
        adjusted_stop_loss = stop_loss_pips * volatility_adjustment

        pip_value = 0.0001

        risk_amount = balance * adjusted_risk

        units = int(risk_amount / (adjusted_stop_loss * pip_value))

        if units < 1:
            logger.warning(f"Calculated units too low ({units}), setting to minimum 1")
            units = 1

        logger.info(
            f"Calculated units for {instrument}: {units} | "
            f"Confidence: {confidence:.2f} | Adjusted risk: {adjusted_risk:.4f} | Adjusted SL: {adjusted_stop_loss}"
        )
        return units