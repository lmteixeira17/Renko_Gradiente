"""Roda apenas GAIN_65 sobre 6 anos e salva JSON."""
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

c = {
    "renko_r": 25, "tick_size": 5.0, "tick_value": 0.20,
    "base_qty": 1, "max_levels": 3, "martingale": False,
    "price_increment": 100.0, "gain_increment": 65.0,
    "gain_increment_pct": 0.0, "stop_loss_pts": 300.0,
    "stop_loss_pct": 0.0, "slippage_pts": 2.0,
    "emolumentos_pct": 0.0001, "daily_stop_loss": 100.0,
    "preservation_stop": False, "preservation_levels": 3,
    "trailing_stop_value": 0.0, "start_time_ms": 34200000,
    "end_time_ms": 60600000, "use_macd": True, "use_2mv": True,
    "min_bricks_for_signal": 2,
}

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

out = {
    "name": "GAIN_65_SL300_DS100_ML3",
    "total_pnl": total, "profit_factor": agg.profit_factor,
    "win_rate": agg.win_rate, "max_drawdown": agg.max_drawdown,
    "n_trades": agg.n_trades, "avg_trade": agg.avg_trade,
    "annual_pnls": annual, "cv": cv,
    "max_year_contrib_pct": max_contrib,
    "years": list(years),
}

out_path = PROJECT_ROOT / "reports" / "win_gain65_sixyear_only.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)

print(f"Total: R${total:,.2f}", flush=True)
print(f"PF: {agg.profit_factor:.2f} | WR: {agg.win_rate:.1f}% | DD: R${agg.max_drawdown:,.2f} | Trades: {agg.n_trades}", flush=True)
for y in years:
    pnl = annual.get(y, 0.0)
    pct = pnl / total * 100 if total != 0 else 0
    print(f"{y}: R${pnl:>12,.2f} ({pct:6.1f}%)", flush=True)
print(f"CV: {cv:.2f} | MaxYearContrib: {max_contrib:.1f}%", flush=True)
print(f"Saved: {out_path}", flush=True)
