import logging
import asyncio
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from oanda_client import OandaClient
from position_sizer import PositionSizer
from instrument_selector import InstrumentSelector

logger = logging.getLogger("trade_executor")

class TradeExecutor:
    def __init__(self, oanda_client: OandaClient, position_sizer: PositionSizer, instrument_selector: InstrumentSelector):
        self.oanda_client = oanda_client
        self.position_sizer = position_sizer
        self.instrument_selector = instrument_selector
        self.min_stop_loss_pips = 10.0
        self.max_stop_loss_pips = 50.0
        self.trailing_stop_pips = 15.0
        self.min_profit_pips = 5.0
        self.max_trade_duration = timedelta(hours=4)

    async def execute_trade(self, instrument: str, units: int, stop_loss_pips: float = None) -> Tuple[bool, Dict]:
        """Execute a trade with comprehensive analysis and risk management"""
        if units <= 0:
            logger.error("Units <= 0, abort trade")
            return False, {"error": "Invalid units"}

        try:
            # Get current price for analysis
            current_price = await self.oanda_client.get_price(instrument)
            if current_price is None:
                return False, {"error": "Unable to get current price"}

            # Calculate optimal stop loss if not provided
            if stop_loss_pips is None:
                stop_loss_pips = await self._calculate_optimal_stop_loss(instrument, current_price)

            # Validate stop loss
            if not self._validate_stop_loss(stop_loss_pips):
                return False, {"error": "Invalid stop loss"}

            # Execute the trade
            success, response = await self.oanda_client.create_trade(instrument, units, stop_loss_pips)
            
            if not success:
                logger.error(f"Trade failed for {instrument}: {response}")
                return False, response

            # Record the trade
            self.position_sizer.record_trade(instrument)
            
            # Extract trade details
            trade_info = self._extract_trade_info(response, instrument, units, current_price, stop_loss_pips)
            
            logger.info(f"Trade executed successfully: {trade_info}")
            return True, trade_info

        except Exception as e:
            logger.error(f"Error executing trade for {instrument}: {e}")
            return False, {"error": str(e)}

    async def _calculate_optimal_stop_loss(self, instrument: str, current_price: float) -> float:
        """Calculate optimal stop loss based on volatility and market conditions"""
        try:
            # Get recent candles for volatility analysis
            candles = await self.oanda_client.get_candles(instrument, count=50, granularity="M5")
            if len(candles) < 20:
                return self.min_stop_loss_pips

            # Calculate ATR (Average True Range)
            atr = self._calculate_atr_from_candles(candles)
            
            # Convert ATR to pips
            pip_size = 0.01 if instrument.endswith("JPY") else 0.0001
            atr_pips = atr / pip_size
            
            # Use ATR-based stop loss with bounds
            optimal_sl = max(self.min_stop_loss_pips, min(atr_pips * 1.5, self.max_stop_loss_pips))
            
            return optimal_sl

        except Exception as e:
            logger.warning(f"Error calculating optimal stop loss: {e}")
            return self.min_stop_loss_pips

    def _calculate_atr_from_candles(self, candles: list, period: int = 14) -> float:
        """Calculate ATR from candle data"""
        if len(candles) < period + 1:
            return 0.001  # Default small value
        
        true_ranges = []
        for i in range(1, len(candles)):
            high = float(candles[i]['mid']['h'])
            low = float(candles[i]['mid']['l'])
            prev_close = float(candles[i-1]['mid']['c'])
            
            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)
            true_ranges.append(max(tr1, tr2, tr3))
        
        # Calculate average
        return sum(true_ranges[-period:]) / period

    def _validate_stop_loss(self, stop_loss_pips: float) -> bool:
        """Validate stop loss is within acceptable range"""
        return self.min_stop_loss_pips <= stop_loss_pips <= self.max_stop_loss_pips

    def _extract_trade_info(self, response: Dict, instrument: str, units: int, 
                           entry_price: float, stop_loss_pips: float) -> Dict:
        """Extract and format trade information from API response"""
        try:
            order = response.get('orderFillTransaction', {})
            
            trade_info = {
                'instrument': instrument,
                'units': units,
                'entry_price': entry_price,
                'stop_loss_pips': stop_loss_pips,
                'trade_id': order.get('id'),
                'time': order.get('time'),
                'pl': order.get('pl', 0),
                'commission': order.get('commission', 0),
                'financing': order.get('financing', 0),
                'expected_roi': self._calculate_expected_roi(entry_price, stop_loss_pips, units),
                'risk_reward_ratio': self._calculate_risk_reward_ratio(entry_price, stop_loss_pips)
            }
            
            return trade_info
            
        except Exception as e:
            logger.error(f"Error extracting trade info: {e}")
            return {
                'instrument': instrument,
                'units': units,
                'entry_price': entry_price,
                'stop_loss_pips': stop_loss_pips,
                'error': 'Failed to extract full trade info'
            }

    def _calculate_expected_roi(self, entry_price: float, stop_loss_pips: float, units: int) -> float:
        """Calculate expected ROI based on stop loss"""
        pip_size = 0.01 if entry_price < 100 else 0.0001  # Rough JPY detection
        risk_amount = stop_loss_pips * pip_size * units
        position_value = entry_price * units
        
        if position_value > 0:
            return risk_amount / position_value
        return 0.0

    def _calculate_risk_reward_ratio(self, entry_price: float, stop_loss_pips: float) -> float:
        """Calculate risk/reward ratio"""
        # Assuming 1:1 risk/reward for now, can be enhanced with take profit
        return 1.0

    async def analyze_and_execute_trades(self) -> Dict:
        """Analyze market and execute trades for best opportunities"""
        results = {
            'trades_executed': 0,
            'trades_skipped': 0,
            'total_pnl': 0.0,
            'errors': []
        }

        try:
            # Get best instruments to trade
            best_instruments = await self.instrument_selector.get_best_instruments(count=3)
            
            for instrument_data in best_instruments:
                instrument = instrument_data['instrument']
                score = instrument_data['score']
                
                try:
                    # Calculate position size
                    stop_loss_pips = await self._calculate_optimal_stop_loss(
                        instrument, instrument_data['current_price']
                    )
                    
                    units = await self.position_sizer.calculate_units(
                        instrument, stop_loss_pips, confidence_boost=score - 0.5
                    )
                    
                    if units > 0:
                        # Execute trade
                        success, trade_info = await self.execute_trade(instrument, units, stop_loss_pips)
                        
                        if success:
                            results['trades_executed'] += 1
                            results['total_pnl'] += trade_info.get('pl', 0)
                            logger.info(f"Trade executed: {instrument} - {trade_info}")
                        else:
                            results['errors'].append(f"Failed to execute {instrument}: {trade_info}")
                    else:
                        results['trades_skipped'] += 1
                        logger.info(f"Trade skipped for {instrument}: insufficient units or risk limits")
                
                except Exception as e:
                    error_msg = f"Error processing {instrument}: {e}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
                    continue

        except Exception as e:
            error_msg = f"Error in analyze_and_execute_trades: {e}"
            results['errors'].append(error_msg)
            logger.error(error_msg)

        return results

    async def evaluate_exit(self, instrument: str, trade_id: str, entry_price: float) -> bool:
        """Evaluate if a trade should be closed early"""
        try:
            current_price = await self.oanda_client.get_price(instrument)
            if current_price is None:
                return False

            # Calculate price change
            price_change = (current_price - entry_price) / entry_price
            
            # Exit conditions
            profit_threshold = 0.002  # 20 pips profit
            loss_limit = -0.002       # 20 pips loss
            
            if price_change >= profit_threshold:
                logger.info(f"Profit target reached for {instrument}: {price_change:.4f}")
                return await self._close_trade(trade_id, instrument)
            elif price_change <= loss_limit:
                logger.info(f"Loss limit reached for {instrument}: {price_change:.4f}")
                return await self._close_trade(trade_id, instrument)
            
            return False

        except Exception as e:
            logger.error(f"Error evaluating exit for {instrument}: {e}")
            return False

    async def _close_trade(self, trade_id: str, instrument: str) -> bool:
        """Close a specific trade"""
        try:
            success, response = await self.oanda_client.close_trade(trade_id)
            if success:
                self.position_sizer.close_trade(instrument)
                logger.info(f"Trade {trade_id} closed successfully")
                return True
            else:
                logger.error(f"Failed to close trade {trade_id}: {response}")
                return False
        except Exception as e:
            logger.error(f"Error closing trade {trade_id}: {e}")
            return False

    async def get_trade_summary(self) -> Dict:
        """Get summary of recent trading activity"""
        try:
            open_trades = await self.oanda_client.get_open_trades()
            trade_history = await self.oanda_client.get_trade_history(count=20)
            
            summary = {
                'open_trades': len(open_trades),
                'recent_trades': len(trade_history),
                'total_pnl': sum(float(trade.get('pl', 0)) for trade in trade_history),
                'win_rate': self._calculate_win_rate(trade_history),
                'avg_trade_duration': self._calculate_avg_duration(trade_history)
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting trade summary: {e}")
            return {'error': str(e)}

    def _calculate_win_rate(self, trades: list) -> float:
        """Calculate win rate from trade history"""
        if not trades:
            return 0.0
        
        winning_trades = sum(1 for trade in trades if float(trade.get('pl', 0)) > 0)
        return winning_trades / len(trades)

    def _calculate_avg_duration(self, trades: list) -> float:
        """Calculate average trade duration in minutes"""
        if not trades:
            return 0.0
        
        total_duration = 0
        valid_trades = 0
        
        for trade in trades:
            try:
                open_time = datetime.fromisoformat(trade.get('openTime', '').replace('Z', '+00:00'))
                close_time = datetime.fromisoformat(trade.get('closeTime', '').replace('Z', '+00:00'))
                duration = (close_time - open_time).total_seconds() / 60  # minutes
                total_duration += duration
                valid_trades += 1
            except:
                continue
        
        return total_duration / valid_trades if valid_trades > 0 else 0.0