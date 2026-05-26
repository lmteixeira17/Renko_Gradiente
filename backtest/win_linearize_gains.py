"""
Testar alternativas para linearizar ganhos anuais do WIN.
Foco: reduzir dependencia de um unico ano (2023).

Variacoes testadas:
1. Preservation stop ativado (breakeven apos N niveis)
2. Trailing stop agressivo
3. ML2 (menos niveis = menos risco em tendencia)
4. Stop diario mais apertado (R$50)
5. Combinacoes das anteriores
"""
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
        "preservation_stop": cfg.preservation_stop,
        "preservation_levels": cfg.preservation_levels,
        "trailing_stop_value": cfg.trailing_stop_value,
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

    # Calcula PnL por ano
    annual_pnls = {}
    for r in results:
        year = r.start_date[:4]
        annual_pnls[year] = annual_pnls.get(year, 0.0) + r.net_pnl

    return {
        "name": cfg.name, "asset": cfg.asset, "years": cfg.years,
        "n_days": len(days), "n_trades": agg.n_trades, "win_rate": agg.win_rate,
        "profit_factor": agg.profit_factor, "net_pnl": agg.net_pnl,
        "max_drawdown": agg.max_drawdown, "max_drawdown_pct": dd_pct,
        "avg_trade": agg.avg_trade, "return_dd_ratio": return_dd,
        "exec_time_s": dt, "initial_capital": cfg.initial_capital,
        "annual_pnls": annual_pnls,
    }


def calc_coefficient_of_variation(annual_pnls: dict) -> float:
    """CV = desvio_padrao / media. Menor = mais linear/consistente."""
    import numpy as np
    values = list(annual_pnls.values())
    if not values or np.mean(values) == 0:
        return float('inf')
    return abs(np.std(values) / np.mean(values))


def calc_max_year_contribution(annual_pnls: dict) -> float:
    """Qual % do total o melhor ano representa. Menor = mais distribuido."""
    total = sum(annual_pnls.values())
    if total == 0:
        return 0.0
    return max(annual_pnls.values()) / total * 100


