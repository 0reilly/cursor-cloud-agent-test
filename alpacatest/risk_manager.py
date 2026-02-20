"""
Risk Management Module for Crypto Trading
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple, Any
import json
import os

from config import (
    MAX_POSITIONS, MAX_POSITION_SIZE_PCT, MIN_POSITION_SIZE,
    MAX_DAILY_LOSS_PCT, MAX_TOTAL_LOSS_PCT, VOLATILITY_ADJUSTMENT,
    STOP_LOSS_PCT, TAKE_PROFIT_PCT, TRAILING_STOP_PCT,
    CRYPTO_SYMBOLS
)

logger = logging.getLogger(__name__)


class RiskManager:
    """Manages portfolio risk, position sizing, and trade validation"""
    
    def __init__(self, data_dir: str = "data", client=None):
        self.data_dir = data_dir
        self.risk_metrics_file = os.path.join(data_dir, "risk_metrics.json")
        self.trade_log_file = os.path.join(data_dir, "trades.csv")
        self.client = client  # Optional AlpacaClient
        
        # Load or initialize risk metrics
        self.risk_metrics = self._load_risk_metrics()
        
        # Risk limits state
        self.daily_pnl = 0.0
        self.total_pnl = 0.0
        self.max_daily_loss = 0.0
        self.max_total_loss = 0.0
        
        # Initialize from risk metrics
        self._update_risk_limits()
        
        logger.info("Risk Manager initialized")
    
    def _load_risk_metrics(self) -> Dict[str, Any]:
        """Load risk metrics from file or create default"""
        try:
            if os.path.exists(self.risk_metrics_file):
                with open(self.risk_metrics_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error loading risk metrics: {e}")
        
        # Default metrics
        return {
            'initial_capital': 0.0,
            'current_capital': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_pnl': 0.0,
            'daily_pnl': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'last_reset': datetime.now().isoformat(),
            'daily_resets': 0,
            'circuit_breaker_triggered': False
        }
    
    def _save_risk_metrics(self):
        """Save risk metrics to file"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            with open(self.risk_metrics_file, 'w') as f:
                json.dump(self.risk_metrics, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving risk metrics: {e}")
    
    def _update_risk_limits(self):
        """Update risk limits based on current capital"""
        current_capital = self.risk_metrics.get('current_capital', 0)
        if current_capital <= 0:
            current_capital = 50000  # Default if not set
        
        self.max_daily_loss = current_capital * MAX_DAILY_LOSS_PCT
        self.max_total_loss = current_capital * MAX_TOTAL_LOSS_PCT
    
    # ============ PORTFOLIO VALIDATION ============
    
    def _filter_active_positions(self, positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out positions where asset is not active/tradable"""
        if not positions or self.client is None:
            return positions
        
        active_positions = []
        for position in positions:
            symbol = position.get('symbol')
            if not symbol:
                continue
            # Convert symbol format if needed (e.g., BTCUSD -> BTC/USD)
            formatted_symbol = symbol.replace('USD', '/USD') if 'USD' in symbol and '/' not in symbol else symbol
            try:
                if self.client.is_asset_active(formatted_symbol):
                    active_positions.append(position)
                else:
                    logger.warning(f"Position {symbol} is inactive, excluding from risk calculations")
            except Exception as e:
                logger.warning(f"Error checking asset status for {symbol}: {e}")
                # Include by default to be conservative
                active_positions.append(position)
        
        return active_positions
    
    def validate_trade(self, symbol: str, qty: float, price: float, 
                      side: str, positions: List[Dict[str, Any]], 
                      account_cash: float) -> Tuple[bool, str]:
        """
        Validate a trade against risk rules
        
        Returns: (is_valid, reason)
        """
        reasons = []
        
        # 1. Check position count limit
        if len(positions) >= MAX_POSITIONS:
            return False, f"Max positions ({MAX_POSITIONS}) reached"
        
        # 2. Check position size limit
        position_value = qty * price
        position_pct = position_value / account_cash if account_cash > 0 else 0
        
        if position_pct > MAX_POSITION_SIZE_PCT:
            reasons.append(f"Position size {position_pct:.1%} > max {MAX_POSITION_SIZE_PCT:.1%}")
        
        if position_value < MIN_POSITION_SIZE:
            reasons.append(f"Position value ${position_value:.2f} < min ${MIN_POSITION_SIZE}")
        
        # 3. Check daily loss limit
        if self.daily_pnl <= -self.max_daily_loss:
            reasons.append(f"Daily loss limit reached: ${self.daily_pnl:.2f}")
        
        # 4. Check total loss limit
        if self.total_pnl <= -self.max_total_loss:
            reasons.append(f"Total loss limit reached: ${self.total_pnl:.2f}")
        
        # 5. Check if already have position in same symbol
        existing_position = next((p for p in positions if p['symbol'] == symbol), None)
        if existing_position:
            # Check if we're adding to position (same side)
            existing_side = existing_position['side']
            if existing_side == side:
                # Calculate new total position size
                new_qty = existing_position['qty'] + qty
                new_value = new_qty * price
                new_pct = new_value / account_cash if account_cash > 0 else 0
                
                if new_pct > MAX_POSITION_SIZE_PCT * 2:  # Allow doubling up
                    reasons.append(f"Adding to position would exceed size limit")
        
        # 6. Check circuit breaker
        if self.risk_metrics.get('circuit_breaker_triggered', False):
            return False, "Circuit breaker triggered - trading halted"
        
        if reasons:
            return False, "; ".join(reasons)
        
        return True, "Trade validated"
    
    def calculate_position_size(self, account_cash: float, current_price: float,
                              confidence: float, volatility: float, 
                              existing_positions: List[Dict[str, Any]]) -> Tuple[float, Dict[str, Any]]:
        """
        Calculate optimal position size with portfolio considerations
        """
        # Base position size (same as strategy calculation)
        base_size_pct = MAX_POSITION_SIZE_PCT * confidence
        
        # Adjust for volatility if enabled
        if VOLATILITY_ADJUSTMENT and volatility > 0:
            vol_adjustment = 1.0 / (1.0 + volatility * 5)
            base_size_pct *= vol_adjustment
        
        # Adjust for portfolio concentration
        if existing_positions:
            current_exposure = sum(p.get('market_value', 0) for p in existing_positions)
            exposure_pct = current_exposure / account_cash if account_cash > 0 else 0
            
            # Reduce new position if portfolio is already concentrated
            concentration_adjustment = max(0.1, 1.0 - exposure_pct * 2)
            base_size_pct *= concentration_adjustment
        
        # Calculate dollar amount
        position_value = account_cash * base_size_pct
        
        # Ensure minimum size
        if position_value < MIN_POSITION_SIZE:
            position_value = MIN_POSITION_SIZE
        
        # Calculate quantity
        quantity = position_value / current_price
        
        # Round to appropriate decimals for crypto (6-8 decimal places)
        quantity = round(quantity, 6)
        
        # Calculate stop loss and take profit levels
        stop_loss_price = current_price * (1 - STOP_LOSS_PCT)
        take_profit_price = current_price * (1 + TAKE_PROFIT_PCT)
        
        # Calculate position metrics
        position_metrics = {
            'quantity': quantity,
            'position_value': position_value,
            'position_pct': base_size_pct,
            'current_price': current_price,
            'stop_loss': stop_loss_price,
            'take_profit': take_profit_price,
            'trailing_stop': current_price * (1 - TRAILING_STOP_PCT),
            'risk_amount': position_value * STOP_LOSS_PCT,
            'reward_amount': position_value * TAKE_PROFIT_PCT,
            'risk_reward_ratio': TAKE_PROFIT_PCT / STOP_LOSS_PCT,
            'confidence': confidence,
            'volatility': volatility,
        }
        
        return quantity, position_metrics
    
    # ============ PORTFOLIO MONITORING ============
    
    def update_portfolio_risk(self, positions: List[Dict[str, Any]], 
                             account_value: float, daily_pnl: float) -> Dict[str, Any]:
        """
        Calculate portfolio-level risk metrics
        """
        if not positions:
            return {
                'portfolio_value': account_value,
                'num_positions': 0,
                'concentration': 0.0,
                'total_exposure': 0.0,
                'total_unrealized_pnl': 0.0,
                'max_position_pct': 0.0,
                'var_95': 0.0,
                'correlation_score': 0.0,
            }
        
        # Calculate basic metrics
        total_exposure = sum(p.get('market_value', 0) for p in positions)
        total_unrealized_pnl = sum(p.get('unrealized_pl', 0) for p in positions)
        
        # Calculate concentration (Herfindahl-Hirschman Index)
        position_values = [p.get('market_value', 0) for p in positions]
        if total_exposure > 0:
            concentration = sum((v / total_exposure) ** 2 for v in position_values)
        else:
            concentration = 0.0
        
        # Calculate max position percentage
        max_position_value = max(position_values) if position_values else 0
        max_position_pct = max_position_value / account_value if account_value > 0 else 0
        
        # Simple Value at Risk calculation (historical simulation)
        # For now, use a simplified approach
        var_95 = total_exposure * 0.05  # Assume 5% daily VaR for crypto
        
        # Calculate correlation score (simplified - assume crypto are highly correlated)
        correlation_score = 0.8  # Default high correlation for crypto
        
        # Update daily PnL tracking
        self.daily_pnl = daily_pnl
        self.total_pnl = self.risk_metrics.get('total_pnl', 0) + daily_pnl
        
        return {
            'portfolio_value': account_value,
            'num_positions': len(positions),
            'concentration': concentration,
            'total_exposure': total_exposure,
            'total_unrealized_pnl': total_unrealized_pnl,
            'max_position_pct': max_position_pct,
            'var_95': var_95,
            'correlation_score': correlation_score,
            'daily_pnl': daily_pnl,
            'daily_pnl_pct': daily_pnl / account_value if account_value > 0 else 0,
            'max_daily_loss': self.max_daily_loss,
            'remaining_daily_loss': self.max_daily_loss + daily_pnl,
        }
    
    def check_circuit_breaker(self, positions: List[Dict[str, Any]], 
                             account_value: float, daily_pnl: float) -> Tuple[bool, str]:
        """
        Check if circuit breaker should be triggered
        """
        positions = self._filter_active_positions(positions)
        reasons = []
        
        # 1. Check daily loss limit
        if daily_pnl <= -self.max_daily_loss:
            reasons.append(f"Daily loss limit breached: ${daily_pnl:.2f} <= -${self.max_daily_loss:.2f}")
        
        # 2. Check total loss limit
        if self.total_pnl <= -self.max_total_loss:
            reasons.append(f"Total loss limit breached: ${self.total_pnl:.2f} <= -${self.max_total_loss:.2f}")
        
        # 3. Check for large single position loss
        for position in positions:
            unrealized_pnl_pct = position.get('unrealized_plpc', 0)
            if unrealized_pnl_pct <= -0.10:  # 10% loss on single position
                reasons.append(f"Large loss on {position['symbol']}: {unrealized_pnl_pct:.1%}")
        
        # 4. Check portfolio concentration
        total_exposure = sum(p.get('market_value', 0) for p in positions)
        if total_exposure > 0:
            concentration = sum((p.get('market_value', 0) / total_exposure) ** 2 
                              for p in positions)
            if concentration > 0.5:  # Highly concentrated portfolio
                reasons.append(f"High portfolio concentration: {concentration:.2f}")
        
        if reasons:
            self.risk_metrics['circuit_breaker_triggered'] = True
            self._save_risk_metrics()
            return True, "; ".join(reasons)
        
        return False, ""
    
    def reset_circuit_breaker(self):
        """Reset circuit breaker"""
        self.risk_metrics['circuit_breaker_triggered'] = False
        self._save_risk_metrics()
        logger.info("Circuit breaker reset")
    
    # ============ TRADE LOGGING & PERFORMANCE ============
    
    def log_trade(self, trade_data: Dict[str, Any]):
        """Log a completed trade"""
        try:
            # Add timestamp if not present
            if 'timestamp' not in trade_data:
                trade_data['timestamp'] = datetime.now().isoformat()
            
            # Create DataFrame for the trade
            trade_df = pd.DataFrame([trade_data])
            
            # Append to CSV
            if os.path.exists(self.trade_log_file):
                trade_df.to_csv(self.trade_log_file, mode='a', header=False, index=False)
            else:
                os.makedirs(self.data_dir, exist_ok=True)
                trade_df.to_csv(self.trade_log_file, index=False)
            
            # Update risk metrics
            self._update_trade_metrics(trade_data)
            
            logger.info(f"Trade logged: {trade_data.get('symbol')} {trade_data.get('side')} "
                       f"{trade_data.get('quantity')} @ {trade_data.get('price')}")
            
        except Exception as e:
            logger.error(f"Error logging trade: {e}")
    
    def _update_trade_metrics(self, trade_data: Dict[str, Any]):
        """Update risk metrics after a trade"""
        # Update trade counts
        self.risk_metrics['total_trades'] = self.risk_metrics.get('total_trades', 0) + 1
        
        # Check if trade was profitable
        pnl = trade_data.get('realized_pnl', 0)
        if pnl > 0:
            self.risk_metrics['winning_trades'] = self.risk_metrics.get('winning_trades', 0) + 1
            self.risk_metrics['total_pnl'] = self.risk_metrics.get('total_pnl', 0) + pnl
        elif pnl < 0:
            self.risk_metrics['losing_trades'] = self.risk_metrics.get('losing_trades', 0) + 1
            self.risk_metrics['total_pnl'] = self.risk_metrics.get('total_pnl', 0) + pnl
        
        # Update win rate
        total = self.risk_metrics.get('total_trades', 1)
        wins = self.risk_metrics.get('winning_trades', 0)
        self.risk_metrics['win_rate'] = wins / total if total > 0 else 0
        
        # Save updated metrics
        self._save_risk_metrics()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        return {
            'total_trades': self.risk_metrics.get('total_trades', 0),
            'winning_trades': self.risk_metrics.get('winning_trades', 0),
            'losing_trades': self.risk_metrics.get('losing_trades', 0),
            'win_rate': self.risk_metrics.get('win_rate', 0),
            'total_pnl': self.risk_metrics.get('total_pnl', 0),
            'daily_pnl': self.daily_pnl,
            'max_daily_loss': self.max_daily_loss,
            'remaining_daily_loss': self.max_daily_loss + self.daily_pnl,
            'circuit_breaker': self.risk_metrics.get('circuit_breaker_triggered', False),
            'last_reset': self.risk_metrics.get('last_reset', ''),
        }
    
    def reset_daily_metrics(self):
        """Reset daily metrics (call at start of trading day)"""
        self.daily_pnl = 0.0
        self.risk_metrics['daily_pnl'] = 0.0
        self.risk_metrics['daily_resets'] = self.risk_metrics.get('daily_resets', 0) + 1
        self.risk_metrics['last_reset'] = datetime.now().isoformat()
        self._save_risk_metrics()
        logger.info("Daily metrics reset")
    
    # ============ RISK ADJUSTMENT METHODS ============
    
    def adjust_for_volatility(self, positions: List[Dict[str, Any]], 
                             volatility_data: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Adjust position sizes based on current volatility
        """
        adjusted_positions = []
        
        for position in positions:
            symbol = position['symbol']
            volatility = volatility_data.get(symbol, 0.02)
            
            # Skip if low volatility data
            if volatility <= 0:
                adjusted_positions.append(position)
                continue
            
            # Calculate volatility adjustment factor
            # Higher volatility = smaller position size
            adjustment = 1.0 / (1.0 + volatility * 10)
            
            # Apply adjustment to suggested position size (for new trades)
            # For existing positions, we could adjust stop losses
            adjusted_position = position.copy()
            
            # Adjust stop loss based on volatility
            current_price = position.get('current_price', 0)
            if current_price > 0:
                # Wider stop loss in high volatility
                volatility_stop = STOP_LOSS_PCT * (1 + volatility * 5)
                adjusted_position['volatility_adjusted_stop'] = current_price * (1 - volatility_stop)
            
            adjusted_positions.append(adjusted_position)
        
        return adjusted_positions
    
    def calculate_correlation_matrix(self, price_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Calculate correlation matrix between crypto assets
        """
        returns_data = {}
        
        for symbol, df in price_data.items():
            if len(df) > 10:
                returns_data[symbol] = df['close'].pct_change().dropna()
        
        if not returns_data:
            return pd.DataFrame()
        
        # Create DataFrame of returns
        returns_df = pd.DataFrame(returns_data)
        
        # Calculate correlation matrix
        correlation_matrix = returns_df.corr()
        
        return correlation_matrix
    
    def check_portfolio_diversification(self, positions: List[Dict[str, Any]],
                                      correlation_matrix: pd.DataFrame) -> float:
        """
        Calculate portfolio diversification score (0-1, higher is more diversified)
        """
        if len(positions) <= 1:
            return 0.0
        
        # Extract symbols and weights
        symbols = [p['symbol'] for p in positions]
        weights = np.array([p.get('market_value', 0) for p in positions])
        
        # Normalize weights
        total_value = weights.sum()
        if total_value <= 0:
            return 0.0
        
        weights = weights / total_value
        
        # Calculate diversification score
        # Simple measure: 1 - average correlation between positions
        diversification = 1.0
        
        # Try to get correlations from matrix
        try:
            # Get submatrix for our positions
            pos_symbols = [s for s in symbols if s in correlation_matrix.columns]
            if len(pos_symbols) > 1:
                sub_corr = correlation_matrix.loc[pos_symbols, pos_symbols]
                # Calculate weighted average correlation
                avg_corr = 0.0
                count = 0
                
                for i, sym1 in enumerate(pos_symbols):
                    for j, sym2 in enumerate(pos_symbols):
                        if i < j:  # Upper triangle
                            avg_corr += sub_corr.loc[sym1, sym2]
                            count += 1
                
                if count > 0:
                    avg_corr /= count
                    diversification = 1.0 - abs(avg_corr)
        
        except Exception as e:
            logger.warning(f"Error calculating diversification: {e}")
        
        return max(0.0, min(1.0, diversification))


# ============ TEST FUNCTIONS ============

def test_risk_manager():
    """Test the risk manager"""
    print("Testing Risk Manager...")
    
    try:
        # Initialize
        risk_manager = RiskManager(data_dir="data")
        
        # Test position size calculation
        quantity, metrics = risk_manager.calculate_position_size(
            account_cash=10000,
            current_price=50000,  # BTC price
            confidence=0.7,
            volatility=0.02,
            existing_positions=[]
        )
        
        print(f"✅ Position size calculated: {quantity:.6f} BTC")
        print(f"   Position value: ${metrics['position_value']:.2f}")
        print(f"   Stop loss: ${metrics['stop_loss']:.2f}")
        print(f"   Take profit: ${metrics['take_profit']:.2f}")
        
        # Test trade validation
        mock_positions = [
            {'symbol': 'ETH/USD', 'qty': 1.0, 'market_value': 3000, 'side': 'buy'},
            {'symbol': 'SOL/USD', 'qty': 10.0, 'market_value': 1500, 'side': 'buy'},
        ]
        
        is_valid, reason = risk_manager.validate_trade(
            symbol='BTC/USD',
            qty=0.1,
            price=50000,
            side='buy',
            positions=mock_positions,
            account_cash=10000
        )
        
        print(f"✅ Trade validation: {'PASS' if is_valid else 'FAIL'} - {reason}")
        
        # Test portfolio risk calculation
        portfolio_risk = risk_manager.update_portfolio_risk(
            positions=mock_positions,
            account_value=15000,
            daily_pnl=250
        )
        
        print(f"✅ Portfolio risk calculated:")
        print(f"   Positions: {portfolio_risk['num_positions']}")
        print(f"   Total exposure: ${portfolio_risk['total_exposure']:.2f}")
        print(f"   Concentration: {portfolio_risk['concentration']:.2f}")
        
        # Test circuit breaker
        circuit_triggered, circuit_reason = risk_manager.check_circuit_breaker(
            positions=mock_positions,
            account_value=15000,
            daily_pnl=-1000  # Large loss
        )
        
        print(f"✅ Circuit breaker: {'TRIGGERED' if circuit_triggered else 'OK'}")
        if circuit_triggered:
            print(f"   Reason: {circuit_reason}")
        
        # Test performance summary
        performance = risk_manager.get_performance_summary()
        print(f"✅ Performance summary:")
        print(f"   Total trades: {performance['total_trades']}")
        print(f"   Win rate: {performance['win_rate']:.1%}")
        print(f"   Total PnL: ${performance['total_pnl']:.2f}")
        
        print("\nRisk Manager test completed successfully!")
        
    except Exception as e:
        print(f"❌ Risk Manager test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_risk_manager()