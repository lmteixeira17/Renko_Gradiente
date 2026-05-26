"""
Teste PARALELO de 5 configs promissoras sobre 2023+2024.
Usa multiprocessing para rodar configs simultaneamente.
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from multiprocessing import Pool, cpu_count

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import list_days
from backtest_engine_v2 import run_day_fast, aggregate_results


@dataclass
class Config:
    name: str
    asset: str = "WIN"
    years: tuple = ("2023", "2024")
    initial_capital: float = 15000.0
    renko_r: int = 25
    tick_size: float = 5.0
    tick_value: float = 0.20
    base_qty: int = 1
    max_levels: int = 3
    martingale: bool = False
    price_increment: float = 100.0
    gain_increment: float = 50.0
    gain_increment_pct: float = 0.0
    stop_loss_pts: float = 300.0
    stop_loss_pct: float = 0.0
    slippage_pts: float = 2.0
    emolumentos_pct: float = 0.0001
    daily_stop_loss: float = 100.0
    preservation_stop: bool = False
    preservation_levels: int = 3
    trailing_stop_value: float = 0.0
    start_time_ms: int = 34200000
    end_time_ms: int = 60600000
    use_macd: bool = True
    use_2mv: bool = True
    min_bricks_for_signal: int = 2


def run_single(cfg_dict):
    """Roda uma unica config (deve ser picklable)."""
    cfg = Config(**cfg_dict)
    days = []
    for y in cfg.years:
        days.extend([d for d in list_days(cfg.asset) if d.startswith(y)])
    days.sort()

    c = asdict(cfg)
    c.pop("name")
    c.pop("asset")
    c.pop("years")
    c.pop("initial_capital")

    results = []
    for day in days:
        try:
            res = run_day_fast(cfg.asset, day, c)
            results.append(res)
        except Exception as e:
            pass

    agg = aggregate_results(results)
    dd_pct = agg.max_drawdown / cfg.initial_capital * 100 if agg.max_drawdown > 0 else 0.0

    annual = {}
    for r in results:
        y = r.start_date[:4]
        annual[y] = annual.get(y, 0.0) + r.net_pnl

    return {
        "name": cfg.name, "net_pnl": agg.net_pnl, "n_trades": agg.n_trades,
        "win_rate": agg.win_rate, "profit_factor": agg.profit_factor,
        "max_drawdown": agg.max_drawdown, "max_drawdown_pct": dd_pct,
        "avg_trade": agg.avg_trade, "annual_pnls": annual,
    }


def main():
    configs = [
        Config(name="BASE_fixed"),
        Config(name="PRESERV", preservation_stop=True, preservation_levels=1),
        Config(name="TRAIL100", trailing_stop_value=100.0),
        Config(name="PRESERV_TRAIL50", preservation_stop=True, preservation_levels=1, trailing_stop_value=50.0),
        Config(name="ML2", max_levels=2),
        Config(name="ML2_PRESERV", max_levels=2, preservation_stop=True, preservation_levels=1),
        Config(name="DS50", daily_stop_loss=50.0),
        Config(name="GAIN30", gain_increment=30.0),
        Config(name="GAIN100", gain_increment=100.0),
        Config(name="SL200", stop_loss_pts=200.0),
    ]

    # Converte para dicts para pickling
    cfg_dicts = [asdict(c) for c in configs]

    t0 = time.time()
    n_workers = min(len(configs), cpu_count())
    print(f"Running {len(configs)} configs with {n_workers} workers...", flush=True)

    with Pool(processes=n_workers) as pool:
        results = pool.map(run_single, cfg_dicts)

    dt = time.time() - t0
    print(f"\nDone in {dt:.1f}s\n")

    print(f"{'Config':<25s} | {'Total':>10s} | {'2023':>10s} | {'2024':>10s} | {'PF':>5s} | {'DD%':>5s}")
    print("-" * 80)
    for r in results:
        pnl23 = r['annual_pnls'].get('2023', 0.0)
        pnl24 = r['annual_pnls'].get('2024', 0.0)
        print(f"{r['name']:<25s} | {r['net_pnl']:>10,.0f} | {pnl23:>10,.0f} | {pnl24:>10,.0f} | "
              f"{r['profit_factor']:5.2f} | {r['max_drawdown_pct']:5.1f}")

    # Ranking por equilibrio
    print("\n" + "=" * 80)
    print("RANKING: maximiza 2024, preserva 2023, penaliza DD")
    scored = []
    for r in results:
        pnl23 = r['annual_pnls'].get('2023', 0.0)
        pnl24 = r['annual_pnls'].get('2024', 0.0)
        score = (pnl24 * 2) + pnl23 - (r['max_drawdown_pct'] * 10)
        scored.append((score, r))
    scored.sort(reverse=True)
    for i, (score, r) in enumerate(scored, 1):
        pnl23 = r['annual_pnls'].get('2023', 0.0)
        pnl24 = r['annual_pnls'].get('2024', 0.0)
        print(f"{i}. {r['name']:<25s} | Score={score:>10,.0f} | 2023={pnl23:>10,.0f} | 2024={pnl24:>10,.0f}")

    out = PROJECT_ROOT / "reports" / "win_linearize_parallel.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
