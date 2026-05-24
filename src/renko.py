"""Renko brick builder from tick stream — Numba-accelerated.

Implements Nelogica-style Renko:
  Brick size = (R * tick_size) - tick_size
  Reversal requires 2 * brick_size movement.
"""
from __future__ import annotations

import numpy as np
from numba import njit
from dataclasses import dataclass
from typing import List


@dataclass
class RenkoBrick:
    open_price: float
    close_price: float
    high_price: float
    low_price: float
    direction: int  # +1 up (green), -1 down (red)
    start_time_ms: int
    end_time_ms: int
    n_ticks: int


@njit(cache=True)
def _build_renko_numba(
    prices: np.ndarray,
    times: np.ndarray,
    tick_size: float,
    r_value: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Build Renko bricks. Returns arrays of brick data."""
    brick_size = (r_value * tick_size) - tick_size
    reversal_size = 2 * brick_size

    n = len(prices)
    # Pre-allocate arrays (assume max ~n/10 bricks)
    max_bricks = n // 2
    opens = np.empty(max_bricks, dtype=np.float64)
    closes = np.empty(max_bricks, dtype=np.float64)
    highs = np.empty(max_bricks, dtype=np.float64)
    lows = np.empty(max_bricks, dtype=np.float64)
    dirs = np.empty(max_bricks, dtype=np.int8)
    starts = np.empty(max_bricks, dtype=np.int64)
    ends = np.empty(max_bricks, dtype=np.int64)
    tick_counts = np.empty(max_bricks, dtype=np.int32)

    brick_count = 0
    current_high = prices[0]
    current_low = prices[0]
    current_open = prices[0]
    current_direction = 0
    start_time = times[0]
    n_ticks = 0

    for i in range(n):
        price = prices[i]
        t = times[i]
        n_ticks += 1
        if price > current_high:
            current_high = price
        if price < current_low:
            current_low = price

        if current_direction == 0:
            if price >= current_open + brick_size:
                current_direction = 1
            elif price <= current_open - brick_size:
                current_direction = -1
            continue

        if current_direction == 1:
            if price >= current_open + brick_size:
                # Close up brick
                if brick_count < max_bricks:
                    opens[brick_count] = current_open
                    closes[brick_count] = current_open + brick_size
                    highs[brick_count] = current_high
                    lows[brick_count] = current_low
                    dirs[brick_count] = 1
                    starts[brick_count] = start_time
                    ends[brick_count] = t
                    tick_counts[brick_count] = n_ticks
                    brick_count += 1
                current_open = current_open + brick_size
                current_high = price
                current_low = price
                start_time = t
                n_ticks = 0
            elif price <= current_open - reversal_size:
                # Reversal to down
                if brick_count < max_bricks:
                    opens[brick_count] = current_open
                    closes[brick_count] = current_open + brick_size
                    highs[brick_count] = current_high
                    lows[brick_count] = current_low
                    dirs[brick_count] = 1
                    starts[brick_count] = start_time
                    ends[brick_count] = t
                    tick_counts[brick_count] = n_ticks
                    brick_count += 1
                current_open = current_open - reversal_size + brick_size
                current_high = price
                current_low = price
                current_direction = -1
                start_time = t
                n_ticks = 0
        else:
            if price <= current_open - brick_size:
                if brick_count < max_bricks:
                    opens[brick_count] = current_open
                    closes[brick_count] = current_open - brick_size
                    highs[brick_count] = current_high
                    lows[brick_count] = current_low
                    dirs[brick_count] = -1
                    starts[brick_count] = start_time
                    ends[brick_count] = t
                    tick_counts[brick_count] = n_ticks
                    brick_count += 1
                current_open = current_open - brick_size
                current_high = price
                current_low = price
                start_time = t
                n_ticks = 0
            elif price >= current_open + reversal_size:
                if brick_count < max_bricks:
                    opens[brick_count] = current_open
                    closes[brick_count] = current_open - brick_size
                    highs[brick_count] = current_high
                    lows[brick_count] = current_low
                    dirs[brick_count] = -1
                    starts[brick_count] = start_time
                    ends[brick_count] = t
                    tick_counts[brick_count] = n_ticks
                    brick_count += 1
                current_open = current_open + reversal_size - brick_size
                current_high = price
                current_low = price
                current_direction = 1
                start_time = t
                n_ticks = 0

    return (
        opens[:brick_count],
        closes[:brick_count],
        highs[:brick_count],
        lows[:brick_count],
        dirs[:brick_count],
        starts[:brick_count],
        ends[:brick_count],
        tick_counts[:brick_count],
    )


def build_renko(
    prices: np.ndarray,
    times: np.ndarray,
    tick_size: float,
    r_value: int,
) -> list[RenkoBrick]:
    """Build Renko bricks from tick prices."""
    result = _build_renko_numba(prices, times, tick_size, r_value)
    bricks = []
    for i in range(len(result[0])):
        bricks.append(
            RenkoBrick(
                open_price=result[0][i],
                close_price=result[1][i],
                high_price=result[2][i],
                low_price=result[3][i],
                direction=int(result[4][i]),
                start_time_ms=int(result[5][i]),
                end_time_ms=int(result[6][i]),
                n_ticks=int(result[7][i]),
            )
        )
    return bricks
