"""Teste RAPIDO: apenas 3 configs sobre 2023+2024 (~3 min total)."""
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import list_days
from backtest_engine_v2 import run_day_fast, aggregate_results


def test(name, **kwargs):
    years = ("2023", "2024")
    days = []
    for y in years:
        days.extend([d for d in list_days("WIN") if d.startswith(y)])
    days.sort()

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
    t0 = time.time()
    for day in days:
        try:
            results.append(run_day_fast("WIN", day, c))
        except Exception as e:
            pass
    dt = time.time() - t0

    agg = aggregate_results(results)
    annual = {}
    for r in results:
        y = r.start_date[:4]
        annual[y] = annual.get(y, 0.0) + r.net_pnl

    pnl23 = annual.get('2023', 0.0)
    pnl24 = annual.get('2024', 0.0)
    print(f"{name:<30s} | Total={agg.net_pnl:>10,.0f} | 2023={pnl23:>10,.0f} | 2024={pnl24:>10,.0f} | "
          f"PF={agg.profit_factor:5.2f} | WR={agg.win_rate:5.1f}% | DD={agg.max_drawdown:>8,.0f} | {dt:.1f}s", flush=True)
    return {"name": name, "total": agg.net_pnl, "2023": pnl23, "2024": pnl24,
            "pf": agg.profit_factor, "wr": agg.win_rate, "dd": agg.max_drawdown, "n_trades": agg.n_trades}


print(f"{'Config':<30s} | {'Total':>10s} | {'2023':>10s} | {'2024':>10s} | {'PF':>5s} | {'WR%':>5s} | {'DD':>8s} | t(s)")
print("-" * 110)

results = []
results.append(test("BASE_fixed"))
results.append(test("PRESERV_L1", preservation_stop=True, preservation_levels=1))
results.append(test("TRAIL_50", trailing_stop_value=50.0))
results.append(test("TRAIL_100", trailing_stop_value=100.0))
results.append(test("PRESERV1_TRAIL50", preservation_stop=True, preservation_levels=1, trailing_stop_value=50.0))
results.append(test("ML2", max_levels=2))
results.append(test("ML2_PRESERV1", max_levels=2, preservation_stop=True, preservation_levels=1))
results.append(test("DS50", daily_stop_loss=50.0))
results.append(test("GAIN30", gain_increment=30.0))
results.append(test("GAIN100", gain_increment=100.0))
results.append(test("SL200", stop_loss_pts=200.0))

# Ranking
print("\n" + "=" * 80)
print("RANKING por equilibrio (2*2024 + 2023 - DD/100)")
scored = []
for r in results:
    score = (r["2024"] * 2) + r["2023"] - (r["dd"] / 100)
    scored.append((score, r))
scored.sort(reverse=True)
for i, (score, r) in enumerate(scored, 1):
    print(f"{i:2d}. {r['name']:<25s} Score={score:>10,.0f} | 2023={r['2023']:>10,.0f} | 2024={r['2024']:>10,.0f}")

out = PROJECT_ROOT / "reports" / "win_linearize_quick.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print(f"\nSaved: {out}")
