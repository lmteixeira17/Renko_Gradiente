"""Technical indicators: EMA, MACD, 2MV Padrão."""
from __future__ import annotations

import numpy as np
from dataclasses import dataclass


def ema(prices: np.ndarray, period: int) -> np.ndarray:
    """Exponential Moving Average."""
    alpha = 2.0 / (period + 1)
    result = np.empty_like(prices, dtype=np.float64)
    result[0] = prices[0]
    for i in range(1, len(prices)):
        result[i] = prices[i] * alpha + result[i - 1] * (1 - alpha)
    return result


def macd(
    prices: np.ndarray,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """MACD: returns (macd_line, signal_line, histogram)."""
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


@dataclass
class TwoMVSignal:
    """2MV Padrão color state."""
    color: str  # 'green', 'red', 'neutral'
    ema_fast: float
    ema_slow: float
    slope_fast: float
    slope_slow: float


def twomv_signal(
    prices: np.ndarray,
    ema_fast_arr: np.ndarray,
    ema_slow_arr: np.ndarray,
    idx: int,
) -> TwoMVSignal:
    """Determine 2MV Padrão color at index idx.

    Green: price > ema_fast > ema_slow, both slopes ascending.
    Red: price < ema_fast < ema_slow, both slopes descending.
    Neutral: all other cases.
    """
    price = prices[idx]
    ef = ema_fast_arr[idx]
    es = ema_slow_arr[idx]

    slope_fast = ema_fast_arr[idx] - ema_fast_arr[max(0, idx - 1)] if idx > 0 else 0.0
    slope_slow = ema_slow_arr[idx] - ema_slow_arr[max(0, idx - 1)] if idx > 0 else 0.0

    if price > ef and ef > es and slope_fast > 0 and slope_slow > 0:
        color = "green"
    elif price < ef and ef < es and slope_fast < 0 and slope_slow < 0:
        color = "red"
    else:
        color = "neutral"

    return TwoMVSignal(color=color, ema_fast=ef, ema_slow=es, slope_fast=slope_fast, slope_slow=slope_slow)
