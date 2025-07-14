import asyncio
import json
import os
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import numpy as np

from oanda_client import OandaClient

logger = logging.getLogger("position_sizer")

STATE_FILE = "trade_state.json"

class PositionSizer:
    def __init__(self, oanda_client: OandaClient, 
                 min_risk=0.01, max_risk=0.03, max_open_trades=100,
                 max_drawdown=0.10, max_daily_loss=0.02):
        self.oanda_client = oanda_client
        self.min_risk = min_risk  # 1% minimum risk per trade
        self.max_risk = max_risk  # 3% maximum risk per trade
        self.max_open_trades = max_open_trades
        self.max_drawdown = max_drawdown  # 10% max drawdown
        self.max_daily_loss = max_daily_loss  # 2% max daily loss
        self.trade_cooldown_minutes = 0.1  # 6 seconds cooldown
        self.min_confidence = 0.5
        
        # Enhanced state management
        self.trade_state = {
            "last_trade_time": {},
            "open_trades": 0,
            "daily_stats": {
                "date": datetime.now().date().isoformat(),
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "pnl": 0.0,
                "max_loss": 0.0
            },
            "peak_equity": 0.0,
            "performance": defaultdict(lambda: {
                "wins": 0, 
                "losses": 0, 
                "confidence": 0.7,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "total_trades": 0
            }),
            "risk_metrics": {
                "current_drawdown": 0.0,
                "daily_loss": 0.0,
                "consecutive_losses": 0,
                "max_consecutive_losses": 0
            }
        }
        self._load_state()

    def _load_state(self):
        """Load trade state from file"""
        if os.path.isfile(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as f:
                    data = json.load(f)
                    self.trade_state.update(data)
                    
                    # Convert string dates back to datetime objects
                    for inst, t_str in self.trade_state["last_trade_time"].items():
                        if isinstance(t_str, str):
                            self.trade_state["last_trade_time"][inst] = datetime.fromisoformat(t_str)
                    
                    # Reset daily stats if it's a new day
                    if self.trade_state["daily_stats"]["date"] != datetime.now().date().isoformat():
                        self._reset_daily_stats()
                    
                    logger.info("Trade state loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load trade state: {e}")

    def _save_state(self):
        """Save trade state to file"""
        try:
            data = self.trade_state.copy()
            data["last_trade_time"] = {
                k: v.isoformat() if isinstance(v, datetime) else v
                for k, v in self.trade_state["last_trade_time"].items()
            }
            with open(STATE_FILE, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug("Trade state saved")
        except Exception as e:
                logger.warning(f"Failed to save trade state: {e}")

    def _reset_daily_stats(self):
        """Reset daily statistics for new trading day"""
        self.trade_state["daily_stats"] = {
            "date": datetime.now().date().isoformat(),
            "trades": 0,
            "wins": 0,
            "losses": 0,
            "pnl": 0.0,
            "max_loss": 0.0
        }
        self.trade_state["risk_metrics"]["daily_loss"] = 0.0
        self._save_state()

    async def update_equity_and_drawdown(self):
        """Update equity and calculate current drawdown"""
        equity = await self.oanda_client.get_equity()
        if equity is None:
            return
        
        # Update peak equity if current equity is higher
        if equity > self.trade_state["peak_equity"]:
            self.trade_state["peak_equity"] = equity
        
        # Calculate drawdown
        if self.trade_state["peak_equity"] > 0:
            drawdown = (self.trade_state["peak_equity"] - equity) / self.trade_state["peak_equity"]
            self.trade_state["risk_metrics"]["current_drawdown"] = drawdown
        
        self._save_state()

    def update_performance(self, instrument: str, won: bool, pnl: float):
        """Update performance metrics for an instrument"""
        perf = self.trade_state["performance"][instrument]
        perf["total_trades"] += 1
        
        if won:
            perf["wins"] += 1
            perf["avg_win"] = (perf["avg_win"] * (perf["wins"] - 1) + pnl) / perf["wins"]
            perf["confidence"] = min(1.0, perf["confidence"] + 0.05)
            self.trade_state["risk_metrics"]["consecutive_losses"] = 0
        else:
            perf["losses"] += 1
            perf["avg_loss"] = (perf["avg_loss"] * (perf["losses"] - 1) + abs(pnl)) / perf["losses"]
            perf["confidence"] = max(0.1, perf["confidence"] - 0.1)
            self.trade_state["risk_metrics"]["consecutive_losses"] += 1
        
        # Update max consecutive losses
        self.trade_state["risk_metrics"]["max_consecutive_losses"] = max(
            self.trade_state["risk_metrics"]["max_consecutive_losses"],
            self.trade_state["risk_metrics"]["consecutive_losses"]
        )
        
        # Update daily stats
        self.trade_state["daily_stats"]["trades"] += 1
        self.trade_state["daily_stats"]["pnl"] += pnl
        
        if won:
            self.trade_state["daily_stats"]["wins"] += 1
        else:
            self.trade_state["daily_stats"]["losses"] += 1
            self.trade_state["daily_stats"]["max_loss"] = min(
                self.trade_state["daily_stats"]["max_loss"], pnl
            )
        
        self._save_state()

    def get_confidence(self, instrument: str) -> float:
        """Get confidence score for an instrument"""
        return self.trade_state["performance"].get(instrument, {}).get("confidence", 0.5)

    def can_trade(self, instrument: str) -> Tuple[bool, str]:
        """Check if we can trade an instrument with reason"""
        # Check cooldown
        last_time = self.trade_state["last_trade_time"].get(instrument)
        if last_time and datetime.utcnow() - last_time < timedelta(minutes=self.trade_cooldown_minutes):
            return False, f"Cooldown active for {instrument}"
        
        # Check max open trades
        if self.trade_state["open_trades"] >= self.max_open_trades:
            return False, f"Max open trades reached ({self.max_open_trades})"
        
        # Check drawdown
        if self.trade_state["risk_metrics"]["current_drawdown"] > self.max_drawdown:
            return False, f"Max drawdown exceeded ({self.trade_state['risk_metrics']['current_drawdown']:.2%})"
        
        # Check daily loss limit
        if self.trade_state["daily_stats"]["max_loss"] < -self.max_daily_loss:
            return False, f"Daily loss limit exceeded ({self.trade_state['daily_stats']['max_loss']:.2%})"
        
        # Check consecutive losses
        if self.trade_state["risk_metrics"]["consecutive_losses"] >= 5:
            return False, f"Too many consecutive losses ({self.trade_state['risk_metrics']['consecutive_losses']})"
        
        return True, "OK"

    def record_trade(self, instrument: str):
        """Record a new trade"""
        self.trade_state["last_trade_time"][instrument] = datetime.utcnow()
        self.trade_state["open_trades"] += 1
        self._save_state()

    def close_trade(self, instrument: str):
        """Record trade closure"""
        self.trade_state["open_trades"] = max(0, self.trade_state["open_trades"] - 1)
        self._save_state()

    async def calculate_units(self, instrument: str, stop_loss_pips: float, confidence_boost: float = 0.0) -> int:
        """Calculate position size with advanced risk management"""
        # Update equity and drawdown
        await self.update_equity_and_drawdown()
        
        # Check if we can trade
        can_trade, reason = self.can_trade(instrument)
        if not can_trade:
            logger.info(f"Cannot trade {instrument}: {reason}")
            return 0

        # Get account balance
        balance = await self.oanda_client.get_account_balance()
        if balance is None:
            logger.error("No account balance, cannot calculate units")
            return 0

        # Get confidence score
        base_confidence = self.get_confidence(instrument)
        adjusted_confidence = min(1.0, base_confidence + confidence_boost)
        
        if adjusted_confidence < self.min_confidence:
            logger.info(f"Confidence {adjusted_confidence:.2f} below threshold {self.min_confidence}")
            return 0

        # Calculate risk percentage based on confidence
        risk_percentage = self.min_risk + (self.max_risk - self.min_risk) * adjusted_confidence
        risk_percentage = min(max(risk_percentage, self.min_risk), self.max_risk)

        # Adjust for market conditions
        volatility_adjustment = self._calculate_volatility_adjustment(instrument, adjusted_confidence)
        adjusted_stop_loss = stop_loss_pips * volatility_adjustment

        # Calculate pip value
        pip_value = 0.01 if instrument.endswith("JPY") else 0.0001

        # Calculate risk amount
        risk_amount = balance * risk_percentage

        # Check margin availability
        margin_available = await self.oanda_client.get_margin_available()
        if margin_available is None:
            logger.error("No margin info available, skipping trade")
            return 0

        # Calculate units based on risk
        units_by_risk = int(risk_amount / (adjusted_stop_loss * pip_value))

        # Get current price for margin calculation
        price = await self.oanda_client.get_price(instrument)
        if price is None:
            logger.error(f"Price for {instrument} unavailable, skipping trade")
            return 0

        # Calculate maximum units based on margin
        max_units_margin = int(margin_available / price * 0.8)  # 80% of available margin

        # Take the minimum of risk-based and margin-based units
        units = min(units_by_risk, max_units_margin)

        # Apply Kelly Criterion adjustment
        kelly_adjustment = self._calculate_kelly_adjustment(instrument)
        units = int(units * kelly_adjustment)

        if units < 1:
            logger.warning(f"Units calculated less than 1 ({units}), no trade placed")
            return 0

        logger.info(
            f"PositionSizer: {instrument} units={units} | conf={adjusted_confidence:.2f} | "
            f"risk={risk_percentage:.3f} | SL={adjusted_stop_loss:.1f} | Kelly={kelly_adjustment:.2f}"
        )
        return units

    def _calculate_volatility_adjustment(self, instrument: str, confidence: float) -> float:
        """Calculate volatility adjustment factor"""
        # Higher confidence = lower volatility adjustment
        base_adjustment = 1.5 if confidence < 0.6 else 1.0
        
        # Adjust based on consecutive losses
        consecutive_losses = self.trade_state["risk_metrics"]["consecutive_losses"]
        if consecutive_losses > 0:
            base_adjustment *= (1 + consecutive_losses * 0.1)
        
        return min(base_adjustment, 2.5)  # Cap at 2.5x

    def _calculate_kelly_adjustment(self, instrument: str) -> float:
        """Calculate Kelly Criterion adjustment"""
        perf = self.trade_state["performance"][instrument]
        
        if perf["total_trades"] < 10:
            return 0.5  # Conservative for new instruments
        
        win_rate = perf["wins"] / perf["total_trades"] if perf["total_trades"] > 0 else 0.5
        avg_win = perf["avg_win"] if perf["avg_win"] > 0 else 1.0
        avg_loss = perf["avg_loss"] if perf["avg_loss"] > 0 else 1.0
        
        # Kelly formula: f = (bp - q) / b
        # where b = odds received, p = probability of win, q = probability of loss
        b = avg_win / avg_loss
        p = win_rate
        q = 1 - p
        
        kelly_fraction = (b * p - q) / b if b > 0 else 0
        
        # Apply conservative Kelly (half Kelly)
        conservative_kelly = max(0, min(kelly_fraction * 0.5, 0.25))
        
        return conservative_kelly if conservative_kelly > 0 else 0.1

    def get_risk_summary(self) -> Dict:
        """Get comprehensive risk summary"""
        return {
            "current_drawdown": self.trade_state["risk_metrics"]["current_drawdown"],
            "daily_loss": self.trade_state["daily_stats"]["max_loss"],
            "consecutive_losses": self.trade_state["risk_metrics"]["consecutive_losses"],
            "open_trades": self.trade_state["open_trades"],
            "peak_equity": self.trade_state["peak_equity"],
            "daily_stats": self.trade_state["daily_stats"],
            "can_trade": self.trade_state["risk_metrics"]["current_drawdown"] <= self.max_drawdown
        }

    def get_performance_summary(self) -> Dict:
        """Get performance summary for all instruments"""
        summary = {}
        for instrument, perf in self.trade_state["performance"].items():
            if perf["total_trades"] > 0:
                win_rate = perf["wins"] / perf["total_trades"]
                summary[instrument] = {
                    "total_trades": perf["total_trades"],
                    "wins": perf["wins"],
                    "losses": perf["losses"],
                    "win_rate": win_rate,
                    "confidence": perf["confidence"],
                    "avg_win": perf["avg_win"],
                    "avg_loss": perf["avg_loss"]
                }
        return summary