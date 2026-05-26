"""Testar a config vencedora de 2026 em longo prazo 2021-2026."""
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import time
from pathlib import Path
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import list_days
from backtest_engine_v2 import run_day_fast, aggregate_results


@dataclass
class Config:
    name: str
    asset: str
    years: list[str]
    initial_capital: float


def run_test(cfg: Config) -> dict:
    days = []
    for y in cfg.years:
        days.extend([d for d in list_days(cfg.asset) if d.startswith(y)])
    days.sort()

    c = {
        "renko_r": 25, "tick_size": 5.0, "tick_value": 0.20,
        "base_qty": 1, "max_levels": 3, "martingale": False,
        "price_increment": 100.0, "gain_increment": 0.0,
        "gain_increment_pct": 0.001,
        "stop_loss_pts": 0.0,
        "stop_loss_pct": 0.003,
        "slippage_pts": 2.0, "emolumentos_pct": 0.0001,
        "daily_stop_loss": 75.0,
        "start_time_ms": 34200000, "end_time_ms": 60600000,
        "use_macd": True, "use_2mv": True, "min_bricks_for_signal": 2,
    }

    results = []
    t0 = time.time()
    for day in days:
        try:
            res = run_day_fast(cfg.asset, day, c)
            results.append(res)
        except Exception as e:
            print(f"  {day}: ERROR {e}", flush=True)
    dt = time.time() - t0

    agg = aggregate_results(results)
    dd_pct = agg.max_drawdown / cfg.initial_capital * 100 if agg.max_drawdown > 0 else 0.0
    return_dd = agg.net_pnl / agg.max_drawdown if agg.max_drawdown > 0 else 0.0

    return {
        "name": cfg.name, "asset": cfg.asset, "years": cfg.years,
        "n_days": len(days), "n_trades": agg.n_trades, "win_rate": agg.win_rate,
        "profit_factor": agg.profit_factor, "net_pnl": agg.net_pnl,
        "max_drawdown": agg.max_drawdown, "max_drawdown_pct": dd_pct,
        "avg_trade": agg.avg_trade, "return_dd_ratio": return_dd,
        "exec_time_s": dt, "initial_capital": cfg.initial_capital,
        "stop_loss_pct": 0.003, "gain_increment_pct": 0.001,
        "daily_stop_loss": 75.0,
    }


def main():
    configs = [
        Config("WIN_pct_03_01_DS75_2021-2026_cap5000", "WIN",
               ["2021", "2022", "2023", "2024", "2025", "2026"], 5000.0),
        Config("WIN_pct_03_01_DS75_2021-2026_cap10000", "WIN",
               ["2021", "2022", "2023", "2024", "2025", "2026"], 10000.0),
        Config("WIN_pct_03_01_DS75_2021-2026_cap15000", "WIN",
               ["2021", "2022", "2023", "2024", "2025", "2026"], 15000.0),
    ]

    all_results = []
    for cfg in configs:
        print(f">>> {cfg.name}...", flush=True)
        res = run_test(cfg)
        all_results.append(res)
        print(f"  {res['name']:55s} | Trades={res['n_trades']:5d} PnL=R${res['net_pnl']:10,.2f} "
              f"WR={res['win_rate']:5.1f}% PF={res['profit_factor']:.2f} "
              f"DD=R${res['max_drawdown']:9,.2f} ({res['max_drawdown_pct']:5.1f}%) "
              f"R/DD={res['return_dd_ratio']:5.2f} ({res['exec_time_s']:.1f}s)", flush=True)

    out_path = PROJECT_ROOT / "reports" / "win_pct_03_01_long_term.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n>>> Saved to {out_path}", flush=True)


if __name__ == "__main__":
    main()
