#!/usr/bin/env python3
import sys
sys.path.append('.')
from alpaca_client import AlpacaClient

client = AlpacaClient()
account = client.get_account()
print(f'Account number: {account["account_number"]}')
print(f'Cash: ${account["cash"]}')
print(f'Portfolio value: ${account["portfolio_value"]}')
print(f'Equity: ${account["equity"]}')
print(f'Buying power: ${account["buying_power"]}')

positions = client.get_positions()
print(f'Positions: {len(positions)}')
for p in positions:
    print(f'  {p["symbol"]}: {p["qty"]} units, Market value: ${p["market_value"]}, PnL: {p["unrealized_plpc"]:.2%}')