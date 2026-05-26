"""Otimizacao focada ao redor da config vencedora G72.

Varia gain, SL pct, daily stop em torno do otimo conhecido. Roda longo prazo
2021-2026 ja com EOD fix + daily-stop force-close (paridade MQL5).

Metrica: Sortino-like score = (PnL anual medio) / (DD maximo) ponderado por CV anual.
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
ASSET = "WIN"
days = []
for y in YEARS:
    days.extend([d for d in list_days(ASSET) if d.startswith(y)])
days.sort()
print(f"Total dias: {len(days)}", flush=True)

base = {
    "renko_r": 25, "tick_size": 5.0, "tick_value": 0.20,
    "base_qty": 1, "max_levels": 3, "martingale": False,
    "price_increment": 100.0,
    "gain_increment_pct": 0.0,
    "stop_loss_pts": 0.0,
    "slippage_pts": 2.0,
    "emolumentos_pct": 0.0001,
    "preservation_stop": False, "trailing_stop_value": 0.0,
    "start_time_ms": 34200000, "end_time_ms": 60600000,
    "use_macd": True, "use_2mv": True, "min_bricks_for_signal": 2,
    "force_close_eod": True, "force_close_daily_stop": True,
}

# Grid focado ao redor do otimo conhecido (G72, SL 0.3%, DS75)
GAINS    = [65.0, 70.0, 72.0, 75.0, 80.0, 85.0]
SL_PCTS  = [0.0025, 0.003, 0.0035, 0.004]
DS_LIST  = [50.0, 75.0, 100.0, 125.0]

GRID = list(product(GAINS, SL_PCTS, DS_LIST))
print(f"Grid total: {len(GRID)} configs", flush=True)

def run_config(gain, sl_pct, ds):
    cfg = {**base, "gain_increment": gain, "stop_loss_pct": sl_pct, "daily_stop_loss": ds}
    results = []
    for d in days:
        try:
            results.append(run_day_fast(ASSET, d, cfg))
        except Exception:
            pass
    agg = aggregate_results(results)
    annual = {}
    for r in results:
        y = r.start_date[:4]
        annual[y] = annual.get(y, 0.0) + r.net_pnl
    vals = [annual.get(y, 0.0) for y in YEARS]
    cv = abs(np.std(vals) / np.mean(vals)) if np.mean(vals) != 0 else float("inf")
    return agg, annual, vals, cv

all_results = []
best_by_pnl = None
best_by_rdd = None
best_by_rdd_score = -1e18
best_by_pnl_score = -1e18

for idx, (gain, sl_pct, ds) in enumerate(GRID):
    agg, annual, vals, cv = run_config(gain, sl_pct, ds)
    rdd = agg.net_pnl / agg.max_drawdown if agg.max_drawdown > 0 else 0.0
    rec = {
        "gain": gain, "sl_pct": sl_pct, "ds": ds,
        "pnl": agg.net_pnl, "dd": agg.max_drawdown, "pf": agg.profit_factor,
        "wr": agg.win_rate, "n": agg.n_trades,
        "annual": annual, "cv": cv, "rdd": rdd,
        "neg_years": sum(1 for v in vals if v < 0),
    }
    all_results.append(rec)
    if agg.net_pnl > best_by_pnl_score:
        best_by_pnl_score = agg.net_pnl
        best_by_pnl = rec
    if rdd > best_by_rdd_score:
        best_by_rdd_score = rdd
        best_by_rdd = rec
    print(f"[{idx+1:>3}/{len(GRID)}] G{gain:>4.0f} SL{sl_pct*100:.2f}% DS{ds:>5.0f} | "
          f"PnL R${agg.net_pnl:>10,.0f} DD R${agg.max_drawdown:>8,.0f} "
          f"R/DD {rdd:>4.2f} PF {agg.profit_factor:.2f} CV {cv:.2f} NegYrs {rec['neg_years']}",
          flush=True)

all_results.sort(key=lambda r: r["pnl"], reverse=True)

print(f"\n=== TOP 10 POR PnL ===", flush=True)
for r in all_results[:10]:
    print(f"  G{r['gain']:>4.0f} SL{r['sl_pct']*100:.2f}% DS{r['ds']:>5.0f} | "
          f"PnL R${r['pnl']:>10,.0f} DD R${r['dd']:>8,.0f} R/DD {r['rdd']:.2f} CV {r['cv']:.2f}",
          flush=True)

all_results.sort(key=lambda r: r["rdd"], reverse=True)
print(f"\n=== TOP 10 POR R/DD ===", flush=True)
for r in all_results[:10]:
    print(f"  G{r['gain']:>4.0f} SL{r['sl_pct']*100:.2f}% DS{r['ds']:>5.0f} | "
          f"PnL R${r['pnl']:>10,.0f} DD R${r['dd']:>8,.0f} R/DD {r['rdd']:.2f} CV {r['cv']:.2f}",
          flush=True)

out = PROJECT_ROOT / "reports" / "optimize_around_g72.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump({
        "all": all_results,
        "best_pnl": best_by_pnl,
        "best_rdd": best_by_rdd,
        "grid_size": len(GRID),
    }, f, indent=2, ensure_ascii=False)
print(f"\nSaved: {out}", flush=True)
