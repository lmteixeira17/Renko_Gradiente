"""
Bateria completa de testes WIN:
- Dados reais 2025 e 2026
- Stop gain/loss como % do valor de mercado
- Variacoes de stop diario
- Diferentes capitais de referencia

Fases:
1. Baselines 2025 e 2026 (config atual + stops diarios)
2. Grid de stop % em 2025 e 2026
3. Melhores configs em longo prazo 2021-2026
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import list_days
from backtest_engine_v2 import run_day_fast, aggregate_results


@dataclass
class TestConfig:
    name: str
    asset: str
    years: list[str]
    # Params
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
    start_time_ms: int = 34200000  # 9:30
    end_time_ms: int = 60600000    # 16:50
    # Meta
    initial_capital: float = 5000.0


def run_test(cfg: TestConfig) -> dict[str, Any]:
    days = []
    for y in cfg.years:
        days.extend([d for d in list_days(cfg.asset) if d.startswith(y)])
    days.sort()

    c = {
        "renko_r": cfg.renko_r,
        "tick_size": cfg.tick_size,
        "tick_value": cfg.tick_value,
        "base_qty": cfg.base_qty,
        "max_levels": cfg.max_levels,
        "martingale": cfg.martingale,
        "price_increment": cfg.price_increment,
        "gain_increment": cfg.gain_increment,
        "gain_increment_pct": cfg.gain_increment_pct,
        "stop_loss_pts": cfg.stop_loss_pts,
        "stop_loss_pct": cfg.stop_loss_pct,
        "slippage_pts": cfg.slippage_pts,
        "emolumentos_pct": cfg.emolumentos_pct,
        "daily_stop_loss": cfg.daily_stop_loss,
        "start_time_ms": cfg.start_time_ms,
        "end_time_ms": cfg.end_time_ms,
        "use_macd": True,
        "use_2mv": True,
        "min_bricks_for_signal": 2,
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
        "name": cfg.name,
        "asset": cfg.asset,
        "years": cfg.years,
        "n_days": len(days),
        "n_trades": agg.n_trades,
        "win_rate": agg.win_rate,
        "profit_factor": agg.profit_factor,
        "net_pnl": agg.net_pnl,
        "max_drawdown": agg.max_drawdown,
        "max_drawdown_pct": dd_pct,
        "avg_trade": agg.avg_trade,
        "gross_profit": agg.gross_profit,
        "gross_loss": agg.gross_loss,
        "return_dd_ratio": return_dd,
        "exec_time_s": dt,
        "initial_capital": cfg.initial_capital,
        "renko_r": cfg.renko_r,
        "max_levels": cfg.max_levels,
        "martingale": cfg.martingale,
        "price_increment": cfg.price_increment,
        "gain_increment": cfg.gain_increment,
        "gain_increment_pct": cfg.gain_increment_pct,
        "stop_loss_pts": cfg.stop_loss_pts,
        "stop_loss_pct": cfg.stop_loss_pct,
        "daily_stop_loss": cfg.daily_stop_loss,
    }


def print_result(r: dict):
    print(f"  {r['name']:50s} | Trades={r['n_trades']:5d} PnL=R${r['net_pnl']:10,.2f} "
          f"WR={r['win_rate']:5.1f}% PF={r['profit_factor']:.2f} "
          f"DD=R${r['max_drawdown']:9,.2f} ({r['max_drawdown_pct']:5.1f}%) "
          f"R/DD={r['return_dd_ratio']:5.2f} Avg={r['avg_trade']:.2f} ({r['exec_time_s']:.1f}s)", flush=True)


def run_phase(name: str, configs: list[TestConfig], results: list[dict]) -> list[dict]:
    print(f"\n{'='*80}")
    print(f"=== {name} ===")
    print(f"{'='*80}", flush=True)
    for cfg in configs:
        print(f">>> {cfg.name}...", flush=True)
        res = run_test(cfg)
        results.append(res)
        print_result(res)
    return results


def main():
    all_results: list[dict] = []

    # ========================================================================
    # FASE 1: Baselines 2025 e 2026 (config atual + varios stops diarios)
    # ========================================================================
    print("\n>>> FASE 1: Baselines em 2025 e 2026", flush=True)
    stops = [50.0, 75.0, 100.0, 150.0, 200.0]
    capitals = [5000.0, 10000.0, 15000.0]

    fase1_configs = []
    for year in ["2025", "2026"]:
        for stop in stops:
            for cap in capitals:
                fase1_configs.append(TestConfig(
                    name=f"WIN_baseline_{year}_stop{stop:.0f}_cap{cap:.0f}",
                    asset="WIN",
                    years=[year],
                    daily_stop_loss=stop,
                    initial_capital=cap,
                ))

    all_results = run_phase("FASE 1: Baselines 2025-2026", fase1_configs, all_results)

    # ========================================================================
    # FASE 2: Grid de Stop % em 2025 e 2026
    # ========================================================================
    print("\n>>> FASE 2: Stop % do valor de mercado em 2025 e 2026", flush=True)
    sl_pcts = [0.001, 0.0015, 0.002, 0.003]       # 0.1%, 0.15%, 0.2%, 0.3%
    gain_pcts = [0.0005, 0.0008, 0.001]            # 0.05%, 0.08%, 0.1%
    stops2 = [75.0, 100.0, 150.0]
    caps2 = [5000.0, 10000.0, 15000.0]

    fase2_configs = []
    for year in ["2025", "2026"]:
        for sl_pct in sl_pcts:
            for gain_pct in gain_pcts:
                for stop in stops2:
                    for cap in caps2:
                        # Pula combinacoes muito ruins (gain > sl)
                        if gain_pct >= sl_pct:
                            continue
                        fase2_configs.append(TestConfig(
                            name=f"WIN_pct_{year}_SL{sl_pct:.4f}_G{gain_pct:.4f}_DS{stop:.0f}_cap{cap:.0f}",
                            asset="WIN",
                            years=[year],
                            stop_loss_pts=0.0,
                            stop_loss_pct=sl_pct,
                            gain_increment=0.0,
                            gain_increment_pct=gain_pct,
                            daily_stop_loss=stop,
                            initial_capital=cap,
                        ))

    all_results = run_phase("FASE 2: Stop % 2025-2026", fase2_configs, all_results)

    # ========================================================================
    # FASE 3: Melhores configs em longo prazo 2021-2026
    # ========================================================================
    print("\n>>> FASE 3: Longo prazo 2021-2026", flush=True)

    # Baseline longo prazo
    fase3_configs = [
        TestConfig(name="WIN_baseline_2021-2026_stop100_cap5000", asset="WIN",
                   years=["2021", "2022", "2023", "2024", "2025", "2026"],
                   daily_stop_loss=100.0, initial_capital=5000.0),
        TestConfig(name="WIN_baseline_2021-2026_stop100_cap10000", asset="WIN",
                   years=["2021", "2022", "2023", "2024", "2025", "2026"],
                   daily_stop_loss=100.0, initial_capital=10000.0),
        TestConfig(name="WIN_baseline_2021-2026_stop100_cap15000", asset="WIN",
                   years=["2021", "2022", "2023", "2024", "2025", "2026"],
                   daily_stop_loss=100.0, initial_capital=15000.0),
    ]

    # Adiciona top configs de stop % (escolhidas manualmente com base no grid)
    top_pct_configs = [
        (0.0015, 0.0008, 100.0),   # SL 0.15%, gain 0.08%, stop 100
        (0.002, 0.0008, 100.0),    # SL 0.2%, gain 0.08%, stop 100
        (0.0015, 0.0005, 75.0),    # SL 0.15%, gain 0.05%, stop 75
        (0.001, 0.0005, 75.0),     # SL 0.1%, gain 0.05%, stop 75
    ]
    for sl_pct, gain_pct, stop in top_pct_configs:
        for cap in [5000.0, 10000.0, 15000.0]:
            fase3_configs.append(TestConfig(
                name=f"WIN_pct_2021-2026_SL{sl_pct:.4f}_G{gain_pct:.4f}_DS{stop:.0f}_cap{cap:.0f}",
                asset="WIN",
                years=["2021", "2022", "2023", "2024", "2025", "2026"],
                stop_loss_pts=0.0,
                stop_loss_pct=sl_pct,
                gain_increment=0.0,
                gain_increment_pct=gain_pct,
                daily_stop_loss=stop,
                initial_capital=cap,
            ))

    all_results = run_phase("FASE 3: Longo prazo 2021-2026", fase3_configs, all_results)

    # ========================================================================
    # FASE 4: Stop diario mais agressivo (R$30, R$40) em 2025-2026
    # ========================================================================
    print("\n>>> FASE 4: Stops diarios agressivos 2025-2026", flush=True)
    fase4_configs = []
    for year in ["2025", "2026"]:
        for stop in [30.0, 40.0, 50.0, 60.0]:
            for cap in [5000.0, 10000.0]:
                fase4_configs.append(TestConfig(
                    name=f"WIN_baseline_{year}_stop{stop:.0f}_cap{cap:.0f}",
                    asset="WIN",
                    years=[year],
                    daily_stop_loss=stop,
                    initial_capital=cap,
                ))
    all_results = run_phase("FASE 4: Stops agressivos 2025-2026", fase4_configs, all_results)

    # ========================================================================
    # FASE 5: Comparacao 2025 vs 2021-2025 para mesma config
    # ========================================================================
    print("\n>>> FASE 5: Comparacao periodos para baseline", flush=True)
    fase5_configs = [
        TestConfig(name="WIN_baseline_2025_only_cap5000", asset="WIN", years=["2025"],
                   daily_stop_loss=100.0, initial_capital=5000.0),
        TestConfig(name="WIN_baseline_2021-2025_cap5000", asset="WIN",
                   years=["2021", "2022", "2023", "2024", "2025"],
                   daily_stop_loss=100.0, initial_capital=5000.0),
        TestConfig(name="WIN_baseline_2021-2026_cap5000", asset="WIN",
                   years=["2021", "2022", "2023", "2024", "2025", "2026"],
                   daily_stop_loss=100.0, initial_capital=5000.0),
    ]
    all_results = run_phase("FASE 5: Comparacao periodos", fase5_configs, all_results)

    # ========================================================================
    # Save & Rank
    # ========================================================================
    # Rank por return/dd
    all_results.sort(key=lambda x: x["return_dd_ratio"], reverse=True)

    print("\n" + "="*100)
    print("=== RANKING GLOBAL (Return/DD) ===")
    print("="*100)
    for i, r in enumerate(all_results[:30], 1):
        print(f"{i:2d}. {r['name']:55s} | PnL=R${r['net_pnl']:10,.2f} "
              f"DD={r['max_drawdown_pct']:5.1f}% R/DD={r['return_dd_ratio']:6.2f} "
              f"PF={r['profit_factor']:5.2f} WR={r['win_rate']:5.1f}%", flush=True)

    out_path = PROJECT_ROOT / "reports" / "win_full_battery_2025_2026.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n>>> Saved to {out_path}", flush=True)

    # Rankings separados por fase/categoria
    print("\n>>> Gerando rankings detalhados...", flush=True)

    # Top por PnL
    by_pnl = sorted(all_results, key=lambda x: x["net_pnl"], reverse=True)
    print("\n=== TOP 10 POR PnL ===")
    for i, r in enumerate(by_pnl[:10], 1):
        print(f"{i:2d}. {r['name']:55s} | PnL=R${r['net_pnl']:10,.2f} DD={r['max_drawdown_pct']:5.1f}%", flush=True)

    # Top por menor DD%
    by_dd = sorted(all_results, key=lambda x: x["max_drawdown_pct"])
    print("\n=== TOP 10 MENOR DD% ===")
    for i, r in enumerate(by_dd[:10], 1):
        print(f"{i:2d}. {r['name']:55s} | DD={r['max_drawdown_pct']:5.1f}% PnL=R${r['net_pnl']:10,.2f}", flush=True)


if __name__ == "__main__":
    main()
