#!/usr/bin/env python3
import sys
sys.path.append('.')
from alpaca_client import AlpacaClient
from risk_manager import RiskManager

client = AlpacaClient()
risk_mgr = RiskManager(data_dir="data", client=client)

# Get current positions
positions = client.get_positions()
print(f"Total positions: {len(positions)}")
for p in positions:
    print(f"  {p['symbol']}: {p['qty']} units, PnL: {p['unrealized_plpc']:.2%}")

# Get account
account = client.get_account()
account_value = account['portfolio_value']
daily_pnl = 0.0  # assume zero for test

# Check circuit breaker
triggered, reason = risk_mgr.check_circuit_breaker(positions, account_value, daily_pnl)
print(f"\nCircuit breaker triggered: {triggered}")
print(f"Reason: {reason}")

# Test filter_active_positions
filtered = risk_mgr._filter_active_positions(positions)
print(f"\nFiltered positions: {len(filtered)}")
for p in filtered:
    print(f"  {p['symbol']}: {p['qty']} units")

# Check if MKRUSD is filtered out
mkr_positions = [p for p in positions if p['symbol'] == 'MKRUSD']
print(f"\nMKRUSD in original positions: {len(mkr_positions)}")
print(f"MKRUSD in filtered positions: {len([p for p in filtered if p['symbol'] == 'MKRUSD'])}")

# Also test is_asset_active
print(f"\nIs BTC/USD active? {client.is_asset_active('BTC/USD')}")
print(f"Is MKR/USD active? {client.is_asset_active('MKR/USD')}")