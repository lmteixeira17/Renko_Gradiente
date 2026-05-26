"""
Teste FOCADO: apenas 2023 (ano bom) e 2024 (ano ruim) para iterar rapido.
Meta: encontrar configs que melhorem 2024 sem destruir 2023.
"""
import sys
sys.stdout.reconfigure(line_buffering=True)
import json
import time
from pathlib import Path
from dataclasses import dataclass, asdict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import list_days
from backtest_engine_v2 import run_day_fast, aggregate_results


@dataclass
class Config:
    name: str
    asset: str = "WIN"
    years: tuple = ("2023", "2024")
    initial_capital: float = 15000.0
    renko_r: int = 25
    tick_size: float = 5.0
    tick_value: float = 0.20
    base_qty: int = 1
    max_levels: int = 3
    martingale: bool = False
    price_increment: float = 100.0
    gain_increment: float = 50.0
    gain_increment_pct: float = 0.0
    stop_loss_pts: float = 300.0
    stop_loss_pct: float = 0.0
    slippage_pts: float = 2.0
    emolumentos_pct: float = 0.0001
    daily_stop_loss: float = 100.0
    preservation_stop: bool = False
    preservation_levels: int = 3
    trailing_stop_value: float = 0.0
    start_time_ms: int = 34200000
    end_time_ms: int = 60600000
    use_macd: bool = True
    use_2mv: bool = True
    min_bricks_for_signal: int = 2


def run_test(cfg: Config) -> dict:
    days = []
    for y in cfg.years:
        days.extend([d for d in list_days(cfg.asset) if d.startswith(y)])
    days.sort()

    c = asdict(cfg)
    c.pop("name")
    c.pop("asset")
    c.pop("years")
    c.pop("initial_capital")

    results = []
    t0 = time.time()
    for day in days:
        try:
            res = run_day_fast(cfg.asset, day, c)
            results.append(res)
        except Exception as e:
            print(f"  {day}: ERR {e}", flush=True)
    dt = time.time() - t0

    agg = aggregate_results(results)
    dd_pct = agg.max_drawdown / cfg.initial_capital * 100 if agg.max_drawdown > 0 else 0.0

    annual = {}
    for r in results:
        y = r.start_date[:4]
        annual[y] = annual.get(y, 0.0) + r.net_pnl

    return {
        "name": cfg.name, "net_pnl": agg.net_pnl, "n_trades": agg.n_trades,
        "win_rate": agg.win_rate, "profit_factor": agg.profit_factor,
        "max_drawdown": agg.max_drawdown, "max_drawdown_pct": dd_pct,
        "avg_trade": agg.avg_trade, "exec_time_s": dt,
        "annual_pnls": annual,
    }


