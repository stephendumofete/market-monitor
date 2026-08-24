"""
FILE: app.py
Purpose:
    Streamlit entry point for the Market Research Monitor.

Run this file from the project directory with:

    streamlit run app.py

The browser is only the display layer. Market-data retrieval lives in
market_data.py, while all mathematical calculations live in calculations.py.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import streamlit as st
from calculations import calculate_all
from config import (
    ASSET_CHOICES,
    DEFAULT_ASSETS,
    DEFAULT_LOOKBACK,
    DEFAULT_REFRESH_SECONDS,
    DEFAULT_TIMEFRAME,
    TIMEFRAMES,
)
from market_data import fetch_multiple_candles, fetch_spot_prices


st.set_page_config(
    page_title="Ibsteve Market Research Monitor",
    layout="wide",
)

st.title("Market Research Monitor")
st.caption(
    "Numerical monitoring only — no trading signals or predictions."
)

# These controls are deliberately simple. Changing them changes the data
# passed into the same calculation functions; the mathematics is not changed.
asset_columns = st.columns(3)

selected_assets: list[str] = []

for index, column in enumerate(asset_columns):
    default_asset = DEFAULT_ASSETS[index]
    default_index = ASSET_CHOICES.index(default_asset)

    selected = column.selectbox(
        f"Asset {index + 1}",
        ASSET_CHOICES,
        index=default_index,
        key=f"asset_{index}",
    )
    selected_assets.append(selected)

# Preventing duplicate assets makes the three-asset correlation table easier
# to interpret.
if len(set(selected_assets)) != len(selected_assets):
    st.warning("Please select three different assets.")
    st.stop()

control_columns = st.columns(3)

timeframe = control_columns[0].selectbox(
    "Timeframe",
    TIMEFRAMES,
    index=TIMEFRAMES.index(DEFAULT_TIMEFRAME),
)

lookback = control_columns[1].number_input(
    "Lookback periods",
    min_value=20,
    max_value=200,
    value=DEFAULT_LOOKBACK,
    step=1,
)

refresh_seconds = control_columns[2].number_input(
    "Refresh interval (seconds)",
    min_value=15,
    max_value=600,
    value=DEFAULT_REFRESH_SECONDS,
    step=15,
)

st.divider()


@st.fragment(run_every=refresh_seconds)
def live_monitor() -> None:
    """Fetch and display the current research data."""
    # We need one extra candle for the first log return, plus a small buffer.
    outputsize = max(int(lookback) + 5, 25)

    try:
        candles = fetch_multiple_candles(
            selected_assets,
            timeframe,
            outputsize,
        )
        spot_prices = fetch_spot_prices(selected_assets)

        results = calculate_all(candles, int(lookback))

    except Exception as error:
        st.error(f"Data update failed: {error}")
        return

    st.caption(
        "Last successful update: "
        + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    )

    # Spot price is displayed separately from the last completed candle close.
    # This keeps the live/current price distinct from the OHLC calculation data.
    st.header("Current Spot Prices")
    spot_columns = st.columns(3)

    for column, symbol in zip(spot_columns, selected_assets):
        column.metric(symbol, format_price(symbol, spot_prices[symbol]))

    st.header("1. Price Estimation")

    for symbol in selected_assets:
        values = results[symbol]["price_estimation"]

        st.subheader(symbol)

        price_columns = st.columns(6)

        price_columns[0].metric(
            "Last close",
            format_price(symbol, values["last_close"]),
        )
        price_columns[1].metric(
            "Realized volatility",
            f'{values["realized_volatility"]:.6f}',
        )
        price_columns[2].metric(
            "Expected move",
            format_price(symbol, values["expected_move"]),
        )
        price_columns[3].metric(
            "Expected high",
            format_price(symbol, values["expected_high"]),
        )
        price_columns[4].metric(
            "Expected low",
            format_price(symbol, values["expected_low"]),
        )
        price_columns[5].metric(
            "Range position",
            f'{values["range_position"]:.3f}',
        )

        sigma_columns = st.columns(3)
        sigma_columns[0].write(
            f'2σ move: **{format_price(symbol, values["two_sigma_move"])}**'
        )
        sigma_columns[1].write(
            f'2σ estimated high: **{format_price(symbol, values["estimated_high"])}**'
        )
        sigma_columns[2].write(
            f'2σ estimated low: **{format_price(symbol, values["estimated_low"])}**'
        )

    st.header("2. Volatility Expansion Ratio")

    ver_rows = []

    for symbol in selected_assets:
        values = results[symbol]["volatility_expansion"]

        ver_rows.append(
            {
                "Asset": symbol,
                "10-period volatility": values["short_volatility"],
                "20-period volatility": values["long_volatility"],
                "VER": values["ratio"],
                "Description": values["classification"],
            }
        )

    st.dataframe(
        pd.DataFrame(ver_rows),
        hide_index=True,
        width="stretch",
    )

    st.header("3. Statistical Skewness")

    skew_rows = []

    for symbol in selected_assets:
        skew_rows.append(
            {
                "Asset": symbol,
                "20-period statistical skewness": results[symbol]["skewness"],
            }
        )

    st.dataframe(
        pd.DataFrame(skew_rows),
        hide_index=True,
        width="stretch",
    )

    st.header("4. Mean Reversion Z-Score")

    zscore_rows = []

    for symbol in selected_assets:
        values = results[symbol]["mean_reversion"]

        zscore_rows.append(
            {
                "Asset": symbol,
                "Current price": values["current_price"],
                "20-period mean": values["mean"],
                "20-period standard deviation": values["standard_deviation"],
                "Z-score": values["z_score"],
            }
        )

    st.dataframe(
        pd.DataFrame(zscore_rows),
        hide_index=True,
        width="stretch",
    )

    st.header("5. Return Correlation")

    st.dataframe(
        results["correlation"],
        width="stretch",
    )

    st.header("6. Last 20 OHLC Candles")

    for symbol in selected_assets:
        st.subheader(symbol)

        display_data = candles[symbol].tail(lookback).copy()
        display_data = display_data.reset_index()
        display_data["datetime"] = display_data["datetime"].dt.strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        columns = ["datetime", "open", "high", "low", "close"]

        if "volume" in display_data.columns:
            columns.append("volume")

        st.dataframe(
            display_data[columns],
            hide_index=True,
            width="stretch",
        )


def format_price(symbol: str, value: float) -> str:
    """
    Format prices for display without changing their underlying value.

    JPY-quoted forex pairs commonly use three decimal places, while many
    non-JPY forex pairs use five. Crypto is shown with two by default.
    This is presentation only; all calculations use the full numeric value.
    """
    if "/" not in symbol:
        return f"{value:,.2f}"

    base, quote = symbol.split("/")

    if base in {"BTC", "ETH", "SOL", "XRP", "BNB", "DOGE", "ADA"}:
        decimals = 2
    elif quote == "JPY":
        decimals = 3
    else:
        decimals = 5

    return f"{value:,.{decimals}f}"


live_monitor()
