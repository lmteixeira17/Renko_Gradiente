"""Debug single-day trades."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from btp_loader import open_day
from renko import build_renko
from indicators import ema, macd, twomv_signal
from ea_gradiente import EAGradiente
from backtest_engine import run_day_backtest

asset = "WIN"
day = "2024-06-14"
renko_r = 25
tick_size = 5.0
tick_value = 0.20

ea = EAGradiente(
    base_qty=1,
    price_increment=100.0,
    gain_increment=50.0,
    max_levels=5,
    stop_loss_pts=1000.0,
    martingale=True,
    tick_value=tick_value,
    use_macd=True,
    use_2mv=True,
    min_bricks_for_signal=2,
)

res = run_day_backtest(asset, day, ea, tick_size, renko_r, tick_value)
for t in res.trades[:10]:
    print(f"Dir={t.direction:+.0f} Qty={t.qty} Entry={t.entry_price:.0f} Exit={t.exit_price:.0f} PnL={t.pnl:+.2f} Reason={t.exit_reason}")

# Also inspect the packet to see price range
pkt = open_day(asset, day)
print(f"\nPacket {day}: price range {pkt.price.min():.0f} - {pkt.price.max():.0f}, ticks={pkt.n_ticks}")
pkt.close()
