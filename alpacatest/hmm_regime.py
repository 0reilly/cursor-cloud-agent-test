"""
Hidden Markov Model for Crypto Market Regime Detection
Inspired by quantitative approaches like Medallion Fund
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
import logging
from dataclasses import dataclass
from hmmlearn import hmm
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)


@dataclass
class MarketRegime:
    """Market regime classification"""
    name: str
    id: int
    description: str
    characteristics: Dict[str, float]
    trading_rules: Dict[str, str]
    

class CryptoHMMRegimeDetector:
    """
    Hidden Markov Model for detecting crypto market regimes
    Based on approach used by quantitative funds for regime-aware trading
    """
    
    # Define market regimes (inspired by Medallion's approach)
    REGIMES = [
        MarketRegime(
            id=0,
            name="STRONG_BULL",
            description="Strong uptrend, high momentum, low volatility",
            characteristics={
                "trend_strength": 0.8,
                "volatility": 0.3,
                "momentum": 0.9,
                "mean_reversion": 0.1
            },
            trading_rules={
                "position_size": "max_allowed",
                "stop_loss": "wide",
                "take_profit": "let_run",
                "entry_aggression": "aggressive"
            }
        ),
        MarketRegime(
            id=1,
            name="WEAK_BULL",
            description="Moderate uptrend, medium volatility",
            characteristics={
                "trend_strength": 0.6,
                "volatility": 0.5,
                "momentum": 0.7,
                "mean_reversion": 0.3
            },
            trading_rules={
                "position_size": "moderate",
                "stop_loss": "medium",
                "take_profit": "balanced",
                "entry_aggression": "moderate"
            }
        ),
        MarketRegime(
            id=2,
            name="SIDEWAYS",
            description="Range-bound, mean-reverting, choppy",
            characteristics={
                "trend_strength": 0.2,
                "volatility": 0.4,
                "momentum": 0.3,
                "mean_reversion": 0.9
            },
            trading_rules={
                "position_size": "small",
                "stop_loss": "tight",
                "take_profit": "quick",
                "entry_aggression": "conservative"
            }
        ),
        MarketRegime(
            id=3,
            name="WEAK_BEAR",
            description="Moderate downtrend, selling pressure",
            characteristics={
                "trend_strength": -0.6,
                "volatility": 0.7,
                "momentum": -0.7,
                "mean_reversion": 0.4
            },
            trading_rules={
                "position_size": "small_short",
                "stop_loss": "tight",
                "take_profit": "quick",
                "entry_aggression": "conservative"
            }
        ),
        MarketRegime(
            id=4,
            name="STRONG_BEAR",
            description="Strong downtrend, panic selling, high volatility",
            characteristics={
                "trend_strength": -0.9,
                "volatility": 0.9,
                "momentum": -0.9,
                "mean_reversion": 0.1
            },
            trading_rules={
                "position_size": "max_short",
                "stop_loss": "wide",
                "take_profit": "let_run_short",
                "entry_aggression": "aggressive"
            }
        ),
    ]
    
    def __init__(self, n_regimes: int = 5, n_features: int = 4):
        """
        Initialize HMM regime detector
        
        Args:
            n_regimes: Number of hidden states (regimes) to detect
            n_features: Number of feature dimensions
        """
        self.n_regimes = n_regimes
        self.n_features = n_features
        
        # Initialize Gaussian HMM
        self.model = hmm.GaussianHMM(
            n_components=n_regimes,
            covariance_type="diag",  # Diagonal covariance for simplicity
            n_iter=100,
            random_state=42,
            verbose=False
        )
        
        # Model state
        self.is_fitted = False
        self.regime_transition_matrix = None
        self.regime_means = None
        self.regime_covars = None
        
        logger.info(f"HMM Regime Detector initialized with {n_regimes} regimes")
    
    def extract_features(self, df: pd.DataFrame) -> np.ndarray:
        """
        Extract features for HMM from price data
        Features inspired by quantitative hedge fund approaches
        """
        if len(df) < 30:
            raise ValueError("Need at least 30 data points for feature extraction")
        
        features = []
        
        # Adaptive window sizes based on available data
        data_len = len(df)
        vol_window = min(20, max(5, data_len // 3))
        mom_window = min(10, max(3, data_len // 6))
        feature_len = min(30, max(15, data_len // 2))
        
        # 1. Normalized returns (z-scored)
        returns = df['close'].pct_change().dropna()
        if len(returns) > 0:
            norm_returns = (returns - returns.mean()) / (returns.std() + 1e-8)
            # Take available data, up to feature_len
            take_len = min(feature_len, len(norm_returns))
            features.append(norm_returns.values[-take_len:])
        
        # 2. Rolling volatility (adaptive window)
        volatility = returns.rolling(window=vol_window).std().dropna()
        if len(volatility) > 0:
            norm_vol = (volatility - volatility.mean()) / (volatility.std() + 1e-8)
            take_len = min(feature_len, len(norm_vol))
            features.append(norm_vol.values[-take_len:])
        
        # 3. Rolling momentum (adaptive window)
        momentum = df['close'].pct_change(mom_window).dropna()
        if len(momentum) > 0:
            norm_momentum = (momentum - momentum.mean()) / (momentum.std() + 1e-8)
            take_len = min(feature_len, len(norm_momentum))
            features.append(norm_momentum.values[-take_len:])
        
        # 4. Volume anomaly (volume vs adaptive-period MA)
        if 'volume' in df.columns:
            volume_ma = df['volume'].rolling(window=vol_window).mean()
            volume_ratio = df['volume'] / (volume_ma + 1e-8)
            norm_volume = (volume_ratio - volume_ratio.mean()) / (volume_ratio.std() + 1e-8)
            take_len = min(feature_len, len(norm_volume.dropna()))
            features.append(norm_volume.dropna().values[-take_len:])
        
        # 5. RSI normalized (optional)
        if 'rsi' in df.columns:
            rsi = df['rsi'].dropna()
            if len(rsi) > 0:
                # RSI is already 0-100, normalize to -1 to 1
                norm_rsi = (rsi - 50) / 50
                take_len = min(feature_len, len(norm_rsi))
                features.append(norm_rsi.values[-take_len:])
        
        # Pad or truncate to consistent length
        min_length = min(len(f) for f in features) if features else 0
        if min_length < 10:
            raise ValueError(f"Insufficient feature data: {min_length} points (need at least 10)")
        
        # Take last min_length points for consistency (at least 10)
        take_len = min(15, min_length)  # Use smaller consistent length for small datasets
        feature_array = np.array([f[-take_len:] for f in features]).T
        return feature_array
    
    def fit(self, df: pd.DataFrame):
        """
        Fit HMM to historical data
        """
        logger.info("Fitting HMM to historical data...")
        
        # Extract features
        X = self.extract_features(df)
        
        # Fit HMM
        self.model.fit(X)
        self.is_fitted = True
        
        # Extract model parameters
        self.regime_transition_matrix = self.model.transmat_
        self.regime_means = self.model.means_
        self.regime_covars = self.model.covars_
        
        logger.info(f"HMM fitted successfully. Regime transition matrix shape: {self.regime_transition_matrix.shape}")
        
        # Analyze regime characteristics
        self._analyze_regimes(X)
        
        return self

    def fit_from_features(self, X: np.ndarray, y: Optional[np.ndarray] = None):
        """
        Fit HMM directly from pre-extracted feature matrix
        
        Args:
            X: Feature matrix of shape (n_samples, n_features)
            y: Optional labels (not used for HMM)
        """
        logger.info("Fitting HMM from pre-extracted features...")
        
        # Validate shape
        if X.shape[1] != self.n_features:
            raise ValueError(
                f"Expected {self.n_features} features, got {X.shape[1]}. "
                "Initialize detector with matching n_features."
            )
        
        # Fit HMM
        self.model.fit(X)
        self.is_fitted = True
        
        # Extract model parameters
        self.regime_transition_matrix = self.model.transmat_
        self.regime_means = self.model.means_
        self.regime_covars = self.model.covars_
        
        logger.info(f"HMM fitted successfully. Regime transition matrix shape: {self.regime_transition_matrix.shape}")
        
        # Analyze regime characteristics
        self._analyze_regimes(X)
        
        return self
    
    def _analyze_regimes(self, X: np.ndarray):
        """Analyze and label learned regimes"""
        # Predict regimes for training data
        regime_predictions = self.model.predict(X)
        
        # Calculate statistics for each regime
        self.regime_stats = {}
        
        for regime_id in range(self.n_regimes):
            regime_mask = regime_predictions == regime_id
            if np.sum(regime_mask) > 0:
                regime_data = X[regime_mask]
                
                stats = {
                    'count': np.sum(regime_mask),
                    'percentage': np.sum(regime_mask) / len(X) * 100,
                    'mean_returns': np.mean(regime_data[:, 0]) if regime_data.shape[1] > 0 else 0,
                    'mean_volatility': np.mean(regime_data[:, 1]) if regime_data.shape[1] > 1 else 0,
                    'mean_momentum': np.mean(regime_data[:, 2]) if regime_data.shape[1] > 2 else 0,
                    'stability': self.regime_transition_matrix[regime_id, regime_id],  # Self-transition probability
                }
                
                self.regime_stats[regime_id] = stats
        
        logger.info("Regime analysis completed")
    
    def predict_regime(self, df: pd.DataFrame) -> Tuple[int, float, Dict[str, float]]:
        """
        Predict current market regime
        
        Returns:
            regime_id: Predicted regime (0 to n_regimes-1)
            confidence: Prediction confidence (0-1)
            regime_probs: Probability distribution over all regimes
        """
        if not self.is_fitted:
            raise ValueError("HMM must be fitted before prediction")
        
        # Extract features for latest data
        X = self.extract_features(df)
        
        # Get most recent observation
        latest_observation = X[-1:].reshape(1, -1)
        
        # Predict regime and get probabilities
        regime_probs = self.model.predict_proba(latest_observation)[0]
        regime_id = np.argmax(regime_probs)
        confidence = regime_probs[regime_id]
        
        # Create regime info
        regime_info = {
            'regime_id': int(regime_id),
            'regime_name': self._interpret_regime(regime_id, latest_observation[0]),
            'confidence': float(confidence),
            'probabilities': {f'regime_{i}': float(p) for i, p in enumerate(regime_probs)},
            'expected_duration': 1 / (1 - self.regime_transition_matrix[regime_id, regime_id])
        }
        
        return regime_id, confidence, regime_info
    
    def _interpret_regime(self, regime_id: int, observation: np.ndarray) -> str:
        """
        Interpret regime based on observation characteristics
        """
        if regime_id < len(self.REGIMES):
            return self.REGIMES[regime_id].name
        
        # Dynamically interpret based on observation
        # observation: [norm_returns, norm_vol, norm_momentum, norm_volume, ...]
        
        if len(observation) >= 3:
            norm_returns = observation[0]
            norm_vol = observation[1]
            norm_momentum = observation[2]
            
            if norm_momentum > 0.5 and norm_vol < 0.3:
                return "STRONG_BULL"
            elif norm_momentum > 0.2:
                return "WEAK_BULL"
            elif abs(norm_momentum) < 0.2:
                return "SIDEWAYS"
            elif norm_momentum < -0.2 and norm_vol < 0.5:
                return "WEAK_BEAR"
            elif norm_momentum < -0.5:
                return "STRONG_BEAR"
        
        return f"REGIME_{regime_id}"
    
    def get_regime_trading_rules(self, regime_id: int) -> Dict[str, float]:
        """
        Get trading rules for a specific regime
        
        Returns adjustments to base strategy parameters
        """
        base_rules = {
            'position_size_multiplier': 1.0,
            'stop_loss_multiplier': 1.0,
            'take_profit_multiplier': 1.0,
            'confidence_boost': 0.0,
            'volatility_adjustment': 1.0,
        }
        
        if regime_id < len(self.REGIMES):
            regime = self.REGIMES[regime_id]
            
            if regime.name == "STRONG_BULL":
                return {
                    **base_rules,
                    'position_size_multiplier': 1.5,
                    'stop_loss_multiplier': 1.5,  # Wider stops in strong trends
                    'take_profit_multiplier': 2.0,  # Let profits run
                    'confidence_boost': 0.2,
                    'volatility_adjustment': 0.8,  # Less sensitive to volatility
                }
            elif regime.name == "WEAK_BULL":
                return {
                    **base_rules,
                    'position_size_multiplier': 1.2,
                    'stop_loss_multiplier': 1.0,
                    'take_profit_multiplier': 1.5,
                    'confidence_boost': 0.1,
                }
            elif regime.name == "SIDEWAYS":
                return {
                    **base_rules,
                    'position_size_multiplier': 0.7,
                    'stop_loss_multiplier': 0.7,  # Tighter stops in ranges
                    'take_profit_multiplier': 0.8,  # Take profits quickly
                    'confidence_boost': -0.1,
                    'volatility_adjustment': 1.2,  # More sensitive to volatility
                }
            elif regime.name == "WEAK_BEAR":
                return {
                    **base_rules,
                    'position_size_multiplier': 0.8,
                    'stop_loss_multiplier': 0.8,
                    'take_profit_multiplier': 1.0,
                    'confidence_boost': -0.1,
                }
            elif regime.name == "STRONG_BEAR":
                return {
                    **base_rules,
                    'position_size_multiplier': 1.3,  # Larger for shorting
                    'stop_loss_multiplier': 1.5,
                    'take_profit_multiplier': 2.0,
                    'confidence_boost': 0.2,
                    'volatility_adjustment': 0.8,
                }
        
        return base_rules
    
    def forecast_regime_transitions(self, n_steps: int = 5) -> np.ndarray:
        """
        Forecast regime probabilities n steps ahead
        """
        if not self.is_fitted:
            raise ValueError("HMM must be fitted before forecasting")
        
        # Start with current state distribution (assume last known)
        current_probs = np.ones(self.n_regimes) / self.n_regimes
        
        # Forecast forward
        forecast = [current_probs]
        for _ in range(n_steps):
            next_probs = forecast[-1] @ self.regime_transition_matrix
            forecast.append(next_probs)
        
        return np.array(forecast)
    
    def get_regime_summary(self) -> Dict[str, Any]:
        """Get summary of learned regimes"""
        if not hasattr(self, 'regime_stats'):
            return {}
        
        summary = {}
        for regime_id, stats in self.regime_stats.items():
            regime_name = self._interpret_regime(regime_id, np.zeros(self.n_features))
            trading_rules = self.get_regime_trading_rules(regime_id)
            
            summary[f"regime_{regime_id}"] = {
                'name': regime_name,
                'stats': stats,
                'trading_rules': trading_rules,
                'transition_probability': float(self.regime_transition_matrix[regime_id, regime_id]),
            }
        
        return summary


# ============ INTEGRATION WITH EXISTING STRATEGY ============

class RegimeAwareCryptoStrategy:
    """
    Wrapper that adds regime awareness to existing CryptoMomentumStrategy
    """
    
    def __init__(self, base_strategy, hmm_detector: Optional[CryptoHMMRegimeDetector] = None):
        self.base_strategy = base_strategy
        self.hmm_detector = hmm_detector or CryptoHMMRegimeDetector()
        self.regime_history = []
        
    def analyze_market_with_regime(self, df: pd.DataFrame, account_cash: float) -> Dict[str, Any]:
        """
        Analyze market with regime awareness
        """
        # Get base analysis
        base_analysis = self.base_strategy.analyze_market(df, account_cash)
        
        # If HMM not fitted or insufficient data, return base analysis
        if not self.hmm_detector.is_fitted or len(df) < 30:
            base_analysis['regime_aware'] = False
            return base_analysis
        
        try:
            # Predict current regime
            regime_id, confidence, regime_info = self.hmm_detector.predict_regime(df)
            
            # Get regime trading rules
            regime_rules = self.hmm_detector.get_regime_trading_rules(regime_id)
            
            # Adjust base analysis based on regime
            adjusted_analysis = self._adjust_for_regime(base_analysis, regime_rules, regime_info)
            
            # Store regime history
            self.regime_history.append({
                'timestamp': pd.Timestamp.now(),
                'regime_id': regime_id,
                'regime_name': regime_info['regime_name'],
                'confidence': confidence,
                'signal': adjusted_analysis['signal'],
                'base_signal': base_analysis['signal'],
            })
            
            return adjusted_analysis
            
        except Exception as e:
            logger.warning(f"Regime detection failed: {e}, using base analysis")
            base_analysis['regime_aware'] = False
            base_analysis['regime_error'] = str(e)
            return base_analysis
    
    def analyze_market(self, df: pd.DataFrame, account_cash: float) -> Dict[str, Any]:
        """
        Analyze market with regime awareness (compatibility wrapper).
        """
        return self.analyze_market_with_regime(df, account_cash)
    
    def _adjust_for_regime(self, base_analysis: Dict[str, Any], 
                          regime_rules: Dict[str, float],
                          regime_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adjust trading signals based on market regime
        """
        adjusted = base_analysis.copy()
        
        # Mark as regime-aware
        adjusted['regime_aware'] = True
        adjusted['regime_info'] = regime_info
        adjusted['regime_rules'] = regime_rules
        
        # Adjust confidence based on regime
        base_confidence = adjusted.get('confidence', 0.5)
        regime_confidence_boost = regime_rules.get('confidence_boost', 0.0)
        adjusted_confidence = base_confidence + regime_confidence_boost
        
        # Apply indicator confluence filter if available
        if 'indicators' in adjusted:
            indicator_score = self._calculate_indicator_score(adjusted['indicators'])
            # Multiply confidence by indicator score
            adjusted_confidence *= indicator_score
            # If indicator score is too low, consider holding
            if indicator_score < 0.4 and adjusted.get('signal') != 'hold':
                adjusted['signal'] = 'hold'
                adjusted['confidence'] = 0.1
                adjusted['reasons'].append(f"Low indicator confluence (score {indicator_score:.2f}) - holding")
        
        # Clamp to valid range
        adjusted_confidence = max(0.1, min(0.9, adjusted_confidence))
        adjusted['confidence'] = adjusted_confidence
        
        # Adjust position size in position metrics if present
        if 'position_size' in adjusted:
            position_metrics = adjusted['position_size'].copy()
            size_multiplier = regime_rules.get('position_size_multiplier', 1.0)
            
            # Adjust quantity and value
            position_metrics['quantity'] *= size_multiplier
            position_metrics['position_value'] *= size_multiplier
            position_metrics['position_pct'] *= size_multiplier
            
            # Adjust stop loss and take profit
            stop_multiplier = regime_rules.get('stop_loss_multiplier', 1.0)
            tp_multiplier = regime_rules.get('take_profit_multiplier', 1.0)
            
            current_price = position_metrics.get('current_price', 0)
            if current_price > 0:
                # Recalculate with adjusted multipliers
                from config import STOP_LOSS_PCT, TAKE_PROFIT_PCT
                position_metrics['stop_loss'] = current_price * (1 - STOP_LOSS_PCT * stop_multiplier)
                position_metrics['take_profit'] = current_price * (1 + TAKE_PROFIT_PCT * tp_multiplier)
            
            adjusted['position_size'] = position_metrics
        
        # Potentially flip signals in strong bear regimes
        # (e.g., be more aggressive with short signals)
        regime_name = regime_info.get('regime_name', '')
        if regime_name == "STRONG_BEAR":
            if adjusted['signal'] == 'buy':
                # In strong bear markets, avoid buying
                adjusted['signal'] = 'hold'
                adjusted['confidence'] = 0.1
                adjusted['reasons'].append("Strong bear regime - avoiding buy signals")
            elif adjusted['signal'] == 'sell':
                # Be more aggressive with shorting
                adjusted['confidence'] = min(0.9, adjusted['confidence'] * 1.3)
                adjusted['reasons'].append("Strong bear regime - increasing short confidence")
        
        elif regime_name == "STRONG_BULL":
            if adjusted['signal'] == 'sell':
                # In strong bull markets, avoid selling
                adjusted['signal'] = 'hold'
                adjusted['confidence'] = 0.1
                adjusted['reasons'].append("Strong bull regime - avoiding sell signals")
            elif adjusted['signal'] == 'buy':
                # Be more aggressive with buying
                adjusted['confidence'] = min(0.9, adjusted['confidence'] * 1.3)
                adjusted['reasons'].append("Strong bull regime - increasing buy confidence")
        
        return adjusted
    
    def _calculate_indicator_score(self, indicators: Dict[str, float]) -> float:
        """
        Calculate a score from 0 to 1 based on indicator confluence.
        Higher score means stronger signal confirmation.
        """
        score = 0.0
        total_weights = 0
        
        # RSI score (30-70 is neutral, extremes are stronger but may be overbought/oversold)
        rsi = indicators.get('rsi', 50)
        if 40 <= rsi <= 60:
            rsi_score = 0.5
        elif 30 <= rsi <= 70:
            rsi_score = 0.7
        else:
            rsi_score = 0.3  # Extreme values may be reversal signals
        score += rsi_score * 0.2
        total_weights += 0.2
        
        # MACD score (bullish if MACD > signal, bearish if MACD < signal)
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)
        macd_score = 0.5
        if macd > macd_signal:
            macd_score = 0.8
        elif macd < macd_signal:
            macd_score = 0.2
        score += macd_score * 0.2
        total_weights += 0.2
        
        # Bollinger Bands score (price near middle band is neutral, near edges is extreme)
        bb_percent = indicators.get('bb_percent', 0.5)
        bb_score = 1.0 - abs(bb_percent - 0.5) * 2  # 1 at middle, 0 at edges
        score += bb_score * 0.15
        total_weights += 0.15
        
        # Volume score (above average is good)
        volume_ratio = indicators.get('volume_ratio', 1.0)
        volume_score = min(1.0, volume_ratio)  # cap at 1.0
        score += volume_score * 0.15
        total_weights += 0.15
        
        # Trend score (price above SMA20)
        price = indicators.get('price', 0)
        sma_20 = indicators.get('sma_20', price)
        trend_score = 0.5
        if price > sma_20:
            trend_score = 0.8
        elif price < sma_20:
            trend_score = 0.2
        score += trend_score * 0.2
        total_weights += 0.2
        
        # Momentum score (positive momentum good)
        momentum_pct = indicators.get('momentum_pct', 0)
        momentum_score = 0.5 + momentum_pct * 10  # scale
        momentum_score = max(0.1, min(0.9, momentum_score))
        score += momentum_score * 0.1
        total_weights += 0.1
        
        if total_weights > 0:
            final_score = score / total_weights
        else:
            final_score = 0.5
            
        return final_score

    def train_hmm(self, historical_data: Dict[str, pd.DataFrame]):
        """
        Train HMM on historical data from multiple symbols
        """
        logger.info("Training HMM on historical data...")
        
        # Combine features from multiple symbols
        all_features = []
        
        for symbol, df in historical_data.items():
            try:
                features = self.hmm_detector.extract_features(df)
                all_features.append(features)
                logger.debug(f"Extracted features from {symbol}: {features.shape}")
            except Exception as e:
                logger.warning(f"Failed to extract features from {symbol}: {e}")
        
        if not all_features:
            raise ValueError("No valid features extracted from historical data")
        
        # Combine all features
        X = np.vstack(all_features)
        
        # Fit HMM
        self.hmm_detector.fit_from_features(X)
        
        logger.info(f"HMM trained on {len(X)} samples from {len(historical_data)} symbols")
        return self.hmm_detector


