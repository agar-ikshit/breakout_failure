from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from .indicators import compute_atr, find_local_maxima, find_local_minima
from .settings import K_FACTOR, LOCAL_WINDOW
import logging

logger = logging.getLogger(__name__)


def download_ohlcv(symbol: str, period: str = "5d", interval: str = "1d") -> Optional[pd.DataFrame]:
    """
    Fetch OHLCV data using yfinance.
    Automatically tries with '', '.NS', and '.BO' suffixes.
    """
    for suffix in ["", ".NS", ".BO"]:
        try:
            df = yf.download(symbol + suffix, period=period, interval=interval, progress=False, auto_adjust=False)
            if not df.empty:
                df = df.reset_index()
                df.columns = [c.capitalize() for c in df.columns]
                if "Datetime" not in df.columns:
                    df.rename(columns={"Date": "Datetime"}, inplace=True)
                return df
        except Exception as e:
            logger.warning("Attempt with %s%s failed: %s", symbol, suffix, e)
            continue

    logger.error("Failed to fetch data for %s", symbol)
    return None


def analyze_vrz_vwap(
    ticker: str,
    company_name: str,
    interval: str = "1d",
    period: str = "5d",
    k: float = K_FACTOR,
    window: int = LOCAL_WINDOW
) -> Optional[List[Dict]]:
    """
    Analyze a single ticker for breakout failures using VRZ logic and ATR,
    using yfinance OHLCV data.
    """
    df = download_ohlcv(ticker, period=period, interval=interval)
    if df is None:
        logger.warning("No candle data for %s", ticker)
        return None

    # Compute ATR
    df["H-L"] = df["High"] - df["Low"]
    df["H-C"] = (df["High"] - df["Close"].shift(1)).abs()
    df["L-C"] = (df["Low"] - df["Close"].shift(1)).abs()
    df["TR"] = df[["H-L", "H-C", "L-C"]].max(axis=1)
    df["ATR"] = compute_atr(df)

    df["VRZ_High"] = np.nan
    df["VRZ_Low"] = np.nan

    # Local extrema detection
    local_max_idx = find_local_maxima(df["High"], window)
    for i in local_max_idx:
        atr_val = df["ATR"].iloc[i]
        if pd.notna(atr_val):
            df.at[i, "VRZ_High"] = df["High"].iloc[i] + k * atr_val

    local_min_idx = find_local_minima(df["Low"], window)
    for i in local_min_idx:
        atr_val = df["ATR"].iloc[i]
        if pd.notna(atr_val):
            df.at[i, "VRZ_Low"] = df["Low"].iloc[i] - k * atr_val

    # Forward-fill levels
    df["VRZ_High_ffill"] = df["VRZ_High"].ffill()
    df["VRZ_Low_ffill"] = df["VRZ_Low"].ffill()

    breakout_failures = []
    lookahead_bars = 10

    # VRZ High breakout failure
    for i in range(len(df)):
        vrz_high_val = df["VRZ_High_ffill"].iloc[i]
        if pd.notna(vrz_high_val) and df["Close"].iloc[i] > vrz_high_val:
            for j in range(i + 1, min(i + lookahead_bars + 1, len(df))):
                if df["Close"].iloc[j] < vrz_high_val:
                    breakout_failures.append({
                        "company": company_name,
                        "ticker": ticker,
                        "failure_time": pd.to_datetime(df["Datetime"].iloc[j]),
                        "location": "VRZ High",
                        "break_time": pd.to_datetime(df["Datetime"].iloc[i]),
                        "close_at_failure": float(df["Close"].iloc[j])
                    })
                    break

    # VRZ Low breakout failure
    for i in range(len(df)):
        vrz_low_val = df["VRZ_Low_ffill"].iloc[i]
        if pd.notna(vrz_low_val) and df["Close"].iloc[i] < vrz_low_val:
            for j in range(i + 1, min(i + lookahead_bars + 1, len(df))):
                if df["Close"].iloc[j] > vrz_low_val:
                    breakout_failures.append({
                        "company": company_name,
                        "ticker": ticker,
                        "failure_time": pd.to_datetime(df["Datetime"].iloc[j]),
                        "location": "VRZ Low",
                        "break_time": pd.to_datetime(df["Datetime"].iloc[i]),
                        "close_at_failure": float(df["Close"].iloc[j])
                    })
                    break

    return breakout_failures
