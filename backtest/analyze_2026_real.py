"""Analise detalhada de 2026 para config GAIN_65 + Stop% 0.3% + DS75."""
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import numpy as np
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import open_day, list_days
from renko import build_renko
from backtest_engine_v2 import prepare_signals
from backtest_fast import simulate_day_fast

asset = "WIN"
year = "2026"
days = [d for d in list_days(asset) if d.startswith(year)]
days.sort()

c = {
    "renko_r": 25, "tick_size": 5.0, "tick_value": 0.20,
    "base_qty": 1, "max_levels": 3, "martingale": False,
    "price_increment": 100.0, "gain_increment": 65.0,
    "gain_increment_pct": 0.0, "stop_loss_pts": 0.0,
    "stop_loss_pct": 0.003, "slippage_pts": 2.0,
    "emolumentos_pct": 0.0001, "daily_stop_loss": 75.0,
    "preservation_stop": False, "preservation_levels": 3,
    "trailing_stop_value": 0.0, "start_time_ms": 34200000,
    "end_time_ms": 60600000, "use_macd": True, "use_2mv": True,
    "min_bricks_for_signal": 2,
}


def run_day_detailed(asset, day, config):
    """Roda um dia e retorna os trades individuais."""
    pkt = open_day(asset, day)
    prices = pkt.price
    times = pkt.time_ms
    tick_size = config.get("tick_size", 5.0)
    tick_value = config.get("tick_value", 0.20)
    bricks = build_renko(prices, times, tick_size, config.get("renko_r", 25))
    entry_signals = prepare_signals(
        bricks,
        use_macd=config.get("use_macd", True),
        use_2mv=config.get("use_2mv", True),
        min_bricks=config.get("min_bricks_for_signal", 2),
    )
    if entry_signals is None:
        pkt.close()
        return []
    brick_end_times = np.array([b.end_time_ms for b in bricks], dtype=np.int64)
    brick_idx = np.searchsorted(brick_end_times, times, side='right')
    brick_idx = np.clip(brick_idx, 0, len(bricks) - 1).astype(np.int32)
    (
        entry_times, exit_times, entry_prices, exit_prices,
        qtys, pnls, directions, reasons,
    ) = simulate_day_fast(
        prices, times, brick_idx, entry_signals,
        base_qty=config.get("base_qty", 1),
        price_increment=config.get("price_increment", 100.0),
        gain_increment=config.get("gain_increment", 50.0),
        gain_increment_pct=config.get("gain_increment_pct", 0.0),
        max_levels=config.get("max_levels", 5),
        stop_loss_pts=config.get("stop_loss_pts", 1000.0),
        stop_loss_pct=config.get("stop_loss_pct", 0.0),
        tick_value=tick_value,
        martingale=config.get("martingale", True),
        slippage_pts=config.get("slippage_pts", 2.0),
        emolumentos_pct=config.get("emolumentos_pct", 0.0001),
        preservation_stop=config.get("preservation_stop", False),
        preservation_levels=config.get("preservation_levels", 3),
        trailing_stop_value=config.get("trailing_stop_value", 0.0),
        daily_stop_loss=config.get("daily_stop_loss", 999999.0),
        start_time_ms=config.get("start_time_ms", 0),
        end_time_ms=config.get("end_time_ms", 86400000),
    )
    pkt.close()
    trades = []
    for i in range(len(pnls)):
        if pnls[i] == 0 and qtys[i] == 0:
            break
        trades.append({
            "entry_time": int(entry_times[i]),
            "exit_time": int(exit_times[i]),
            "entry_price": float(entry_prices[i]),
            "exit_price": float(exit_prices[i]),
            "qty": int(qtys[i]),
            "pnl": float(pnls[i]),
            "direction": int(directions[i]),
            "reason": int(reasons[i]),
        })
    return trades


print(f">>> Analisando {len(days)} dias de {asset} em {year}...")
print(f">>> Config: GAIN_65 | SL 0.3% | DS75 | ML3\n")

daily_stats = []
monthly_pnls = {}
all_trades = []

for day in days:
    trades = run_day_detailed(asset, day, c)
    month = day[:7]
    day_pnl = sum(t["pnl"] for t in trades)
    monthly_pnls[month] = monthly_pnls.get(month, 0.0) + day_pnl

    n_trades = len(trades)
    daily_stats.append({
        "date": day,
        "n_trades": n_trades,
        "pnl": day_pnl,
        "win_trades": sum(1 for t in trades if t["pnl"] > 0),
        "loss_trades": sum(1 for t in trades if t["pnl"] <= 0),
        "max_qty": max((t["qty"] for t in trades), default=0),
    })

    for t in trades:
        all_trades.append({
            "date": day,
            "entry_time": t["entry_time"],
            "pnl": t["pnl"],
            "qty": t["qty"],
            "direction": t["direction"],
            "reason": t["reason"],
        })

# ===== RESUMO GERAL =====
total_pnl = sum(d["pnl"] for d in daily_stats)
total_trades = sum(d["n_trades"] for d in daily_stats)
days_with_trades = sum(1 for d in daily_stats if d["n_trades"] > 0)
days_profitable = sum(1 for d in daily_stats if d["pnl"] > 0)
days_loss = sum(1 for d in daily_stats if d["pnl"] < 0)

