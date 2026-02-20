"""
Main Trading Engine - Automated Crypto Trading Loop
"""

import pandas as pd
import numpy as np
import time
import schedule
import threading
import signal
import sys
from datetime import datetime, timedelta
import logging
import json
import os
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import traceback

# Import our modules
from alpaca_client import AlpacaClient
from strategy import CryptoMomentumStrategy
from hmm_regime import CryptoHMMRegimeDetector, RegimeAwareCryptoStrategy
from risk_manager import RiskManager
from config import (
    TIME_FRAME, LOOKBACK_PERIOD, CRYPTO_SYMBOLS,
    MAX_POSITIONS, TRADING_HOURS, PERFORMANCE_LOG,
    TRADE_LOG, ERROR_LOG
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(ERROR_LOG),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class TradeSignal:
    """Represents a trading signal"""
    symbol: str
    signal: str  # 'buy', 'sell', 'hold'
    confidence: float
    quantity: float
    price: float
    reasons: List[str]
    indicators: Dict[str, Any]
    position_metrics: Dict[str, Any]
    timestamp: datetime = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


@dataclass
class TradingState:
    """Current state of the trading engine"""
    running: bool = False
    last_scan: Optional[datetime] = None
    total_scans: int = 0
    total_trades: int = 0
    active_positions: int = 0
    daily_pnl: float = 0.0
    total_pnl: float = 0.0
    circuit_breaker_triggered: bool = False
    last_error: Optional[str] = None
    
    def update_after_scan(self):
        """Update state after a market scan"""
        self.last_scan = datetime.now()
        self.total_scans += 1
    
    def update_after_trade(self):
        """Update state after a trade"""
        self.total_trades += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['last_scan'] = self.last_scan.isoformat() if self.last_scan else None
        return data


class TradingEngine:
    """Main trading engine that orchestrates the entire system"""
    
    def __init__(self, scan_interval_minutes: int = 5):
        """
        Initialize trading engine
        
        Args:
            scan_interval_minutes: How often to scan markets (default: 5 minutes)
        """
        self.scan_interval = scan_interval_minutes
        
        # Initialize components
        logger.info("Initializing Trading Engine...")
        self.client = AlpacaClient()
        # Initialize HMM regime-aware strategy
        base_strategy = CryptoMomentumStrategy()
        hmm_detector = CryptoHMMRegimeDetector()
        self.strategy = RegimeAwareCryptoStrategy(base_strategy, hmm_detector)
        # Train HMM on synthetic data (fallback)
        self._train_hmm_on_synthetic_data(hmm_detector)
        self.risk_manager = RiskManager(data_dir="data", client=self.client)
        
        # State
        self.state = TradingState()
        self.stop_event = threading.Event()
        
        # Performance tracking
        self.performance_file = PERFORMANCE_LOG
        self.trade_log_file = TRADE_LOG
        
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"Trading Engine initialized with {scan_interval_minutes}-minute scan interval")
    
    def _train_hmm_on_synthetic_data(self, hmm_detector):
        """
        Train HMM detector on synthetic data (fallback when insufficient real data).
        Based on compare_strategies.py synthetic data generation.
        """
        import numpy as np
        import pandas as pd
        
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
        
        # Train HMM using the detector's train_hmm method (via RegimeAwareCryptoStrategy)
        # We'll use the same approach as compare_strategies: extract features and fit
        try:
            # Combine features from all symbols
            all_features = []
            for symbol, df in historical_data.items():
                features = hmm_detector.extract_features(df)
                all_features.append(features)
            
            X = np.vstack(all_features)
            hmm_detector.fit_from_features(X)
            logger.info(f"HMM trained on synthetic data: {len(X)} samples")
        except Exception as e:
            logger.warning(f"HMM synthetic training failed: {e}")
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
    
    def start(self):
        """Start the trading engine"""
        if self.state.running:
            logger.warning("Trading engine is already running")
            return
        
        logger.info("Starting Trading Engine...")
        self.state.running = True
        
        # Reset daily metrics at start
        self.risk_manager.reset_daily_metrics()
        
        # Get initial account state
        account = self.client.get_account()
        if account:
            logger.info(f"Account: {account['account_number']}")
            logger.info(f"Cash: ${account['cash']:,.2f}")
            logger.info(f"Portfolio Value: ${account['portfolio_value']:,.2f}")
        
        # Start the main loop in a separate thread
        self.thread = threading.Thread(target=self._main_loop, daemon=True)
        self.thread.start()
        
        logger.info("Trading Engine started successfully")
    
    def stop(self):
        """Stop the trading engine gracefully"""
        logger.info("Stopping Trading Engine...")
        self.state.running = False
        self.stop_event.set()
        
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=30)
        
        # Save final state
        self._save_state()
        logger.info("Trading Engine stopped")
    
    def _main_loop(self):
        """Main trading loop"""
        logger.info("Main trading loop started")
        
        while self.state.running and not self.stop_event.is_set():
            try:
                # Check if market is open (crypto is 24/7, but we can respect configured hours)
                if not self._is_trading_hours():
                    logger.debug("Outside trading hours, sleeping...")
                    time.sleep(60)  # Check every minute
                    continue
                
                # Check circuit breaker
                if self.state.circuit_breaker_triggered:
                    logger.warning("Circuit breaker triggered, trading halted")
                    time.sleep(self.scan_interval * 60)  # Full interval
                    continue
                
                # Run market scan
                self._scan_markets()
                
                # Sleep until next scan
                sleep_seconds = self.scan_interval * 60
                logger.debug(f"Sleeping for {sleep_seconds} seconds until next scan")
                
                # Sleep in chunks to check for stop event
                for _ in range(sleep_seconds // 10):
                    if self.stop_event.is_set():
                        break
                    time.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                logger.error(traceback.format_exc())
                self.state.last_error = str(e)
                time.sleep(60)  # Wait a minute before retrying
    
    def _is_trading_hours(self) -> bool:
        """Check if current time is within trading hours"""
        # Crypto trades 24/7, but we respect configured hours
        current_hour = datetime.now().hour
        start_hour = TRADING_HOURS.get("start_hour", 0)
        end_hour = TRADING_HOURS.get("end_hour", 24)
        
        return start_hour <= current_hour < end_hour
    
    def _scan_markets(self):
        """Scan all markets for trading opportunities"""
        logger.info(f"Scanning {len(CRYPTO_SYMBOLS)} crypto markets...")
        
        # Get current account state
        account = self.client.get_account()
        if not account:
            logger.error("Failed to get account information, skipping scan")
            return
        
        positions = self.client.get_positions()
        self.state.active_positions = len(positions)
        
        # Update portfolio risk
        portfolio_risk = self.risk_manager.update_portfolio_risk(
            positions=positions,
            account_value=account['portfolio_value'],
            daily_pnl=self.state.daily_pnl
        )
        
        # Check circuit breaker
        circuit_triggered, circuit_reason = self.risk_manager.check_circuit_breaker(
            positions=positions,
            account_value=account['portfolio_value'],
            daily_pnl=self.state.daily_pnl
        )
        
        if circuit_triggered:
            self.state.circuit_breaker_triggered = True
            logger.error(f"Circuit breaker triggered: {circuit_reason}")
            return
        
        # Scan each symbol
        for symbol in CRYPTO_SYMBOLS:
            try:
                if self.stop_event.is_set():
                    break
                
                self._analyze_symbol(symbol, account, positions)
                time.sleep(1)  # Small delay between symbols to avoid rate limits
                
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue
        
        # Check existing positions for exit signals
        self._manage_existing_positions(positions, account)
        
        # Update state
        self.state.update_after_scan()
        self._save_state()
        
        logger.info(f"Market scan completed. Positions: {len(positions)}, "
                   f"Daily PnL: ${self.state.daily_pnl:.2f}")
    
    def _analyze_symbol(self, symbol: str, account: Dict[str, Any], 
                       positions: List[Dict[str, Any]]):
        """Analyze a specific symbol for trading opportunities"""
        # Get market data
        df = self.client.get_market_data(
            symbol=symbol,
            timeframe=TIME_FRAME,
            limit=LOOKBACK_PERIOD
        )
        
        if df.empty or len(df) < 20:
            logger.debug(f"Insufficient data for {symbol}, skipping")
            return
        
        # Check if we already have a position
        existing_position = next((p for p in positions if p['symbol'] == symbol), None)
        
        if existing_position:
            # We already have a position, check if we should exit
            # (Exit logic handled in _manage_existing_positions)
            return
        
        # Run strategy analysis
        analysis = self.strategy.analyze_market(df, account['cash'])
        
        if 'error' in analysis:
            logger.debug(f"Analysis error for {symbol}: {analysis['error']}")
            return
        
        # Skip hold signals
        if analysis['signal'] == 'hold':
            return
        
        # Create trade signal
        current_price = df.iloc[-1]['close']
        
        # Calculate position size using risk manager
        volatility = analysis.get('indicators', {}).get('atr_percent', 0.02)
        quantity, position_metrics = self.risk_manager.calculate_position_size(
            account_cash=account['cash'],
            current_price=current_price,
            confidence=analysis['confidence'],
            volatility=volatility,
            existing_positions=positions
        )
        
        # Validate trade with risk manager
        is_valid, reason = self.risk_manager.validate_trade(
            symbol=symbol,
            qty=quantity,
            price=current_price,
            side='buy' if analysis['signal'] == 'buy' else 'sell',
            positions=positions,
            account_cash=account['cash']
        )
        
        if not is_valid:
            logger.debug(f"Trade not valid for {symbol}: {reason}")
            return
        
        # Create signal object
        signal = TradeSignal(
            symbol=symbol,
            signal=analysis['signal'],
            confidence=analysis['confidence'],
            quantity=quantity,
            price=current_price,
            reasons=analysis.get('reasons', []),
            indicators=analysis.get('indicators', {}),
            position_metrics=position_metrics
        )
        
        # Execute the trade
        self._execute_trade(signal, account)
    
    def _execute_trade(self, signal: TradeSignal, account: Dict[str, Any]):
        """Execute a trade based on signal"""
        logger.info(f"Executing {signal.signal} signal for {signal.symbol}: "
                   f"{signal.quantity:.6f} @ ${signal.price:.2f} "
                   f"(confidence: {signal.confidence:.2f})")
        
        # Place order
        order = self.client.place_market_order(
            symbol=signal.symbol,
            qty=signal.quantity,
            side=signal.signal  # 'buy' or 'sell'
        )
        
        if not order:
            logger.error(f"Failed to place order for {signal.symbol}")
            return
        
        # Log the trade
        trade_data = {
            'timestamp': signal.timestamp.isoformat(),
            'symbol': signal.symbol,
            'side': signal.signal,
            'quantity': signal.quantity,
            'price': signal.price,
            'order_id': order['id'],
            'order_status': order['status'],
            'confidence': signal.confidence,
            'account_cash_before': account['cash'],
            'position_metrics': signal.position_metrics,
            'reasons': signal.reasons,
            'indicators': signal.indicators,
        }
        
        self.risk_manager.log_trade(trade_data)
        self.state.update_after_trade()
        
        logger.info(f"Order placed: {order['id']} - {signal.signal} {signal.quantity} "
                   f"{signal.symbol} @ ${signal.price:.2f}")
    
    def _manage_existing_positions(self, positions: List[Dict[str, Any]], 
                                 account: Dict[str, Any]):
        """Manage existing positions (check for exits, adjust stops)"""
        for position in positions:
            try:
                symbol = position['symbol']
                
                # Get current market data
                df = self.client.get_market_data(
                    symbol=symbol,
                    timeframe=TIME_FRAME,
                    limit=50  # Less data needed for exit decisions
                )
                
                if df.empty:
                    continue
                
                # Check for exit signals
                should_exit, exit_reason = self._check_exit_signal(
                    position, df, account
                )
                
                if should_exit:
                    self._exit_position(position, exit_reason)
                    
            except Exception as e:
                logger.error(f"Error managing position {position['symbol']}: {e}")
                continue
    
    def _check_exit_signal(self, position: Dict[str, Any], df: pd.DataFrame,
                          account: Dict[str, Any]) -> Tuple[bool, str]:
        """Check if we should exit a position"""
        symbol = position['symbol']
        current_price = df.iloc[-1]['close']
        entry_price = position['avg_entry_price']
        current_pnl_pct = position['unrealized_plpc']
        
        reasons = []
        
        # 1. Check stop loss (using position_metrics from entry)
        # For now, use simple percentage-based stop
        stop_loss_pct = -STOP_LOSS_PCT
        if current_pnl_pct <= stop_loss_pct:
            reasons.append(f"Stop loss hit: {current_pnl_pct:.1%} <= {stop_loss_pct:.1%}")
        
        # 2. Check take profit
        take_profit_pct = TAKE_PROFIT_PCT
        if current_pnl_pct >= take_profit_pct:
            reasons.append(f"Take profit hit: {current_pnl_pct:.1%} >= {take_profit_pct:.1%}")
        
        # 3. Check strategy exit signal
        analysis = self.strategy.analyze_market(df, account['cash'])
        
        if analysis.get('signal') == 'sell' and position['side'] == 'buy':
            reasons.append(f"Strategy sell signal (confidence: {analysis['confidence']:.2f})")
        elif analysis.get('signal') == 'buy' and position['side'] == 'sell':
            reasons.append(f"Strategy buy signal for short position")
        
        # 4. Check trailing stop (simplified)
        # In production, track highest price since entry
        trailing_stop_pct = TRAILING_STOP_PCT
        # For now, just check if we've given back significant profits
        
        if reasons:
            return True, "; ".join(reasons)
        
        return False, ""
    
    def _exit_position(self, position: Dict[str, Any], reason: str):
        """Exit a position"""
        symbol = position['symbol']
        
        logger.info(f"Exiting position {symbol}: {reason}")
        
        # Close the position
        result = self.client.close_position(symbol)
        
        if result:
            # Log the exit
            exit_data = {
                'timestamp': datetime.now().isoformat(),
                'symbol': symbol,
                'action': 'exit',
                'reason': reason,
                'quantity': position['qty'],
                'entry_price': position['avg_entry_price'],
                'exit_price': result.get('filled_avg_price', 0),
                'unrealized_pl': position['unrealized_pl'],
                'unrealized_plpc': position['unrealized_plpc'],
                'order_id': result.get('id', ''),
            }
            
            self.risk_manager.log_trade(exit_data)
            logger.info(f"Position closed: {symbol}, PnL: ${position['unrealized_pl']:.2f}")
        else:
            logger.error(f"Failed to close position {symbol}")
    
    def _save_state(self):
        """Save current state to disk"""
        try:
            state_data = {
                'engine_state': self.state.to_dict(),
                'performance': self.risk_manager.get_performance_summary(),
                'last_updated': datetime.now().isoformat(),
            }
            
            with open(self.performance_file, 'w') as f:
                json.dump(state_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving state: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current engine status"""
        account = self.client.get_account()
        positions = self.client.get_positions()
        
        return {
            'engine': self.state.to_dict(),
            'account': account,
            'positions': positions,
            'performance': self.risk_manager.get_performance_summary(),
            'components': {
                'client': 'AlpacaClient',
                'strategy': 'RegimeAwareCryptoStrategy',
                'risk_manager': 'RiskManager',
            }
        }
    
    def run_once(self):
        """Run a single market scan (for testing/debugging)"""
        logger.info("Running single market scan...")
        self._scan_markets()
        logger.info("Single scan completed")
    
    def run_backtest(self, days: int = 7):
        """
        Run a backtest on historical data
        
        Note: This is a simplified backtest. For production,
        you'd want a dedicated backtesting framework.
        """
        logger.info(f"Running backtest for {days} days...")
        
        # This would require historical data and proper backtesting logic
        # For now, just demonstrate the structure
        
        results = {
            'total_days': days,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_return': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
        }
        
        logger.info(f"Backtest completed: {results}")
        return results


# ============ COMMAND LINE INTERFACE ============

def main():
    """Main entry point for the trading engine"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Crypto Trading Engine')
    parser.add_argument('--interval', type=int, default=5,
                       help='Scan interval in minutes (default: 5)')
    parser.add_argument('--once', action='store_true',
                       help='Run a single scan and exit')
    parser.add_argument('--backtest', type=int,
                       help='Run backtest for N days')
    parser.add_argument('--status', action='store_true',
                       help='Show current status')
    
    args = parser.parse_args()
    
    # Initialize engine
    engine = TradingEngine(scan_interval_minutes=args.interval)
    
    if args.status:
        status = engine.get_status()
        print(json.dumps(status, indent=2))
        return
    
    if args.backtest:
        engine.run_backtest(days=args.backtest)
        return
    
    if args.once:
        engine.run_once()
        return
    
    # Run continuously
    try:
        engine.start()
        
        # Keep main thread alive
        while engine.state.running:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nShutting down...")
        engine.stop()
    except Exception as e:
        print(f"Error: {e}")
        traceback.print_exc()
        engine.stop()


if __name__ == "__main__":
    main()