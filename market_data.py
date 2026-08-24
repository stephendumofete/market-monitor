"""
FILE: market_data.py
Purpose:
    Handles market-data retrieval through yfinance.

    This file keeps Yahoo Finance details separate from the calculations so
    the mathematical code does not depend on a particular data provider.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import yfinance as yf


# The dashboard uses friendly names such as USD/JPY, while Yahoo Finance
# uses symbols such as USDJPY=X for foreign exchange and BTC-USD for crypto.
YAHOO_SYMBOLS = {
    "USD/JPY": "USDJPY=X",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "EUR/JPY": "EURJPY=X",
    "GBP/JPY": "GBPJPY=X",
    "EUR/GBP": "EURGBP=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "USDCAD=X",
    "USD/CHF": "USDCHF=X",
    "NZD/USD": "NZDUSD=X",
    "CAD/JPY": "CADJPY=X",
    "BTC/USD": "BTC-USD",
    "ETH/USD": "ETH-USD",
    "SOL/USD": "SOL-USD",
    "XRP/USD": "XRP-USD",
    "BNB/USD": "BNB-USD",
    "DOGE/USD": "DOGE-USD",
    "XAU/USD":  "GC=F",
}


# yfinance accepts these intraday intervals. Yahoo does not provide every
# arbitrary multi-hour interval directly, so we keep the dashboard to the
# intervals the current yfinance API documents.
YAHOO_INTERVALS = {
    "1min": "1m",
    "2min": "2m",
    "5min": "5m",
    "15min": "15m",
    "30min": "30m",
    "1h": "60m",
    "1day": "1d",
}


def _yahoo_symbol(symbol: str) -> str:
    """Translate the dashboard symbol into Yahoo Finance's symbol."""
    try:
        return YAHOO_SYMBOLS[symbol]
    except KeyError as error:
        raise ValueError(f"Unsupported asset: {symbol}") from error


def _period_for_interval(interval: str) -> str:
    """Choose a small history window appropriate for the selected interval."""
    if interval in {"1m", "2m", "5m", "15m", "30m", "60m"}:
        return "5d"
    return "1mo"


def fetch_candles(
    symbol: str,
    interval: str,
    outputsize: int = 25,
) -> pd.DataFrame:
    """Download recent OHLC candles for one instrument."""
    yahoo_symbol = _yahoo_symbol(symbol)
    yahoo_interval = YAHOO_INTERVALS.get(interval, interval)

    data = yf.Ticker(yahoo_symbol).history(
        period=_period_for_interval(yahoo_interval),
        interval=yahoo_interval,
        auto_adjust=False,
        prepost=False,
    )

    if data.empty:
        raise RuntimeError(f"No candle data returned for {symbol}.")

    data = data.rename(columns=str.lower)
    required = ["open", "high", "low", "close"]
    data = data.dropna(subset=required)

    # Keep only the most recent rows needed by the calculations.
    data = data.tail(outputsize).copy()
    data.index.name = "datetime"

    return data


def fetch_multiple_candles(
    symbols: Iterable[str],
    interval: str,
    outputsize: int = 25,
) -> dict[str, pd.DataFrame]:
    """Fetch the same amount of OHLC history for each selected asset."""
    return {
        symbol: fetch_candles(symbol, interval, outputsize)
        for symbol in symbols
    }


def fetch_spot_prices(symbols: Iterable[str]) -> dict[str, float]:
    """Fetch the latest available market price for each selected asset.

    fast_info provides a current/latest price field without requiring us to
    treat the most recent completed candle close as the current spot price.
    A recent 1-minute close is used as a fallback if fast_info is unavailable.
    """
    spot_prices: dict[str, float] = {}

    for symbol in symbols:
        yahoo_symbol = _yahoo_symbol(symbol)
        ticker = yf.Ticker(yahoo_symbol)

        try:
            spot = ticker.fast_info.get("last_price")
        except Exception:
            spot = None

        if spot is None or pd.isna(spot):
            fallback = ticker.history(
                period="1d",
                interval="1m",
                auto_adjust=False,
                prepost=False,
            )
            if fallback.empty:
                raise RuntimeError(f"Could not obtain a spot price for {symbol}.")
            spot = fallback["Close"].dropna().iloc[-1]

        spot_prices[symbol] = float(spot)

    return spot_prices
