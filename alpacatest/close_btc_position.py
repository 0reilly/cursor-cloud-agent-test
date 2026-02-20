#!/usr/bin/env python3
import sys
sys.path.append('.')
from alpaca_client import AlpacaClient

client = AlpacaClient()

# Get positions
positions = client.get_positions()
print(f"Found {len(positions)} positions")

for p in positions:
    symbol = p['symbol']
    qty = p['qty']
    market_value = p['market_value']
    pnl_pct = p['unrealized_plpc']
    
    print(f"Position: {symbol}, Qty: {qty}, Value: ${market_value:.2f}, PnL: {pnl_pct:.2%}")
    
    if symbol == 'BTCUSD':
        print(f"Closing BTC position...")
        # Place sell order
        try:
            order = client.place_market_order(
                symbol='BTC/USD',
                qty=qty,
                side='sell'
            )
            print(f"Order placed: {order}")
        except Exception as e:
            print(f"Error closing position: {e}")
    else:
        print(f"Skipping {symbol} (not BTC)")