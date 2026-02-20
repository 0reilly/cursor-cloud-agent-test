#!/usr/bin/env python3
import sys
import time
import logging
sys.path.append('.')
from trading_engine import TradingEngine

logging.basicConfig(level=logging.INFO)

print("Testing Enhanced HMM Regime-Aware Strategy with Indicator Filtering")
print("=" * 70)

# Create engine with short scan interval for test
engine = TradingEngine(scan_interval_minutes=1)  # 1 minute for quick test

# Reset circuit breaker flag
engine.state.circuit_breaker_triggered = False

# Get initial account info
account = engine.client.get_account()
print(f"Account: {account['account_number']}")
print(f"Cash: ${account['cash']:.2f}")
print(f"Portfolio Value: ${account['portfolio_value']:.2f}")

positions = engine.client.get_positions()
print(f"Positions: {len(positions)}")
for p in positions:
    symbol = p['symbol']
    pnl_pct = p['unrealized_plpc']
    print(f"  {symbol}: {p['qty']} units, PnL: {pnl_pct:.2%}")

# Run one scan manually (bypass threading)
print("\nRunning single market scan...")
engine._scan_markets()

# Check results
print(f"\nScan completed.")
print(f"Total scans: {engine.state.total_scans}")
print(f"Total trades: {engine.state.total_trades}")
print(f"Active positions: {engine.state.active_positions}")
print(f"Circuit breaker triggered: {engine.state.circuit_breaker_triggered}")

# Check regime history
if hasattr(engine.strategy, 'regime_history') and engine.strategy.regime_history:
    print(f"\nRegime history ({len(engine.strategy.regime_history)} entries):")
    for entry in engine.strategy.regime_history[-5:]:  # last 5
        print(f"  {entry['timestamp']}: {entry['regime_name']} (confidence {entry['confidence']:.2f}), signal: {entry['signal']}")
else:
    print("\nNo regime history yet.")

# Check if any trades were placed
if engine.state.total_trades > 0:
    print("\nTrades placed during scan:")
    # Read trades.csv last line
    import csv
    with open('data/trades.csv', 'r') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        for row in rows[-engine.state.total_trades:]:
            print(f"  {row['timestamp']}: {row['symbol']} {row['side']} {row['quantity']} @ {row['price']}")
else:
    print("\nNo trades placed.")

print("\nTest complete.")