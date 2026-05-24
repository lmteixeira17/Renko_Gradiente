"""Run annual backtest for EA Gradiente Linear."""
from __future__ import annotations

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import list_days
from backtest_engine_v2 import run_day_fast, aggregate_results, print_result, save_report


def main():
    asset = "WIN"
    start_day = "2024-01-01"
    end_day = "2024-12-31"

    config = {
        "renko_r": 25,
        "tick_size": 5.0,
        "tick_value": 0.20,
        "base_qty": 1,
        "max_levels": 3,
        "martingale": False,
        "price_increment": 100.0,
        "gain_increment": 50.0,
        "stop_loss_pts": 300.0,
        "use_macd": True,
        "use_2mv": True,
        "min_bricks_for_signal": 2,
        "slippage_pts": 2.0,
        "emolumentos_pct": 0.0001,
        "preservation_stop": False,
        "preservation_levels": 3,
        "trailing_stop_value": 0.0,
        "daily_stop_loss": 999999.0,
    }

    days = [d for d in list_days(asset) if start_day <= d <= end_day]
    print(f"Running annual backtest for {asset}: {len(days)} days")

    daily_results = []
    t0 = time.time()
    for day in days:
        try:
            res = run_day_fast(asset, day, config)
            daily_results.append(res)
            if res.n_trades > 0:
                print(f"  {day}: {res.n_trades:3d} trades, PnL R$ {res.net_pnl:8,.2f}, WR {res.win_rate:.1f}%")
        except Exception as e:
            print(f"  {day}: ERROR {e}")

    total_time = time.time() - t0
    agg = aggregate_results(daily_results)
    print_result(agg)
    print(f"Total execution time: {total_time:.1f}s ({len(days)} days)")

    report_path = PROJECT_ROOT / "reports" / f"backtest_annual_{asset}_{start_day}_{end_day}.json"
    save_report(agg, report_path)
    print(f"Report saved to {report_path}")


if __name__ == "__main__":
    main()