def main():
    cfgs = [
        # === BASELINES ===
        Config(name="BASE_fixed_SL300_G50_ML3_DS100"),
        Config(name="BASE_pct_03_01_ML3_DS75", stop_loss_pct=0.003, gain_increment_pct=0.001,
               daily_stop_loss=75.0, gain_increment=0.0, stop_loss_pts=0.0),
        Config(name="BASE_pct_03_005_ML3_DS75", stop_loss_pct=0.003, gain_increment_pct=0.0005,
               daily_stop_loss=75.0, gain_increment=0.0, stop_loss_pts=0.0),

        # === PRESERVATION STOP (breakeven) ===
        Config(name="PRESERV_fixed_SL300_G50_ML3_DS100", preservation_stop=True, preservation_levels=1),
        Config(name="PRESERV_pct_03_01_ML3_DS75", stop_loss_pct=0.003, gain_increment_pct=0.001,
               daily_stop_loss=75.0, gain_increment=0.0, stop_loss_pts=0.0,
               preservation_stop=True, preservation_levels=1),

        # === TRAILING STOP ===
        Config(name="TRAIL_fixed_SL300_G50_ML3_DS100_t50", trailing_stop_value=50.0),
        Config(name="TRAIL_fixed_SL300_G50_ML3_DS100_t100", trailing_stop_value=100.0),
        Config(name="TRAIL_pct_03_01_ML3_DS75_t50", stop_loss_pct=0.003, gain_increment_pct=0.001,
               daily_stop_loss=75.0, gain_increment=0.0, stop_loss_pts=0.0,
               trailing_stop_value=50.0),

        # === PRESERV + TRAIL ===
        Config(name="PRESERV_TRAIL_fixed_SL300_G50_ML3_DS100", preservation_stop=True, preservation_levels=1, trailing_stop_value=50.0),
        Config(name="PRESERV_TRAIL_pct_03_01_ML3_DS75", stop_loss_pct=0.003, gain_increment_pct=0.001,
               daily_stop_loss=75.0, gain_increment=0.0, stop_loss_pts=0.0,
               preservation_stop=True, preservation_levels=1, trailing_stop_value=50.0),

        # === ML2 (menos risco) ===
        Config(name="ML2_fixed_SL300_G50_DS100", max_levels=2),
        Config(name="ML2_pct_03_01_DS75", stop_loss_pct=0.003, gain_increment_pct=0.001,
               daily_stop_loss=75.0, gain_increment=0.0, stop_loss_pts=0.0, max_levels=2),

        # === GAIN DIFERENTE ===
        Config(name="GAIN100_fixed_SL300_ML3_DS100", gain_increment=100.0),
        Config(name="GAIN30_fixed_SL300_ML3_DS100", gain_increment=30.0),
        Config(name="GAIN75_fixed_SL300_ML3_DS100", gain_increment=75.0),
        Config(name="GAIN75_pct_03_ML3_DS75", stop_loss_pct=0.003, gain_increment=75.0,
               daily_stop_loss=75.0, gain_increment_pct=0.0, stop_loss_pts=0.0),

        # === STOP DIARIO MAIS APERTADO ===
        Config(name="DS50_fixed_SL300_G50_ML3", daily_stop_loss=50.0),
        Config(name="DS50_pct_03_01_ML3", stop_loss_pct=0.003, gain_increment_pct=0.001,
               daily_stop_loss=50.0, gain_increment=0.0, stop_loss_pts=0.0),

        # === SL MAIS APERTADO ===
        Config(name="SL200_fixed_G50_ML3_DS100", stop_loss_pts=200.0),
        Config(name="SL400_fixed_G50_ML3_DS100", stop_loss_pts=400.0),

        # === COMBINACOES PROMISSORAS ===
        Config(name="ML2_PRESERV_TRAIL_pct_03_01_DS75", stop_loss_pct=0.003, gain_increment_pct=0.001,
               daily_stop_loss=75.0, gain_increment=0.0, stop_loss_pts=0.0,
               max_levels=2, preservation_stop=True, preservation_levels=1, trailing_stop_value=50.0),
        Config(name="ML2_PRESERV_pct_03_01_DS75", stop_loss_pct=0.003, gain_increment_pct=0.001,
               daily_stop_loss=75.0, gain_increment=0.0, stop_loss_pts=0.0,
               max_levels=2, preservation_stop=True, preservation_levels=1),
    ]

    results = []
    print(f"{'Config':<45s} | {'Total':>10s} | {'2023':>10s} | {'2024':>10s} | {'PF':>5s} | {'DD%':>5s} | {'t(s)':>5s}")
    print("-" * 115)
    for cfg in cfgs:
        r = run_test(cfg)
        results.append(r)
        pnl23 = r['annual_pnls'].get('2023', 0.0)
        pnl24 = r['annual_pnls'].get('2024', 0.0)
        print(f"{r['name']:<45s} | {r['net_pnl']:>10,.0f} | {pnl23:>10,.0f} | {pnl24:>10,.0f} | "
              f"{r['profit_factor']:5.2f} | {r['max_drawdown_pct']:5.1f} | {r['exec_time_s']:5.1f}", flush=True)

    # Score de linearidade: queremos maximizar 2024 e minimizar perda em 2023
    # Score = (pnl24 * 2) + pnl23 - (dd_pct * 10)
    print("\n" + "=" * 115)
    print("RANKING POR EQUILIBRIO (maximiza 2024, preserva 2023, penaliza DD)")
    print("=" * 115)
    scored = []
    for r in results:
        pnl23 = r['annual_pnls'].get('2023', 0.0)
        pnl24 = r['annual_pnls'].get('2024', 0.0)
        score = (pnl24 * 2) + pnl23 - (r['max_drawdown_pct'] * 10)
        scored.append((score, r))
    scored.sort(reverse=True)

    for i, (score, r) in enumerate(scored, 1):
        pnl23 = r['annual_pnls'].get('2023', 0.0)
        pnl24 = r['annual_pnls'].get('2024', 0.0)
        print(f"{i:2d}. {r['name']:<45s} | Score={score:>10,.0f} | 2023={pnl23:>10,.0f} | 2024={pnl24:>10,.0f} | PF={r['profit_factor']:.2f} | DD={r['max_drawdown_pct']:.1f}%")

    out = PROJECT_ROOT / "reports" / "win_linearize_focused.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n>>> Saved: {out}")


if __name__ == "__main__":
    main()
