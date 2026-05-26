"""Teste completo GAIN_65 vs baseline sobre 2021-2026. Salva JSON detalhado."""
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import numpy as np
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import list_days
from backtest_engine_v2 import run_day_fast, aggregate_results

years = ("2021", "2022", "2023", "2024", "2025", "2026")
days = []
for y in years:
    days.extend([d for d in list_days("WIN") if d.startswith(y)])
days.sort()


def run_config(name, **kwargs):
    c = {
        "renko_r": 25, "tick_size": 5.0, "tick_value": 0.20,
        "base_qty": 1, "max_levels": 3, "martingale": False,
        "price_increment": 100.0, "gain_increment": 50.0,
        "gain_increment_pct": 0.0, "stop_loss_pts": 300.0,
        "stop_loss_pct": 0.0, "slippage_pts": 2.0,
        "emolumentos_pct": 0.0001, "daily_stop_loss": 100.0,
        "preservation_stop": False, "preservation_levels": 3,
        "trailing_stop_value": 0.0, "start_time_ms": 34200000,
        "end_time_ms": 60600000, "use_macd": True, "use_2mv": True,
        "min_bricks_for_signal": 2,
    }
    c.update(kwargs)

    results = []
    for day in days:
        try:
            results.append(run_day_fast("WIN", day, c))
        except Exception as e:
            pass

    agg = aggregate_results(results)
    annual = {}
    for r in results:
        y = r.start_date[:4]
        annual[y] = annual.get(y, 0.0) + r.net_pnl

    total = agg.net_pnl
    vals = [annual.get(y, 0.0) for y in years]
    cv = abs(np.std(vals) / np.mean(vals)) if np.mean(vals) != 0 else float("inf")
    max_contrib = max(vals) / total * 100 if total != 0 else 0

    return {
        "name": name, "config": {k: v for k, v in c.items() if k in [
            "gain_increment", "stop_loss_pts", "daily_stop_loss", "max_levels"
        ]},
        "total_pnl": total, "profit_factor": agg.profit_factor,
        "win_rate": agg.win_rate, "max_drawdown": agg.max_drawdown,
        "n_trades": agg.n_trades, "avg_trade": agg.avg_trade,
        "annual_pnls": annual, "cv": cv, "max_year_contrib_pct": max_contrib,
        "years": list(years),
    }


print(">>> Running BASE_fixed (gain=50)...", flush=True)
base = run_config("BASE_fixed_G50")
print(f"    Total={base['total_pnl']:,.2f} CV={base['cv']:.2f} MaxAno={base['max_year_contrib_pct']:.1f}%", flush=True)

print(">>> Running GAIN_65...", flush=True)
g65 = run_config("GAIN_65", gain_increment=65.0)
print(f"    Total={g65['total_pnl']:,.2f} CV={g65['cv']:.2f} MaxAno={g65['max_year_contrib_pct']:.1f}%", flush=True)

# Tabela comparativa
print("\n" + "=" * 80)
print("COMPARACAO ANUAL DETALHADA")
print("=" * 80)
print(f"{'Ano':<6s} | {'BASE (G50)':>12s} | {'GAIN_65':>12s} | {'Delta':>12s} | {'BASE%':>7s} | {'G65%':>7s}")
print("-" * 80)
for y in years:
    b = base["annual_pnls"].get(y, 0.0)
    g = g65["annual_pnls"].get(y, 0.0)
    delta = g - b
    bpct = b / base["total_pnl"] * 100 if base["total_pnl"] != 0 else 0
    gpct = g / g65["total_pnl"] * 100 if g65["total_pnl"] != 0 else 0
    print(f"{y} | R${b:>10,.2f} | R${g:>10,.2f} | R${delta:>10,.2f} | {bpct:6.1f}% | {gpct:6.1f}%")

print("-" * 80)
bt = base["total_pnl"]
gt = g65["total_pnl"]
print(f"TOTAL | R${bt:>10,.2f} | R${gt:>10,.2f} | R${gt-bt:>10,.2f} |")
print(f"DD    | R${base['max_drawdown']:>10,.2f} | R${g65['max_drawdown']:>10,.2f} | R${g65['max_drawdown']-base['max_drawdown']:>10,.2f} |")
print(f"PF    | {base['profit_factor']:>10.2f} | {g65['profit_factor']:>10.2f} |")
print(f"CV    | {base['cv']:>10.2f} | {g65['cv']:>10.2f} |")
print(f"MaxAno| {base['max_year_contrib_pct']:>9.1f}% | {g65['max_year_contrib_pct']:>9.1f}% |")

out = PROJECT_ROOT / "reports" / "win_gain65_sixyear.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump([base, g65], f, indent=2, ensure_ascii=False)
print(f"\n>>> Saved: {out}")
