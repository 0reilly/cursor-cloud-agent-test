import requests
import json

API_KEY = "PKDRGGN4ILLYPNMPB4AQFU24X5"
SECRET_KEY = "PKDRGGN4ILLYPNMPB4AQFU24X5"  # same as key
BASE_URL = "https://paper-api.alpaca.markets"

headers = {
    "APCA-API-KEY-ID": API_KEY,
    "APCA-API-SECRET-KEY": SECRET_KEY
}

# Test getting account
response = requests.get(f"{BASE_URL}/v2/account", headers=headers)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("Success! Account data:", response.json())
else:
    print("Error:", response.text)
    # Try with v2 in base URL
    headers2 = headers.copy()
    response2 = requests.get("https://paper-api.alpaca.markets/v2/account", headers=headers2)
    print(f"Second attempt status: {response2.status_code}")
    if response2.status_code == 200:
        print("Success with v2 in URL:", response2.json())
    else:
        print("Error2:", response2.text)