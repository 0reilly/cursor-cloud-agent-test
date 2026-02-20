"""
Crypto Momentum Trading Strategy
"""

import pandas as pd
import numpy as np
import ta
from typing import Dict, List, Optional, Tuple, Any
import logging

from config import (
    RSI_OVERBOUGHT, RSI_OVERSOLD, TIME_FRAME, LOOKBACK_PERIOD,
    MACD_SIGNAL_PERIOD, BOLLINGER_PERIOD, BOLLINGER_STD
)

logger = logging.getLogger(__name__)


class CryptoMomentumStrategy:
    """Crypto momentum trading strategy"""
    
    def __init__(self):
        self.name = "Crypto Momentum Strategy"
        self.version = "1.0"
        
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators on price data"""
        if df.empty or len(df) < 20:
            return df
        
        # Make a copy to avoid modifying original
        df = df.copy()
        
        # Price-based indicators
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Moving averages
        df['sma_20'] = ta.trend.sma_indicator(df['close'], window=20)
        df['ema_12'] = ta.trend.ema_indicator(df['close'], window=12)
        df['ema_26'] = ta.trend.ema_indicator(df['close'], window=26)
        
        # MACD
        macd = ta.trend.MACD(df['close'])
        df['macd'] = macd.macd()
        df['macd_signal'] = macd.macd_signal()
        df['macd_histogram'] = macd.macd_diff()
        
        # RSI
        df['rsi'] = ta.momentum.rsi(df['close'], window=14)
        
        # Bollinger Bands
        bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['bb_upper'] = bb.bollinger_hband()
        df['bb_middle'] = bb.bollinger_mavg()
        df['bb_lower'] = bb.bollinger_lband()
        df['bb_width'] = bb.bollinger_wband()
        df['bb_percent'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
        
        # Stochastic
        stoch = ta.momentum.StochasticOscillator(df['high'], df['low'], df['close'])
        df['stoch_k'] = stoch.stoch()
        df['stoch_d'] = stoch.stoch_signal()
        
        # Volume indicators
        df['volume_sma'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma']
        
        # ATR for volatility
        df['atr'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        df['atr_percent'] = df['atr'] / df['close']
        
        # Price channels
        df['high_20'] = df['high'].rolling(window=20).max()
        df['low_20'] = df['low'].rolling(window=20).min()
        df['channel_percent'] = (df['close'] - df['low_20']) / (df['high_20'] - df['low_20'])
        
        # Momentum
        df['momentum'] = df['close'] - df['close'].shift(5)
        df['momentum_pct'] = df['momentum'] / df['close'].shift(5)
        
        # Rate of Change
        df['roc'] = ta.momentum.roc(df['close'], window=10)
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate trading signals based on indicators"""
        if df.empty or len(df) < 20:
            return {'signal': 'hold', 'confidence': 0.0, 'reason': 'Insufficient data'}
        
        # Get latest values
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        # Initialize signal
        signal = 'hold'
        confidence = 0.5
        reasons = []
        
        # ===== BULLISH SIGNALS =====
        bullish_signals = 0
        total_bullish = 0
        
        # 1. RSI Oversold
        if latest['rsi'] < RSI_OVERSOLD:
            bullish_signals += 1
            reasons.append(f"RSI oversold ({latest['rsi']:.1f} < {RSI_OVERSOLD})")
        total_bullish += 1
        
        # 2. MACD bullish crossover
        if (prev['macd'] < prev['macd_signal'] and 
            latest['macd'] > latest['macd_signal']):
            bullish_signals += 1
            reasons.append("MACD bullish crossover")
        total_bullish += 1
        
        # 3. Price above moving averages
        if latest['close'] > latest['sma_20']:
            bullish_signals += 1
            reasons.append(f"Price above SMA20 ({latest['close']:.2f} > {latest['sma_20']:.2f})")
        total_bullish += 1
        
        # 4. Stochastic oversold
        if latest['stoch_k'] < 20:
            bullish_signals += 1
            reasons.append(f"Stochastic oversold ({latest['stoch_k']:.1f} < 20)")
        total_bullish += 1
        
        # 5. Bollinger Band oversold
        if latest['bb_percent'] < 0.2:
            bullish_signals += 1
            reasons.append(f"Bollinger Band oversold ({latest['bb_percent']:.2%})")
        total_bullish += 1
        
        # 6. Positive momentum
        if latest['momentum_pct'] > 0.01:  # 1% positive momentum
            bullish_signals += 1
            reasons.append(f"Positive momentum ({latest['momentum_pct']:.2%})")
        total_bullish += 1
        
        # 7. High volume confirmation
        if latest['volume_ratio'] > 1.5:
            bullish_signals += 1
            reasons.append(f"High volume ({latest['volume_ratio']:.1f}x average)")
        total_bullish += 1
        
        # ===== BEARISH SIGNALS =====
        bearish_signals = 0
        total_bearish = 0
        
        # 1. RSI Overbought
        if latest['rsi'] > RSI_OVERBOUGHT:
            bearish_signals += 1
            reasons.append(f"RSI overbought ({latest['rsi']:.1f} > {RSI_OVERBOUGHT})")
        total_bearish += 1
        
        # 2. MACD bearish crossover
        if (prev['macd'] > prev['macd_signal'] and 
            latest['macd'] < latest['macd_signal']):
            bearish_signals += 1
            reasons.append("MACD bearish crossover")
        total_bearish += 1
        
        # 3. Price below moving averages
        if latest['close'] < latest['sma_20']:
            bearish_signals += 1
            reasons.append(f"Price below SMA20 ({latest['close']:.2f} < {latest['sma_20']:.2f})")
        total_bearish += 1
        
        # 4. Stochastic overbought
        if latest['stoch_k'] > 80:
            bearish_signals += 1
            reasons.append(f"Stochastic overbought ({latest['stoch_k']:.1f} > 80)")
        total_bearish += 1
        
        # 5. Bollinger Band overbought
        if latest['bb_percent'] > 0.8:
            bearish_signals += 1
            reasons.append(f"Bollinger Band overbought ({latest['bb_percent']:.2%})")
        total_bearish += 1
        
        # 6. Negative momentum
        if latest['momentum_pct'] < -0.01:  # 1% negative momentum
            bearish_signals += 1
            reasons.append(f"Negative momentum ({latest['momentum_pct']:.2%})")
        total_bearish += 1
        
        # 7. High volume on down move
        if latest['volume_ratio'] > 1.5 and latest['returns'] < 0:
            bearish_signals += 1
            reasons.append(f"High volume on down move ({latest['volume_ratio']:.1f}x)")
        total_bearish += 1
        
        # ===== DECISION LOGIC =====
        # Calculate confidence scores
        bullish_score = bullish_signals / max(total_bullish, 1)
        bearish_score = bearish_signals / max(total_bearish, 1)
        
        # Strong signals require at least 40% of indicators
        if bullish_score >= 0.4 and bullish_score > bearish_score:
            signal = 'buy'
            confidence = min(0.5 + bullish_score * 0.5, 0.9)
            
        elif bearish_score >= 0.4 and bearish_score > bullish_score:
            signal = 'sell'
            confidence = min(0.5 + bearish_score * 0.5, 0.9)
            
        else:
            signal = 'hold'
            confidence = 0.5
            
        # Adjust confidence based on volatility
        if not pd.isna(latest['atr_percent']):
            # Higher volatility reduces confidence
            vol_adjustment = 1.0 - min(latest['atr_percent'] * 10, 0.3)
            confidence *= vol_adjustment
            
        # Ensure confidence is reasonable
        confidence = max(0.1, min(confidence, 0.9))
        
        # Prepare result
        result = {
            'signal': signal,
            'confidence': confidence,
            'reasons': reasons,
            'indicators': {
                'price': float(latest['close']),
                'rsi': float(latest['rsi']) if not pd.isna(latest['rsi']) else None,
                'macd': float(latest['macd']) if not pd.isna(latest['macd']) else None,
                'macd_signal': float(latest['macd_signal']) if not pd.isna(latest['macd_signal']) else None,
                'sma_20': float(latest['sma_20']) if not pd.isna(latest['sma_20']) else None,
                'bb_percent': float(latest['bb_percent']) if not pd.isna(latest['bb_percent']) else None,
                'stoch_k': float(latest['stoch_k']) if not pd.isna(latest['stoch_k']) else None,
                'volume_ratio': float(latest['volume_ratio']) if not pd.isna(latest['volume_ratio']) else None,
                'atr_percent': float(latest['atr_percent']) if not pd.isna(latest['atr_percent']) else None,
                'momentum_pct': float(latest['momentum_pct']) if not pd.isna(latest['momentum_pct']) else None,
            },
            'scores': {
                'bullish_score': bullish_score,
                'bearish_score': bearish_score,
                'bullish_signals': bullish_signals,
                'bearish_signals': bearish_signals,
            }
        }
        
        return result
    
    def calculate_position_size(self, account_cash: float, current_price: float,
                               confidence: float, volatility: float) -> Tuple[float, Dict[str, Any]]:
        """Calculate optimal position size based on risk parameters"""
        from config import (
            MAX_POSITION_SIZE_PCT, MIN_POSITION_SIZE, 
            STOP_LOSS_PCT, VOLATILITY_ADJUSTMENT
        )
        
        # Base position size (percentage of capital)
        base_size_pct = MAX_POSITION_SIZE_PCT * confidence
        
        # Adjust for volatility if enabled
        if VOLATILITY_ADJUSTMENT and volatility > 0:
            # Reduce position size in high volatility
            vol_adjustment = 1.0 / (1.0 + volatility * 5)
            base_size_pct *= vol_adjustment
        
        # Calculate dollar amount
        position_value = account_cash * base_size_pct
        
        # Ensure minimum size
        if position_value < MIN_POSITION_SIZE:
            position_value = MIN_POSITION_SIZE
        
        # Calculate quantity
        quantity = position_value / current_price
        
        # Round to appropriate decimals for crypto
        # Crypto typically allows 6-8 decimal places
        quantity = round(quantity, 6)
        
        # Calculate stop loss and take profit levels
        stop_loss_price = current_price * (1 - STOP_LOSS_PCT)
        take_profit_price = current_price * (1 + STOP_LOSS_PCT * 2)  # 2:1 reward:risk
        
        result = {
            'quantity': quantity,
            'position_value': position_value,
            'position_pct': base_size_pct,
            'current_price': current_price,
            'stop_loss': stop_loss_price,
            'take_profit': take_profit_price,
            'risk_reward_ratio': 2.0,
            'volatility_adjustment': VOLATILITY_ADJUSTMENT,
        }
        
        return quantity, result
    
    def analyze_market(self, df: pd.DataFrame, account_cash: float) -> Dict[str, Any]:
        """Complete market analysis for trading decision"""
        # Calculate indicators
        df_with_indicators = self.calculate_indicators(df)
        
        if df_with_indicators.empty:
            return {'error': 'No data available for analysis'}
        
        # Generate signals
        signal_result = self.generate_signals(df_with_indicators)
        
        if signal_result['signal'] == 'hold':
            return signal_result
        
        # Get current price
        current_price = df_with_indicators.iloc[-1]['close']
        
        # Get volatility (ATR %)
        volatility = df_with_indicators.iloc[-1]['atr_percent'] if 'atr_percent' in df_with_indicators.columns else 0.02
        
        # Calculate position size
        quantity, size_info = self.calculate_position_size(
            account_cash, current_price, signal_result['confidence'], volatility
        )
        
        # Combine results
        result = {
            **signal_result,
            'position_size': size_info,
            'analysis_timestamp': pd.Timestamp.now().isoformat(),
            'data_points': len(df),
        }
        
        return result
    
    def backtest_signal(self, df: pd.DataFrame, lookback_days: int = 30) -> Dict[str, Any]:
        """Backtest the strategy signal over historical data"""
        if len(df) < 100:
            return {'error': 'Insufficient data for backtest'}
        
        # Use last N days for backtest
        test_data = df.tail(min(len(df), lookback_days * 288))  # ~288 5-min bars per day
        
        if len(test_data) < 20:
            return {'error': 'Not enough data for backtest'}
        
        # Calculate indicators
        test_data = self.calculate_indicators(test_data)
        
        # Generate signals for each point (excluding latest for forward-looking bias)
        signals = []
        for i in range(20, len(test_data) - 1):
            window = test_data.iloc[:i+1]
            signal = self.generate_signals(window)
            
            # Record signal and next period return
            next_return = test_data.iloc[i+1]['returns'] if i + 1 < len(test_data) else 0
            
            signals.append({
                'timestamp': test_data.iloc[i].name,
                'signal': signal['signal'],
                'confidence': signal['confidence'],
                'next_return': next_return,
            })
        
        # Analyze performance
        if not signals:
            return {'error': 'No signals generated'}
        
        signals_df = pd.DataFrame(signals)
        
        # Calculate returns by signal type
        buy_signals = signals_df[signals_df['signal'] == 'buy']
        sell_signals = signals_df[signals_df['signal'] == 'sell']
        hold_signals = signals_df[signals_df['signal'] == 'hold']
        
        buy_returns = buy_signals['next_return'].mean() if not buy_signals.empty else 0
        sell_returns = sell_signals['next_return'].mean() if not sell_signals.empty else 0
        hold_returns = hold_signals['next_return'].mean() if not hold_signals.empty else 0
        
        # Calculate win rates
        buy_win_rate = (buy_signals['next_return'] > 0).mean() if not buy_signals.empty else 0
        sell_win_rate = (sell_signals['next_return'] < 0).mean() if not sell_signals.empty else 0
        
        # Calculate cumulative returns if following strategy
        cumulative_returns = 1.0
        strategy_returns = []
        
        for _, row in signals_df.iterrows():
            if row['signal'] == 'buy':
                cumulative_returns *= (1 + row['next_return'])
            elif row['signal'] == 'sell':
                cumulative_returns *= (1 - row['next_return'])  # Short position
            strategy_returns.append(cumulative_returns)
        
        total_return = cumulative_returns - 1
        
        result = {
            'total_signals': len(signals_df),
            'buy_signals': len(buy_signals),
            'sell_signals': len(sell_signals),
            'hold_signals': len(hold_signals),
            'buy_avg_return': buy_returns,
            'sell_avg_return': sell_returns,
            'hold_avg_return': hold_returns,
            'buy_win_rate': buy_win_rate,
            'sell_win_rate': sell_win_rate,
            'total_return': total_return,
            'annualized_return': total_return * (365 / lookback_days) if lookback_days > 0 else 0,
            'sharpe_ratio': signals_df['next_return'].mean() / signals_df['next_return'].std() if len(signals_df) > 1 and signals_df['next_return'].std() > 0 else 0,
        }
        
        return result


