"""Fast tick-by-tick backtest using Numba."""
from __future__ import annotations

import numpy as np
from numba import njit
from typing import Tuple


@njit(cache=True)
def _simulate_day(
    prices: np.ndarray,
    times: np.ndarray,
    brick_idx: np.ndarray,
    entry_signals: np.ndarray,
    base_qty: int,
    price_increment: float,
    gain_increment: float,
    gain_increment_pct: float,
    max_levels: int,
    stop_loss_pts: float,
    stop_loss_pct: float,
    tick_value: float,
    martingale: bool,
    slippage_pts: float,
    emolumentos_pct: float,
    preservation_stop: bool,
    preservation_levels: int,
    trailing_stop_value: float,
    daily_stop_loss: float,
    max_trades_per_day: int,
    start_time_ms: int,
    end_time_ms: int,
    force_close_eod: bool,
    force_close_daily_stop: bool,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    max_trades = 2000
    entry_times = np.empty(max_trades, dtype=np.int64)
    exit_times = np.empty(max_trades, dtype=np.int64)
    entry_prices = np.empty(max_trades, dtype=np.float64)
    exit_prices = np.empty(max_trades, dtype=np.float64)
    qtys = np.empty(max_trades, dtype=np.int32)
    pnls = np.empty(max_trades, dtype=np.float64)
    directions = np.empty(max_trades, dtype=np.int8)
    reasons = np.empty(max_trades, dtype=np.int8)

    trade_count = 0
    daily_pnl = 0.0

    direction = 0
    position_qty = 0
    position_cost = 0.0
    avg_price = 0.0
    target_price = 0.0
    stop_price = 0.0
    highest_profit = 0.0
    breakeven_stop = False

    level_prices = np.empty(10, dtype=np.float64)
    level_qtys = np.empty(10, dtype=np.int32)
    level_filled = np.empty(10, dtype=np.bool_)
    n_levels = 0

    last_processed_brick = -1
    forced_close_done = False

    for i in range(len(prices)):
        price = prices[i]
        time_ms = times[i]

        # EOD force-close: at end of trading window, close any open position at market
        if force_close_eod and not forced_close_done and time_ms > end_time_ms and direction != 0 and position_qty > 0:
            exit_p = price
            if direction == 1:
                exit_p = price - slippage_pts
                pnl = (exit_p - avg_price) * position_qty * tick_value
            else:
                exit_p = price + slippage_pts
                pnl = (avg_price - exit_p) * position_qty * tick_value
            financial_value_entry = avg_price * position_qty * tick_value
            financial_value_exit = exit_p * position_qty * tick_value
            pnl -= (financial_value_entry + financial_value_exit) * emolumentos_pct
            if trade_count < max_trades:
                entry_times[trade_count] = 0
                exit_times[trade_count] = time_ms
                entry_prices[trade_count] = avg_price
                exit_prices[trade_count] = exit_p
                qtys[trade_count] = position_qty
                pnls[trade_count] = pnl
                directions[trade_count] = direction
                reasons[trade_count] = 3  # EOD reason
                trade_count += 1
            daily_pnl += pnl
            direction = 0
            position_qty = 0
            position_cost = 0.0
            avg_price = 0.0
            target_price = 0.0
            stop_price = 0.0
            highest_profit = 0.0
            breakeven_stop = False
            n_levels = 0
            forced_close_done = True

        # Time filter
        if time_ms < start_time_ms or time_ms > end_time_ms:
            continue

        # Daily stop force-close: if open position and daily stop already hit, close it
        if force_close_daily_stop and direction != 0 and position_qty > 0 and daily_pnl <= -daily_stop_loss:
            exit_p = price
            if direction == 1:
                exit_p = price - slippage_pts
                pnl = (exit_p - avg_price) * position_qty * tick_value
            else:
                exit_p = price + slippage_pts
                pnl = (avg_price - exit_p) * position_qty * tick_value
            financial_value_entry = avg_price * position_qty * tick_value
            financial_value_exit = exit_p * position_qty * tick_value
            pnl -= (financial_value_entry + financial_value_exit) * emolumentos_pct
            if trade_count < max_trades:
                entry_times[trade_count] = 0
                exit_times[trade_count] = time_ms
                entry_prices[trade_count] = avg_price
                exit_prices[trade_count] = exit_p
                qtys[trade_count] = position_qty
                pnls[trade_count] = pnl
                directions[trade_count] = direction
                reasons[trade_count] = 4  # daily-stop reason
                trade_count += 1
            daily_pnl += pnl
            direction = 0
            position_qty = 0
            position_cost = 0.0
            avg_price = 0.0
            target_price = 0.0
            stop_price = 0.0
            highest_profit = 0.0
            breakeven_stop = False
            n_levels = 0
            continue

        bidx = brick_idx[i]

        if bidx > last_processed_brick:
            for bi in range(last_processed_brick + 1, bidx + 1):
                if bi < len(entry_signals) and direction == 0:
                    if daily_pnl <= -daily_stop_loss:
                        continue
                    sig = entry_signals[bi]
                    if sig != 0 and (max_trades_per_day == 0 or trade_count < max_trades_per_day):
                        direction = sig
                        n_levels = max_levels
                        anchor = price
                        effective_gain = gain_increment
                        effective_stop = stop_loss_pts
                        if gain_increment_pct > 0.0:
                            effective_gain = anchor * gain_increment_pct
                        if stop_loss_pct > 0.0:
                            effective_stop = anchor * stop_loss_pct
                        for li in range(n_levels):
                            if direction == 1:
                                level_prices[li] = anchor - li * price_increment
                            else:
                                level_prices[li] = anchor + li * price_increment
                            if martingale:
                                level_qtys[li] = base_qty * (2 ** li)
                            else:
                                level_qtys[li] = base_qty
                            level_filled[li] = False
                        position_qty = 0
                        position_cost = 0.0
                        avg_price = 0.0
                        target_price = 0.0
                        stop_price = 0.0
                        highest_profit = 0.0
                        breakeven_stop = False
            last_processed_brick = bidx

        if direction == 0:
            continue

        # Level fills with slippage
        for li in range(n_levels):
            if level_filled[li]:
                continue
            fill_price = 0.0
            if direction == 1 and price <= level_prices[li]:
                fill_price = level_prices[li] - slippage_pts
                level_filled[li] = True
                position_cost += fill_price * level_qtys[li]
                position_qty += level_qtys[li]
                avg_price = position_cost / position_qty
                target_price = avg_price + effective_gain
                stop_price = avg_price - effective_stop
            elif direction == -1 and price >= level_prices[li]:
                fill_price = level_prices[li] + slippage_pts
                level_filled[li] = True
                position_cost += fill_price * level_qtys[li]
                position_qty += level_qtys[li]
                avg_price = position_cost / position_qty
                target_price = avg_price - effective_gain
                stop_price = avg_price + effective_stop

            if preservation_stop and position_qty > 0 and not breakeven_stop:
                filled_levels = 0
                for fj in range(n_levels):
                    if level_filled[fj]:
                        filled_levels += 1
                if filled_levels >= preservation_levels:
                    buffer_pts = slippage_pts * 2 + 1.0
                    if direction == 1:
                        target_price = avg_price + buffer_pts
                    else:
                        target_price = avg_price - buffer_pts
                    breakeven_stop = True

        if position_qty == 0:
            continue

        if direction == 1:
            unreal = (price - avg_price) * position_qty * tick_value
        else:
            unreal = (avg_price - price) * position_qty * tick_value

        if unreal > highest_profit:
            highest_profit = unreal

        # REAL trailing stop: follows profit with a gap of trailing_stop_value
        if trailing_stop_value > 0 and highest_profit >= trailing_stop_value:
            if direction == 1:
                new_stop = avg_price + (highest_profit - trailing_stop_value) / (position_qty * tick_value)
                if new_stop > stop_price:
                    stop_price = new_stop
            else:
                new_stop = avg_price - (highest_profit - trailing_stop_value) / (position_qty * tick_value)
                if new_stop < stop_price:
                    stop_price = new_stop

        hit_target = False
        exit_p = 0.0
        if direction == 1 and price >= target_price:
            hit_target = True
            exit_p = target_price + slippage_pts
        elif direction == -1 and price <= target_price:
            hit_target = True
            exit_p = target_price - slippage_pts

        if hit_target:
            if direction == 1:
                pnl = (exit_p - avg_price) * position_qty * tick_value
            else:
                pnl = (avg_price - exit_p) * position_qty * tick_value
            financial_value_entry = avg_price * position_qty * tick_value
            financial_value_exit = exit_p * position_qty * tick_value
            pnl -= (financial_value_entry + financial_value_exit) * emolumentos_pct
            if trade_count < max_trades:
                entry_times[trade_count] = 0
                exit_times[trade_count] = time_ms
                entry_prices[trade_count] = avg_price
                exit_prices[trade_count] = exit_p
                qtys[trade_count] = position_qty
                pnls[trade_count] = pnl
                directions[trade_count] = direction
                reasons[trade_count] = 1
                trade_count += 1
            daily_pnl += pnl
            direction = 0
            position_qty = 0
            position_cost = 0.0
            avg_price = 0.0
            target_price = 0.0
            stop_price = 0.0
            highest_profit = 0.0
            breakeven_stop = False
            n_levels = 0
            continue

        hit_stop = False
        exit_p = price
        if direction == 1 and price <= stop_price:
            hit_stop = True
            exit_p = stop_price - slippage_pts
        elif direction == -1 and price >= stop_price:
            hit_stop = True
            exit_p = stop_price + slippage_pts

        if hit_stop:
            if direction == 1:
                pnl = (exit_p - avg_price) * position_qty * tick_value
            else:
                pnl = (avg_price - exit_p) * position_qty * tick_value
            financial_value_entry = avg_price * position_qty * tick_value
            financial_value_exit = exit_p * position_qty * tick_value
            pnl -= (financial_value_entry + financial_value_exit) * emolumentos_pct
            if trade_count < max_trades:
                entry_times[trade_count] = 0
                exit_times[trade_count] = time_ms
                entry_prices[trade_count] = avg_price
                exit_prices[trade_count] = exit_p
                qtys[trade_count] = position_qty
                pnls[trade_count] = pnl
                directions[trade_count] = direction
                reasons[trade_count] = 2
                trade_count += 1
            daily_pnl += pnl
            direction = 0
            position_qty = 0
            position_cost = 0.0
            avg_price = 0.0
            target_price = 0.0
            stop_price = 0.0
            highest_profit = 0.0
            breakeven_stop = False
            n_levels = 0
            continue

    return (
        entry_times[:trade_count],
        exit_times[:trade_count],
        entry_prices[:trade_count],
        exit_prices[:trade_count],
        qtys[:trade_count],
        pnls[:trade_count],
        directions[:trade_count],
        reasons[:trade_count],
    )


def simulate_day_fast(
    prices: np.ndarray,
    times: np.ndarray,
    brick_idx: np.ndarray,
    entry_signals: np.ndarray,
    base_qty: int = 1,
    price_increment: float = 100.0,
    gain_increment: float = 50.0,
    gain_increment_pct: float = 0.0,
    max_levels: int = 5,
    stop_loss_pts: float = 1000.0,
    stop_loss_pct: float = 0.0,
    tick_value: float = 0.20,
    martingale: bool = True,
    slippage_pts: float = 0.0,
    emolumentos_pct: float = 0.0,
    preservation_stop: bool = False,
    preservation_levels: int = 3,
    trailing_stop_value: float = 0.0,
    daily_stop_loss: float = 999999.0,
    max_trades_per_day: int = 0,
    start_time_ms: int = 0,
    end_time_ms: int = 86400000,
    force_close_eod: bool = False,
    force_close_daily_stop: bool = False,
):
    return _simulate_day(
        prices, times, brick_idx, entry_signals,
        base_qty, price_increment, gain_increment, gain_increment_pct, max_levels,
        stop_loss_pts, stop_loss_pct, tick_value, martingale,
        slippage_pts, emolumentos_pct,
        preservation_stop, preservation_levels, trailing_stop_value,
        daily_stop_loss, max_trades_per_day, start_time_ms, end_time_ms,
        force_close_eod, force_close_daily_stop,
    )
