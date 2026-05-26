"""A/B test: G72 6 anos com vs sem fechamento forcado EOD + daily-stop.

Mede o impacto do bug critico de paridade entre Python e MQL5.
"""
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

YEARS = ("2021", "2022", "2023", "2024", "2025", "2026")
days = []
for y in YEARS:
    days.extend([d for d in list_days("WIN") if d.startswith(y)])
days.sort()
print(f"Total dias: {len(days)}", flush=True)

base = {
    "renko_r": 25, "tick_size": 5.0, "tick_value": 0.20,
    "base_qty": 1, "max_levels": 3, "martingale": False,
    "price_increment": 100.0, "gain_increment": 72.0,
    "gain_increment_pct": 0.0, "stop_loss_pts": 0.0,
    "stop_loss_pct": 0.003, "slippage_pts": 2.0,
    "emolumentos_pct": 0.0001, "daily_stop_loss": 75.0,
    "preservation_stop": False, "preservation_levels": 3,
    "trailing_stop_value": 0.0, "start_time_ms": 34200000,
    "end_time_ms": 60600000, "use_macd": True, "use_2mv": True,
    "min_bricks_for_signal": 2,
}

configs = {
    "no_force_close":   {"force_close_eod": False, "force_close_daily_stop": False},
    "eod_only":         {"force_close_eod": True,  "force_close_daily_stop": False},
    "ds_only":          {"force_close_eod": False, "force_close_daily_stop": True},
    "both_mql5_parity": {"force_close_eod": True,  "force_close_daily_stop": True},
}

summary = {}
for name, extra in configs.items():
    cfg = {**base, **extra}
    results = []
    for day in days:
        try:
            results.append(run_day_fast("WIN", day, cfg))
        except Exception:
            pass
    agg = aggregate_results(results)
    annual = {}
    for r in results:
        y = r.start_date[:4]
        annual[y] = annual.get(y, 0.0) + r.net_pnl
    total = agg.net_pnl
    vals = [annual.get(y, 0.0) for y in YEARS]
    cv = abs(np.std(vals) / np.mean(vals)) if np.mean(vals) != 0 else float("inf")
    summary[name] = {
        "total_pnl": total,
        "profit_factor": agg.profit_factor,
        "win_rate": agg.win_rate,
        "max_drawdown": agg.max_drawdown,
        "n_trades": agg.n_trades,
        "cv": cv,
        "annual": annual,
    }
    print(f"\n[{name}]", flush=True)
    print(f"  PnL R${total:>12,.2f} | PF {agg.profit_factor:.2f} | WR {agg.win_rate:.1f}% | DD R${agg.max_drawdown:,.2f} | N {agg.n_trades}", flush=True)
    for y in YEARS:
        print(f"  {y}: R${annual.get(y,0.0):>12,.2f}", flush=True)

out = PROJECT_ROOT / "reports" / "validate_eod_fix.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2, ensure_ascii=False)
print(f"\nSaved: {out}", flush=True)

# Print delta table
base_pnl = summary["no_force_close"]["total_pnl"]
print(f"\n=== IMPACTO DA CORRECAO ===", flush=True)
print(f"Baseline (sem fix):  R${base_pnl:>12,.2f}", flush=True)
for name in ("eod_only", "ds_only", "both_mql5_parity"):
    delta = summary[name]["total_pnl"] - base_pnl
    pct = delta / base_pnl * 100 if base_pnl != 0 else 0
    print(f"{name:>20s}: R${summary[name]['total_pnl']:>12,.2f} (Delta R${delta:>+11,.2f} = {pct:+.1f}%)", flush=True)
