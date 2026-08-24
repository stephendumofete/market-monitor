"""
FILE: config.py
Purpose:
    Central place for default dashboard settings and available instruments.
"""

DEFAULT_ASSETS = ["USD/JPY", "EUR/USD", "GBP/USD"]

# These intervals are supported directly by the current yfinance API.
TIMEFRAMES = ["1min", "2min", "5min", "15min", "30min", "1h", "1day"]

DEFAULT_TIMEFRAME = "5min"
DEFAULT_LOOKBACK = 20
DEFAULT_REFRESH_SECONDS = 60

# These thresholds describe the numerical VER value only; they do not create
# a trading signal.
VER_COMPRESSION = 0.8
VER_NORMAL = 1.2
VER_STRONG = 1.5

ASSET_CHOICES = [
    "USD/JPY",
    "EUR/USD",
    "GBP/USD",
    "EUR/JPY",
    "GBP/JPY",
    "EUR/GBP",
    "AUD/USD",
    "USD/CAD",
    "USD/CHF",
    "NZD/USD",
    "CAD/JPY",
    "BTC/USD",
    "ETH/USD",
    "SOL/USD",
    "XRP/USD",
    "BNB/USD",
    "DOGE/USD",
    "XAU/USD",
]
