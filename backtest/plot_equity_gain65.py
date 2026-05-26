"""Plota equity curve da config GAIN_65 + Stop% vs baseline."""
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import list_days
from backtest_engine_v2 import run_day_fast

years = ("2021", "2022", "2023", "2024", "2025", "2026")
days = []
for y in years:
    days.extend([d for d in list_days("WIN") if d.startswith(y)])
days.sort()


def run_and_get_pnls(gain, stop_pct=None, ds=100.0):
    c = {
        "renko_r": 25, "tick_size": 5.0, "tick_value": 0.20,
        "base_qty": 1, "max_levels": 3, "martingale": False,
        "price_increment": 100.0, "gain_increment": gain,
        "gain_increment_pct": 0.0, "stop_loss_pts": 300.0,
        "stop_loss_pct": 0.0, "slippage_pts": 2.0,
        "emolumentos_pct": 0.0001, "daily_stop_loss": ds,
        "preservation_stop": False, "preservation_levels": 3,
        "trailing_stop_value": 0.0, "start_time_ms": 34200000,
        "end_time_ms": 60600000, "use_macd": True, "use_2mv": True,
        "min_bricks_for_signal": 2,
    }
    if stop_pct is not None:
        c["stop_loss_pct"] = stop_pct
        c["stop_loss_pts"] = 0.0
    pnls = []
    for day in days:
        try:
            res = run_day_fast("WIN", day, c)
            pnls.append(res.net_pnl)
        except Exception:
            pnls.append(0.0)
    return np.cumsum(pnls)


print(">>> Running baseline (G50 SL300 DS100)...", flush=True)
eq_base = run_and_get_pnls(50.0, None, 100.0)

print(">>> Running GAIN_65 + Stop% 0.3% + DS75...", flush=True)
eq_g65 = run_and_get_pnls(65.0, 0.003, 75.0)

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Equity curves
ax = axes[0]
ax.plot(eq_base, label="Baseline (G50 SL300 DS100)", color="gray", alpha=0.7, linewidth=1.5)
ax.plot(eq_g65, label="GAIN_65 + Stop% 0.3% + DS75", color="#2ecc71", linewidth=2)
ax.set_title("Equity Curve — WIN 2021-2026")
ax.set_xlabel("Dias")
ax.set_ylabel("PnL Acumulado (R$)")
ax.legend(loc="upper left")
ax.grid(True, alpha=0.3)
ax.axhline(0, color="black", linewidth=0.5)

# Barras anuais
ax = axes[1]
years_list = list(years)
annual_base = []
annual_g65 = []
for y in years_list:
    idx = [i for i, d in enumerate(days) if d.startswith(y)]
    annual_base.append(eq_base[idx[-1]] - (eq_base[idx[0]-1] if idx[0] > 0 else 0))
    annual_g65.append(eq_g65[idx[-1]] - (eq_g65[idx[0]-1] if idx[0] > 0 else 0))

x = np.arange(len(years_list))
width = 0.35
bars1 = ax.bar(x - width/2, annual_base, width, label="Baseline", color="gray", alpha=0.7)
bars2 = ax.bar(x + width/2, annual_g65, width, label="GAIN_65 + Stop%", color="#2ecc71")
ax.set_title("PnL Anual — WIN 2021-2026")
ax.set_xlabel("Ano")
ax.set_ylabel("PnL (R$)")
ax.set_xticks(x)
ax.set_xticklabels(years_list)
ax.legend()
ax.grid(True, alpha=0.3, axis="y")
ax.axhline(0, color="black", linewidth=0.5)

# Add value labels on bars
for bar in bars1:
    height = bar.get_height()
    ax.annotate(f"R${height:,.0f}", xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=7, color="gray")
for bar in bars2:
    height = bar.get_height()
    ax.annotate(f"R${height:,.0f}", xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=7, color="#27ae60")

plt.tight_layout()
out_path = PROJECT_ROOT / "reports" / "equity_GAIN65_vs_baseline.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Saved: {out_path}")
