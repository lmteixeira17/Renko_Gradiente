"""Backtest engine for EA Gradiente Linear using BTP tick data."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from btp_loader import open_day, list_days
from renko import build_renko, RenkoBrick
from indicators import ema, macd, twomv_signal
from ea_gradiente import EAGradiente, Trade


@dataclass
class BacktestResult:
    asset: str
    start_date: str
    end_date: str
    n_days: int = 0
    n_trades: int = 0
    n_wins: int = 0
    n_losses: int = 0
    win_rate: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    net_pnl: float = 0.0
    profit_factor: float = 0.0
    max_drawdown: float = 0.0
    avg_trade: float = 0.0
    trades: list[Trade] = field(default_factory=list)
    daily_pnls: dict[str, float] = field(default_factory=dict)


def run_day_backtest(
    asset: str,
    day: str,
    ea: EAGradiente,
    tick_size: float,
    renko_r: int,
    tick_value: float,
) -> BacktestResult:
    """Run backtest for a single day."""
    pkt = open_day(asset, day)
    prices = pkt.price  # float prices
    times = pkt.time_ms

    # Build Renko bricks
    bricks = build_renko(prices, times, tick_size, renko_r)
    if len(bricks) < 73:
        pkt.close()
        return BacktestResult(asset=asset, start_date=day, end_date=day)

    # Build close price series from bricks for indicators
    brick_closes = np.array([b.close_price for b in bricks], dtype=np.float64)
    brick_times = np.array([b.end_time_ms for b in bricks], dtype=np.int64)

    # Indicators
    ema21 = ema(brick_closes, 21)
    ema72 = ema(brick_closes, 72)
    _, _, macd_hist = macd(brick_closes, 12, 26, 9)

    twomv_colors = []
    for i in range(len(bricks)):
        sig = twomv_signal(brick_closes, ema21, ema72, i)
        twomv_colors.append(sig.color)

    # EA state
    ea.reset_state()
    ea.tick_value = tick_value

    # Map each tick to current brick index (approximate via time)
    # Simplification: iterate bricks, and for each brick, process its ticks
    # We need to know which ticks belong to which brick
    # Using time boundaries
    brick_idx_for_tick = np.zeros(len(prices), dtype=np.int32)
    bidx = 0
    for i in range(len(prices)):
        t = times[i]
        while bidx < len(bricks) - 1 and t > bricks[bidx].end_time_ms:
            bidx += 1
        brick_idx_for_tick[i] = bidx

    # Track which bricks have been "closed" for EA processing
    last_processed_brick = -1

    for i in range(len(prices)):
        price = prices[i]
        time_ms = times[i]
        bidx = brick_idx_for_tick[i]

        # Process new brick close
        if bidx > last_processed_brick:
            for bi in range(last_processed_brick + 1, bidx + 1):
                ea.on_brick_close(
                    bi,
                    bricks,
                    macd_hist=list(macd_hist),
                    twomv_colors=twomv_colors,
                )
            last_processed_brick = bidx

        # Process tick (fills, stops)
        ea.on_tick(time_ms, price)

    pkt.close()

    st = ea.state
    result = BacktestResult(
        asset=asset,
        start_date=day,
        end_date=day,
        n_days=1,
        n_trades=st.n_trades,
        n_wins=st.n_wins,
        n_losses=st.n_losses,
        win_rate=st.n_wins / st.n_trades * 100 if st.n_trades > 0 else 0.0,
        gross_profit=st.gross_profit,
        gross_loss=abs(st.gross_loss),
        net_pnl=st.total_pnl,
        profit_factor=st.gross_profit / abs(st.gross_loss) if st.gross_loss != 0 else float("inf"),
        max_drawdown=st.max_drawdown,
        avg_trade=st.total_pnl / st.n_trades if st.n_trades > 0 else 0.0,
        trades=st.closed_trades,
        daily_pnls={day: st.total_pnl},
    )
    return result


def aggregate_results(results: list[BacktestResult]) -> BacktestResult:
    """Aggregate multiple daily results."""
    if not results:
        return BacktestResult(asset="", start_date="", end_date="")

    agg = BacktestResult(
        asset=results[0].asset,
        start_date=results[0].start_date,
        end_date=results[-1].end_date,
        n_days=len(results),
    )

    peak = 0.0
    equity = 0.0

    for r in results:
        agg.n_trades += r.n_trades
        agg.n_wins += r.n_wins
        agg.n_losses += r.n_losses
        agg.gross_profit += r.gross_profit
        agg.gross_loss += r.gross_loss
        agg.net_pnl += r.net_pnl
        agg.daily_pnls.update(r.daily_pnls)
        agg.trades.extend(r.trades)

        equity += r.net_pnl
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > agg.max_drawdown:
            agg.max_drawdown = dd

    agg.win_rate = agg.n_wins / agg.n_trades * 100 if agg.n_trades > 0 else 0.0
    agg.profit_factor = (
        agg.gross_profit / agg.gross_loss if agg.gross_loss > 0 else float("inf")
    )
    agg.avg_trade = agg.net_pnl / agg.n_trades if agg.n_trades > 0 else 0.0
    return agg


def print_result(result: BacktestResult):
    print(f"\n{'='*60}")
    print(f"Backtest Result: {result.asset} | {result.start_date} to {result.end_date}")
    print(f"{'='*60}")
    print(f"Days tested    : {result.n_days}")
    print(f"Total trades   : {result.n_trades}")
    print(f"Wins / Losses  : {result.n_wins} / {result.n_losses}")
    print(f"Win rate       : {result.win_rate:.2f}%")
    print(f"Gross profit   : R$ {result.gross_profit:,.2f}")
    print(f"Gross loss     : R$ {result.gross_loss:,.2f}")
    print(f"Net PnL        : R$ {result.net_pnl:,.2f}")
    print(f"Profit factor  : {result.profit_factor:.2f}")
    print(f"Max drawdown   : R$ {result.max_drawdown:,.2f}")
    print(f"Avg trade      : R$ {result.avg_trade:,.2f}")
    print(f"{'='*60}\n")


def save_report(result: BacktestResult, path: Path):
    """Save result as JSON."""
    data = {
        "asset": result.asset,
        "start_date": result.start_date,
        "end_date": result.end_date,
        "n_days": result.n_days,
        "n_trades": result.n_trades,
        "n_wins": result.n_wins,
        "n_losses": result.n_losses,
        "win_rate": result.win_rate,
        "gross_profit": result.gross_profit,
        "gross_loss": result.gross_loss,
        "net_pnl": result.net_pnl,
        "profit_factor": result.profit_factor,
        "max_drawdown": result.max_drawdown,
        "avg_trade": result.avg_trade,
        "daily_pnls": result.daily_pnls,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
