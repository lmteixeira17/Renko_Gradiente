"""Auditoria completa dos resultados finais."""
import sys
sys.path.insert(0, 'src')
from backtest_engine_v2 import run_day_fast, aggregate_results
from btp_loader import list_days

HMS_TO_MS = lambda h, m: ((h * 60) + m) * 60 * 1000

config_win_base = {
    'renko_r': 25, 'tick_size': 5.0, 'tick_value': 0.20,
    'base_qty': 1, 'max_levels': 3, 'martingale': False,
    'price_increment': 100.0, 'gain_increment': 50.0,
    'stop_loss_pts': 300.0, 'use_macd': True, 'use_2mv': True,
    'min_bricks_for_signal': 2, 'slippage_pts': 2.0,
    'emolumentos_pct': 0.0001, 'preservation_stop': False,
    'preservation_levels': 3, 'trailing_stop_value': 0.0,
    'daily_stop_loss': 999999.0,
    'start_time_ms': HMS_TO_MS(9, 30),
    'end_time_ms': HMS_TO_MS(16, 50),
}

config_win_stop100 = dict(config_win_base)
config_win_stop100['daily_stop_loss'] = 100.0

config_win_stop200 = dict(config_win_base)
config_win_stop200['daily_stop_loss'] = 200.0

config_wdo = {
    'renko_r': 10, 'tick_size': 0.5, 'tick_value': 10.0,
    'base_qty': 1, 'max_levels': 3, 'martingale': False,
    'price_increment': 2.0, 'gain_increment': 0.5,
    'stop_loss_pts': 20.0, 'use_macd': True, 'use_2mv': True,
    'min_bricks_for_signal': 2, 'slippage_pts': 1.0,
    'emolumentos_pct': 0.0001, 'preservation_stop': False,
    'preservation_levels': 3, 'trailing_stop_value': 0.0,
    'daily_stop_loss': 999999.0,
    'start_time_ms': HMS_TO_MS(9, 30),
    'end_time_ms': HMS_TO_MS(16, 50),
}


def analyze(asset, config, label):
    sep = "=" * 70
    print(f"\n{sep}")
    print(f"  {label}")
    print(f"{sep}")

    days = [d for d in list_days(asset) if d.startswith('2021') or d.startswith('2022') or d.startswith('2023') or d.startswith('2024') or d.startswith('2025')]
    days.sort()

    results = []
    for day in days:
        try:
            res = run_day_fast(asset, day, config)
            results.append(res)
        except Exception as e:
            pass

    agg = aggregate_results(results)
    dd_pct = agg.max_drawdown / 5000 * 100 if agg.max_drawdown > 0 else 0.0

    results_by_year = {}
    for day, res in zip(days, results):
        y = day[:4]
        if y not in results_by_year:
            results_by_year[y] = []
        results_by_year[y].append(res)

    print(f"Periodo: 2021-2025 | Dias testados: {agg.n_days}")
    print(f"Total trades: {agg.n_trades}")
    print(f"Win Rate: {agg.win_rate:.1f}%")
    print(f"Profit Factor: {agg.profit_factor:.2f}")
    print(f"Net PnL: R$ {agg.net_pnl:,.2f}")
    print(f"Max Drawdown: R$ {agg.max_drawdown:,.2f} ({dd_pct:.1f}%)")
    print(f"Avg trade: R$ {agg.avg_trade:.2f}")
    print()
    print(f"  {'Ano':>6} | {'PnL':>14} | {'Trades':>8} | {'DD':>12} | {'DD%':>6}")
    print(f"  {'-'*6}-+-{'-'*14}-+-{'-'*8}-+-{'-'*12}-+-{'-'*6}")

    for y in sorted(results_by_year.keys()):
        agg_y = aggregate_results(results_by_year[y])
        dd_y = agg_y.max_drawdown / 5000 * 100 if agg_y.max_drawdown > 0 else 0
        print(f"  {y:>6} | R$ {agg_y.net_pnl:>10,.2f} | {agg_y.n_trades:>8} | R$ {agg_y.max_drawdown:>10,.2f} | {dd_y:>5.1f}%")

    pnls = [r.net_pnl for r in results if r.n_trades > 0]
    if pnls:
        avg_day = sum(pnls) / len(pnls)
        best_day = max(pnls)
        worst_day = min(pnls)
        profit_days = sum(1 for p in pnls if p > 0)
        loss_days = sum(1 for p in pnls if p < 0)
        flat_days = sum(1 for p in pnls if p == 0)
        print()
        print(f"Dias operados: {len(pnls)}")
        print(f"Dias com lucro: {profit_days} ({profit_days/len(pnls)*100:.1f}%)")
        print(f"Dias com prejuizo: {loss_days} ({loss_days/len(pnls)*100:.1f}%)")
        print(f"Dias sem operacao/flat: {flat_days}")
        print(f"Media diaria: R$ {avg_day:.2f}")
        print(f"Melhor dia: R$ {best_day:.2f}")
        print(f"Pior dia: R$ {worst_day:.2f}")


if __name__ == "__main__":
    analyze('WIN', config_win_base, 'WIN 25R nomart ML3 SL300 | 09:30-16:50 | sem stop diario')
    analyze('WIN', config_win_stop100, 'WIN 25R nomart ML3 SL300 | 09:30-16:50 | stop R$100/dia')
    analyze('WIN', config_win_stop200, 'WIN 25R nomart ML3 SL300 | 09:30-16:50 | stop R$200/dia')
    analyze('WDO', config_wdo, 'WDO 10R nomart ML3 SL20 | 09:30-16:50 | sem stop diario')
