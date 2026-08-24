"""
FILE: calculations.py
Purpose:
    Contains the mathematical part of the market monitor.

The functions here do not know anything about Streamlit or the API.
They receive pandas Series/DataFrames and return numerical results.

That separation makes the mathematics easier to read, test, and change.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def log_returns(close: pd.Series) -> pd.Series:
    """
    Calculate logarithmic returns.

    r_t = ln(P_t / P_(t-1))

    Log returns are useful here because they express price changes
    proportionally and can be added across consecutive periods.
    """
    return np.log(close / close.shift(1)).dropna()


def price_estimation(
    candles: pd.DataFrame,
    lookback: int = 20,
) -> dict[str, float]:
    """
    Estimate a one-standard-deviation and two-standard-deviation price range.

    Realized volatility here means the standard deviation of the last
    `lookback` log returns. It is a windowed volatility measure, not an
    annualized volatility figure.
    """
    closes = candles["close"].astype(float)
    returns = log_returns(closes)

    if len(returns) < lookback:
        raise ValueError("Not enough returns for price estimation.")

    recent_returns = returns.tail(lookback)
    realized_volatility = recent_returns.std()

    last_close = float(closes.iloc[-1])

    # Multiplying volatility by price converts the proportional volatility
    # into an approximate price-distance for the selected instrument.
    expected_move = last_close * realized_volatility
    expected_high = last_close + expected_move
    expected_low = last_close - expected_move

    two_sigma_move = last_close * (2 * realized_volatility)
    estimated_high = last_close + two_sigma_move
    estimated_low = last_close - two_sigma_move

    # The earlier spreadsheet idea called this "distance from previous
    # range", but its original formula mixed a price with log returns.
    # Here we use a dimensionally consistent range position instead:
    # (close - range_low) / (range_high - range_low).
    range_window = closes.tail(lookback)
    range_high = float(range_window.max())
    range_low = float(range_window.min())
    range_width = range_high - range_low

    if range_width == 0:
        range_position = math.nan
    else:
        range_position = (last_close - range_low) / range_width

    return {
        "realized_volatility": float(realized_volatility),
        "last_close": last_close,
        "expected_move": float(expected_move),
        "expected_high": float(expected_high),
        "expected_low": float(expected_low),
        "two_sigma_move": float(two_sigma_move),
        "estimated_high": float(estimated_high),
        "estimated_low": float(estimated_low),
        "range_high": range_high,
        "range_low": range_low,
        "range_position": float(range_position),
    }


def volatility_expansion_ratio(
    candles: pd.DataFrame,
    short_window: int = 10,
    long_window: int = 20,
) -> dict[str, float | str]:
    """
    Compare recent volatility with the longer volatility window.

    VER = standard_deviation(10 returns) / standard_deviation(20 returns)

    A value above 1 means the recent 10-period volatility is larger than
    the 20-period volatility. The labels are descriptive thresholds, not
    trading signals.
    """
    returns = log_returns(candles["close"].astype(float))

    short_volatility = returns.tail(short_window).std()
    long_volatility = returns.tail(long_window).std()

    if long_volatility == 0:
        ratio = math.nan
    else:
        ratio = short_volatility / long_volatility

    if math.isnan(ratio):
        classification = "undefined"
    elif ratio < 0.8:
        classification = "compression"
    elif ratio < 1.2:
        classification = "normal"
    elif ratio < 1.5:
        classification = "expansion"
    else:
        classification = "strong expansion"

    return {
        "short_volatility": float(short_volatility),
        "long_volatility": float(long_volatility),
        "ratio": float(ratio),
        "classification": classification,
    }


def statistical_skewness(
    candles: pd.DataFrame,
    lookback: int = 20,
) -> float:
    """
    Calculate Fisher-Pearson sample skewness of the recent log returns.

    Skewness measures asymmetry in a distribution. Using returns instead of
    raw price levels makes the statistic more appropriate for comparing
    different instruments and price scales.
    """
    returns = log_returns(candles["close"].astype(float)).tail(lookback)

    if len(returns) < lookback:
        raise ValueError("Not enough returns for skewness.")

    return float(returns.skew())


def mean_reversion_zscore(
    candles: pd.DataFrame,
    lookback: int = 20,
) -> dict[str, float]:
    """
    Calculate a price Z-score relative to the recent mean.

    Z = (current_price - mean_20) / standard_deviation_20

    This is a standardized distance from the recent mean. It does not
    predict that a reversal will happen; it only describes where the
    current price sits relative to the recent distribution.
    """
    closes = candles["close"].astype(float).tail(lookback)

    mean_price = closes.mean()
    standard_deviation = closes.std()
    current_price = float(closes.iloc[-1])

    if standard_deviation == 0:
        z_score = math.nan
    else:
        z_score = (current_price - mean_price) / standard_deviation

    return {
        "current_price": current_price,
        "mean": float(mean_price),
        "standard_deviation": float(standard_deviation),
        "z_score": float(z_score),
    }


def return_correlation(
    candles_by_symbol: dict[str, pd.DataFrame],
    lookback: int = 20,
) -> pd.DataFrame:
    """
    Calculate pairwise Pearson correlation between recent log returns.

    Correlating returns rather than price levels measures whether the assets'
    recent movements have tended to move together or in opposite directions.
    """
    return_series: dict[str, pd.Series] = {}

    for symbol, candles in candles_by_symbol.items():
        returns = log_returns(candles["close"].astype(float)).tail(lookback)
        return_series[symbol] = returns.reset_index(drop=True)

    returns_frame = pd.DataFrame(return_series)

    # Pearson correlation ranges from -1 to +1:
    # +1 = move together, 0 = little linear relationship, -1 = move opposite.
    return returns_frame.corr(method="pearson")


def calculate_all(
    candles_by_symbol: dict[str, pd.DataFrame],
    lookback: int = 20,
) -> dict[str, dict]:
    """Run every dashboard calculation for every selected asset."""
    results: dict[str, dict] = {}

    for symbol, candles in candles_by_symbol.items():
        results[symbol] = {
            "price_estimation": price_estimation(candles, lookback),
            "volatility_expansion": volatility_expansion_ratio(candles),
            "skewness": statistical_skewness(candles, lookback),
            "mean_reversion": mean_reversion_zscore(candles, lookback),
        }

    results["correlation"] = return_correlation(candles_by_symbol, lookback)

    return results
