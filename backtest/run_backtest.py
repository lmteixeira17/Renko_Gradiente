"""Run backtest for EA Gradiente Linear on BTP tick data."""
from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import list_days
from backtest_engine import run_day_backtest, aggregate_results, print_result, save_report
from ea_gradiente import EAGradiente


def main():
    # Configurations
    asset = "WIN"
    renko_r = 25
    tick_size = 5.0
    tick_value = 0.20  # R$ per point for WIN
    start_day = "2024-01-01"
    end_day = "2024-03-31"

    ea = EAGradiente(
        base_qty=1,
        price_increment=100.0,  # 100 points between levels
        gain_increment=50.0,    # 50 points target
        max_levels=5,
        stop_loss_pts=1000.0,
        daily_stop_loss=500.0,
        martingale=True,
        tick_value=tick_value,
        use_macd=True,
        use_2mv=True,
        min_bricks_for_signal=2,
    )

    days = [d for d in list_days(asset) if start_day <= d <= end_day]
    print(f"Running backtest for {asset}: {len(days)} days from {start_day} to {end_day}")

    daily_results = []
    for day in days:
        try:
            res = run_day_backtest(asset, day, ea, tick_size, renko_r, tick_value)
            daily_results.append(res)
            print(f"  {day}: {res.n_trades} trades, PnL R$ {res.net_pnl:,.2f}")
        except Exception as e:
            print(f"  {day}: ERROR {e}")

    agg = aggregate_results(daily_results)
    print_result(agg)

    report_path = PROJECT_ROOT / "reports" / f"backtest_{asset}_{start_day}_{end_day}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    save_report(agg, report_path)
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()
