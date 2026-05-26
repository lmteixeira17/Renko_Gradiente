"""Fast backtest engine v2 using Numba."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from btp_loader import open_day, list_days
from renko import build_renko
from indicators import ema, macd, twomv_signal
from backtest_fast import simulate_day_fast


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
    daily_pnls: dict[str, float] = field(default_factory=dict)


def prepare_signals(bricks, use_macd=True, use_2mv=True, min_bricks=2):
    """Prepare entry signals per brick."""
    if len(bricks) < 73:
        return None
    brick_closes = np.array([b.close_price for b in bricks], dtype=np.float64)
    ema21 = ema(brick_closes, 21)
    ema72 = ema(brick_closes, 72)
    _, _, macd_hist = macd(brick_closes, 12, 26, 9)

    entry_signals = np.zeros(len(bricks), dtype=np.int8)
    for i in range(1, len(bricks)):
        curr = bricks[i]
        prev = bricks[i - 1]

        if curr.direction == 1:
            side = 1
        elif curr.direction == -1:
            side = -1
        else:
            continue

        if use_2mv:
            color = twomv_signal(brick_closes, ema21, ema72, i).color
            if side == 1 and color != "green":
                continue
            if side == -1 and color != "red":
                continue

        if use_macd:
            hist = macd_hist[i]
            if side == 1 and hist <= 0:
                continue
            if side == -1 and hist >= 0:
                continue

        if prev.direction != curr.direction:
            entry_signals[i] = side
        else:
            count = 1
            for j in range(i - 1, -1, -1):
                if bricks[j].direction == curr.direction:
                    count += 1
                else:
                    break
            if count >= min_bricks:
                entry_signals[i] = side

    return entry_signals


def run_day_fast(asset: str, day: str, config: dict) -> BacktestResult:
    """Run fast backtest for one day."""
    pkt = open_day(asset, day)
    prices = pkt.price
    times = pkt.time_ms

    renko_r = config.get("renko_r", 25)
    tick_size = config.get("tick_size", 5.0)
    tick_value = config.get("tick_value", 0.20)

    bricks = build_renko(prices, times, tick_size, renko_r)
    entry_signals = prepare_signals(
        bricks,
        use_macd=config.get("use_macd", True),
        use_2mv=config.get("use_2mv", True),
        min_bricks=config.get("min_bricks_for_signal", 2),
    )

    if entry_signals is None:
        pkt.close()
        return BacktestResult(asset=asset, start_date=day, end_date=day)

    # Filtro de distancia EMA (nao opera quando mercado muito esticado)
    max_ema_dist = config.get("max_ema_distance_pts", 0.0)
    if max_ema_dist > 0 and len(bricks) >= 73:
        brick_closes = np.array([b.close_price for b in bricks], dtype=np.float64)
        ema21_arr = ema(brick_closes, 21)
        ema72_arr = ema(brick_closes, 72)
        for i in range(len(bricks)):
            if entry_signals[i] != 0:
                dist = abs(ema21_arr[i] - ema72_arr[i])
                if dist > max_ema_dist:
                    entry_signals[i] = 0

    # Niveis dinamicos baseados em distancia EMA
    ema_dist_ml2 = config.get("ema_dist_ml2_threshold", 0.0)
    ema_dist_ml1 = config.get("ema_dist_ml1_threshold", 0.0)
    effective_max_levels = config.get("max_levels", 3)
    if len(bricks) >= 73 and (ema_dist_ml2 > 0 or ema_dist_ml1 > 0):
        brick_closes = np.array([b.close_price for b in bricks], dtype=np.float64)
        ema21_arr = ema(brick_closes, 21)
        ema72_arr = ema(brick_closes, 72)
        last_dist = abs(ema21_arr[-1] - ema72_arr[-1])
        if ema_dist_ml1 > 0 and last_dist > ema_dist_ml1:
            effective_max_levels = 1
        elif ema_dist_ml2 > 0 and last_dist > ema_dist_ml2:
            effective_max_levels = 2

    # Map ticks to bricks using searchsorted
    brick_end_times = np.array([b.end_time_ms for b in bricks], dtype=np.int64)
    brick_idx = np.searchsorted(brick_end_times, times, side='right')
    brick_idx = np.clip(brick_idx, 0, len(bricks) - 1).astype(np.int32)

    (
        entry_times,
        exit_times,
        entry_prices,
        exit_prices,
        qtys,
        pnls,
        directions,
        reasons,
    ) = simulate_day_fast(
        prices,
        times,
        brick_idx,
        entry_signals,
        base_qty=config.get("base_qty", 1),
        price_increment=config.get("price_increment", 100.0),
        gain_increment=config.get("gain_increment", 50.0),
        gain_increment_pct=config.get("gain_increment_pct", 0.0),
        max_levels=effective_max_levels,
        stop_loss_pts=config.get("stop_loss_pts", 1000.0),
        stop_loss_pct=config.get("stop_loss_pct", 0.0),
        tick_value=tick_value,
        martingale=config.get("martingale", True),
        slippage_pts=config.get("slippage_pts", 2.0),
        emolumentos_pct=config.get("emolumentos_pct", 0.0001),
        preservation_stop=config.get("preservation_stop", False),
        preservation_levels=config.get("preservation_levels", 3),
        trailing_stop_value=config.get("trailing_stop_value", 0.0),
        daily_stop_loss=config.get("daily_stop_loss", 999999.0),
        max_trades_per_day=config.get("max_trades_per_day", 0),
        start_time_ms=config.get("start_time_ms", 0),
        end_time_ms=config.get("end_time_ms", 86400000),
    )

    pkt.close()

    n_trades = len(pnls)
    n_wins = int(np.sum(pnls > 0))
    n_losses = n_trades - n_wins
    gross_profit = float(np.sum(pnls[pnls > 0]))
    gross_loss = float(np.sum(np.abs(pnls[pnls < 0])))
    net_pnl = float(np.sum(pnls))

    # Max drawdown from trade sequence
    peak = 0.0
    equity = 0.0
    max_dd = 0.0
    for p in pnls:
        equity += p
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd

    return BacktestResult(
        asset=asset,
        start_date=day,
        end_date=day,
        n_days=1,
        n_trades=n_trades,
        n_wins=n_wins,
        n_losses=n_losses,
        win_rate=n_wins / n_trades * 100 if n_trades > 0 else 0.0,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        net_pnl=net_pnl,
        profit_factor=gross_profit / gross_loss if gross_loss > 0 else float("inf"),
        max_drawdown=max_dd,
        avg_trade=net_pnl / n_trades if n_trades > 0 else 0.0,
        daily_pnls={day: net_pnl},
    )


def aggregate_results(results: list[BacktestResult]) -> BacktestResult:
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
        equity += r.net_pnl
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > agg.max_drawdown:
            agg.max_drawdown = dd
    agg.win_rate = agg.n_wins / agg.n_trades * 100 if agg.n_trades > 0 else 0.0
    agg.profit_factor = agg.gross_profit / agg.gross_loss if agg.gross_loss > 0 else float("inf")
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
