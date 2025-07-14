import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from oanda_client import OandaClient

logger = logging.getLogger("instrument_selector")

class InstrumentSelector:
    def __init__(self, oanda_client: OandaClient):
        self.oanda = oanda_client
        self.instruments = [
            "EUR_USD", "GBP_USD", "USD_JPY", "AUD_USD", "USD_CHF",
            "USD_CAD", "NZD_USD", "EUR_GBP", "EUR_JPY", "GBP_JPY"
        ]
        self.analysis_cache = {}
        self.cache_ttl = 30  # 30 seconds cache

    async def get_best_instruments(self, count: int = 3) -> List[Dict]:
        """Get the best instruments to trade based on analysis"""
        instruments_data = []
        
        for instrument in self.instruments:
            try:
                analysis = await self._analyze_instrument(instrument)
                if analysis and analysis['score'] > 0.5:  # Minimum score threshold
                    instruments_data.append(analysis)
            except Exception as e:
                logger.error(f"Error analyzing {instrument}: {e}")
                continue
        
        # Sort by score and return top instruments
        instruments_data.sort(key=lambda x: x['score'], reverse=True)
        return instruments_data[:count]

    async def _analyze_instrument(self, instrument: str) -> Optional[Dict]:
        """Comprehensive instrument analysis"""
        cache_key = f"{instrument}_{datetime.now().timestamp() // self.cache_ttl}"
        if cache_key in self.analysis_cache:
            return self.analysis_cache[cache_key]

        try:
            # Get recent price data
            candles = await self.oanda.get_candles(instrument, count=100, granularity="M5")
            if len(candles) < 50:
                return None

            # Convert to DataFrame
            df = self._candles_to_dataframe(candles)
            
            # Calculate technical indicators
            analysis = {
                'instrument': instrument,
                'current_price': df['close'].iloc[-1],
                'momentum_score': self._calculate_momentum(df),
                'volatility_score': self._calculate_volatility(df),
                'trend_score': self._calculate_trend(df),
                'volume_score': self._calculate_volume_score(df),
                'regime': self._detect_market_regime(df),
                'support_resistance': self._find_support_resistance(df),
                'risk_level': self._assess_risk_level(df)
            }
            
            # Calculate composite score
            analysis['score'] = self._calculate_composite_score(analysis)
            
            # Cache the result
            self.analysis_cache[cache_key] = analysis
            return analysis
            
        except Exception as e:
            logger.error(f"Error in instrument analysis for {instrument}: {e}")
            return None

    def _candles_to_dataframe(self, candles: List[Dict]) -> pd.DataFrame:
        """Convert OANDA candles to pandas DataFrame"""
        data = []
        for candle in candles:
            if candle['complete']:
                data.append({
                    'time': pd.to_datetime(candle['time']),
                    'open': float(candle['mid']['o']),
                    'high': float(candle['mid']['h']),
                    'low': float(candle['mid']['l']),
                    'close': float(candle['mid']['c']),
                    'volume': int(candle.get('volume', 0))
                })
        
        df = pd.DataFrame(data)
        df.set_index('time', inplace=True)
        return df

    def _calculate_momentum(self, df: pd.DataFrame) -> float:
        """Calculate momentum score using RSI and MACD"""
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9).mean()
        
        # Momentum score (0-1)
        rsi_score = 1 - abs(rsi.iloc[-1] - 50) / 50  # Closer to 50 = better
        macd_score = abs(macd.iloc[-1] - signal.iloc[-1]) / df['close'].iloc[-1] * 100
        
        return (rsi_score + min(macd_score, 1.0)) / 2

    def _calculate_volatility(self, df: pd.DataFrame) -> float:
        """Calculate volatility score"""
        returns = df['close'].pct_change().dropna()
        volatility = returns.std() * np.sqrt(288)  # Annualized (5-min data)
        
        # Normalize volatility (0.1 = low, 0.3 = high)
        vol_score = min(volatility / 0.2, 1.0)
        return vol_score

    def _calculate_trend(self, df: pd.DataFrame) -> float:
        """Calculate trend strength using ADX and moving averages"""
        # ADX calculation
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean()
        
        # Moving averages
        ma20 = df['close'].rolling(window=20).mean()
        ma50 = df['close'].rolling(window=50).mean()
        
        # Trend score
        price_above_ma = df['close'].iloc[-1] > ma20.iloc[-1] > ma50.iloc[-1]
        trend_strength = atr.iloc[-1] / df['close'].iloc[-1] * 100
        
        return (0.7 if price_above_ma else 0.3) * min(trend_strength, 1.0)

    def _calculate_volume_score(self, df: pd.DataFrame) -> float:
        """Calculate volume-based score"""
        if 'volume' not in df.columns or df['volume'].sum() == 0:
            return 0.5  # Default score if no volume data
        
        avg_volume = df['volume'].rolling(window=20).mean()
        current_volume = df['volume'].iloc[-1]
        
        if avg_volume.iloc[-1] > 0:
            volume_ratio = current_volume / avg_volume.iloc[-1]
            return min(volume_ratio, 2.0) / 2.0
        return 0.5

    def _detect_market_regime(self, df: pd.DataFrame) -> str:
        """Detect market regime (trending, ranging, volatile)"""
        # Calculate indicators
        returns = df['close'].pct_change().dropna()
        volatility = returns.std()
        
        # ADX for trend strength
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Simple trend detection
        ma20 = df['close'].rolling(window=20).mean()
        ma50 = df['close'].rolling(window=50).mean()
        
        trend_strength = abs(ma20.iloc[-1] - ma50.iloc[-1]) / df['close'].iloc[-1]
        
        if volatility > 0.002:  # High volatility
            return "volatile"
        elif trend_strength > 0.005:  # Strong trend
            return "trending"
        else:
            return "ranging"

    def _find_support_resistance(self, df: pd.DataFrame) -> Dict:
        """Find key support and resistance levels"""
        current_price = df['close'].iloc[-1]
        
        # Simple S/R using recent highs and lows
        recent_high = df['high'].tail(20).max()
        recent_low = df['low'].tail(20).min()
        
        # Moving averages as dynamic levels
        ma20 = df['close'].rolling(window=20).mean().iloc[-1]
        ma50 = df['close'].rolling(window=50).mean().iloc[-1]
        
        return {
            'resistance': recent_high,
            'support': recent_low,
            'ma20': ma20,
            'ma50': ma50,
            'distance_to_resistance': (recent_high - current_price) / current_price,
            'distance_to_support': (current_price - recent_low) / current_price
        }

    def _assess_risk_level(self, df: pd.DataFrame) -> str:
        """Assess current risk level"""
        volatility = df['close'].pct_change().std()
        atr = self._calculate_atr(df)
        
        if volatility > 0.003 or atr > df['close'].iloc[-1] * 0.002:
            return "high"
        elif volatility > 0.0015 or atr > df['close'].iloc[-1] * 0.001:
            return "medium"
        else:
            return "low"

    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(window=period).mean().iloc[-1]

    def _calculate_composite_score(self, analysis: Dict) -> float:
        """Calculate composite trading score"""
        weights = {
            'momentum_score': 0.25,
            'volatility_score': 0.20,
            'trend_score': 0.25,
            'volume_score': 0.15,
            'risk_level': 0.15
        }
        
        # Risk level adjustment
        risk_multiplier = {
            'low': 1.0,
            'medium': 0.8,
            'high': 0.6
        }
        
        base_score = (
            analysis['momentum_score'] * weights['momentum_score'] +
            analysis['volatility_score'] * weights['volatility_score'] +
            analysis['trend_score'] * weights['trend_score'] +
            analysis['volume_score'] * weights['volume_score']
        )
        
        risk_adjustment = risk_multiplier.get(analysis['risk_level'], 0.8)
        
        return base_score * risk_adjustment

    async def get_market_overview(self) -> Dict:
        """Get overview of all instruments"""
        overview = {
            'total_instruments': len(self.instruments),
            'trending': 0,
            'ranging': 0,
            'volatile': 0,
            'best_opportunities': []
        }
        
        for instrument in self.instruments:
            try:
                analysis = await self._analyze_instrument(instrument)
                if analysis:
                    overview[analysis['regime']] += 1
                    if analysis['score'] > 0.7:
                        overview['best_opportunities'].append({
                            'instrument': instrument,
                            'score': analysis['score'],
                            'regime': analysis['regime']
                        })
            except Exception as e:
                logger.error(f"Error in market overview for {instrument}: {e}")
        
        return overview