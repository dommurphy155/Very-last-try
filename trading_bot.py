import os
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from oanda_client import OandaClient
from position_sizer import PositionSizer
from trade_executor import TradeExecutor
from trade_closer import TradeCloser
from instrument_selector import InstrumentSelector

logger = logging.getLogger("trading_bot")

class TradingBot:
    def __init__(self):
        api_key = os.getenv("OANDA_API_KEY")
        account_id = os.getenv("OANDA_ACCOUNT_ID")

        if not api_key or not account_id:
            raise ValueError("OANDA_API_KEY and OANDA_ACCOUNT_ID must be set in environment variables.")

        # Initialize components
        self.oanda = OandaClient(api_key, account_id)
        self.position_sizer = PositionSizer(self.oanda)
        self.instrument_selector = InstrumentSelector(self.oanda)
        self.trade_executor = TradeExecutor(self.oanda, self.position_sizer, self.instrument_selector)
        self.trade_closer = TradeCloser(self.oanda, self.position_sizer)
        
        # Trading parameters
        self.scan_interval = 7  # seconds
        self.max_trades_per_scan = 2
        self.is_running = False
        self.last_scan_time = None
        
        # Performance tracking
        self.session_stats = {
            'scans_completed': 0,
            'trades_executed': 0,
            'trades_closed': 0,
            'total_pnl': 0.0,
            'errors': 0,
            'start_time': datetime.utcnow()
        }

    async def start(self):
        """Start the trading bot with continuous scanning"""
        if self.is_running:
            logger.warning("Trading bot is already running")
            return
        
        self.is_running = True
        logger.info("🤖 Trading bot started - scanning every 7 seconds")
        
        try:
            while self.is_running:
                await self._run_scan_cycle()
                await asyncio.sleep(self.scan_interval)
                
        except KeyboardInterrupt:
            logger.info("🛑 Trading bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Trading bot crashed: {e}")
            raise
        finally:
            await self.stop()

    async def stop(self):
        """Stop the trading bot"""
        self.is_running = False
        logger.info("🛑 Trading bot stopping...")
        await self.oanda.close()

    async def _run_scan_cycle(self):
        """Run a single scan cycle"""
        cycle_start = datetime.utcnow()
        self.session_stats['scans_completed'] += 1
        
        try:
            # Update equity and drawdown
            await self.position_sizer.update_equity_and_drawdown()
            
            # Check if we can trade (risk management)
            risk_summary = self.position_sizer.get_risk_summary()
            if not risk_summary['can_trade']:
                logger.info(f"⛔ Trading blocked: {risk_summary}")
                return
            
            # Monitor and close existing trades
            close_results = await self.trade_closer.monitor_trades()
            if close_results['trades_closed'] > 0:
                logger.info(f"📉 Closed {close_results['trades_closed']} trades")
                self.session_stats['trades_closed'] += close_results['trades_closed']
            
            # Analyze market and execute new trades
            if self._should_execute_trades():
                trade_results = await self.trade_executor.analyze_and_execute_trades()
                
                if trade_results['trades_executed'] > 0:
                    logger.info(f"📈 Executed {trade_results['trades_executed']} trades")
                    self.session_stats['trades_executed'] += trade_results['trades_executed']
                
                if trade_results['errors']:
                    self.session_stats['errors'] += len(trade_results['errors'])
                    for error in trade_results['errors']:
                        logger.error(f"Trade error: {error}")
            
            # Update session stats
            self.session_stats['total_pnl'] = await self._calculate_total_pnl()
            
            # Log cycle completion
            cycle_duration = (datetime.utcnow() - cycle_start).total_seconds()
            logger.debug(f"✅ Scan cycle completed in {cycle_duration:.2f}s")
            
        except Exception as e:
            self.session_stats['errors'] += 1
            logger.error(f"❌ Error in scan cycle: {e}")

    def _should_execute_trades(self) -> bool:
        """Determine if we should execute trades in this cycle"""
        # Rate limiting: don't execute trades too frequently
        if self.last_scan_time and (datetime.utcnow() - self.last_scan_time).total_seconds() < 30:
            return False
        
        # Check risk limits
        risk_summary = self.position_sizer.get_risk_summary()
        if not risk_summary['can_trade']:
            return False
        
        # Check if we have room for more trades
        if risk_summary['open_trades'] >= 5:  # Conservative limit
            return False
        
        self.last_scan_time = datetime.utcnow()
        return True

    async def _calculate_total_pnl(self) -> float:
        """Calculate total PnL from open trades and account"""
        try:
            # Get account equity
            equity = await self.oanda.get_equity()
            balance = await self.oanda.get_account_balance()
            
            if equity is not None and balance is not None:
                return equity - balance
            
            return 0.0
        except Exception as e:
            logger.error(f"Error calculating total PnL: {e}")
            return 0.0

    async def run(self) -> Dict:
        """Run a single trading cycle (for manual execution)"""
        try:
            # Update equity and drawdown
            await self.position_sizer.update_equity_and_drawdown()
            
            # Check risk management
            risk_summary = self.position_sizer.get_risk_summary()
            if not risk_summary['can_trade']:
                return {
                    'success': False,
                    'reason': f"Trading blocked: {risk_summary}",
                    'risk_summary': risk_summary
                }
            
            # Monitor existing trades
            close_results = await self.trade_closer.monitor_trades()
            
            # Execute new trades
            trade_results = await self.trade_executor.analyze_and_execute_trades()
            
            return {
                'success': True,
                'trades_executed': trade_results['trades_executed'],
                'trades_closed': close_results['trades_closed'],
                'risk_summary': risk_summary,
                'errors': trade_results['errors'] + close_results['errors']
            }
            
        except Exception as e:
            logger.error(f"Error in run(): {e}")
            return {
                'success': False,
                'reason': str(e),
                'errors': [str(e)]
            }

    async def get_open_trades(self) -> List[Dict]:
        """Get all open trades with enhanced information"""
        try:
            open_trades = await self.oanda.get_open_trades()
            enhanced_trades = []
            
            for trade in open_trades:
                enhanced_trade = {
                    'id': trade.get('id'),
                    'instrument': trade.get('instrument'),
                    'units': int(trade.get('currentUnits', 0)),
                    'entry_price': float(trade.get('price', 0)),
                    'unrealized_pl': float(trade.get('unrealizedPL', 0)),
                    'open_time': trade.get('openTime'),
                    'duration': self._calculate_trade_duration(trade.get('openTime')),
                    'confidence': self.position_sizer.get_confidence(trade.get('instrument', ''))
                }
                enhanced_trades.append(enhanced_trade)
            
            return enhanced_trades
            
        except Exception as e:
            logger.error(f"Error getting open trades: {e}")
            return []

    def _calculate_trade_duration(self, open_time_str: str) -> str:
        """Calculate trade duration as a string"""
        try:
            open_time = datetime.fromisoformat(open_time_str.replace('Z', '+00:00'))
            duration = datetime.utcnow().replace(tzinfo=open_time.tzinfo) - open_time
            return str(duration).split('.')[0]  # Remove microseconds
        except:
            return "Unknown"

    async def get_daily_report(self) -> Dict:
        """Get comprehensive daily trading report"""
        try:
            # Get account information
            account_summary = await self.oanda.get_account_summary()
            equity = await self.oanda.get_equity()
            balance = await self.oanda.get_account_balance()
            
            # Get performance data
            performance_summary = self.position_sizer.get_performance_summary()
            risk_summary = self.position_sizer.get_risk_summary()
            closed_trades_summary = await self.trade_closer.get_closed_trades_summary()
            
            # Calculate daily PnL
            daily_pnl = 0.0
            if equity is not None and balance is not None:
                daily_pnl = equity - balance
            
            return {
                'date': datetime.utcnow().date().isoformat(),
                'account': {
                    'balance': balance,
                    'equity': equity,
                    'margin_available': account_summary.get('marginAvailable') if account_summary else None,
                    'daily_pnl': daily_pnl
                },
                'trading': {
                    'open_trades': len(await self.get_open_trades()),
                    'session_stats': self.session_stats,
                    'risk_summary': risk_summary,
                    'performance_summary': performance_summary,
                    'closed_trades': closed_trades_summary
                },
                'market_overview': await self.instrument_selector.get_market_overview()
            }
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return {'error': str(e)}

    async def get_weekly_report(self) -> Dict:
        """Get weekly trading report"""
        try:
            # Get trade history for the week
            trade_history = await self.oanda.get_trade_history(count=100)
            
            # Filter for this week
            week_start = datetime.utcnow() - timedelta(days=7)
            weekly_trades = []
            
            for trade in trade_history:
                try:
                    close_time = datetime.fromisoformat(trade.get('closeTime', '').replace('Z', '+00:00'))
                    if close_time >= week_start:
                        weekly_trades.append(trade)
                except:
                    continue
            
            # Calculate weekly statistics
            weekly_pnl = sum(float(trade.get('pl', 0)) for trade in weekly_trades)
            winning_trades = sum(1 for trade in weekly_trades if float(trade.get('pl', 0)) > 0)
            win_rate = winning_trades / len(weekly_trades) if weekly_trades else 0.0
            
            return {
                'period': 'weekly',
                'trades': len(weekly_trades),
                'winning_trades': winning_trades,
                'win_rate': win_rate,
                'total_pnl': weekly_pnl,
                'avg_trade_pnl': weekly_pnl / len(weekly_trades) if weekly_trades else 0.0,
                'best_trade': max((float(trade.get('pl', 0)) for trade in weekly_trades), default=0.0),
                'worst_trade': min((float(trade.get('pl', 0)) for trade in weekly_trades), default=0.0)
            }
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            return {'error': str(e)}

    async def run_diagnostics(self) -> Dict:
        """Run comprehensive system diagnostics"""
        try:
            diagnostics = {
                'timestamp': datetime.utcnow().isoformat(),
                'system_status': 'OK',
                'errors': []
            }
            
            # Test OANDA connection
            try:
                balance = await self.oanda.get_account_balance()
                diagnostics['oanda_connection'] = 'OK' if balance is not None else 'FAILED'
            except Exception as e:
                diagnostics['oanda_connection'] = 'FAILED'
                diagnostics['errors'].append(f"OANDA connection failed: {e}")
            
            # Test instrument analysis
            try:
                best_instruments = await self.instrument_selector.get_best_instruments(count=1)
                diagnostics['instrument_analysis'] = 'OK' if best_instruments else 'FAILED'
            except Exception as e:
                diagnostics['instrument_analysis'] = 'FAILED'
                diagnostics['errors'].append(f"Instrument analysis failed: {e}")
            
            # Check risk management
            try:
                risk_summary = self.position_sizer.get_risk_summary()
                diagnostics['risk_management'] = 'OK'
                diagnostics['risk_summary'] = risk_summary
            except Exception as e:
                diagnostics['risk_management'] = 'FAILED'
                diagnostics['errors'].append(f"Risk management failed: {e}")
            
            # Check open trades
            try:
                open_trades = await self.get_open_trades()
                diagnostics['open_trades'] = len(open_trades)
            except Exception as e:
                diagnostics['open_trades'] = 'ERROR'
                diagnostics['errors'].append(f"Open trades check failed: {e}")
            
            # Overall status
            if diagnostics['errors']:
                diagnostics['system_status'] = 'ERRORS'
            
            return diagnostics
            
        except Exception as e:
            return {
                'timestamp': datetime.utcnow().isoformat(),
                'system_status': 'CRITICAL_ERROR',
                'error': str(e)
            }

    async def force_close_all_trades(self, reason: str = "Manual close") -> Dict:
        """Force close all open trades"""
        return await self.trade_closer.force_close_all_trades(reason)

    def get_session_stats(self) -> Dict:
        """Get current session statistics"""
        return self.session_stats.copy()