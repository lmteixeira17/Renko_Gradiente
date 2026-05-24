"""Generate equity curve for a backtest configuration."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from btp_loader import list_days
from backtest_engine_v2 import run_day_fast


def main():
    asset = "WIN"
    years = ["2023", "2024"]
    days = []
    for y in years:
        days.extend([d for d in list_days(asset) if d.startswith(y)])
    days.sort()

    config = {
        "renko_r": 25, "tick_size": 5.0, "tick_value": 0.20,
        "base_qty": 1, "max_levels": 3, "martingale": False,
        "price_increment": 100.0, "gain_increment": 50.0,
        "stop_loss_pts": 300.0, "use_macd": True, "use_2mv": True,
        "min_bricks_for_signal": 2, "slippage_pts": 2.0,
        "emolumentos_pct": 0.0001, "preservation_stop": False,
        "preservation_levels": 3, "trailing_stop_value": 0.0,
        "daily_stop_loss": 999999.0,
    }

    daily_pnls = []
    daily_dates = []
    for day in days:
        try:
            res = run_day_fast(asset, day, config)
            daily_pnls.append(res.net_pnl)
            daily_dates.append(day)
        except Exception as e:
            print(f"Error {day}: {e}")

    equity = np.cumsum(daily_pnls)
    
    fig, axes = plt.subplots(2, 1, figsize=(14, 8), gridspec_kw={'height_ratios': [3, 1]})
    
    # Equity curve
    ax1 = axes[0]
    ax1.plot(range(len(equity)), equity, color='steelblue', linewidth=1.2)
    ax1.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax1.fill_between(range(len(equity)), equity, 0, where=(equity >= 0), alpha=0.2, color='green')
    ax1.fill_between(range(len(equity)), equity, 0, where=(equity < 0), alpha=0.2, color='red')
    ax1.set_title(f"EA Gradiente Linear — Equity Curve ({asset} {years[0]}-{years[-1]})\n"
                  f"Renko 25R | ML3 | SL300 | No Martingale | PnL: R$ {equity[-1]:,.2f}")
    ax1.set_ylabel("Equity (R$)")
    ax1.grid(True, alpha=0.3)

    # Daily PnL bars
    ax2 = axes[1]
    colors = ['green' if p >= 0 else 'red' for p in daily_pnls]
    ax2.bar(range(len(daily_pnls)), daily_pnls, color=colors, alpha=0.7, width=1.0)
    ax2.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax2.set_ylabel("Daily PnL (R$)")
    ax2.set_xlabel("Trading Day")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    out_path = PROJECT_ROOT / "reports" / f"equity_{asset}_{years[0]}_{years[-1]}.png"
    plt.savefig(out_path, dpi=150)
    print(f"Saved equity curve to {out_path}")

    # Stats
    peak = np.maximum.accumulate(equity)
    drawdown = peak - equity
    max_dd_idx = np.argmax(drawdown)
    print(f"Max drawdown: R$ {drawdown[max_dd_idx]:,.2f} at day {max_dd_idx} ({daily_dates[max_dd_idx]})")
    print(f"Total days: {len(daily_pnls)}, Positive: {sum(1 for p in daily_pnls if p > 0)}, Negative: {sum(1 for p in daily_pnls if p < 0)}")


if __name__ == "__main__":
    main()
