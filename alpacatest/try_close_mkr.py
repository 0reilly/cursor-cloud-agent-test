#!/usr/bin/env python3
import sys
sys.path.append('.')
from alpaca_client import AlpacaClient

client = AlpacaClient()

# Try to close MKRUSD with limit order at extreme price
symbol = 'MKR/USD'
qty = 0.099879999

print(f"Attempting to close MKRUSD position: {qty} units")

# Try market order first (likely to fail)
try:
    order = client.place_market_order(symbol=symbol, qty=qty, side='sell')
    print(f"Market order placed: {order}")
except Exception as e:
    print(f"Market order failed: {e}")

# Try limit order at $1 (extreme low)
try:
    limit_price = 1.0
    order = client.place_limit_order(symbol=symbol, qty=qty, side='sell', limit_price=limit_price)
    print(f"Limit order at ${limit_price} placed: {order}")
except Exception as e:
    print(f"Limit order failed: {e}")

# Try limit order at $100 (more reasonable but still low)
try:
    limit_price = 100.0
    order = client.place_limit_order(symbol=symbol, qty=qty, side='sell', limit_price=limit_price)
    print(f"Limit order at ${limit_price} placed: {order}")
except Exception as e:
    print(f"Limit order at $100 failed: {e}")

# Check current price if available
try:
    bars = client.get_bars(symbol, timeframe='5Min', limit=1)
    if bars is not None and not bars.empty:
        current_price = bars['close'].iloc[-1]
        print(f"Current MKR price: ${current_price}")
        # Try limit order at slightly below current
        limit_price = current_price * 0.95
        order = client.place_limit_order(symbol=symbol, qty=qty, side='sell', limit_price=limit_price)
        print(f"Limit order at ${limit_price:.2f} (5% below market) placed: {order}")
except Exception as e:
    print(f"Could not get price or place order: {e}")