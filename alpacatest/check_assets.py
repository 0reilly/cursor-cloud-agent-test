#!/usr/bin/env python3
import sys
sys.path.append('.')
from alpaca_client import AlpacaClient

client = AlpacaClient()

assets = client.get_available_crypto()
print(f"Total crypto assets: {len(assets)}")

# Check if MKR/USD is in the list
mkr_found = False
for asset in assets:
    if asset['symbol'] == 'MKR/USD':
        mkr_found = True
        print(f"MKR/USD found: {asset}")
        break

if not mkr_found:
    print("MKR/USD not found in active crypto assets")

# List all assets
print("\nFirst 10 crypto assets:")
for i, asset in enumerate(assets[:10]):
    print(f"{i+1}. {asset['symbol']} - {asset['name']} (status: {asset['status']}, tradable: {asset['tradable']})")