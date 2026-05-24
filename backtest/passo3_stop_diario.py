"""Passo 3: Testar stop financeiro diário rigoroso em 5 anos."""
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
    daily_stop: float
    years: list[str]


def run_config(cfg: Config) -> dict:
    days = []
    for y in cfg.years:
        days.extend([d for d in list_days(cfg.asset) if d.startswith(y)])
    days.sort()

    # Base config: WIN 25R nomart ML3 SL300 (melhor configuração curto prazo)
    c = {
        "renko_r": 25, "tick_size": 5.0, "tick_value": 0.20,
        "base_qty": 1, "max_levels": 3, "martingale": False,
        "price_increment": 100.0, "gain_increment": 50.0,
        "stop_loss_pts": 300.0, "use_macd": True, "use_2mv": True,
        "min_bricks_for_signal": 2, "slippage_pts": 2.0,
        "emolumentos_pct": 0.0001, "preservation_stop": False,
        "preservation_levels": 3, "trailing_stop_value": 0.0,
        "daily_stop_loss": cfg.daily_stop,
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
    dd_pct = agg.max_drawdown / 5000 * 100 if agg.max_drawdown > 0 else 0.0
    return {
        "passo": 3,
        "config_name": cfg.name, "asset": cfg.asset, "years": cfg.years,
        "daily_stop": cfg.daily_stop,
        "n_days": len(days), "n_trades": agg.n_trades, "win_rate": agg.win_rate,
        "profit_factor": agg.profit_factor, "net_pnl": agg.net_pnl,
        "max_drawdown": agg.max_drawdown, "max_drawdown_pct": dd_pct,
        "avg_trade": agg.avg_trade, "gross_profit": agg.gross_profit,
        "gross_loss": agg.gross_loss, "exec_time_s": dt,
    }


def main():
    years = ["2021", "2022", "2023", "2024", "2025"]

    configs = [
        Config("WIN_25R_ML3_SL300_stop100", "WIN", 100.0, years),
        Config("WIN_25R_ML3_SL300_stop200", "WIN", 200.0, years),
        Config("WIN_25R_ML3_SL300_stop300", "WIN", 300.0, years),
        Config("WIN_25R_ML3_SL300_stop500", "WIN", 500.0, years),
        Config("WIN_25R_ML3_SL300_stop750", "WIN", 750.0, years),
        Config("WIN_25R_ML3_SL300_stop1000", "WIN", 1000.0, years),
        Config("WIN_25R_ML3_SL300_stop999999", "WIN", 999999.0, years),  # baseline (no daily stop)
    ]

    all_results = []
    for cfg in configs:
        print(f">>> Passo 3 | Testing {cfg.name} (daily_stop=R$ {cfg.daily_stop})...", flush=True)
        res = run_config(cfg)
        all_results.append(res)
        print(f"    Trades={res['n_trades']:5d} PnL=R${res['net_pnl']:11,.2f} "
              f"WR={res['win_rate']:5.1f}% PF={res['profit_factor']:.2f} "
              f"DD=R${res['max_drawdown']:9,.2f} ({res['max_drawdown_pct']:.1f}%) "
              f"Avg={res['avg_trade']:.2f} ({res['exec_time_s']:.1f}s)", flush=True)

    for r in all_results:
        dd = r["max_drawdown"]
        r["return_dd_ratio"] = r["net_pnl"] / dd if dd > 0 else 0.0

    all_results.sort(key=lambda x: x["return_dd_ratio"], reverse=True)
    print("\n=== PASSO 3 — RANKING ===", flush=True)
    for i, r in enumerate(all_results, 1):
        print(f"{i:2d}. {r['config_name']:40s} | PnL=R${r['net_pnl']:11,.2f} "
              f"DD={r['max_drawdown_pct']:5.1f}% R/DD={r['return_dd_ratio']:.2f} PF={r['profit_factor']:.2f} WR={r['win_rate']:5.1f}%", flush=True)

    out_path = PROJECT_ROOT / "reports" / "passo3_stop_diario_2021_2025.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_path}", flush=True)


if __name__ == "__main__":
    main()
