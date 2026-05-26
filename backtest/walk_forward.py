"""Walk-forward analysis para a config GAIN_72.

Janelas: train 12m / test 6m, deslizando 6m por vez (overlapping out-of-sample).
Para cada janela:
  - Treina (avalia) um pequeno grid no periodo de treino
  - Escolhe a melhor (PnL com penalidade por DD)
  - Aplica no periodo de teste e registra OOS

Output: PnL out-of-sample agregado vs PnL in-sample, mostrando degradacao
(robustez da estrategia).
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from itertools import product

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import list_days
from backtest_engine_v2 import run_day_fast, aggregate_results

ASSET = "WIN"
ALL_DAYS = sorted(list_days(ASSET))
print(f"Total dias: {len(ALL_DAYS)} ({ALL_DAYS[0]} .. {ALL_DAYS[-1]})", flush=True)

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

# Grid pequeno mas representativo
GRID = list(product(
    [65.0, 72.0, 80.0],      # gain_increment (pts)
    [0.0025, 0.003, 0.0035], # stop_loss_pct
    [75.0, 100.0, 150.0],    # daily_stop_loss
))
print(f"Grid: {len(GRID)} configs", flush=True)

def days_in_range(start: str, end: str):
    return [d for d in ALL_DAYS if start <= d <= end]

def run_config(days, gain, sl_pct, ds):
    cfg = {**base, "gain_increment": gain, "stop_loss_pct": sl_pct, "daily_stop_loss": ds}
    results = []
    for d in days:
        try:
            results.append(run_day_fast(ASSET, d, cfg))
        except Exception:
            pass
    return aggregate_results(results)

def score(agg, dd_penalty=0.5):
    return agg.net_pnl - dd_penalty * agg.max_drawdown

# Janelas: train 12m, test 6m. Inicio: 2021-04-30
def make_windows():
    first = datetime.strptime(ALL_DAYS[0], "%Y-%m-%d")
    last = datetime.strptime(ALL_DAYS[-1], "%Y-%m-%d")
    windows = []
    t_start = first
    while True:
        train_start = t_start
        train_end = train_start + timedelta(days=365)
        test_start = train_end + timedelta(days=1)
        test_end = test_start + timedelta(days=180)
        if test_end > last:
            break
        windows.append((
            train_start.strftime("%Y-%m-%d"),
            train_end.strftime("%Y-%m-%d"),
            test_start.strftime("%Y-%m-%d"),
            test_end.strftime("%Y-%m-%d"),
        ))
        t_start += timedelta(days=180)
    return windows

windows = make_windows()
print(f"Janelas walk-forward: {len(windows)}", flush=True)

results_wf = []
total_is_pnl = 0.0
total_oos_pnl = 0.0
total_oos_dd = 0.0

for w_idx, (ts, te, vs, ve) in enumerate(windows):
    train_days = days_in_range(ts, te)
    test_days = days_in_range(vs, ve)
    print(f"\n--- Window {w_idx+1}/{len(windows)} TRAIN {ts}..{te} ({len(train_days)}d) -> TEST {vs}..{ve} ({len(test_days)}d) ---", flush=True)

    best = None
    best_score = -1e18
    for gain, sl_pct, ds in GRID:
        agg = run_config(train_days, gain, sl_pct, ds)
        s = score(agg)
        if s > best_score:
            best_score = s
            best = (gain, sl_pct, ds, agg)
    bg, bsl, bds, bagg = best
    print(f"  BEST IS: gain={bg} SLpct={bsl} DS={bds} | PnL R${bagg.net_pnl:,.2f} DD R${bagg.max_drawdown:,.2f}", flush=True)

    # OOS test
    oos_agg = run_config(test_days, bg, bsl, bds)
    print(f"  OOS:     PnL R${oos_agg.net_pnl:,.2f} DD R${oos_agg.max_drawdown:,.2f} PF {oos_agg.profit_factor:.2f}", flush=True)
    results_wf.append({
        "train_start": ts, "train_end": te,
        "test_start": vs, "test_end": ve,
        "best_gain": bg, "best_sl_pct": bsl, "best_ds": bds,
        "is_pnl": bagg.net_pnl, "is_dd": bagg.max_drawdown, "is_pf": bagg.profit_factor,
        "oos_pnl": oos_agg.net_pnl, "oos_dd": oos_agg.max_drawdown, "oos_pf": oos_agg.profit_factor,
        "oos_trades": oos_agg.n_trades, "oos_wr": oos_agg.win_rate,
    })
    total_is_pnl += bagg.net_pnl
    total_oos_pnl += oos_agg.net_pnl
    total_oos_dd = max(total_oos_dd, oos_agg.max_drawdown)

print(f"\n=== RESUMO WALK-FORWARD ===", flush=True)
print(f"Total IS PnL:  R${total_is_pnl:,.2f}", flush=True)
print(f"Total OOS PnL: R${total_oos_pnl:,.2f}", flush=True)
print(f"Degradacao:    {(1 - total_oos_pnl/total_is_pnl)*100:.1f}%", flush=True)
print(f"Max OOS DD:    R${total_oos_dd:,.2f}", flush=True)

out = PROJECT_ROOT / "reports" / "walk_forward_win_g72.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump({
        "windows": results_wf,
        "total_is_pnl": total_is_pnl,
        "total_oos_pnl": total_oos_pnl,
        "degradation_pct": (1 - total_oos_pnl/total_is_pnl)*100 if total_is_pnl > 0 else 0,
    }, f, indent=2, ensure_ascii=False)
print(f"Saved: {out}", flush=True)
