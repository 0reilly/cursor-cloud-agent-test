#!/usr/bin/env python3
import sys
sys.path.append('.')
from alpaca_client import AlpacaClient

client = AlpacaClient()

try:
    assets = client.api.list_assets(status='active')
    if assets:
        asset = assets[0]
        print("Asset._raw type:", type(asset._raw))
        print("Asset._raw:", asset._raw)
        # Try to see keys
        if isinstance(asset._raw, dict):
            print("Keys:", list(asset._raw.keys()))
        else:
            print("Not a dict")
except Exception as e:
    print(f"Error: {e}")

# Try get_asset
try:
    asset = client.api.get_asset('BTC/USD')
    print("\nBTC/USD asset._raw:", asset._raw)
    if isinstance(asset._raw, dict):
        print("Keys:", list(asset._raw.keys()))
except Exception as e:
    print(f"Error get_asset: {e}")