# ============ TEST FUNCTIONS ============

def test_strategy():
    """Test the strategy with sample data"""
    print("Testing Crypto Momentum Strategy...")
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=100, freq='5min')
    prices = 100 + np.cumsum(np.random.randn(100) * 0.5)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.randn(100) * 1000 + 5000,
    })
    df.set_index('timestamp', inplace=True)
    
    # Test strategy
    strategy = CryptoMomentumStrategy()
    
    # Test indicators
    df_with_indicators = strategy.calculate_indicators(df)
    print(f"✅ Indicators calculated: {len([col for col in df_with_indicators.columns if 'sma' in col or 'rsi' in col])} indicators added")
    
    # Test signal generation
    signal = strategy.generate_signals(df_with_indicators)
    print(f"✅ Signal generated: {signal['signal']} (confidence: {signal['confidence']:.2f})")
    print(f"Reasons: {signal['reasons'][:3]}...")
    
    # Test position sizing
    quantity, size_info = strategy.calculate_position_size(
        account_cash=10000,
        current_price=df_with_indicators.iloc[-1]['close'],
        confidence=signal['confidence'],
        volatility=0.02
    )
    print(f"✅ Position size calculated: {quantity:.6f} units")
    print(f"Position value: ${size_info['position_value']:.2f}")
    
    # Test complete analysis
    analysis = strategy.analyze_market(df, account_cash=10000)
    print(f"✅ Complete analysis: {analysis['signal']} signal with {analysis['confidence']:.2f} confidence")
    
    # Test backtest
    backtest = strategy.backtest_signal(df, lookback_days=5)
    if 'error' not in backtest:
        print(f"✅ Backtest completed: {backtest['total_signals']} signals, {backtest['total_return']:.2%} return")
    
    print("\nStrategy test completed successfully!")


if __name__ == "__main__":
    test_strategy()