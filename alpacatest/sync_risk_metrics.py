#!/usr/bin/env python3
import sys
sys.path.append('.')
from alpaca_client import AlpacaClient
import json
import os
import config

client = AlpacaClient()
account = client.get_account()
if not account:
    print("Failed to get account")
    sys.exit(1)

actual_capital = float(account['portfolio_value'])
print(f"Actual portfolio value: ${actual_capital:.2f}")

# Load current risk metrics
risk_file = "data/risk_metrics.json"
if os.path.exists(risk_file):
    with open(risk_file, 'r') as f:
        risk_metrics = json.load(f)
else:
    risk_metrics = {}

# Update capital fields
risk_metrics['initial_capital'] = actual_capital
risk_metrics['current_capital'] = actual_capital

# Ensure other fields exist
defaults = {
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
    'circuit_breaker_triggered': False
}

for key, val in defaults.items():
    if key not in risk_metrics:
        risk_metrics[key] = val

# Save back
with open(risk_file, 'w') as f:
    json.dump(risk_metrics, f, indent=2)

print(f"Updated risk metrics with actual capital: ${actual_capital:.2f}")
print(f"Circuit breaker reset to: {risk_metrics['circuit_breaker_triggered']}")

# Also update config.py's INITIAL_CAPITAL?
config_capital = config.INITIAL_CAPITAL
if abs(config_capital - actual_capital) > 100:  # More than $100 difference
    print(f"\nNote: config.py INITIAL_CAPITAL is set to ${config_capital:.0f}, but actual capital is ${actual_capital:.2f}.")
    print("You may want to update config.py to match actual capital for accurate position sizing.")
else:
    print(f"\nconfig.py INITIAL_CAPITAL (${config_capital:.0f}) matches actual capital within tolerance.")