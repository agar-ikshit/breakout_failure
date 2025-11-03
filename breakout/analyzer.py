from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np
import yfinance as yf
import logging
import plotly.graph_objects as go
from .indicators import compute_atr, find_local_maxima, find_local_minima
from .settings import K_FACTOR, LOCAL_WINDOW

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# ✅ 1. Data Fetching
# -----------------------------------------------------------------------------
def get_intraday_data(symbol: str, period: str = "5d", interval: str = "15m") -> Optional[pd.DataFrame]:
    """
    Fetch intraday OHLCV data for NSE stocks using Yahoo Finance.
    Example symbol: 'RELIANCE.NS', 'TCS.NS', etc.
    """
    try:
        logger.info(f"Fetching {symbol} data from Yahoo Finance...")
        df = yf.download(symbol, period=period, interval=interval, progress=False, ignore_tz=True)

        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return None

        # Flatten multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        # Drop NA and reset index
        df = df.dropna().reset_index()

        # Normalize column name
        if "Datetime" in df.columns:
            df.rename(columns={"Datetime": "Date"}, inplace=True)

        required_cols = {"Open", "High", "Low", "Close", "Volume"}
        if not required_cols.issubset(df.columns):
            logger.warning(f"Missing required OHLCV columns in {symbol}")
            return None

        return df

    except Exception as e:
        logger.error(f"Error fetching Yahoo data for {symbol}: {e}")
        return None

# -----------------------------------------------------------------------------
# ✅ 2. VRZ Analysis
# -----------------------------------------------------------------------------
def analyze_vrz_vwap(
    ticker: str,
    company_name: str,
    k: float = 2.0,
    window: int = 20,
    period: str = "5d",
    interval: str = "5m"
) -> Tuple[List[Dict], pd.DataFrame]:
    """
    Analyze VRZ (Volatility Range Zone) breakout failures using VWAP bands.
    """
    full_ticker = ticker if ticker.endswith(".NS") else f"{ticker}.NS"
    try:
        df = get_intraday_data(full_ticker, period=period, interval=interval)
        if df is None or df.empty:
            logger.warning(f"No data for {full_ticker}")
            return [], pd.DataFrame()

        # Compute VWAP
        df["VWAP"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / df["Volume"].cumsum()

        # Compute ATR (simple rolling high-low range)
        df["ATR"] = (df["High"] - df["Low"]).rolling(window=window, min_periods=1).mean()

        # Upper and lower VRZ bands
        df["upper_band"] = df["VWAP"] + k * df["ATR"]
        df["lower_band"] = df["VWAP"] - k * df["ATR"]

        failures = []
        for i in range(1, len(df)):
            prev_close, curr_close = df["Close"].iloc[i - 1], df["Close"].iloc[i]
            prev_upper, curr_upper = df["upper_band"].iloc[i - 1], df["upper_band"].iloc[i]
            prev_lower, curr_lower = df["lower_band"].iloc[i - 1], df["lower_band"].iloc[i]

            # Detect upper band failure (cross from above → below)
            if prev_close > prev_upper and curr_close < curr_upper:
                failures.append({
                    "company": company_name,
                    "ticker": full_ticker,
                    "location": "VRZ High Failure",
                    "failure_time": df["Date"].iloc[i],
                })

            # Detect lower band failure (cross from below → above)
            elif prev_close < prev_lower and curr_close > curr_lower:
                failures.append({
                    "company": company_name,
                    "ticker": full_ticker,
                    "location": "VRZ Low Failure",
                    "failure_time": df["Date"].iloc[i],
                })

        return failures, df

    except Exception as e:
        logger.error(f"Error analyzing {ticker}: {e}")
        return [], pd.DataFrame()

# -----------------------------------------------------------------------------
# ✅ 3. Visualization
# -----------------------------------------------------------------------------
def plot_vrz_failures(df: pd.DataFrame, failures: List[Dict], company_name: str, ticker: str):
    """
    Plot candlestick chart with VRZ High/Low bands and mark breakout failure points.
    """
    if df is None or df.empty:
        logger.warning(f"No data to plot for {ticker}")
        return None

    # Ensure datetime conversion
    time_col = "Date"
    df[time_col] = pd.to_datetime(df[time_col])

    fig = go.Figure()

    # 1️⃣ Candlestick Chart
    fig.add_trace(go.Candlestick(
        x=df[time_col],
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price",
        increasing_line_color="lime",
        decreasing_line_color="red",
        showlegend=True
    ))

    # 2️⃣ VRZ Bands
    fig.add_trace(go.Scatter(
        x=df[time_col],
        y=df["upper_band"],
        line=dict(color="orange", width=1.5, dash="dash"),
        name="VRZ High"
    ))
    fig.add_trace(go.Scatter(
        x=df[time_col],
        y=df["lower_band"],
        line=dict(color="cyan", width=1.5, dash="dash"),
        name="VRZ Low"
    ))

    # 3️⃣ Plot Failures
    high_fail_x, high_fail_y = [], []
    low_fail_x, low_fail_y = [], []

    for f in failures:
        ft = pd.to_datetime(f["failure_time"])
        loc = f["location"]

        # Find nearest time (avoid exact match issues)
        idx = (df[time_col] - ft).abs().idxmin()
        y_val = df.loc[idx, "Close"]

        if "High" in loc:
            high_fail_x.append(ft)
            high_fail_y.append(y_val)
        else:
            low_fail_x.append(ft)
            low_fail_y.append(y_val)

    # Add all failures in one trace each (cleaner legend)
    if high_fail_x:
        fig.add_trace(go.Scatter(
            x=high_fail_x, y=high_fail_y,
            mode="markers",
            marker=dict(color="red", size=10, symbol="x"),
            name="🔴 VRZ High Failures"
        ))

    if low_fail_x:
        fig.add_trace(go.Scatter(
            x=low_fail_x, y=low_fail_y,
            mode="markers",
            marker=dict(color="green", size=10, symbol="x"),
            name="🟢 VRZ Low Failures"
        ))

    # 4️⃣ Styling
    fig.update_layout(
        title=f"{company_name} ({ticker}) — VRZ Breakout Failures",
        xaxis_title="Time",
        yaxis_title="Price",
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=600,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified"
    )

    return fig
