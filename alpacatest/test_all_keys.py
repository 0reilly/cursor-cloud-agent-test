import requests
import json

# Test all possible key combinations
key_pairs = [
    ("PKDRGGN4ILLYPNMPB4AQFU24X5", "PKDRGGN4ILLYPNMPB4AQFU24X5", "original self"),
    ("PKHQYDABNWHVD5LVB6VB5SBSYL", "Zk9dcfKDGPLWecPW6LbTB3EYiHEZ7TxGE7zevWkSu19", "new pair"),
    # Also test original key with empty secret
    ("PKDRGGN4ILLYPNMPB4AQFU24X5", "", "original empty"),
]

BASE_URL = "https://paper-api.alpaca.markets"

for api_key, secret_key, description in key_pairs:
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"API Key: {api_key[:10]}...{api_key[-10:]}")
    print(f"Secret: {secret_key[:10]}...{secret_key[-10:] if secret_key else 'None'}")
    
    headers = {
        "APCA-API-KEY-ID": api_key,
        "APCA-API-SECRET-KEY": secret_key
    }
    
    try:
        response = requests.get(f"{BASE_URL}/v2/account", headers=headers, timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ SUCCESS! Account authenticated")
            print(f"  Cash: {data.get('cash')}")
            print(f"  Buying Power: {data.get('buying_power')}")
            print(f"  Portfolio Value: {data.get('portfolio_value')}")
            print(f"  Equity: {data.get('equity')}")
            print(f"  Status: {data.get('status')}")
            break  # Stop at first success
        else:
            print(f"❌ Failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

print(f"\n{'='*60}")
print("Testing complete. If none worked, check:")
print("1. Make sure you're using PAPER trading keys (not live)")
print("2. Check the Alpaca dashboard: https://app.alpaca.markets/paper/dashboard/overview")
print("3. Keys should be: API Key ID (starts with PK) and Secret Key (longer)")
print("4. The endpoint should be: https://paper-api.alpaca.markets/v2")