import requests
import json

API_KEY = "PKDPEBVEYSCY3OGB9PXV"
SECRET_KEY = "TWCtMTS9S8L0j4Y0q7g7IXPiegH9gUmzZRzkl3k3"
BASE_URL = "https://paper-api.alpaca.markets"

headers = {
    "APCA-API-KEY-ID": API_KEY,
    "APCA-API-SECRET-KEY": SECRET_KEY
}

response = requests.get(f"{BASE_URL}/v2/account", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print("Success! Account data:")
    print(f"  Cash: {data.get('cash')}")
    print(f"  Buying Power: {data.get('buying_power')}")
    print(f"  Portfolio Value: {data.get('portfolio_value')}")
else:
    print("Error:", response.text)