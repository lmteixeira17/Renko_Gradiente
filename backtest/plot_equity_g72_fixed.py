"""Gera curva de equity da config G72 com engine corrigida (EOD fix)."""
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import numpy as np
import matplotlib.pyplot as plt
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

cfg = {
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
    "force_close_eod": True, "force_close_daily_stop": True,
}

print(f"Rodando G72 (com EOD fix) sobre {len(days)} dias...", flush=True)
results = []
for d in days:
    try:
        results.append(run_day_fast("WIN", d, cfg))
    except Exception:
        pass

# Equity by day
dates = []
equity = []
running = 0.0
peak = 0.0
dd = []
for r in results:
    running += r.net_pnl
    if running > peak:
        peak = running
    dates.append(r.start_date)
    equity.append(running)
    dd.append(running - peak)

# Save data
out_json = PROJECT_ROOT / "reports" / "equity_g72_fixed.json"
with open(out_json, "w", encoding="utf-8") as f:
    json.dump({
        "dates": dates,
        "equity": equity,
        "drawdown": dd,
        "total_pnl": running,
        "peak": peak,
        "max_dd": min(dd) if dd else 0,
    }, f, indent=2, ensure_ascii=False)
print(f"Saved JSON: {out_json}", flush=True)

# Plot
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
x = np.arange(len(dates))
ax1.plot(x, equity, color="#1f77b4", linewidth=1.0, label="Equity")
ax1.fill_between(x, equity, alpha=0.15, color="#1f77b4")
ax1.set_ylabel("Equity acumulada (R$)")
ax1.grid(alpha=0.3)
ax1.set_title(f"WIN G72 + SL0.3% + DS75 (engine MQL5-parity) | PnL R${running:,.0f} | DD R${abs(min(dd)):,.0f}")
ax1.legend(loc="upper left")

ax2.fill_between(x, dd, 0, color="#d62728", alpha=0.5)
ax2.set_ylabel("Drawdown (R$)")
ax2.set_xlabel("Dia (sequencial)")
ax2.grid(alpha=0.3)

n_ticks = 12
step = max(1, len(dates) // n_ticks)
ax1.set_xticks(x[::step])
ax1.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=45, ha="right")

plt.tight_layout()
out_png = PROJECT_ROOT / "reports" / "equity_g72_fixed.png"
plt.savefig(out_png, dpi=120)
print(f"Saved PNG: {out_png}", flush=True)
print(f"Total: R${running:,.2f} | Peak: R${peak:,.2f} | MaxDD: R${abs(min(dd)):,.2f}", flush=True)
