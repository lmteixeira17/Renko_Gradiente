"""EA Gradiente Linear com Preço Médio — core logic.

Operates on Renko bricks with 2MV + MACD filters.
Uses Martingale progression and reactive average price.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class Level:
    price: float
    qty: int
    filled: bool = False


@dataclass
class Trade:
    entry_time_ms: int
    exit_time_ms: int = 0
    direction: int = 0  # +1 long, -1 short
    entry_price: float = 0.0
    exit_price: float = 0.0
    qty: int = 0
    pnl: float = 0.0
    exit_reason: str = ""


@dataclass
class EAGradienteState:
    """Internal state of the EA."""
    direction: Literal["long", "short", "flat"] = "flat"
    levels: list[Level] = field(default_factory=list)
    position_qty: int = 0
    position_cost: float = 0.0  # sum(price * qty)
    avg_price: float = 0.0
    target_price: float = 0.0
    stop_price: float = 0.0
    max_levels: int = 5
    current_level_idx: int = 0
    open_trades: list[Trade] = field(default_factory=list)
    closed_trades: list[Trade] = field(default_factory=list)
    total_pnl: float = 0.0
    daily_pnl: float = 0.0
    max_drawdown: float = 0.0
    peak_equity: float = 0.0
    n_trades: int = 0
    n_wins: int = 0
    n_losses: int = 0
    gross_profit: float = 0.0
    gross_loss: float = 0.0


class EAGradiente:
    """EA Gradiente Linear com Preço Médio."""

    def __init__(
        self,
        base_qty: int = 1,
        price_increment: float = 5.0,
        gain_increment: float = 5.0,
        max_levels: int = 5,
        stop_loss_pts: float = 1000.0,
        daily_stop_loss: float = 500.0,
        profit_target: float | None = None,
        martingale: bool = True,
        tick_value: float = 0.20,  # R$ per point for WIN
        use_macd: bool = True,
        use_2mv: bool = True,
        min_bricks_for_signal: int = 2,
        trailing_stop_enabled: bool = False,
        trailing_stop_value: float = 20.0,
        preservation_stop_enabled: bool = False,
        preservation_levels: int = 3,
    ):
        self.base_qty = base_qty
        self.price_increment = price_increment
        self.gain_increment = gain_increment
        self.max_levels = max_levels
        self.stop_loss_pts = stop_loss_pts
        self.daily_stop_loss = daily_stop_loss
        self.profit_target = profit_target
        self.martingale = martingale
        self.tick_value = tick_value
        self.use_macd = use_macd
        self.use_2mv = use_2mv
        self.min_bricks_for_signal = min_bricks_for_signal
        self.trailing_stop_enabled = trailing_stop_enabled
        self.trailing_stop_value = trailing_stop_value
        self.preservation_stop_enabled = preservation_stop_enabled
        self.preservation_levels = preservation_levels

        self.state = EAGradienteState()
        self.last_signal_brick_idx = -1
        self.highest_profit_seen = 0.0

    def reset_state(self):
        self.state = EAGradienteState()
        self.last_signal_brick_idx = -1
        self.highest_profit_seen = 0.0

    def _build_levels(self, direction: Literal["long", "short"], anchor_price: float) -> list[Level]:
        levels = []
        for i in range(self.max_levels):
            if direction == "long":
                price = anchor_price - i * self.price_increment
            else:
                price = anchor_price + i * self.price_increment
            if self.martingale:
                qty = self.base_qty * (2 ** i)
            else:
                qty = self.base_qty
            levels.append(Level(price=price, qty=qty))
        return levels

    def check_entry_signal(
        self,
        bricks,
        brick_idx: int,
        macd_hist: list[float] | None = None,
        twomv_colors: list[str] | None = None,
    ) -> Literal["long", "short", "none"]:
        """Check entry conditions on brick close.

        Rules (from spec):
        1. Last brick direction matches signal
        2. 2MV color matches direction
        3. MACD histogram on correct side (>0 buy, <0 sell)
        4. Pullback entry: previous brick was correction (opposite color)
           OR at least min_bricks_for_signal in same direction
        """
        if brick_idx < 1:
            return "none"

        curr = bricks[brick_idx]
        prev = bricks[brick_idx - 1]

        # Condition 1: current brick direction
        if curr.direction == 1:
            side = "long"
        elif curr.direction == -1:
            side = "short"
        else:
            return "none"

        # Condition 2: 2MV color
        if self.use_2mv and twomv_colors is not None:
            color = twomv_colors[brick_idx]
            if side == "long" and color != "green":
                return "none"
            if side == "short" and color != "red":
                return "none"

        # Condition 3: MACD histogram
        if self.use_macd and macd_hist is not None:
            hist = macd_hist[brick_idx]
            if side == "long" and hist <= 0:
                return "none"
            if side == "short" and hist >= 0:
                return "none"

        # Condition 4: trigger - pullback or continuation after correction
        if prev.direction != curr.direction:
            # Pullback entry: previous was opposite (correction), current confirms
            return side
        else:
            # Need at least N consecutive bricks in same direction
            count = 1
            for i in range(brick_idx - 1, -1, -1):
                if bricks[i].direction == curr.direction:
                    count += 1
                else:
                    break
            if count >= self.min_bricks_for_signal:
                return side

        return "none"

    def on_brick_close(
        self,
        brick_idx: int,
        bricks,
        macd_hist: list[float] | None = None,
        twomv_colors: list[str] | None = None,
    ):
        """Process brick close event. Returns any orders to place."""
        orders_to_place: list[tuple[float, int, str]] = []  # (price, qty, side)

        if self.state.direction == "flat":
            signal = self.check_entry_signal(bricks, brick_idx, macd_hist, twomv_colors)
            if signal != "none":
                anchor = bricks[brick_idx].close_price
                self.state.direction = signal
                self.state.levels = self._build_levels(signal, anchor)
                self.state.current_level_idx = 0
                self.state.position_qty = 0
                self.state.position_cost = 0.0
                # Place first 5 orders (or max_levels if <5)
                n_initial = min(5, len(self.state.levels))
                for i in range(n_initial):
                    lvl = self.state.levels[i]
                    side = "buy" if signal == "long" else "sell"
                    orders_to_place.append((lvl.price, lvl.qty, side))

        return orders_to_place

    def on_tick(self, time_ms: int, price: float) -> list[Trade]:
        """Process a tick, check fills and stops. Returns closed trades."""
        closed: list[Trade] = []
        st = self.state

        if st.direction == "flat":
            return closed

        # Check level fills (limit orders)
        for lvl in st.levels:
            if lvl.filled:
                continue
            if st.direction == "long" and price <= lvl.price:
                # Buy limit fill
                lvl.filled = True
                st.position_cost += lvl.price * lvl.qty
                st.position_qty += lvl.qty
                st.avg_price = st.position_cost / st.position_qty if st.position_qty > 0 else 0.0
                st.target_price = st.avg_price + self.gain_increment
                st.stop_price = st.avg_price - self.stop_loss_pts
                # Send next level if exists
            elif st.direction == "short" and price >= lvl.price:
                # Sell limit fill
                lvl.filled = True
                st.position_cost += lvl.price * lvl.qty
                st.position_qty += lvl.qty
                st.avg_price = st.position_cost / st.position_qty if st.position_qty > 0 else 0.0
                st.target_price = st.avg_price - self.gain_increment
                st.stop_price = st.avg_price + self.stop_loss_pts

        if st.position_qty == 0:
            return closed

        # Calculate unrealized PnL
        if st.direction == "long":
            unreal = (price - st.avg_price) * st.position_qty * self.tick_value / (1.0 if self.tick_value >= 1 else 1.0)
            # Actually tick_value is R$ per point; price is in points
            # WIN: 1 point = 0.20 R$? No, WIN: 1 index point = R$ 0.20 per contract
            unreal = (price - st.avg_price) * st.position_qty * self.tick_value
        else:
            unreal = (st.avg_price - price) * st.position_qty * self.tick_value

        # Track highest profit for trailing stop
        if unreal > self.highest_profit_seen:
            self.highest_profit_seen = unreal

        # Check target (reactive average price take profit)
        hit_target = False
        if st.direction == "long" and price >= st.target_price:
            hit_target = True
        elif st.direction == "short" and price <= st.target_price:
            hit_target = True

        if hit_target:
            # Close entire position at target
            trade = Trade(
                entry_time_ms=0,  # will set below
                exit_time_ms=time_ms,
                direction=1 if st.direction == "long" else -1,
                entry_price=st.avg_price,
                exit_price=st.target_price,
                qty=st.position_qty,
                pnl=(st.target_price - st.avg_price) * st.position_qty * self.tick_value
                    if st.direction == "long"
                    else (st.avg_price - st.target_price) * st.position_qty * self.tick_value,
                exit_reason="target",
            )
            st.closed_trades.append(trade)
            closed.append(trade)
            self._update_stats(trade)
            self._reset_position()
            return closed

        # Check stop loss
        hit_stop = False
        if st.direction == "long" and price <= st.stop_price:
            hit_stop = True
        elif st.direction == "short" and price >= st.stop_price:
            hit_stop = True

        if hit_stop:
            trade = Trade(
                entry_time_ms=0,
                exit_time_ms=time_ms,
                direction=1 if st.direction == "long" else -1,
                entry_price=st.avg_price,
                exit_price=st.stop_price,
                qty=st.position_qty,
                pnl=(st.stop_price - st.avg_price) * st.position_qty * self.tick_value
                    if st.direction == "long"
                    else (st.avg_price - st.stop_price) * st.position_qty * self.tick_value,
                exit_reason="stop",
            )
            st.closed_trades.append(trade)
            closed.append(trade)
            self._update_stats(trade)
            self._reset_position()
            return closed

        # Check trailing stop
        if self.trailing_stop_enabled and self.highest_profit_seen > self.trailing_stop_value:
            trail_price = st.avg_price + (self.highest_profit_seen - self.trailing_stop_value) / (st.position_qty * self.tick_value) if st.direction == "long" else \
                          st.avg_price - (self.highest_profit_seen - self.trailing_stop_value) / (st.position_qty * self.tick_value)
            if st.direction == "long" and price <= trail_price:
                hit_stop = True
                exit_p = price
            elif st.direction == "short" and price >= trail_price:
                hit_stop = True
                exit_p = price
            if hit_stop:
                trade = Trade(
                    entry_time_ms=0,
                    exit_time_ms=time_ms,
                    direction=1 if st.direction == "long" else -1,
                    entry_price=st.avg_price,
                    exit_price=exit_p,
                    qty=st.position_qty,
                    pnl=(exit_p - st.avg_price) * st.position_qty * self.tick_value
                        if st.direction == "long"
                        else (st.avg_price - exit_p) * st.position_qty * self.tick_value,
                    exit_reason="trailing_stop",
                )
                st.closed_trades.append(trade)
                closed.append(trade)
                self._update_stats(trade)
                self._reset_position()
                return closed

        return closed

    def _reset_position(self):
        self.state.direction = "flat"
        self.state.levels = []
        self.state.position_qty = 0
        self.state.position_cost = 0.0
        self.state.avg_price = 0.0
        self.state.target_price = 0.0
        self.state.stop_price = 0.0
        self.state.current_level_idx = 0
        self.highest_profit_seen = 0.0

    def _update_stats(self, trade: Trade):
        st = self.state
        st.n_trades += 1
        st.total_pnl += trade.pnl
        st.daily_pnl += trade.pnl
        if trade.pnl > 0:
            st.n_wins += 1
            st.gross_profit += trade.pnl
        else:
            st.n_losses += 1
            st.gross_loss += trade.pnl
        # Drawdown
        equity = st.total_pnl
        if equity > st.peak_equity:
            st.peak_equity = equity
        dd = st.peak_equity - equity
        if dd > st.max_drawdown:
            st.max_drawdown = dd

    def get_pending_level_prices(self) -> list[tuple[float, int, str]]:
        """Return pending limit orders to keep in book."""
        result = []
        if self.state.direction == "flat":
            return result
        for lvl in self.state.levels:
            if not lvl.filled:
                side = "buy" if self.state.direction == "long" else "sell"
                result.append((lvl.price, lvl.qty, side))
        return result
