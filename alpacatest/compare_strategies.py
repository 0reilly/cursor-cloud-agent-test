"""
Compare Trading Strategies: Pure Algorithmic vs HMM-Regime-Aware
Tests both approaches side-by-side with real market data
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any

# Set plotting style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


class StrategyComparison:
    """Compare different trading strategy approaches"""
    
    def __init__(self, train_hmm_on_init: bool = True):
        from alpaca_client import AlpacaClient
        from strategy import CryptoMomentumStrategy
        from hmm_regime import CryptoHMMRegimeDetector, RegimeAwareCryptoStrategy
        
        self.client = AlpacaClient()
        self.base_strategy = CryptoMomentumStrategy()
        
        # Initialize HMM detector
        self.hmm_detector = CryptoHMMRegimeDetector()
        self.regime_aware_strategy = RegimeAwareCryptoStrategy(
            self.base_strategy, self.hmm_detector
        )
        
        # Results storage
        self.results = {
            'pure_algorithmic': [],
            'hmm_regime_aware': [],
            'metadata': {}
        }
        
        print("Strategy Comparison Initialized")
        print("=" * 60)
        print("1. Pure Algorithmic: Technical indicators only")
        print("2. HMM-Regime-Aware: Regime detection + adjusted signals")
        print("=" * 60)
        
        # Train HMM on synthetic data if requested
        if train_hmm_on_init:
            self._train_hmm_on_synthetic_data()
    
    def fetch_market_data(self, symbol: str = "BTC/USD", 
                         timeframe: str = "5Min", 
                         limit: int = 200) -> pd.DataFrame:
        """Fetch market data for testing"""
        print(f"Fetching {symbol} data ({timeframe}, {limit} bars)...")
        
        df = self.client.get_market_data(symbol, timeframe, limit)
        
        if df.empty:
            print(f"⚠️ No data for {symbol}")
            return pd.DataFrame()
        
        print(f"✅ Data retrieved: {len(df)} bars from {df.iloc[0]['timestamp']} to {df.iloc[-1]['timestamp']}")
        print(f"   Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
        print(f"   Latest: ${df.iloc[-1]['close']:.2f}")
        
        return df
    
    def train_hmm_on_history(self, historical_data: Dict[str, pd.DataFrame]):
        """Train HMM on historical data"""
        print("\nTraining HMM on historical data...")
        
        # For testing, create synthetic historical data if needed
        if not historical_data:
            print("Creating synthetic training data...")
            historical_data = self._create_synthetic_training_data()
        
        try:
            # Train HMM
            self.hmm_detector.train_hmm(historical_data)
            
            # Get regime summary
            summary = self.hmm_detector.get_regime_summary()
            print(f"✅ HMM trained on {len(historical_data)} symbols")
            print(f"   Learned regimes:")
            for regime_key, regime_data in summary.items():
                stats = regime_data['stats']
                print(f"   • {regime_data['name']}: {stats['percentage']:.1f}% of samples")
            
            return True
        except Exception as e:
            print(f"⚠️ HMM training failed: {e}")
            print("   Continuing with untrained HMM (will use base strategy)")
            return False
    
    def _create_synthetic_training_data(self) -> Dict[str, pd.DataFrame]:
        """Create synthetic training data for HMM"""
        np.random.seed(42)
        
        symbols = ["BTC/USD", "ETH/USD", "SOL/USD"]
        historical_data = {}
        
        for symbol in symbols:
            # Create 1000 data points with different regimes
            dates = pd.date_range('2024-01-01', periods=1000, freq='5min')
            
            # Simulate different market regimes
            prices = [10000]
            regime_periods = [100, 200, 300, 250, 150]  # Different length regimes
            
            for period in regime_periods:
                for i in range(period):
                    last_price = prices[-1]
                    
                    # Different regimes have different characteristics
                    if period == 100:  # Strong bull
                        change = np.random.normal(0.001, 0.005)
                    elif period == 200:  # Weak bull
                        change = np.random.normal(0.0005, 0.008)
                    elif period == 300:  # Sideways
                        change = np.random.normal(0.000, 0.01)
                    elif period == 250:  # Weak bear
                        change = np.random.normal(-0.0005, 0.007)
                    else:  # Strong bear
                        change = np.random.normal(-0.001, 0.009)
                    
                    prices.append(last_price * (1 + change))
            
            df = pd.DataFrame({
                'timestamp': dates,
                'open': [p * 0.999 for p in prices[:1000]],
                'high': [p * 1.001 for p in prices[:1000]],
                'low': [p * 0.999 for p in prices[:1000]],
                'close': prices[:1000],
                'volume': np.random.randn(1000) * 1000 + 5000,
            })
            df.set_index('timestamp', inplace=True)
            
            historical_data[symbol] = df
        
        return historical_data
    
    def _train_hmm_on_synthetic_data(self):
        """Train HMM on synthetic data for testing"""
        print("\nTraining HMM on synthetic data...")
        
        try:
            # Create synthetic historical data
            historical_data = self._create_synthetic_training_data()
            
            # Train HMM using the regime-aware strategy's method
            trained_detector = self.regime_aware_strategy.train_hmm(historical_data)
            
            print("\u2705 HMM trained successfully on synthetic data")
            
            # Get regime summary
            summary = self.hmm_detector.get_regime_summary()
            print(f"   Learned {len(summary)} regimes:")
            for regime_key, regime_data in summary.items():
                stats = regime_data['stats']
                print(f"   \u2022 {regime_data['name']}: {stats['percentage']:.1f}% of samples")
            
            return True
        except Exception as e:
            print(f"\u26a0\ufe0f HMM training on synthetic data failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def compare_single_symbol(self, symbol: str = "BTC/USD", 
                            account_cash: float = 10000) -> Dict[str, Any]:
        """Compare strategies on a single symbol"""
        print(f"\n{'='*60}")
        print(f"COMPARING STRATEGIES FOR {symbol}")
        print(f"{'='*60}")
        
        # Get market data
        df = self.fetch_market_data(symbol, limit=150)
        if df.empty:
            return {}
        
        # Test 1: Pure Algorithmic
        print("\n1. PURE ALGORITHMIC STRATEGY:")
        print("-" * 40)
        
        pure_result = self.base_strategy.analyze_market(df, account_cash)
        
        print(f"   Signal: {pure_result['signal'].upper()}")
        print(f"   Confidence: {pure_result['confidence']:.2f}")
        print(f"   Reasons: {', '.join(pure_result['reasons'][:2])}...")
        
        if pure_result['signal'] != 'hold':
            pos_info = pure_result.get('position_size', {})
            print(f"   Position: {pos_info.get('quantity', 0):.6f} units")
            print(f"   Value: ${pos_info.get('position_value', 0):.2f}")
            print(f"   Stop Loss: ${pos_info.get('stop_loss', 0):.2f}")
        
        # Test 2: HMM-Regime-Aware
        print("\n2. HMM-REGIME-AWARE STRATEGY:")
        print("-" * 40)
        
        # Train HMM if not already trained
        if not hasattr(self.hmm_detector, 'is_fitted') or not self.hmm_detector.is_fitted:
            # Use current data for training (in production, use separate training data)
            try:
                # Extract features and fit
                X = self.hmm_detector.extract_features(df)
                self.hmm_detector.fit_from_features(X)
                print("   ✅ HMM trained on current data")
            except Exception as e:
                print(f"   ⚠️ HMM training failed: {e}")
        
        if hasattr(self.hmm_detector, 'is_fitted') and self.hmm_detector.is_fitted:
            # Get regime prediction
            try:
                regime_id, confidence, regime_info = self.hmm_detector.predict_regime(df)
                print(f"   Current Regime: {regime_info['regime_name']}")
                print(f"   Regime Confidence: {confidence:.2f}")
                print(f"   Expected Duration: {regime_info['expected_duration']:.1f} periods")
                
                # Get regime trading rules
                regime_rules = self.hmm_detector.get_regime_trading_rules(regime_id)
                print(f"   Position Size Multiplier: {regime_rules['position_size_multiplier']:.1f}x")
                print(f"   Confidence Boost: {regime_rules['confidence_boost']:+.2f}")
                
            except Exception as e:
                print(f"   ⚠️ Regime prediction failed: {e}")
        
        # Get regime-aware analysis
        hmm_result = self.regime_aware_strategy.analyze_market_with_regime(df, account_cash)
        
        print(f"   Signal: {hmm_result['signal'].upper()}")
        print(f"   Confidence: {hmm_result['confidence']:.2f}")
        
        if hmm_result.get('regime_aware'):
            print(f"   Regime-Aware: ✅")
            regime_name = hmm_result['regime_info']['regime_name']
            print(f"   Regime: {regime_name}")
            
            # Show adjustments
            if hmm_result['signal'] != 'hold':
                pos_info = hmm_result.get('position_size', {})
                pure_pos = pure_result.get('position_size', {})
                
                if pure_pos and pos_info:
                    qty_change = (pos_info.get('quantity', 0) / pure_pos.get('quantity', 1)) - 1
                    confidence_change = hmm_result['confidence'] - pure_result['confidence']
                    
                    print(f"   Quantity Change: {qty_change:+.1%}")
                    print(f"   Confidence Change: {confidence_change:+.2f}")
        else:
            print(f"   Regime-Aware: ⚠️ (using base strategy)")
        
        if hmm_result['signal'] != 'hold':
            pos_info = hmm_result.get('position_size', {})
            print(f"   Position: {pos_info.get('quantity', 0):.6f} units")
            print(f"   Value: ${pos_info.get('position_value', 0):.2f}")
            print(f"   Stop Loss: ${pos_info.get('stop_loss', 0):.2f}")
        
        # Compare signals
        print("\n3. COMPARISON:")
        print("-" * 40)
        
        signal_same = pure_result['signal'] == hmm_result['signal']
        confidence_diff = hmm_result['confidence'] - pure_result['confidence']
        
        print(f"   Signals match: {'✅' if signal_same else '⚠️'}")
        print(f"   Confidence difference: {confidence_diff:+.2f}")
        
        if not signal_same:
            print(f"   ⚠️ Signal divergence!")
            print(f"     Pure: {pure_result['signal']}")
            print(f"     HMM: {hmm_result['signal']}")
        
        # Store results
        comparison_result = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'pure_algorithmic': {
                'signal': pure_result['signal'],
                'confidence': pure_result['confidence'],
                'position_size': pure_result.get('position_size', {}),
                'reasons': pure_result.get('reasons', [])[:3],
            },
            'hmm_regime_aware': {
                'signal': hmm_result['signal'],
                'confidence': hmm_result['confidence'],
                'regime_aware': hmm_result.get('regime_aware', False),
                'regime_info': hmm_result.get('regime_info', {}),
                'position_size': hmm_result.get('position_size', {}),
            },
            'comparison': {
                'signals_match': signal_same,
                'confidence_diff': confidence_diff,
                'signal_divergence': not signal_same,
            }
        }
        
        self.results['pure_algorithmic'].append(pure_result)
        self.results['hmm_regime_aware'].append(hmm_result)
        
        return comparison_result
    
    def compare_multiple_symbols(self, symbols: List[str] = None, 
                               account_cash: float = 10000):
        """Compare strategies across multiple symbols"""
        if symbols is None:
            from config import CRYPTO_SYMBOLS
            symbols = CRYPTO_SYMBOLS[:5]  # Test first 5 symbols
        
        print(f"\n{'='*60}")
        print(f"COMPARING STRATEGIES ACROSS {len(symbols)} SYMBOLS")
        print(f"{'='*60}")
        
        comparisons = []
        
        for symbol in symbols:
            try:
                comparison = self.compare_single_symbol(symbol, account_cash)
                if comparison:
                    comparisons.append(comparison)
                
                # Small delay to avoid rate limits
                import time
                time.sleep(1)
                
            except Exception as e:
                print(f"⚠️ Error comparing {symbol}: {e}")
                continue
        
        # Analyze results
        self._analyze_comparisons(comparisons)
        
        return comparisons
    
    def _analyze_comparisons(self, comparisons: List[Dict[str, Any]]):
        """Analyze comparison results"""
        if not comparisons:
            print("No valid comparisons to analyze")
            return
        
        print(f"\n{'='*60}")
        print("ANALYSIS SUMMARY")
        print(f"{'='*60}")
        
        # Count signals
        pure_signals = {'buy': 0, 'sell': 0, 'hold': 0}
        hmm_signals = {'buy': 0, 'sell': 0, 'hold': 0}
        agreements = 0
        total = len(comparisons)
        
        for comp in comparisons:
            pure_signal = comp['pure_algorithmic']['signal']
            hmm_signal = comp['hmm_regime_aware']['signal']
            
            pure_signals[pure_signal] += 1
            hmm_signals[hmm_signal] += 1
            
            if pure_signal == hmm_signal:
                agreements += 1
        
        print(f"\nSignal Distribution:")
        print(f"  Pure Algorithmic: Buy={pure_signals['buy']}, Sell={pure_signals['sell']}, Hold={pure_signals['hold']}")
        print(f"  HMM-Regime-Aware: Buy={hmm_signals['buy']}, Sell={hmm_signals['sell']}, Hold={hmm_signals['hold']}")
        
        agreement_rate = agreements / total * 100
        print(f"\nAgreement Rate: {agreement_rate:.1f}% ({agreements}/{total} symbols)")
        
        # Calculate average confidence
        pure_confidences = [c['pure_algorithmic']['confidence'] for c in comparisons]
        hmm_confidences = [c['hmm_regime_aware']['confidence'] for c in comparisons]
        
        if pure_confidences and hmm_confidences:
            avg_pure_conf = np.mean(pure_confidences)
            avg_hmm_conf = np.mean(hmm_confidences)
            conf_diff = avg_hmm_conf - avg_pure_conf
            
            print(f"\nAverage Confidence:")
            print(f"  Pure Algorithmic: {avg_pure_conf:.2f}")
            print(f"  HMM-Regime-Aware: {avg_hmm_conf:.2f}")
            print(f"  Difference: {conf_diff:+.2f}")
        
        # Identify divergences
        divergences = []
        for comp in comparisons:
            if comp['comparison']['signal_divergence']:
                divergences.append({
                    'symbol': comp['symbol'],
                    'pure': comp['pure_algorithmic']['signal'],
                    'hmm': comp['hmm_regime_aware']['signal'],
                    'pure_conf': comp['pure_algorithmic']['confidence'],
                    'hmm_conf': comp['hmm_regime_aware']['confidence'],
                })
        
        if divergences:
            print(f"\n⚠️ Signal Divergences ({len(divergences)} symbols):")
            for div in divergences:
                print(f"  {div['symbol']}: Pure={div['pure']}({div['pure_conf']:.2f}) "
                      f"vs HMM={div['hmm']}({div['hmm_conf']:.2f})")
        
        # Save results
        self.save_results(comparisons)
    
    def save_results(self, comparisons: List[Dict[str, Any]]):
        """Save comparison results to file"""
        import os
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"data/strategy_comparison_{timestamp}.json"
        
        os.makedirs("data", exist_ok=True)
        
        results_data = {
            'timestamp': datetime.now().isoformat(),
            'total_symbols': len(comparisons),
            'comparisons': comparisons,
            'summary': self._create_summary(comparisons)
        }
        
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        print(f"\n✅ Results saved to: {filename}")
    
    def _create_summary(self, comparisons: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create summary statistics"""
        if not comparisons:
            return {}
        
        pure_buy = sum(1 for c in comparisons if c['pure_algorithmic']['signal'] == 'buy')
        pure_sell = sum(1 for c in comparisons if c['pure_algorithmic']['signal'] == 'sell')
        pure_hold = sum(1 for c in comparisons if c['pure_algorithmic']['signal'] == 'hold')
        
        hmm_buy = sum(1 for c in comparisons if c['hmm_regime_aware']['signal'] == 'buy')
        hmm_sell = sum(1 for c in comparisons if c['hmm_regime_aware']['signal'] == 'sell')
        hmm_hold = sum(1 for c in comparisons if c['hmm_regime_aware']['signal'] == 'hold')
        
        agreements = sum(1 for c in comparisons if c['comparison']['signals_match'])
        
        return {
            'pure_algorithmic': {'buy': pure_buy, 'sell': pure_sell, 'hold': pure_hold},
            'hmm_regime_aware': {'buy': hmm_buy, 'sell': hmm_sell, 'hold': hmm_hold},
            'agreements': agreements,
            'agreement_rate': agreements / len(comparisons) * 100,
            'regime_aware_count': sum(1 for c in comparisons if c['hmm_regime_aware'].get('regime_aware', False))
        }
    
    def plot_comparison(self, comparisons: List[Dict[str, Any]]):
        """Create visualization of comparison results"""
        if not comparisons:
            print("No data to plot")
            return
        
        try:
            # Prepare data
            symbols = [c['symbol'] for c in comparisons]
            pure_conf = [c['pure_algorithmic']['confidence'] for c in comparisons]
            hmm_conf = [c['hmm_regime_aware']['confidence'] for c in comparisons]
            
            # Create figure
            fig, axes = plt.subplots(2, 2, figsize=(14, 10))
            
            # Plot 1: Confidence comparison
            x = np.arange(len(symbols))
            width = 0.35
            
            axes[0, 0].bar(x - width/2, pure_conf, width, label='Pure Algorithmic', alpha=0.8)
            axes[0, 0].bar(x + width/2, hmm_conf, width, label='HMM-Regime-Aware', alpha=0.8)
            axes[0, 0].set_xlabel('Symbol')
            axes[0, 0].set_ylabel('Confidence')
            axes[0, 0].set_title('Strategy Confidence Comparison')
            axes[0, 0].set_xticks(x)
            axes[0, 0].set_xticklabels(symbols, rotation=45, ha='right')
            axes[0, 0].legend()
            axes[0, 0].grid(True, alpha=0.3)
            
            # Plot 2: Signal distribution
            signal_data = {
                'Pure': {
                    'buy': sum(1 for c in comparisons if c['pure_algorithmic']['signal'] == 'buy'),
                    'sell': sum(1 for c in comparisons if c['pure_algorithmic']['signal'] == 'sell'),
                    'hold': sum(1 for c in comparisons if c['pure_algorithmic']['signal'] == 'hold'),
                },
                'HMM': {
                    'buy': sum(1 for c in comparisons if c['hmm_regime_aware']['signal'] == 'buy'),
                    'sell': sum(1 for c in comparisons if c['hmm_regime_aware']['signal'] == 'sell'),
                    'hold': sum(1 for c in comparisons if c['hmm_regime_aware']['signal'] == 'hold'),
                }
            }
            
            x = ['Buy', 'Sell', 'Hold']
            pure_counts = [signal_data['Pure']['buy'], signal_data['Pure']['sell'], signal_data['Pure']['hold']]
            hmm_counts = [signal_data['HMM']['buy'], signal_data['HMM']['sell'], signal_data['HMM']['hold']]
            
            axes[0, 1].bar(x, pure_counts, alpha=0.8, label='Pure')
            axes[0, 1].bar(x, hmm_counts, alpha=0.5, label='HMM')
            axes[0, 1].set_ylabel('Count')
            axes[0, 1].set_title('Signal Distribution')
            axes[0, 1].legend()
            axes[0, 1].grid(True, alpha=0.3)
            
            # Plot 3: Confidence difference histogram
            conf_diff = [c['hmm_regime_aware']['confidence'] - c['pure_algorithmic']['confidence'] 
                        for c in comparisons]
            
            axes[1, 0].hist(conf_diff, bins=10, alpha=0.7, edgecolor='black')
            axes[1, 0].axvline(x=0, color='red', linestyle='--', alpha=0.5)
            axes[1, 0].set_xlabel('Confidence Difference (HMM - Pure)')
            axes[1, 0].set_ylabel('Frequency')
            axes[1, 0].set_title('Confidence Difference Distribution')
            axes[1, 0].grid(True, alpha=0.3)
            
            # Plot 4: Agreement rate
            agreement_rate = sum(1 for c in comparisons if c['comparison']['signals_match']) / len(comparisons) * 100
            disagreement_rate = 100 - agreement_rate
            
            axes[1, 1].pie([agreement_rate, disagreement_rate], 
                          labels=['Agreement', 'Disagreement'],
                          autopct='%1.1f%%',
                          startangle=90,
                          colors=['#2ecc71', '#e74c3c'])
            axes[1, 1].set_title(f'Signal Agreement: {agreement_rate:.1f}%')
            
            plt.tight_layout()
            
            # Save figure
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"data/comparison_plot_{timestamp}.png"
            plt.savefig(filename, dpi=150, bbox_inches='tight')
            plt.show()
            
            print(f"✅ Plot saved to: {filename}")
            
        except Exception as e:
            print(f"⚠️ Plotting failed: {e}")


