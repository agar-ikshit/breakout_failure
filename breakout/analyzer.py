from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import yfinance as yf
from .indicators import compute_atr, find_local_maxima, find_local_minima
from .settings import K_FACTOR, LOCAL_WINDOW
import logging

logger = logging.getLogger(__name__)


def get_intraday_data(symbol: str, period: str = "5d", interval: str = "15m") -> Optional[pd.DataFrame]:
    """
    Fetch intraday OHLCV data for NSE stocks using Yahoo Finance.
    Example symbol: 'RELIANCE.NS', 'TCS.NS', etc.
    """
    try:
        logger.info(f"Fetching {symbol} data from Yahoo Finance...")
        df = yf.download(symbol, period=period, interval=interval, progress=False)

        if df.empty:
            logger.warning(f"No data for {symbol}")
            return None

        # Flatten multi-level columns (new yfinance versions)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        # Drop missing rows and reset index
        df = df.dropna().reset_index()

        # Normalize column names
        df.rename(columns={"Datetime": "Date"}, inplace=True, errors="ignore")

        # Basic check
        required_cols = {"Open", "High", "Low", "Close", "Volume"}
        if not required_cols.issubset(df.columns):
            logger.warning(f"Missing required OHLCV columns in {symbol}")
            return None

        return df

    except Exception as e:
        logger.error(f"Failed to fetch Yahoo Finance data for {symbol}: {e}")
        return None


def analyze_vrz_vwap(ticker, company_name, k=2, window=20):
    """Analyze breakout failures using only Yahoo Finance data (with fixes)"""
    full_ticker = ticker if ticker.endswith(".NS") else f"{ticker}.NS"
    try:
        df = yf.download(full_ticker, period="5d", interval="5m", progress=False)
        if df.empty:
            print(f"No data for {full_ticker}")
            return []

        # Handle multi-index columns (Yahoo Finance sometimes gives these)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df = df.dropna().reset_index()

        # Compute VWAP safely
        df["VWAP"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / df["Volume"].cumsum()

        # Compute ATR (simplified rolling high-low range)
        df["ATR"] = (df["High"] - df["Low"]).rolling(window=window, min_periods=1).mean()

        # Bands
        df["upper_band"] = df["VWAP"] + k * df["ATR"]
        df["lower_band"] = df["VWAP"] - k * df["ATR"]

        failures = []
        for i in range(1, len(df)):
            prev_close = df["Close"].iloc[i - 1]
            curr_close = df["Close"].iloc[i]
            prev_upper = df["upper_band"].iloc[i - 1]
            curr_upper = df["upper_band"].iloc[i]
            prev_lower = df["lower_band"].iloc[i - 1]
            curr_lower = df["lower_band"].iloc[i]

            # Detect upper band failure (cross from above to below)
            if prev_close > prev_upper and curr_close < curr_upper:
                failures.append({
                    "company": company_name,
                    "ticker": full_ticker,
                    "location": "Above → Below Upper Band",
                    "failure_time": df["Datetime"].iloc[i] if "Datetime" in df.columns else df["Date"].iloc[i],
                })

            # Detect lower band failure (cross from below to above)
            elif prev_close < prev_lower and curr_close > curr_lower:
                failures.append({
                    "company": company_name,
                    "ticker": full_ticker,
                    "location": "Below → Above Lower Band",
                    "failure_time": df["Datetime"].iloc[i] if "Datetime" in df.columns else df["Date"].iloc[i],
                })

        return failures

    except Exception as e:
        print(f"Error analyzing {ticker}: {e}")
        return []
