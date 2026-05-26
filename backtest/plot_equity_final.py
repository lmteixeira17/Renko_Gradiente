"""Plota equity curve final: G72 vs baseline G50."""
import sys
sys.stdout.reconfigure(line_buffering=True)
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


def run_and_get_pnls(gain, stop_pct=0.003, ds=75.0):
    c = {
        "renko_r": 25, "tick_size": 5.0, "tick_value": 0.20,
        "base_qty": 1, "max_levels": 3, "martingale": False,
        "price_increment": 100.0, "gain_increment": gain,
        "gain_increment_pct": 0.0, "stop_loss_pts": 0.0,
        "stop_loss_pct": stop_pct, "slippage_pts": 2.0,
        "emolumentos_pct": 0.0001, "daily_stop_loss": ds,
        "preservation_stop": False, "preservation_levels": 3,
        "trailing_stop_value": 0.0, "start_time_ms": 34200000,
        "end_time_ms": 60600000, "use_macd": True, "use_2mv": True,
        "min_bricks_for_signal": 2,
    }
    pnls = []
    for day in days:
        try:
            res = run_day_fast("WIN", day, c)
            pnls.append(res.net_pnl)
        except Exception:
            pnls.append(0.0)
    return np.cumsum(pnls)


print(">>> Running baseline (G50 SL300 DS100)...", flush=True)
eq_base = run_and_get_pnls(50.0, stop_pct=0.0, ds=100.0)
eq_base_sl = run_and_get_pnls(50.0, stop_pct=0.003, ds=75.0)

print(">>> Running GAIN_72 + Stop% 0.3% + DS75...", flush=True)
eq_g72 = run_and_get_pnls(72.0, stop_pct=0.003, ds=75.0)

fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Equity curves
ax = axes[0]
ax.plot(eq_base, label="Baseline (G50 SL300 DS100)", color="gray", alpha=0.5, linewidth=1.5)
ax.plot(eq_base_sl, label="G50 + Stop% 0.3% + DS75", color="#3498db", alpha=0.7, linewidth=1.5)
ax.plot(eq_g72, label="G72 + Stop% 0.3% + DS75", color="#2ecc71", linewidth=2.5)
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
annual_g50p = []
annual_g72 = []
for y in years_list:
    idx = [i for i, d in enumerate(days) if d.startswith(y)]
    annual_base.append(eq_base[idx[-1]] - (eq_base[idx[0]-1] if idx[0] > 0 else 0))
    annual_g50p.append(eq_base_sl[idx[-1]] - (eq_base_sl[idx[0]-1] if idx[0] > 0 else 0))
    annual_g72.append(eq_g72[idx[-1]] - (eq_g72[idx[0]-1] if idx[0] > 0 else 0))

x = np.arange(len(years_list))
width = 0.25
bars1 = ax.bar(x - width, annual_base, width, label="Baseline G50", color="gray", alpha=0.5)
bars2 = ax.bar(x, annual_g50p, width, label="G50 + Stop%", color="#3498db", alpha=0.7)
bars3 = ax.bar(x + width, annual_g72, width, label="G72 + Stop%", color="#2ecc71")
ax.set_title("PnL Anual — WIN 2021-2026")
ax.set_xlabel("Ano")
ax.set_ylabel("PnL (R$)")
ax.set_xticks(x)
ax.set_xticklabels(years_list)
ax.legend()
ax.grid(True, alpha=0.3, axis="y")
ax.axhline(0, color="black", linewidth=0.5)

for bars in [bars1, bars2, bars3]:
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f"R${height:,.0f}", xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=6)

plt.tight_layout()
out_path = PROJECT_ROOT / "reports" / "equity_G72_final.png"
plt.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"Saved: {out_path}")