def main():
    """Main comparison function"""
    print("CRYPTO TRADING STRATEGY COMPARISON")
    print("=" * 60)
    print("Comparing: Pure Algorithmic vs HMM-Regime-Aware")
    print("=" * 60)
    
    # Initialize comparison
    comparison = StrategyComparison()
    
    # Test with a single symbol first
    print("\nTesting with BTC/USD...")
    btc_comparison = comparison.compare_single_symbol("BTC/USD", account_cash=10000)
    
    if not btc_comparison:
        print("Failed to compare BTC/USD")
        return
    
    # Test with multiple symbols
    print("\n" + "=" * 60)
    print("Now testing with multiple symbols...")
    
    # Use major cryptos
    test_symbols = ["BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "XRP/USD"]
    
    comparisons = comparison.compare_multiple_symbols(
        symbols=test_symbols,
        account_cash=10000
    )
    
    # Create visualization
    print("\n" + "=" * 60)
    print("Generating visualization...")
    
    try:
        comparison.plot_comparison(comparisons)
    except Exception as e:
        print(f"Visualization failed: {e}")
        print("(Make sure matplotlib is installed: pip install matplotlib)")
    
    # Final recommendations
    print("\n" + "=" * 60)
    print("RECOMMENDATIONS")
    print("=" * 60)
    
    if comparisons:
        # Analyze which strategy is more decisive
        pure_decisions = sum(1 for c in comparisons if c['pure_algorithmic']['signal'] != 'hold')
        hmm_decisions = sum(1 for c in comparisons if c['hmm_regime_aware']['signal'] != 'hold')
        
        print(f"Pure Algorithmic decisions: {pure_decisions}/{len(comparisons)}")
        print(f"HMM-Regime-Aware decisions: {hmm_decisions}/{len(comparisons)}")
        
        if hmm_decisions > pure_decisions:
            print("✅ HMM-Regime-Aware is more decisive")
        elif pure_decisions > hmm_decisions:
            print("✅ Pure Algorithmic is more decisive")
        else:
            print("✅ Both strategies equally decisive")
        
        # Check average confidence
        pure_avg_conf = np.mean([c['pure_algorithmic']['confidence'] for c in comparisons])
        hmm_avg_conf = np.mean([c['hmm_regime_aware']['confidence'] for c in comparisons])
        
        print(f"\nAverage Confidence:")
        print(f"  Pure Algorithmic: {pure_avg_conf:.2f}")
        print(f"  HMM-Regime-Aware: {hmm_avg_conf:.2f}")
        
        if hmm_avg_conf > pure_avg_conf:
            print("✅ HMM-Regime-Aware has higher confidence")
        else:
            print("✅ Pure Algorithmic has higher confidence")
        
        print("\nSuggested approach:")
        print("1. Start with Pure Algorithmic for simplicity")
        print("2. Add HMM-Regime-Aware as enhancement once profitable")
        print("3. Use regime detection to adjust position sizing and stops")
    
    print("\n" + "=" * 60)
    print("Comparison complete!")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nComparison interrupted by user")
    except Exception as e:
        print(f"\nError in comparison: {e}")
        import traceback
        traceback.print_exc()