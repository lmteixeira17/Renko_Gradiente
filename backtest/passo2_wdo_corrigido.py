"""Passo 2: Corrigir WDO com Renko 10R e validar em 2021-2025."""
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
    renko_r: int
    tick_size: float
    tick_value: float
    price_increment: float
    gain_increment: float
    max_levels: int
    stop_loss_pts: float
    martingale: bool
    years: list[str]
    slippage_pts: float = 1.0
    emolumentos_pct: float = 0.0001


def run_config(cfg: Config) -> dict:
    days = []
    for y in cfg.years:
        days.extend([d for d in list_days(cfg.asset) if d.startswith(y)])
    days.sort()

    c = {
        "renko_r": cfg.renko_r, "tick_size": cfg.tick_size, "tick_value": cfg.tick_value,
        "base_qty": 1, "max_levels": cfg.max_levels, "martingale": cfg.martingale,
        "price_increment": cfg.price_increment, "gain_increment": cfg.gain_increment,
        "stop_loss_pts": cfg.stop_loss_pts, "use_macd": True, "use_2mv": True,
        "min_bricks_for_signal": 2, "slippage_pts": cfg.slippage_pts,
        "emolumentos_pct": cfg.emolumentos_pct, "preservation_stop": False,
        "preservation_levels": 3, "trailing_stop_value": 0.0,
        "daily_stop_loss": 999999.0,
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
        "passo": 2,
        "config_name": cfg.name, "asset": cfg.asset, "years": cfg.years,
        "n_days": len(days), "n_trades": agg.n_trades, "win_rate": agg.win_rate,
        "profit_factor": agg.profit_factor, "net_pnl": agg.net_pnl,
        "max_drawdown": agg.max_drawdown, "max_drawdown_pct": dd_pct,
        "avg_trade": agg.avg_trade, "gross_profit": agg.gross_profit,
        "gross_loss": agg.gross_loss, "exec_time_s": dt,
    }


def main():
    years = ["2021", "2022", "2023", "2024", "2025"]

    configs = [
        # WDO com Renko 10R (correção do viés de volatilidade)
        Config("WDO_10R_nomart_ML3_SL20_2_05", "WDO", 10, 0.5, 10.0, 2.0, 0.5, 3, 20.0, False, years),
        Config("WDO_10R_mart_ML3_SL20_2_05", "WDO", 10, 0.5, 10.0, 2.0, 0.5, 3, 20.0, True, years),
        Config("WDO_10R_nomart_ML3_SL25_2_05", "WDO", 10, 0.5, 10.0, 2.0, 0.5, 3, 25.0, False, years),
        Config("WDO_10R_nomart_ML2_SL20_2_05", "WDO", 10, 0.5, 10.0, 2.0, 0.5, 2, 20.0, False, years),
        Config("WDO_10R_nomart_ML3_SL20_3_10", "WDO", 10, 0.5, 10.0, 3.0, 1.0, 3, 20.0, False, years),
        # Comparativo com Renko 12R
        Config("WDO_12R_nomart_ML3_SL20_2_05", "WDO", 12, 0.5, 10.0, 2.0, 0.5, 3, 20.0, False, years),
        # Comparativo antigo (15R) para mostrar a diferença
        Config("WDO_15R_nomart_ML3_SL30_3_10", "WDO", 15, 0.5, 10.0, 3.0, 1.0, 3, 30.0, False, years),
    ]

    all_results = []
    for cfg in configs:
        print(f">>> Passo 2 | Testing {cfg.name}...", flush=True)
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
    print("\n=== PASSO 2 — RANKING ===", flush=True)
    for i, r in enumerate(all_results, 1):
        print(f"{i:2d}. {r['config_name']:35s} | PnL=R${r['net_pnl']:11,.2f} "
              f"DD={r['max_drawdown_pct']:5.1f}% R/DD={r['return_dd_ratio']:.2f} PF={r['profit_factor']:.2f} WR={r['win_rate']:5.1f}%", flush=True)

    out_path = PROJECT_ROOT / "reports" / "passo2_wdo_corrigido_2021_2025.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {out_path}", flush=True)


if __name__ == "__main__":
    main()
