"""Compara EA rodado em real 2026 vs sintetico 2026 (mesmos dias, mesmo OHLC).

Mede DIRETAMENTE o vies da microestrutura sintetica nesta estrategia
path-dependent.

Real:     C:/HIST_B3/generator_v3/packet/WIN/<day>.btp
Sintetico: D:/HIST_B3/_sandbox/syn_2026_for_validation/packet/WIN/<day>.btp
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

TOOLS = Path("C:/HIST_B3/generator_v3/tools")
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from btp import open_packet
from btp_loader import list_days
from renko import build_renko
from backtest_engine_v2 import prepare_signals
from backtest_fast import simulate_day_fast

REAL_ROOT = Path("C:/HIST_B3/generator_v3")
SYN_ROOT  = Path("D:/HIST_B3/_sandbox/syn_2026_for_validation")

# Apenas os dias sinteticos (79 dias)
syn_days = sorted(p.stem for p in (SYN_ROOT / "packet" / "WIN").glob("*.btp"))
print(f"Dias sinteticos disponiveis: {len(syn_days)}", flush=True)

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

def run_day(root: Path, day: str):
    """Roda EA em um dia, dado root do dataset."""
    path = root / "packet" / "WIN" / f"{day}.btp"
    pkt = open_packet(path)
    prices = pkt.price
    times  = pkt.time_ms

    bricks = build_renko(prices, times, cfg["tick_size"], cfg["renko_r"])
    entry_signals = prepare_signals(bricks, use_macd=True, use_2mv=True, min_bricks=2)
    if entry_signals is None:
        pkt.close()
        return 0.0, 0, 0, 0
    brick_end_times = np.array([b.end_time_ms for b in bricks], dtype=np.int64)
    brick_idx = np.searchsorted(brick_end_times, times, side='right')
    brick_idx = np.clip(brick_idx, 0, len(bricks) - 1).astype(np.int32)

    (_, _, _, _, qtys, pnls, dirs, reasons) = simulate_day_fast(
        prices, times, brick_idx, entry_signals,
        base_qty=1,
        price_increment=cfg["price_increment"],
        gain_increment=cfg["gain_increment"],
        gain_increment_pct=cfg["gain_increment_pct"],
        max_levels=cfg["max_levels"],
        stop_loss_pts=cfg["stop_loss_pts"],
        stop_loss_pct=cfg["stop_loss_pct"],
        tick_value=cfg["tick_value"],
        martingale=cfg["martingale"],
        slippage_pts=cfg["slippage_pts"],
        emolumentos_pct=cfg["emolumentos_pct"],
        preservation_stop=cfg["preservation_stop"],
        preservation_levels=cfg["preservation_levels"],
        trailing_stop_value=cfg["trailing_stop_value"],
        daily_stop_loss=cfg["daily_stop_loss"],
        max_trades_per_day=0,
        start_time_ms=cfg["start_time_ms"],
        end_time_ms=cfg["end_time_ms"],
        force_close_eod=cfg["force_close_eod"],
        force_close_daily_stop=cfg["force_close_daily_stop"],
    )
    pkt.close()
    n = len(pnls)
    pnl_sum = float(np.sum(pnls)) if n > 0 else 0.0
    wins = int(np.sum(pnls > 0)) if n > 0 else 0
    return pnl_sum, n, wins, len(bricks)

per_day = []
real_pnl_total = 0.0
syn_pnl_total  = 0.0
real_trades_total = 0
syn_trades_total  = 0
deltas = []
deltas_pct = []

print(f"{'Day':>12} | {'RealPnL':>10} {'SynPnL':>10} | {'Delta':>10} {'%':>7} | {'NR':>5} {'NS':>5} | {'BR':>4} {'BS':>4}", flush=True)
print("-" * 100, flush=True)

for day in syn_days:
    try:
        r_pnl, r_n, r_w, r_b = run_day(REAL_ROOT, day)
        s_pnl, s_n, s_w, s_b = run_day(SYN_ROOT, day)
    except Exception as e:
        print(f"{day}: ERROR {e}", flush=True)
        continue
    delta = s_pnl - r_pnl
    delta_pct = (delta / r_pnl * 100) if abs(r_pnl) > 0.01 else 0.0
    real_pnl_total += r_pnl
    syn_pnl_total  += s_pnl
    real_trades_total += r_n
    syn_trades_total  += s_n
    deltas.append(delta)
    deltas_pct.append(delta_pct)
    per_day.append({
        "day": day, "real_pnl": r_pnl, "syn_pnl": s_pnl, "delta": delta,
        "delta_pct": delta_pct,
        "real_trades": r_n, "syn_trades": s_n,
        "real_bricks": r_b, "syn_bricks": s_b,
    })
    print(f"{day} | {r_pnl:>+10,.0f} {s_pnl:>+10,.0f} | {delta:>+10,.0f} {delta_pct:>+7.1f}% | {r_n:>5d} {s_n:>5d} | {r_b:>4d} {s_b:>4d}", flush=True)

# Stats
deltas_np = np.array(deltas)
print("\n=== RESUMO ===", flush=True)
print(f"Dias comparados:        {len(per_day)}", flush=True)
print(f"Total Real:            R${real_pnl_total:>+12,.2f}", flush=True)
print(f"Total Sintetico:       R${syn_pnl_total:>+12,.2f}", flush=True)
print(f"Delta total:           R${syn_pnl_total - real_pnl_total:>+12,.2f}", flush=True)
print(f"Delta % do real:       {(syn_pnl_total - real_pnl_total)/abs(real_pnl_total)*100 if abs(real_pnl_total)>0 else 0:+.1f}%", flush=True)
print(f"Delta por dia (medio): R${deltas_np.mean():>+10,.2f}", flush=True)
print(f"Delta por dia (std):   R${deltas_np.std():>10,.2f}", flush=True)
print(f"Trades Real:           {real_trades_total}", flush=True)
print(f"Trades Sintetico:      {syn_trades_total}", flush=True)

# Distribuicao dos deltas
n_pos = int(np.sum(deltas_np > 0))
n_neg = int(np.sum(deltas_np < 0))
n_zero = int(np.sum(np.abs(deltas_np) < 0.01))
print(f"Dias syn > real: {n_pos} | syn < real: {n_neg} | iguais: {n_zero}", flush=True)

out = PROJECT_ROOT / "reports" / "compare_real_vs_syn_2026.json"
with open(out, "w", encoding="utf-8") as f:
    json.dump({
        "summary": {
            "n_days": len(per_day),
            "real_total": real_pnl_total,
            "syn_total":  syn_pnl_total,
            "delta_total": syn_pnl_total - real_pnl_total,
            "delta_pct":   (syn_pnl_total - real_pnl_total)/abs(real_pnl_total)*100 if abs(real_pnl_total)>0 else 0,
            "delta_mean_day": float(deltas_np.mean()),
            "delta_std_day":  float(deltas_np.std()),
            "real_trades":    real_trades_total,
            "syn_trades":     syn_trades_total,
            "n_syn_greater":  n_pos,
            "n_syn_lesser":   n_neg,
        },
        "per_day": per_day,
    }, f, indent=2, ensure_ascii=False)
print(f"\nSaved: {out}", flush=True)
