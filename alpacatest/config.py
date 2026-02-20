"""
Configuration for Crypto Trading Agent
"""

# Alpaca API Configuration
ALPACA_API_KEY = "PKHQYDABNWHVD5LVB6VB5SBSYL"
ALPACA_SECRET_KEY = "Zk9dcfKDGPLWecPW6LbTB3EYiHEZ7TxGE7zevWkSu19"
ALPACA_BASE_URL = "https://paper-api.alpaca.markets"

# Trading Configuration
INITIAL_CAPITAL = 50000  # Target starting capital
MAX_POSITIONS = 5  # Maximum number of simultaneous positions
MAX_POSITION_SIZE_PCT = 0.1  # Max 10% of capital per position
MIN_POSITION_SIZE = 100  # Minimum position size in USD
STOP_LOSS_PCT = 0.02  # 2% stop loss
TAKE_PROFIT_PCT = 0.05  # 5% take profit
TRAILING_STOP_PCT = 0.015  # 1.5% trailing stop

# Risk Management
MAX_DAILY_LOSS_PCT = 0.02  # Max 2% daily loss
MAX_TOTAL_LOSS_PCT = 0.1  # Max 10% total loss
VOLATILITY_ADJUSTMENT = True  # Adjust position size based on volatility

# Trading Strategy
TIME_FRAME = "5Min"  # 5-minute candles for momentum trading
LOOKBACK_PERIOD = 100  # Number of candles to analyze
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_SIGNAL_PERIOD = 9
BOLLINGER_PERIOD = 20
BOLLINGER_STD = 2.0

# Supported Crypto Symbols (focus on major coins)
CRYPTO_SYMBOLS = [
    "BTC/USD", "ETH/USD", "SOL/USD", "ADA/USD", "XRP/USD",
    "DOGE/USD", "LINK/USD", "AVAX/USD", "DOT/USD", "MATIC/USD",
    "UNI/USD", "AAVE/USD", "MKR/USD", "SNX/USD", "COMP/USD"
]

# Trading Hours (crypto is 24/7 but we can set preferences)
TRADING_HOURS = {
    "start_hour": 0,  # 12:00 AM UTC
    "end_hour": 24,   # 24/7 trading
}

# Performance Tracking
PERFORMANCE_LOG = "data/performance.json"
TRADE_LOG = "data/trades.csv"
ERROR_LOG = "data/errors.log"