def main():
    years = ["2021", "2022", "2023", "2024", "2025", "2026"]

    configs = [
        # Baseline original (para comparacao)
        Config(name="baseline_ML3_SL300_DS100", asset="WIN", years=years,
               initial_capital=15000.0, max_levels=3, stop_loss_pts=300.0,
               daily_stop_loss=100.0),

        # Variacao 1: Preservation stop ativado
        Config(name="preserv_ML3_SL300_DS100", asset="WIN", years=years,
               initial_capital=15000.0, max_levels=3, stop_loss_pts=300.0,
               daily_stop_loss=100.0, preservation_stop=True, preservation_levels=2),

        # Variacao 2: Trailing stop agressivo
        Config(name="trail_ML3_SL300_DS100", asset="WIN", years=years,
               initial_capital=15000.0, max_levels=3, stop_loss_pts=300.0,
               daily_stop_loss=100.0, trailing_stop_value=100.0),

        # Variacao 3: Preservation + Trailing
        Config(name="preserv_trail_ML3_SL300_DS100", asset="WIN", years=years,
               initial_capital=15000.0, max_levels=3, stop_loss_pts=300.0,
               daily_stop_loss=100.0, preservation_stop=True, preservation_levels=2,
               trailing_stop_value=100.0),

        # Variacao 4: ML2 (menos niveis = menos risco)
        Config(name="baseline_ML2_SL300_DS100", asset="WIN", years=years,
               initial_capital=15000.0, max_levels=2, stop_loss_pts=300.0,
               daily_stop_loss=100.0),

        # Variacao 5: ML2 + Preservation
        Config(name="preserv_ML2_SL300_DS100", asset="WIN", years=years,
               initial_capital=15000.0, max_levels=2, stop_loss_pts=300.0,
               daily_stop_loss=100.0, preservation_stop=True, preservation_levels=2),

        # Variacao 6: Stop diario mais apertado (R$50)
        Config(name="baseline_ML3_SL300_DS50", asset="WIN", years=years,
               initial_capital=15000.0, max_levels=3, stop_loss_pts=300.0,
               daily_stop_loss=50.0),

        # Variacao 7: ML2 + DS50
        Config(name="baseline_ML2_SL300_DS50", asset="WIN", years=years,
               initial_capital=15000.0, max_levels=2, stop_loss_pts=300.0,
               daily_stop_loss=50.0),

        # Variacao 8: SL mais apertado (200pts) + ML2
        Config(name="baseline_ML2_SL200_DS100", asset="WIN", years=years,
               initial_capital=15000.0, max_levels=2, stop_loss_pts=200.0,
               daily_stop_loss=100.0),

        # Variacao 9: SL mais amplo (400pts) + ML3 + preservation
        Config(name="preserv_ML3_SL400_DS100", asset="WIN", years=years,
               initial_capital=15000.0, max_levels=3, stop_loss_pts=400.0,
               daily_stop_loss=100.0, preservation_stop=True, preservation_levels=2),

        # Variacao 10: ML3 + gain maior (100pts) — captura mais do movimento
        Config(name="baseline_ML3_SL300_gain100_DS100", asset="WIN", years=years,
               initial_capital=15000.0, max_levels=3, stop_loss_pts=300.0,
               gain_increment=100.0, daily_stop_loss=100.0),

        # Variacao 11: ML3 + gain menor (30pts) — take profit rapido
        Config(name="baseline_ML3_SL300_gain30_DS100", asset="WIN", years=years,
               initial_capital=15000.0, max_levels=3, stop_loss_pts=300.0,
               gain_increment=30.0, daily_stop_loss=100.0),

        # Variacao 12: ML2 + gain 75 + preservation
        Config(name="preserv_ML2_SL300_gain75_DS100", asset="WIN", years=years,
               initial_capital=15000.0, max_levels=2, stop_loss_pts=300.0,
               gain_increment=75.0, daily_stop_loss=100.0,
               preservation_stop=True, preservation_levels=2),
    ]

    all_results = []
    for cfg in configs:
        print(f">>> {cfg.name}...", flush=True)
        res = run_test(cfg)
        all_results.append(res)
        cv = calc_coefficient_of_variation(res["annual_pnls"])
        max_contrib = calc_max_year_contribution(res["annual_pnls"])
        print(f"  PnL=R${res['net_pnl']:10,.2f} DD={res['max_drawdown_pct']:5.1f}% "
              f"R/DD={res['return_dd_ratio']:5.2f} PF={res['profit_factor']:.2f} "
              f"CV={cv:.2f} MaxAno={max_contrib:.1f}% ({res['exec_time_s']:.1f}s)", flush=True)

    # Ranking por linearidade (menor CV = mais linear)
    print("\n" + "="*100)
    print("=== RANKING POR LINEARIDADE (Menor Coeficiente de Variacao anual) ===")
    print("="*100)
    by_cv = sorted(all_results, key=lambda x: calc_coefficient_of_variation(x["annual_pnls"]))
    for i, r in enumerate(by_cv, 1):
        cv = calc_coefficient_of_variation(r["annual_pnls"])
        max_contrib = calc_max_year_contribution(r["annual_pnls"])
        print(f"{i:2d}. {r['name']:40s} | PnL=R${r['net_pnl']:10,.2f} "
              f"CV={cv:.2f} MaxAno={max_contrib:.1f}% R/DD={r['return_dd_ratio']:5.2f}")

    # Ranking por menor contribuicao do melhor ano
    print("\n" + "="*100)
    print("=== RANKING POR DISTRIBUICAO (Menor % do melhor ano no total) ===")
    print("="*100)
    by_contrib = sorted(all_results, key=lambda x: calc_max_year_contribution(x["annual_pnls"]))
    for i, r in enumerate(by_contrib, 1):
        cv = calc_coefficient_of_variation(r["annual_pnls"])
        max_contrib = calc_max_year_contribution(r["annual_pnls"])
        print(f"{i:2d}. {r['name']:40s} | PnL=R${r['net_pnl']:10,.2f} "
              f"MaxAno={max_contrib:.1f}% CV={cv:.2f} R/DD={r['return_dd_ratio']:5.2f}")

    # Ranking por Return/DD
    print("\n" + "="*100)
    print("=== RANKING POR Return/DD ===")
    print("="*100)
    by_rdd = sorted(all_results, key=lambda x: x["return_dd_ratio"], reverse=True)
    for i, r in enumerate(by_rdd, 1):
        cv = calc_coefficient_of_variation(r["annual_pnls"])
        max_contrib = calc_max_year_contribution(r["annual_pnls"])
        print(f"{i:2d}. {r['name']:40s} | PnL=R${r['net_pnl']:10,.2f} "
              f"R/DD={r['return_dd_ratio']:5.2f} MaxAno={max_contrib:.1f}% CV={cv:.2f}")

    # Detalhamento do top 3 por linearidade
    print("\n" + "="*100)
    print("=== DETALHAMENTO ANUAL — TOP 3 MAIS LINEARES ===")
    print("="*100)
    for r in by_cv[:3]:
        print(f"\n>> {r['name']}")
        print(f"   Total: R${r['net_pnl']:,.2f} | DD: {r['max_drawdown_pct']:.1f}% | PF: {r['profit_factor']:.2f}")
        for year in years:
            pnl = r['annual_pnls'].get(year, 0.0)
            total = r['net_pnl']
            pct = pnl / total * 100 if total != 0 else 0
            print(f"   {year}: R${pnl:>10,.2f} ({pct:>5.1f}% do total)")

    out_path = PROJECT_ROOT / "reports" / "win_linearize_gains.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    print(f"\n>>> Saved to {out_path}")


if __name__ == "__main__":
    main()
