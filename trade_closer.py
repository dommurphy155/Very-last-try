# trade_closer.py

import logging
import re
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from oanda_client import OandaClient
from position_sizer import PositionSizer

logger = logging.getLogger("trade_closer")

def parse_oanda_time(time_str: str) -> datetime:
    """Clean and parse extended-precision OANDA timestamps safely."""
    try:
        time_str = time_str.replace("Z", "+00:00")
        pattern = r'(\.\d{6})\d*'
        fixed_str = re.sub(pattern, r'\1', time_str)
        return datetime.fromisoformat(fixed_str)
    except Exception as e:
        logger.error(f"Error parsing time {time_str}: {e}")
        return datetime.utcnow()

class TradeCloser:
    def __init__(self, oanda_client: OandaClient, position_sizer: PositionSizer):
        self.oanda = oanda_client
        self.position_sizer = position_sizer
        
        # Exit parameters
        self.trailing_stop_pips = 15.0
        self.min_profit_threshold = 3.0  # in pips
        self.max_trade_duration = timedelta(hours=4)
        self.min_risk_reward = 1.2
        self.max_loss_pips = 30.0
        
        # Trailing stop tracking
        self.trailing_stops = {}  # {trade_id: {'entry_price': float, 'highest_price': float, 'lowest_price': float}}
        
        # Performance tracking
        self.closed_trades = []
        self.daily_stats = {
            'trades_closed': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'max_profit': 0.0,
            'max_loss': 0.0
        }

    async def monitor_trades(self) -> Dict:
        """Monitor all open trades and close them if conditions are met"""
        results = {
            'trades_checked': 0,
            'trades_closed': 0,
            'trades_updated': 0,
            'errors': []
        }
        
        try:
            open_trades = await self.oanda.get_open_trades()
            results['trades_checked'] = len(open_trades)
            
            for trade in open_trades:
                try:
                    trade_result = await self._evaluate_trade(trade)
                    
                    if trade_result['action'] == 'close':
                        results['trades_closed'] += 1
                        logger.info(f"Trade {trade['id']} closed: {trade_result['reason']}")
                    elif trade_result['action'] == 'update':
                        results['trades_updated'] += 1
                        
                except Exception as e:
                    error_msg = f"Error evaluating trade {trade.get('id', 'unknown')}: {e}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
                    continue
                    
        except Exception as e:
            error_msg = f"Error in monitor_trades: {e}"
            results['errors'].append(error_msg)
            logger.error(error_msg)
        
        return results

    async def _evaluate_trade(self, trade: Dict) -> Dict:
        """Evaluate a single trade for closure or updates"""
        trade_id = trade["id"]
        instrument = trade["instrument"]
        current_price = await self.oanda.get_price(instrument)
        
        if current_price is None:
            return {'action': 'none', 'reason': 'Unable to get current price'}
        
        # Parse trade data
        entry_price = float(trade["price"])
        units = int(trade["currentUnits"])
        is_short = units < 0
        unrealized_pl = float(trade.get("unrealizedPL", 0))
        initial_margin = float(trade.get("initialMarginRequired", 1))
        
        # Parse open time
        open_time = parse_oanda_time(trade["openTime"])
        duration = datetime.utcnow().replace(tzinfo=open_time.tzinfo) - open_time
        
        # Initialize trailing stop if not exists
        if trade_id not in self.trailing_stops:
            self.trailing_stops[trade_id] = {
                'entry_price': entry_price,
                'highest_price': entry_price,
                'lowest_price': entry_price
            }
        
        # Update trailing stop
        self._update_trailing_stop(trade_id, current_price, is_short)
        
        # Check exit conditions
        exit_result = await self._check_exit_conditions(
            trade_id, instrument, current_price, entry_price, 
            unrealized_pl, initial_margin, duration, is_short
        )
        
        if exit_result['should_exit']:
            success = await self._close_trade(trade_id, instrument, exit_result['reason'])
            if success:
                # Update performance tracking
                self._update_performance_tracking(trade_id, unrealized_pl, duration)
                return {'action': 'close', 'reason': exit_result['reason']}
            else:
                return {'action': 'none', 'reason': 'Failed to close trade'}
        
        return {'action': 'update', 'reason': 'Trade monitored'}

    def _update_trailing_stop(self, trade_id: str, current_price: float, is_short: bool):
        """Update trailing stop levels"""
        if trade_id not in self.trailing_stops:
            return
        
        ts = self.trailing_stops[trade_id]
        
        if is_short:
            # For short trades, track lowest price
            if current_price < ts['lowest_price']:
                ts['lowest_price'] = current_price
        else:
            # For long trades, track highest price
            if current_price > ts['highest_price']:
                ts['highest_price'] = current_price

    async def _check_exit_conditions(self, trade_id: str, instrument: str, current_price: float,
                                   entry_price: float, unrealized_pl: float, initial_margin: float,
                                   duration: timedelta, is_short: bool) -> Dict:
        """Check all exit conditions for a trade"""
        
        # 1. Time-based exit
        if duration > self.max_trade_duration:
            return {'should_exit': True, 'reason': f'Max duration exceeded ({duration})'}
        
        # 2. Profit target reached
        pip_size = 0.01 if instrument.endswith("JPY") else 0.0001
        profit_pips = abs(current_price - entry_price) / pip_size
        
        if profit_pips >= self.min_profit_threshold:
            # Check risk/reward ratio
            rr_ratio = unrealized_pl / initial_margin if initial_margin > 0 else 0
            if rr_ratio >= self.min_risk_reward:
                return {'should_exit': True, 'reason': f'Profit target reached ({profit_pips:.1f} pips, RR: {rr_ratio:.2f})'}
        
        # 3. Trailing stop hit
        if trade_id in self.trailing_stops:
            ts = self.trailing_stops[trade_id]
            trailing_distance = self.trailing_stop_pips * pip_size
            
            if is_short:
                # For short trades, exit if price rises above trailing stop
                trailing_stop_price = ts['lowest_price'] + trailing_distance
                if current_price >= trailing_stop_price:
                    return {'should_exit': True, 'reason': f'Trailing stop hit (short) at {current_price:.5f}'}
            else:
                # For long trades, exit if price falls below trailing stop
                trailing_stop_price = ts['highest_price'] - trailing_distance
                if current_price <= trailing_stop_price:
                    return {'should_exit': True, 'reason': f'Trailing stop hit (long) at {current_price:.5f}'}
        
        # 4. Maximum loss exceeded
        loss_pips = abs(current_price - entry_price) / pip_size
        if loss_pips >= self.max_loss_pips:
            return {'should_exit': True, 'reason': f'Max loss exceeded ({loss_pips:.1f} pips)'}
        
        # 5. Momentum reversal (additional exit condition)
        if await self._check_momentum_reversal(instrument, current_price, is_short):
            return {'should_exit': True, 'reason': 'Momentum reversal detected'}
        
        return {'should_exit': False, 'reason': 'No exit conditions met'}

    async def _check_momentum_reversal(self, instrument: str, current_price: float, is_short: bool) -> bool:
        """Check for momentum reversal using recent price action"""
        try:
            # Get recent candles for momentum analysis
            candles = await self.oanda.get_candles(instrument, count=10, granularity="M1")
            if len(candles) < 5:
                return False
            
            # Calculate simple momentum
            recent_prices = [float(candle['mid']['c']) for candle in candles[-5:]]
            price_change = (recent_prices[-1] - recent_prices[0]) / recent_prices[0]
            
            # Check for reversal
            if is_short and price_change > 0.001:  # Price rising for short position
                return True
            elif not is_short and price_change < -0.001:  # Price falling for long position
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking momentum reversal: {e}")
            return False

    async def _close_trade(self, trade_id: str, instrument: str, reason: str) -> bool:
        """Close a specific trade"""
        try:
            success, response = await self.oanda.close_trade(trade_id)
            if success:
                self.position_sizer.close_trade(instrument)
                
                # Clean up trailing stop tracking
                if trade_id in self.trailing_stops:
                    del self.trailing_stops[trade_id]
                
                logger.info(f"Trade {trade_id} closed successfully: {reason}")
                return True
            else:
                logger.error(f"Failed to close trade {trade_id}: {response}")
                return False
                
        except Exception as e:
            logger.error(f"Error closing trade {trade_id}: {e}")
            return False

    def _update_performance_tracking(self, trade_id: str, pnl: float, duration: timedelta):
        """Update performance tracking for closed trade"""
        trade_record = {
            'trade_id': trade_id,
            'pnl': pnl,
            'duration_minutes': duration.total_seconds() / 60,
            'closed_at': datetime.utcnow().isoformat(),
            'won': pnl > 0
        }
        
        self.closed_trades.append(trade_record)
        
        # Update daily stats
        self.daily_stats['trades_closed'] += 1
        self.daily_stats['total_pnl'] += pnl
        
        if pnl > 0:
            self.daily_stats['wins'] += 1
            self.daily_stats['max_profit'] = max(self.daily_stats['max_profit'], pnl)
        else:
            self.daily_stats['losses'] += 1
            self.daily_stats['max_loss'] = min(self.daily_stats['max_loss'], pnl)
        
        # Update position sizer performance
        # Note: We need to determine the instrument from the trade record
        # This is a simplified version - in practice, you'd store more trade details
        logger.info(f"Trade performance recorded: PnL={pnl:.2f}, Duration={duration}")

    async def get_closed_trades_summary(self) -> Dict:
        """Get summary of closed trades"""
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'avg_pnl': 0.0,
                'total_pnl': 0.0,
                'avg_duration': 0.0
            }
        
        total_trades = len(self.closed_trades)
        wins = sum(1 for trade in self.closed_trades if trade['won'])
        total_pnl = sum(trade['pnl'] for trade in self.closed_trades)
        avg_duration = sum(trade['duration_minutes'] for trade in self.closed_trades) / total_trades
        
        return {
            'total_trades': total_trades,
            'win_rate': wins / total_trades if total_trades > 0 else 0.0,
            'avg_pnl': total_pnl / total_trades if total_trades > 0 else 0.0,
            'total_pnl': total_pnl,
            'avg_duration': avg_duration,
            'daily_stats': self.daily_stats
        }

    async def force_close_all_trades(self, reason: str = "Manual close") -> Dict:
        """Force close all open trades"""
        results = {
            'trades_closed': 0,
            'errors': []
        }
        
        try:
            open_trades = await self.oanda.get_open_trades()
            
            for trade in open_trades:
                try:
                    success = await self._close_trade(trade['id'], trade['instrument'], reason)
                    if success:
                        results['trades_closed'] += 1
                    else:
                        results['errors'].append(f"Failed to close trade {trade['id']}")
                except Exception as e:
                    results['errors'].append(f"Error closing trade {trade['id']}: {e}")
            
            # Clear trailing stops
            self.trailing_stops.clear()
            
        except Exception as e:
            results['errors'].append(f"Error in force_close_all_trades: {e}")
        
        return results

    def get_trailing_stops_status(self) -> Dict:
        """Get current status of all trailing stops"""
        return {
            'active_trailing_stops': len(self.trailing_stops),
            'trailing_stops': self.trailing_stops.copy()
        }

    def reset_daily_stats(self):
        """Reset daily statistics"""
        self.daily_stats = {
            'trades_closed': 0,
            'wins': 0,
            'losses': 0,
            'total_pnl': 0.0,
            'max_profit': 0.0,
            'max_loss': 0.0
        }
        logger.info("Daily stats reset")