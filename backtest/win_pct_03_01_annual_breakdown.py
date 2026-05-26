"""Breakdown anual da melhor config WIN (0.3%/0.1%/DS75)."""
import sys
sys.stdout.reconfigure(line_buffering=True)
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import list_days
from backtest_engine_v2 import run_day_fast, aggregate_results


def main():
    years = ["2021", "2022", "2023", "2024", "2025", "2026"]
    days = []
    for y in years:
        days.extend([d for d in list_days("WIN") if d.startswith(y)])
    days.sort()

    c = {
        "renko_r": 25, "tick_size": 5.0, "tick_value": 0.20,
        "base_qty": 1, "max_levels": 3, "martingale": False,
        "price_increment": 100.0, "gain_increment": 0.0,
        "gain_increment_pct": 0.001,
        "stop_loss_pts": 0.0, "stop_loss_pct": 0.003,
        "slippage_pts": 2.0, "emolumentos_pct": 0.0001,
        "daily_stop_loss": 75.0,
        "start_time_ms": 34200000, "end_time_ms": 60600000,
        "use_macd": True, "use_2mv": True, "min_bricks_for_signal": 2,
    }

    annual_results = {y: [] for y in years}
    all_results = []

    for day in days:
        try:
            res = run_day_fast("WIN", day, c)
            all_results.append(res)
            year = day[:4]
            if year in annual_results:
                annual_results[year].append(res)
        except Exception as e:
            print(f"  {day}: ERROR {e}", flush=True)

    agg_total = aggregate_results(all_results)
    print("\n" + "="*80)
    print("BREAKDOWN ANUAL — WIN | SL 0,3% | Gain 0,1% | DS R$75")
    print("="*80)
    print(f"{'Ano':>6s} | {'Dias':>5s} | {'Trades':>7s} | {'PnL':>12s} | {'WR':>6s} | {'PF':>5s} | {'DD':>10s}")
    print("-"*80)

    for year in years:
        results = annual_results[year]
        if not results:
            continue
        agg = aggregate_results(results)
        print(f"{year:>6s} | {agg.n_days:>5d} | {agg.n_trades:>7d} | R${agg.net_pnl:>10,.2f} | {agg.win_rate:>5.1f}% | {agg.profit_factor:>4.2f} | R${agg.max_drawdown:>8,.2f}")

    print("-"*80)
    print(f"{'TOTAL':>6s} | {agg_total.n_days:>5d} | {agg_total.n_trades:>7d} | R${agg_total.net_pnl:>10,.2f} | {agg_total.win_rate:>5.1f}% | {agg_total.profit_factor:>4.2f} | R${agg_total.max_drawdown:>8,.2f}")
    print("="*80)

    # Calcula retorno % anual sobre capital de 15k
    print("\n>>> RETORNO % SOBRE CAPITAL DE R$ 15.000:")
    capital = 15000.0
    cumulative = 0.0
    for year in years:
        results = annual_results[year]
        if not results:
            continue
        agg = aggregate_results(results)
        ret_pct = agg.net_pnl / capital * 100
        cumulative += agg.net_pnl
        print(f"  {year}: R${agg.net_pnl:>10,.2f} ({ret_pct:>6.2f}%) | Acumulado: R${cumulative:>10,.2f}")

    print(f"\n  Retorno TOTAL em 6 anos: {cumulative / capital * 100:.1f}%")
    print(f"  Retorno MÉDIO ao ano: {cumulative / capital / len(years) * 100:.1f}%")

    # Estatísticas de consistência
    pnls = [aggregate_results(annual_results[y]).net_pnl for y in years if annual_results[y]]
    import numpy as np
    print(f"\n>>> ESTATÍSTICAS DE CONSISTÊNCIA:")
    print(f"  Anos positivos: {sum(1 for p in pnls if p > 0)}/{len(pnls)}")
    print(f"  Anos negativos: {sum(1 for p in pnls if p < 0)}/{len(pnls)}")
    print(f"  Melhor ano: R${max(pnls):,.2f}")
    print(f"  Pior ano: R${min(pnls):,.2f}")
    print(f"  Desvio padrão anual: R${np.std(pnls):,.2f}")
    print(f"  PnL médio/ano: R${np.mean(pnls):,.2f}")


if __name__ == "__main__":
    main()
