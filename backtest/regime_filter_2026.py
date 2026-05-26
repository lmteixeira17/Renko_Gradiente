"""Testa filtros de regime para mitigar 2026.

Baseline: G72/SL0.30%/DS75 (engine corrigida EOD).
Sweep:
  - max_ema_distance_pts (filtro de EMAs esticadas)
  - min_bricks_for_signal (exigir mais confirmacao de pullback)
Combinacoes: 8 EMAdist x 3 min_bricks = 24 configs.

Objetivo: reduzir perda de 2026 sem destruir 2021-2025.
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import numpy as np
from pathlib import Path
from itertools import product

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
    "preservation_stop": False, "trailing_stop_value": 0.0,
    "start_time_ms": 34200000, "end_time_ms": 60600000,
    "use_macd": True, "use_2mv": True,
    "force_close_eod": True, "force_close_daily_stop": True,
}

EMA_DISTS = [0.0, 200.0, 400.0, 600.0, 800.0, 1000.0, 1500.0, 2000.0]
MIN_BRICKS = [2, 3, 4]
GRID = list(product(EMA_DISTS, MIN_BRICKS))
print(f"Grid: {len(GRID)} configs", flush=True)

results_all = []
for idx, (ema_dist, min_b) in enumerate(GRID):
    cfg = {**base, "max_ema_distance_pts": ema_dist, "min_bricks_for_signal": min_b}
    results = []
    for d in days:
        try:
            results.append(run_day_fast("WIN", d, cfg))
        except Exception:
            pass
    agg = aggregate_results(results)
    annual = {}
    for r in results:
        y = r.start_date[:4]
        annual[y] = annual.get(y, 0.0) + r.net_pnl
    vals = [annual.get(y, 0.0) for y in YEARS]
    cv = abs(np.std(vals) / np.mean(vals)) if np.mean(vals) != 0 else float("inf")
    rdd = agg.net_pnl / agg.max_drawdown if agg.max_drawdown > 0 else 0.0
    neg = sum(1 for v in vals if v < 0)
    rec = {
        "ema_dist": ema_dist, "min_bricks": min_b,
        "pnl": agg.net_pnl, "dd": agg.max_drawdown,
        "pf": agg.profit_factor, "wr": agg.win_rate, "n": agg.n_trades,
        "annual": annual, "cv": cv, "rdd": rdd,
        "pnl_2026": annual.get("2026", 0.0),
        "pnl_2021_2025": sum(annual.get(y, 0.0) for y in YEARS if y != "2026"),
        "neg_years": neg,
    }
    results_all.append(rec)
    print(f"[{idx+1:>2}/{len(GRID)}] EMAd={ema_dist:>6.0f} MinB={min_b} | "
          f"PnL R${agg.net_pnl:>10,.0f} 21-25 R${rec['pnl_2021_2025']:>10,.0f} 2026 R${rec['pnl_2026']:>8,.0f} "
          f"DD R${agg.max_drawdown:>8,.0f} R/DD {rdd:.2f} CV {cv:.2f} N {agg.n_trades:>6}", flush=True)

print(f"\n=== TOP 10 POR PnL (21-25 + 26) ===", flush=True)
results_all.sort(key=lambda r: r["pnl"], reverse=True)
for r in results_all[:10]:
    print(f"  EMAd={r['ema_dist']:>6.0f} MinB={r['min_bricks']} | "
          f"PnL R${r['pnl']:>10,.0f} 21-25 R${r['pnl_2021_2025']:>10,.0f} 2026 R${r['pnl_2026']:>8,.0f} "
          f"R/DD {r['rdd']:.2f}", flush=True)

print(f"\n=== TOP 10 POR MENOR PERDA 2026 ===", flush=True)
results_all.sort(key=lambda r: -r["pnl_2026"])
for r in results_all[:10]:
    print(f"  EMAd={r['ema_dist']:>6.0f} MinB={r['min_bricks']} | "
          f"2026 R${r['pnl_2026']:>8,.0f} 21-25 R${r['pnl_2021_2025']:>10,.0f} Total R${r['pnl']:>10,.0f} "
          f"R/DD {r['rdd']:.2f}", flush=True)

print(f"\n=== TOP 10 POR R/DD ===", flush=True)
results_all.sort(key=lambda r: r["rdd"], reverse=True)
for r in results_all[:10]:
    print(f"  EMAd={r['ema_dist']:>6.0f} MinB={r['min_bricks']} | "
          f"PnL R${r['pnl']:>10,.0f} 21-25 R${r['pnl_2021_2025']:>10,.0f} 2026 R${r['pnl_2026']:>8,.0f} "
          f"R/DD {r['rdd']:.2f}", flush=True)

out = PROJECT_ROOT / "reports" / "regime_filter_2026.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump({"results": results_all}, f, indent=2, ensure_ascii=False)
print(f"\nSaved: {out}", flush=True)
