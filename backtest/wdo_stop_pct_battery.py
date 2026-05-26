"""Bateria de testes WDO com stop % e stop diário."""
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
    # Params
    renko_r: int = 10
    tick_size: float = 0.5
    tick_value: float = 10.0
    base_qty: int = 1
    max_levels: int = 3
    martingale: bool = False
    price_increment: float = 2.0
    gain_increment: float = 0.5
    gain_increment_pct: float = 0.0
    stop_loss_pts: float = 20.0
    stop_loss_pct: float = 0.0
    slippage_pts: float = 1.0
    emolumentos_pct: float = 0.0001
    daily_stop_loss: float = 100.0
    start_time_ms: int = 34200000
    end_time_ms: int = 60600000


def run_test(cfg: Config) -> dict:
    days = []
    for y in cfg.years:
        days.extend([d for d in list_days(cfg.asset) if d.startswith(y)])
    days.sort()

    c = {
        "renko_r": cfg.renko_r, "tick_size": cfg.tick_size, "tick_value": cfg.tick_value,
        "base_qty": cfg.base_qty, "max_levels": cfg.max_levels, "martingale": cfg.martingale,
        "price_increment": cfg.price_increment, "gain_increment": cfg.gain_increment,
        "gain_increment_pct": cfg.gain_increment_pct,
        "stop_loss_pts": cfg.stop_loss_pts, "stop_loss_pct": cfg.stop_loss_pct,
        "slippage_pts": cfg.slippage_pts, "emolumentos_pct": cfg.emolumentos_pct,
        "daily_stop_loss": cfg.daily_stop_loss,
        "start_time_ms": cfg.start_time_ms, "end_time_ms": cfg.end_time_ms,
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
        "stop_loss_pct": cfg.stop_loss_pct, "gain_increment_pct": cfg.gain_increment_pct,
        "daily_stop_loss": cfg.daily_stop_loss,
    }


def main():
    configs = []

    # FASE 1: Baseline WDO 2025 e 2026 com varios stops
    for year in ["2025", "2026"]:
        for stop in [50.0, 100.0, 150.0, 200.0]:
            for cap in [5000.0, 10000.0]:
                configs.append(Config(
                    name=f"WDO_baseline_{year}_stop{stop:.0f}_cap{cap:.0f}",
                    asset="WDO", years=[year],
                    daily_stop_loss=stop, initial_capital=cap,
                ))

    # FASE 2: Stop % WDO 2025 e 2026
    sl_pcts = [0.002, 0.003, 0.005]
    gain_pcts = [0.001, 0.0015, 0.002]
    for year in ["2025", "2026"]:
        for sl_pct in sl_pcts:
            for gain_pct in gain_pcts:
                if gain_pct >= sl_pct:
                    continue
                for stop in [50.0, 100.0]:
                    for cap in [5000.0, 10000.0]:
                        configs.append(Config(
                            name=f"WDO_pct_{year}_SL{sl_pct:.4f}_G{gain_pct:.4f}_DS{stop:.0f}_cap{cap:.0f}",
                            asset="WDO", years=[year],
                            stop_loss_pts=0.0, stop_loss_pct=sl_pct,
                            gain_increment=0.0, gain_increment_pct=gain_pct,
                            daily_stop_loss=stop, initial_capital=cap,
                        ))

    # FASE 3: Longo prazo 2021-2026 — melhores configs
    configs.extend([
        Config(name="WDO_baseline_2021-2026_stop100_cap5000", asset="WDO",
               years=["2021", "2022", "2023", "2024", "2025", "2026"],
               daily_stop_loss=100.0, initial_capital=5000.0),
        Config(name="WDO_baseline_2021-2026_stop100_cap10000", asset="WDO",
               years=["2021", "2022", "2023", "2024", "2025", "2026"],
               daily_stop_loss=100.0, initial_capital=10000.0),
        Config(name="WDO_pct_2021-2026_SL0.0030_G0.0015_DS100_cap5000", asset="WDO",
               years=["2021", "2022", "2023", "2024", "2025", "2026"],
               stop_loss_pts=0.0, stop_loss_pct=0.003,
               gain_increment=0.0, gain_increment_pct=0.0015,
               daily_stop_loss=100.0, initial_capital=5000.0),
        Config(name="WDO_pct_2021-2026_SL0.0030_G0.0015_DS100_cap10000", asset="WDO",
               years=["2021", "2022", "2023", "2024", "2025", "2026"],
               stop_loss_pts=0.0, stop_loss_pct=0.003,
               gain_increment=0.0, gain_increment_pct=0.0015,
               daily_stop_loss=100.0, initial_capital=10000.0),
        Config(name="WDO_pct_2021-2026_SL0.0050_G0.0020_DS100_cap5000", asset="WDO",
               years=["2021", "2022", "2023", "2024", "2025", "2026"],
               stop_loss_pts=0.0, stop_loss_pct=0.005,
               gain_increment=0.0, gain_increment_pct=0.002,
               daily_stop_loss=100.0, initial_capital=5000.0),
        Config(name="WDO_pct_2021-2026_SL0.0050_G0.0020_DS100_cap10000", asset="WDO",
               years=["2021", "2022", "2023", "2024", "2025", "2026"],
               stop_loss_pts=0.0, stop_loss_pct=0.005,
               gain_increment=0.0, gain_increment_pct=0.002,
               daily_stop_loss=100.0, initial_capital=10000.0),
    ])

    all_results = []
    for cfg in configs:
        print(f">>> {cfg.name}...", flush=True)
        res = run_test(cfg)
        all_results.append(res)
        print(f"  {res['name']:55s} | Trades={res['n_trades']:5d} PnL=R${res['net_pnl']:10,.2f} "
              f"WR={res['win_rate']:5.1f}% PF={res['profit_factor']:.2f} "
              f"DD=R${res['max_drawdown']:9,.2f} ({res['max_drawdown_pct']:5.1f}%) "
              f"R/DD={res['return_dd_ratio']:5.2f} ({res['exec_time_s']:.1f}s)", flush=True)

    all_results.sort(key=lambda x: x["return_dd_ratio"], reverse=True)
    print("\n=== RANKING WDO (Return/DD) ===", flush=True)
    for i, r in enumerate(all_results[:20], 1):
        print(f"{i:2d}. {r['name']:55s} | PnL=R${r['net_pnl']:10,.2f} "
              f"DD={r['max_drawdown_pct']:5.1f}% R/DD={r['return_dd_ratio']:5.2f} PF={r['profit_factor']:.2f}", flush=True)

    out_path = PROJECT_ROOT / "reports" / "wdo_stop_pct_battery.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n>>> Saved to {out_path}", flush=True)


if __name__ == "__main__":
    main()
