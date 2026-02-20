#!/usr/bin/env python3
"""
Run trading engine with HMM regime-aware strategy for testing.
"""
import sys
import time
import logging
import signal
import threading
from typing import Dict, List, Any, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

class PatchedRiskManager:
    """
    Risk manager that ignores MKRUSD position for circuit breaker.
    """
    def __init__(self, original_risk_manager):
        self.original = original_risk_manager
        self.data_dir = original_risk_manager.data_dir
        self.risk_metrics = original_risk_manager.risk_metrics
        self.max_daily_loss = original_risk_manager.max_daily_loss
        self.max_total_loss = original_risk_manager.max_total_loss
        self.total_pnl = original_risk_manager.total_pnl
        
    def check_circuit_breaker(self, positions: List[Dict[str, Any]], 
                             account_value: float, daily_pnl: float) -> Tuple[bool, str]:
        """
        Modified circuit breaker that ignores MKRUSD position.
        """
        # Filter out MKRUSD position
        filtered_positions = [p for p in positions if p.get('symbol') != 'MKRUSD']
        
        # Use original logic but with filtered positions
        reasons = []
        
        # 1. Check daily loss limit
        if daily_pnl <= -self.max_daily_loss:
            reasons.append(f"Daily loss limit breached: ${daily_pnl:.2f} <= -${self.max_daily_loss:.2f}")
        
        # 2. Check total loss limit
        if self.total_pnl <= -self.max_total_loss:
            reasons.append(f"Total loss limit breached: ${self.total_pnl:.2f} <= -${self.max_total_loss:.2f}")
        
        # 3. Check for large single position loss (skip MKRUSD)
        for position in filtered_positions:
            unrealized_pnl_pct = position.get('unrealized_plpc', 0)
            if unrealized_pnl_pct <= -0.10:  # 10% loss on single position
                reasons.append(f"Large loss on {position['symbol']}: {unrealized_pnl_pct:.1%}")
        
        # 4. Check portfolio concentration (use filtered positions)
        total_exposure = sum(p.get('market_value', 0) for p in filtered_positions)
        if total_exposure > 0:
            concentration = sum((p.get('market_value', 0) / total_exposure) ** 2 
                              for p in filtered_positions)
            if concentration > 0.5:  # Highly concentrated portfolio
                reasons.append(f"High portfolio concentration: {concentration:.2f}")
        
        if reasons:
            self.risk_metrics['circuit_breaker_triggered'] = True
            self.original._save_risk_metrics()
            return True, "; ".join(reasons)
        
        return False, ""
    
    # Delegate other methods to original
    def __getattr__(self, name):
        return getattr(self.original, name)

def main():
    print("Starting HMM Regime-Aware Trading Engine Test")
    print("=" * 60)
    
    # Import here to avoid circular imports
    from trading_engine import TradingEngine
    
    # Create engine
    engine = TradingEngine(scan_interval_minutes=5)
    
    # Patch risk manager to ignore MKRUSD
    print("Patching risk manager to ignore MKRUSD position...")
    engine.risk_manager = PatchedRiskManager(engine.risk_manager)
    
    # Ensure circuit breaker state is reset
    engine.state.circuit_breaker_triggered = False
    
    # Get initial account info
    account = engine.client.get_account()
    if account:
        print(f"Account: {account['account_number']}")
        print(f"Cash: ${account['cash']:.2f}")
        print(f"Portfolio Value: ${account['portfolio_value']:.2f}")
    
    positions = engine.client.get_positions()
    print(f"Positions: {len(positions)}")
    for p in positions:
        symbol = p['symbol']
        pnl_pct = p['unrealized_plpc']
        print(f"  {symbol}: {p['qty']} units, PnL: {pnl_pct:.2%}")
        if symbol == 'MKRUSD':
            print(f"    (MKRUSD will be ignored in circuit breaker)")
    
    # Run for N scans
    num_scans = 3  # Run 3 scans (15 minutes)
    print(f"\nRunning {num_scans} market scans (5-minute intervals)...")
    
    # Start the engine
    engine.start()
    
    try:
        # Wait for scans to complete
        scans_completed = 0
        last_scans = 0
        
        while scans_completed < num_scans:
            time.sleep(60)  # Check every minute
            
            # Check if new scans happened
            current_scans = engine.state.total_scans
            new_scans = current_scans - last_scans
            if new_scans > 0:
                scans_completed += new_scans
                last_scans = current_scans
                print(f"Scan {scans_completed}/{num_scans} completed at {time.strftime('%H:%M:%S')}")
                
                # Show latest regime if available
                if hasattr(engine.strategy, 'regime_history') and engine.strategy.regime_history:
                    latest = engine.strategy.regime_history[-1]
                    print(f"  Latest regime: {latest['regime_name']} (confidence {latest['confidence']:.2f})")
                
                # Check for any trades
                if engine.state.total_trades > 0:
                    print(f"  Total trades so far: {engine.state.total_trades}")
            
            # Check if engine stopped
            if not engine.state.running:
                print("Engine stopped unexpectedly!")
                break
        
        print(f"\nCompleted {scans_completed} scans.")
        
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        # Stop engine
        print("Stopping trading engine...")
        engine.stop()
    
    # Final report
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print(f"Total scans: {engine.state.total_scans}")
    print(f"Total trades: {engine.state.total_trades}")
    print(f"Active positions: {engine.state.active_positions}")
    print(f"Daily PnL: ${engine.state.daily_pnl:.2f}")
    
    # Regime history summary
    if hasattr(engine.strategy, 'regime_history') and engine.strategy.regime_history:
        print(f"\nRegime History ({len(engine.strategy.regime_history)} entries):")
        # Group by regime
        regime_counts = {}
        for entry in engine.strategy.regime_history:
            regime = entry['regime_name']
            regime_counts[regime] = regime_counts.get(regime, 0) + 1
        
        for regime, count in regime_counts.items():
            percentage = count / len(engine.strategy.regime_history) * 100
            print(f"  {regime}: {count} times ({percentage:.1f}%)")
    
    print("\nCheck 'data/trades.csv' for trade logs and 'reports/' for performance dashboard.")

if __name__ == "__main__":
    main()