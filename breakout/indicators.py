from typing import List
import pandas as pd
import numpy as np

def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """
    Compute ATR (average true range) series.
    Expects df to have columns: High, Low, Close
    """
    h_l = df['High'] - df['Low']
    h_pc = (df['High'] - df['Close'].shift(1)).abs()
    l_pc = (df['Low'] - df['Close'].shift(1)).abs()
    tr = pd.concat([h_l, h_pc, l_pc], axis=1).max(axis=1)
    atr = tr.rolling(period, min_periods=1).mean()
    return atr

def find_local_maxima(series: pd.Series, window: int = 5) -> List[int]:
    maxima_idx = []
    n = len(series)
    if n == 0:
        return maxima_idx
    for i in range(window, n - window):
        current_val = series.iloc[i]
        if (series.iloc[i - window:i + window + 1].drop(series.index[i]) <= current_val).all():
            maxima_idx.append(i)
    return maxima_idx

def find_local_minima(series: pd.Series, window: int = 5) -> List[int]:
    minima_idx = []
    n = len(series)
    if n == 0:
        return minima_idx
    for i in range(window, n - window):
        current_val = series.iloc[i]
        if (series.iloc[i - window:i + window + 1].drop(series.index[i]) >= current_val).all():
            minima_idx.append(i)
    return minima_idx