print("=" * 70)
print("RESUMO GERAL — 2026")
print("=" * 70)
print(f"Total de dias analisados: {len(days)}")
print(f"Dias com trades: {days_with_trades} ({days_with_trades/len(days)*100:.1f}%)")
print(f"Dias lucrativos: {days_profitable} ({days_profitable/len(days)*100:.1f}%)")
print(f"Dias prejuizo:   {days_loss} ({days_loss/len(days)*100:.1f}%)")
print(f"\nTotal de trades: {total_trades}")
print(f"PnL total: R${total_pnl:,.2f}")
print(f"Média trades/dia (todos os dias): {total_trades/len(days):.1f}")
print(f"Média trades/dia (apenas dias com trade): {total_trades/days_with_trades:.1f}")

# ===== ESTATISTICAS DE TRADES =====
win_trades = [t for t in all_trades if t["pnl"] > 0]
loss_trades = [t for t in all_trades if t["pnl"] <= 0]
win_pnl = sum(t["pnl"] for t in win_trades)
loss_pnl = sum(t["pnl"] for t in loss_trades)
pf = abs(win_pnl / loss_pnl) if loss_pnl != 0 else float('inf')
wr = len(win_trades) / len(all_trades) * 100 if all_trades else 0

print(f"\n{'=' * 70}")
print("ESTATISTICAS DE TRADES")
print("=" * 70)
print(f"Trades vencedores: {len(win_trades)} ({wr:.1f}%)")
print(f"Trades perdedores: {len(loss_trades)} ({100-wr:.1f}%)")
if win_trades:
    print(f"Lucro medio por trade vencedor: R${np.mean([t['pnl'] for t in win_trades]):,.2f}")
if loss_trades:
    print(f"Perda media por trade perdedor: R${np.mean([t['pnl'] for t in loss_trades]):,.2f}")
print(f"Profit Factor: {pf:.2f}")

# Contratos
qtys = [t["qty"] for t in all_trades]
print(f"\nContratos por trade:")
print(f"  Min: {min(qtys) if qtys else 0}")
print(f"  Max: {max(qtys) if qtys else 0}")
if qtys:
    print(f"  Medio: {np.mean(qtys):.1f}")
    print(f"  Moda: {Counter(qtys).most_common(1)[0][0]} ({Counter(qtys).most_common(1)[0][1]} trades)")

# ===== DISTRIBUICAO MENSAL =====
print(f"\n{'=' * 70}")
print("PnL MENSAL — 2026")
print("=" * 70)
for m in sorted(monthly_pnls.keys()):
    pnl = monthly_pnls[m]
    print(f"{m}: R${pnl:>10,.2f}")

# ===== TOP 10 E PIOR 10 DIAS =====
print(f"\n{'=' * 70}")
print("TOP 10 DIAS (maior lucro)")
print("=" * 70)
sorted_days = sorted(daily_stats, key=lambda x: x["pnl"], reverse=True)
for d in sorted_days[:10]:
    print(f"{d['date']} | PnL: R${d['pnl']:>10,.2f} | Trades: {d['n_trades']} | WR: {d['win_trades']}/{d['loss_trades']}")

print(f"\n{'=' * 70}")
print("PIOR 10 DIAS (maior prejuizo)")
print("=" * 70)
for d in sorted_days[-10:]:
    print(f"{d['date']} | PnL: R${d['pnl']:>10,.2f} | Trades: {d['n_trades']} | WR: {d['win_trades']}/{d['loss_trades']}")

# ===== DISTRIBUICAO DE TRADES POR DIA =====
print(f"\n{'=' * 70}")
print("DISTRIBUICAO DE TRADES POR DIA")
print("=" * 70)
trade_counts = Counter(d["n_trades"] for d in daily_stats)
for n in sorted(trade_counts.keys()):
    print(f"  {n:2d} trades: {trade_counts[n]:3d} dias ({trade_counts[n]/len(days)*100:5.1f}%)")

# ===== MOTIVOS DE SAIDA =====
reason_names = {0: "stop_loss", 1: "target", 2: "eod", 3: "trailing_stop"}
print(f"\n{'=' * 70}")
print("MOTIVOS DE SAIDA DOS TRADES")
print("=" * 70)
reasons = Counter(t["reason"] for t in all_trades)
for reason, count in reasons.most_common():
    name = reason_names.get(reason, f"reason_{reason}")
    print(f"  {name}: {count} ({count/len(all_trades)*100:.1f}%)")

# ===== HORARIOS DE ENTRADA =====
print(f"\n{'=' * 70}")
print("DISTRIBUICAO HORARIA DE ENTRADA (hora brasilia)")
print("=" * 70)
hours = Counter()
for t in all_trades:
    ms = t["entry_time"]
    if ms > 0:
        hour = int(ms / 1000 / 60 / 60)  # aproximado
        hours[hour] += 1
for h in sorted(hours.keys()):
    print(f"  {h:2d}h: {hours[h]:4d} trades ({hours[h]/len(all_trades)*100:5.1f}%)")

# Salva JSON
out = {
    "config": {k: v for k, v in c.items()},
    "year": year, "asset": asset,
    "n_days": len(days), "n_days_with_trades": days_with_trades,
    "total_trades": total_trades, "total_pnl": total_pnl,
    "win_rate": wr, "profit_factor": pf,
    "daily_stats": daily_stats,
    "monthly_pnls": monthly_pnls,
    "all_trades": all_trades,
}
out_path = PROJECT_ROOT / "reports" / "win_2026_detail_gain65_stoppct.json"
with open(out_path, "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
print(f"\n>>> Saved: {out_path}")