# ============ TEST FUNCTIONS ============

def test_hmm_detector():
    """Test the HMM regime detector"""
    print("Testing HMM Regime Detector...")
    
    try:
        # Check if hmmlearn is available
        import hmmlearn
        print("✅ hmmlearn available")
    except ImportError:
        print("❌ hmmlearn not installed. Install with: pip install hmmlearn")
        print("   For now, using mock implementation")
        return
    
    # Create sample data
    np.random.seed(42)
    dates = pd.date_range('2024-01-01', periods=500, freq='5min')
    
    # Simulate different regimes
    prices = []
    current_price = 100
    
    for i in range(500):
        # Create regime shifts
        if i < 100:
            # Strong bull
            current_price *= 1 + np.random.normal(0.001, 0.005)
        elif i < 200:
            # Sideways
            current_price *= 1 + np.random.normal(0.000, 0.01)
        elif i < 300:
            # Strong bear
            current_price *= 1 + np.random.normal(-0.001, 0.008)
        elif i < 400:
            # Weak bull
            current_price *= 1 + np.random.normal(0.0005, 0.006)
        else:
            # Weak bear
            current_price *= 1 + np.random.normal(-0.0005, 0.007)
        
        prices.append(current_price)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p * 1.01 for p in prices],
        'low': [p * 0.99 for p in prices],
        'close': prices,
        'volume': np.random.randn(500) * 1000 + 5000,
    })
    df.set_index('timestamp', inplace=True)
    
    # Test HMM
    detector = CryptoHMMRegimeDetector(n_regimes=5)
    detector.fit(df)
    
    # Test prediction
    regime_id, confidence, regime_info = detector.predict_regime(df)
    print(f"✅ Regime predicted: {regime_info['regime_name']} (ID: {regime_id})")
    print(f"   Confidence: {confidence:.2f}")
    print(f"   Expected duration: {regime_info['expected_duration']:.1f} periods")
    
    # Test regime rules
    rules = detector.get_regime_trading_rules(regime_id)
    print(f"✅ Trading rules for regime:")
    print(f"   Position size multiplier: {rules['position_size_multiplier']:.1f}")
    print(f"   Stop loss multiplier: {rules['stop_loss_multiplier']:.1f}")
    print(f"   Confidence boost: {rules['confidence_boost']:+.2f}")
    
    # Test summary
    summary = detector.get_regime_summary()
    print(f"✅ Learned {len(summary)} regimes")
    
    for regime_key, regime_data in summary.items():
        stats = regime_data['stats']
        print(f"   {regime_data['name']}: {stats['percentage']:.1f}% of time, "
              f"stability: {regime_data['transition_probability']:.2f}")
    
    # Test integration with strategy
    from strategy import CryptoMomentumStrategy
    base_strategy = CryptoMomentumStrategy()
    regime_aware_strategy = RegimeAwareCryptoStrategy(base_strategy, detector)
    
    analysis = regime_aware_strategy.analyze_market_with_regime(df.tail(100), 10000)
    print(f"✅ Regime-aware analysis: {analysis['signal']} signal")
    print(f"   Regime-aware: {analysis.get('regime_aware', False)}")
    if analysis.get('regime_aware'):
        print(f"   Regime: {analysis['regime_info']['regime_name']}")
        print(f"   Adjusted confidence: {analysis['confidence']:.2f}")
    
    print("\nHMM Regime Detector test completed successfully!")
    

if __name__ == "__main__":
    test_hmm_detector()