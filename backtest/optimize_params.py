"""Parameter optimization grid search for EA Gradiente Linear."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import list_days
from backtest_engine_v2 import run_day_fast, aggregate_results
import json


def test_config(asset: str, days: list[str], config: dict) -> dict:
    results = []
    for day in days:
        try:
            res = run_day_fast(asset, day, config)
            results.append(res)
        except Exception as e:
            pass
    agg = aggregate_results(results)
    return {
        "n_trades": agg.n_trades,
        "win_rate": agg.win_rate,
        "net_pnl": agg.net_pnl,
        "profit_factor": agg.profit_factor,
        "max_drawdown": agg.max_drawdown,
        "avg_trade": agg.avg_trade,
    }


def main():
    asset = "WIN"
    days = [d for d in list_days(asset) if "2024-01-01" <= d <= "2024-03-31"]

    base_config = {
        "renko_r": 25,
        "tick_size": 5.0,
        "tick_value": 0.20,
        "base_qty": 1,
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

    param_grid = []
    for price_inc in [100, 150, 200]:
        for gain_inc in [50, 100]:
            for max_lvl in [4, 5]:
                for sl in [500, 800, 1000]:
                    param_grid.append({
                        "price_increment": float(price_inc),
                        "gain_increment": float(gain_inc),
                        "max_levels": max_lvl,
                        "stop_loss_pts": float(sl),
                    })

    print(f"Testing {len(param_grid)} configurations on {len(days)} days...")
    results = []

    for i, params in enumerate(param_grid):
        cfg = base_config.copy()
        cfg.update(params)
        metrics = test_config(asset, days, cfg)
        metrics.update(params)
        results.append(metrics)
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(param_grid)} done")

    # Sort by net_pnl / max_drawdown ratio
    for r in results:
        dd = r["max_drawdown"]
        r["return_dd_ratio"] = r["net_pnl"] / dd if dd > 0 else 0.0

    results.sort(key=lambda x: x["return_dd_ratio"], reverse=True)

    print("\n=== TOP 10 BY RETURN/DRAWDOWN ===")
    for r in results[:10]:
        print(f"PI={r['price_increment']:.0f} GI={r['gain_increment']:.0f} LV={r['max_levels']} SL={r['stop_loss_pts']:.0f} | "
              f"PnL=R${r['net_pnl']:8,.2f} DD=R${r['max_drawdown']:8,.2f} R/DD={r['return_dd_ratio']:.2f} "
              f"WR={r['win_rate']:.1f}% PF={r['profit_factor']:.2f} Trades={r['n_trades']}")

    # Save
    out_path = PROJECT_ROOT / "reports" / "optimization_grid_2024q1.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
