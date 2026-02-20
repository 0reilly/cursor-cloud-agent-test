import alpaca_trade_api as tradeapi

API_KEY = "PKDRGGN4ILLYPNMPB4AQFU24X5"
SECRET_KEY = ""  # unknown
BASE_URL = "https://paper-api.alpaca.markets/v2"

try:
    api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')
    account = api.get_account()
    print("Success! Account:", account)
except Exception as e:
    print(f"Error: {e}")
    # Try with base URL without /v2
    try:
        api = tradeapi.REST(API_KEY, SECRET_KEY, "https://paper-api.alpaca.markets", api_version='v2')
        account = api.get_account()
        print("Success with base URL without /v2:", account)
    except Exception as e2:
        print(f"Second error: {e2}")