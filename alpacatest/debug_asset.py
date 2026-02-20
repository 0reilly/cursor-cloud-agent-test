#!/usr/bin/env python3
import sys
sys.path.append('.')
from alpaca_client import AlpacaClient

client = AlpacaClient()

# Try to get one asset
try:
    # Use api directly
    asset = client.api.get_asset('BTC/USD')
    print("Asset attributes:")
    print(dir(asset))
    print("\nKey attributes:")
    for attr in dir(asset):
        if not attr.startswith('_'):
            try:
                val = getattr(asset, attr)
                if not callable(val):
                    print(f"  {attr}: {val}")
            except:
                pass
except Exception as e:
    print(f"Error: {e}")

# Try list_assets
try:
    assets = client.api.list_assets(status='active')
    if assets:
        asset = assets[0]
        print("\nFirst asset from list_assets:")
        print(dir(asset))
        print("\nKey attributes:")
        for attr in dir(asset):
            if not attr.startswith('_'):
                try:
                    val = getattr(asset, attr)
                    if not callable(val):
                        print(f"  {attr}: {val}")
                except:
                    pass
except Exception as e:
    print(f"Error list_assets: {e}")