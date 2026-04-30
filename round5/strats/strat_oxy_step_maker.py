"""
OXY step-maker — fade the staircase via maker quotes (no spread cost).

⚠ NEGATIVE RESULT — DO NOT SUBMIT.
   3-day BT (round 5 days 2/3/4):
     FADE, K=4, offset=1, hold=200 → −1,627
     FADE, K=5, offset=3, hold=200 → −1,807
     FADE, K=4, offset=1, hold=20  → −1,101  (least bad)
     FOLLOW, K=4, offset=1, hold=200 → −1,605

   Mechanism of failure: trade_at_spike_rate ≈ 0–4% on these products
   (anatomy/spike_anatomy.csv). At the spike tick our resting maker quote
   does not fill — there are no aggressors. Over the next 50–200 ticks
   pending, our quote tracks the new touch+1 each tick. Aggressor flow
   that arrives later is not random: it correlates with continuation
   (the spike was an MM repricing event reflecting genuine fair-value
   change). So our buy-at-bid+1 fills exactly when a seller appears —
   adverse-selection moment — and the price keeps moving against us
   on the 60–70% of cases that don't revert.

   Mid-only signed-PnL on these spikes is +50k+ over 3 days
   (per_day_pnl.csv), but capturing it requires either (a) fill at the
   spike tick itself (impossible — no trade) or (b) fill on
   reversion-correlated aggressor flow (doesn't exist — flow correlates
   with continuation).

   Conclusion for the OXY pair: locked-spread step jumps are descriptively
   real but not directly tradeable. Best fix is either:
     • leave OXY out of the spike layer (current state — only DISHES +
       IRONING in v7); or
     • add OXYGEN_SHAKE_EVENING_BREATH / CHOCOLATE to v7's standard MM
       universe (no spike trigger, just continuous quote-the-spread on
       the locked-12 plateau, accepting the step adverse-selection cost).
   Variant (b) is a separate experiment (no longer a "spike strategy").

Target products: OXYGEN_SHAKE_EVENING_BREATH, OXYGEN_SHAKE_CHOCOLATE.

Why maker, not taker:
  Both products show locked-spread + ±10 step jumps with trade_at_spike <4%
  (anatomy/spike_anatomy.csv). Taker fade pays spread=12 to harvest a
  ~5-tick reversion → marginal (+880 / +2,750 across 3 days, see
  anatomy/spike_strategy_pnl.csv). Spread > step ⇒ taker math loses;
  maker math wins.

Mechanism:
  When |mid_t − mid_{t-1}| ≥ K · σ_500.shift(1):
    - The counterparty MM stepped both quotes ±k together (zero-trade).
    - 40-50% of the move reverts within 200 ticks (anatomy reversion curve).
  Action: post a passive limit on the *reverted* side at touch+1 (improve
  by 1 tick). If filled and reversion comes, exit at opposite touch-1.
  No spread cost; capture ~5 ticks per round trip when reversion lands.

State machine (per product):
  FLAT (entry_tick=None, pos=0)  →  step detected → entry_tick=now,
                                    target_sign=-spike_sign.
  PENDING (entry_tick set, pos=0) →  re-post maker entry each tick at
                                     fresh touch+1 until filled or
                                     hold_pending_ticks elapses.
  HOLDING (entry_tick set, pos!=0) → post maker exit at opposite touch-1.
                                     If hold_total_ticks elapses, taker
                                     flatten as time-stop.
  Continuation kill: if a same-direction spike (against our target) fires
                     while pending/holding, taker flatten + reset (the
                     reversion thesis just got falsified).

Notes:
  - Position limit = 10. SIZE = 10 (full size on entry).
  - Hold = 200 ticks (matches OXY recovery curve plateau).
  - Pending timeout = 50 ticks (if no aggressor in 50 ticks, abort to
    avoid stale exposure into the next regime).
  - Disjoint from v7 universe (OXY_GARLIC stays in v7 MM; only
    EVENING_BREATH + CHOCOLATE here).

CLI:
    $env:PYTHONPATH="imc_trading/imc-prosperity-4-backtester"
    .venv/Scripts/python.exe -m prosperity4bt round5/strats/strat_oxy_step_maker.py 5--2 5--1 5-0
"""
try:
    from datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Observation, Trade, ProsperityEncoder
except ImportError:
    from prosperity4bt.datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Observation, Trade, ProsperityEncoder
from typing import List, Dict, Tuple, Any
import json
import math


# ─── Logger (kevin-fu1 visualizer) ────────────────────────────────────────
class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state, orders, conversions, trader_data):
        base = len(self.to_json([self.compress_state(state, ""), self.compress_orders(orders), conversions, "", ""]))
        max_item = (self.max_log_length - base) // 3
        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item)),
            self.compress_orders(orders), conversions,
            self.truncate(trader_data, max_item), self.truncate(self.logs, max_item),
        ]))
        self.logs = ""

    def compress_state(self, state, td):
        return [state.timestamp, td, [[l.symbol, l.product, l.denomination] for l in state.listings.values()],
                {s: [od.buy_orders, od.sell_orders] for s, od in state.order_depths.items()},
                [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp] for arr in state.own_trades.values() for t in arr],
                [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp] for arr in state.market_trades.values() for t in arr],
                state.position, [state.observations.plainValueObservations,
                                 {p: [o.bidPrice, o.askPrice, o.transportFees, o.exportTariff, o.importTariff,
                                      getattr(o, "sugarPrice", 0), getattr(o, "sunlightIndex", 0)]
                                  for p, o in state.observations.conversionObservations.items()}]]

    def compress_orders(self, orders):
        return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]

    def to_json(self, v): return json.dumps(v, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, v, n):
        lo, hi, out = 0, min(len(v), n), ""
        while lo <= hi:
            mid = (lo + hi) // 2
            cand = v[:mid] + ("..." if mid < len(v) else "")
            if len(json.dumps(cand)) <= n:
                out, lo = cand, mid + 1
            else:
                hi = mid - 1
        return out


logger = Logger()


# ═══════════════════════════════════════════════════════════════════════════
# Config
# ═══════════════════════════════════════════════════════════════════════════

TS_PER_TICK: int = 100  # IMC engine timestamp increment per tick


class StepCfg:
    __slots__ = (
        "key", "product",
        "sigma_window", "warmup", "k_sigma",
        "hold_total", "hold_pending",
        "size", "position_limit", "maker_offset",
    )

    def __init__(self, key, product, sigma_window, warmup, k_sigma,
                 hold_total, hold_pending, size, position_limit, maker_offset):
        self.key = key
        self.product = product
        self.sigma_window = sigma_window
        self.warmup = warmup
        self.k_sigma = k_sigma
        self.hold_total = hold_total      # ticks to hold position before time-stop taker flatten
        self.hold_pending = hold_pending  # ticks to wait for entry fill before abort
        self.size = size
        self.position_limit = position_limit
        self.maker_offset = maker_offset  # ticks inside the touch (1 = best_bid+1 / best_ask-1)


# σ_window=500 + K=4.0: same detector as vol_spikes.py / spike_anatomy.py.
# hold_total=200: matches recovery_pct_h200 plateau on EVENING_BREATH (0.41).
# hold_pending=50: aborts pending entry if no aggressor in 50 ticks
#                  (mean inter-arrival on these products ≈ 1500 ticks, so
#                  a 50-tick fill window is realistic for "active" periods only).
STEPS: List[StepCfg] = [
    StepCfg("EB",   "OXYGEN_SHAKE_EVENING_BREATH", 500, 50, 4.0, 200, 50, 10, 10, 1),
    StepCfg("CHOC", "OXYGEN_SHAKE_CHOCOLATE",      500, 50, 4.0, 200, 50, 10, 10, 1),
]


# ═══════════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════════

def _take_sell(product: str, depth: OrderDepth, room: int) -> List[Order]:
    """Cross to flat a long position: hit bids."""
    out: List[Order] = []
    if room <= 0:
        return out
    for price in sorted(depth.buy_orders.keys(), reverse=True):
        size = depth.buy_orders[price]
        take = min(room, size)
        if take > 0:
            out.append(Order(product, price, -take))
            room -= take
        if room <= 0:
            break
    return out


def _take_buy(product: str, depth: OrderDepth, room: int) -> List[Order]:
    """Cross to flat a short position: lift asks."""
    out: List[Order] = []
    if room <= 0:
        return out
    for price in sorted(depth.sell_orders.keys()):
        size = -depth.sell_orders[price]
        take = min(room, size)
        if take > 0:
            out.append(Order(product, price, take))
            room -= take
        if room <= 0:
            break
    return out


def _rolling_std(returns: List[float]) -> float:
    n = len(returns)
    if n < 2:
        return 0.0
    m = sum(returns) / n
    var = sum((r - m) ** 2 for r in returns) / n
    return math.sqrt(var) if var > 0 else 0.0


# ═══════════════════════════════════════════════════════════════════════════
# Per-tick step
# ═══════════════════════════════════════════════════════════════════════════

def _step_oxy(cfg: StepCfg, state: TradingState, st: dict,
              result: Dict[Symbol, List[Order]]) -> dict:
    depth = state.order_depths.get(cfg.product)
    if depth is None or not depth.buy_orders or not depth.sell_orders:
        return st

    bid = max(depth.buy_orders.keys())
    ask = min(depth.sell_orders.keys())
    mid = (bid + ask) / 2.0
    pos = state.position.get(cfg.product, 0)

    prev_mid: float = st.get("prev_mid")
    rets: List[float] = st.get("rets", [])
    prev_sigma: float = st.get("prev_sigma", 0.0)
    entry_tick = st.get("entry_tick")        # timestamp at spike detection
    target_sign: int = st.get("target_sign", 0)  # desired position sign post-fill

    ret_now = (mid - prev_mid) if prev_mid is not None else None

    # ── Spike detection (uses prior sigma, not current — no look-ahead) ──
    is_spike = False
    spike_sign = 0
    if ret_now is not None and len(rets) >= cfg.warmup and prev_sigma > 0:
        if abs(ret_now) >= cfg.k_sigma * prev_sigma:
            is_spike = True
            spike_sign = 1 if ret_now > 0 else -1

    orders: List[Order] = []

    # ── 1) Continuation kill: same-direction spike against our target ──
    # If we're targeting LONG (target_sign=+1, faded a down-spike) and a
    # second down-spike fires, the reversion thesis is broken — flatten.
    if entry_tick is not None and is_spike and target_sign != 0:
        if (target_sign > 0 and spike_sign < 0) or (target_sign < 0 and spike_sign > 0):
            if pos > 0:
                orders += _take_sell(cfg.product, depth, pos)
            elif pos < 0:
                orders += _take_buy(cfg.product, depth, -pos)
            entry_tick = None
            target_sign = 0
            logger.print(f"{cfg.key} CONT_KILL t={state.timestamp} ret={ret_now:.2f} "
                         f"prev_sigma={prev_sigma:.2f} pos={pos}")

    # ── 2) Hold-total time-stop: flatten and reset ──
    if entry_tick is not None and (state.timestamp - entry_tick) >= cfg.hold_total * TS_PER_TICK:
        if pos > 0:
            orders += _take_sell(cfg.product, depth, pos)
        elif pos < 0:
            orders += _take_buy(cfg.product, depth, -pos)
        if pos != 0:
            logger.print(f"{cfg.key} TIME_STOP t={state.timestamp} pos={pos} target={target_sign}")
        entry_tick = None
        target_sign = 0

    # ── 3) Hold-pending abort: never filled, give up ──
    if entry_tick is not None and pos == 0 and \
            (state.timestamp - entry_tick) >= cfg.hold_pending * TS_PER_TICK:
        logger.print(f"{cfg.key} PENDING_ABORT t={state.timestamp} target={target_sign}")
        entry_tick = None
        target_sign = 0

    # ── 4) New entry trigger ──
    if is_spike and entry_tick is None and pos == 0:
        target_sign = -spike_sign  # FADE — opposite of the spike
        entry_tick = state.timestamp
        logger.print(f"{cfg.key} STEP t={state.timestamp} ret={ret_now:.2f} "
                     f"prev_sigma={prev_sigma:.2f} spike_sign={spike_sign} target={target_sign}")

    # ── 5) Active maker quoting ──
    if entry_tick is not None and target_sign != 0:
        if pos == 0:
            # PENDING — post entry maker improving the touch by maker_offset.
            room_buy = cfg.position_limit - pos
            room_sell = cfg.position_limit + pos
            if target_sign > 0:
                qty = min(cfg.size, room_buy)
                if qty > 0:
                    orders.append(Order(cfg.product, bid + cfg.maker_offset, qty))
            else:
                qty = min(cfg.size, room_sell)
                if qty > 0:
                    orders.append(Order(cfg.product, ask - cfg.maker_offset, -qty))
        else:
            # HOLDING — post exit on the opposite side at touch − offset.
            # Exit qty = abs(pos) so partial fills keep walking the position to flat.
            if pos > 0:
                orders.append(Order(cfg.product, ask - cfg.maker_offset, -pos))
            else:
                orders.append(Order(cfg.product, bid + cfg.maker_offset, -pos))

    # ── 6) Update rolling history (after decisions, so prior σ was used above) ──
    if ret_now is not None:
        rets.append(ret_now)
        if len(rets) > cfg.sigma_window:
            rets = rets[-cfg.sigma_window:]
        new_sigma = _rolling_std(rets) if len(rets) >= cfg.warmup else 0.0
    else:
        new_sigma = prev_sigma

    if orders:
        result.setdefault(cfg.product, []).extend(orders)

    return {
        "prev_mid": mid,
        "rets": rets,
        "prev_sigma": new_sigma,
        "entry_tick": entry_tick,
        "target_sign": target_sign,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Trader
# ═══════════════════════════════════════════════════════════════════════════

class Trader:
    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0
        td = json.loads(state.traderData) if state.traderData else {}
        step_states: Dict[str, dict] = td.get("step_states", {})

        for cfg in STEPS:
            ts = step_states.get(cfg.key, {})
            step_states[cfg.key] = _step_oxy(cfg, state, ts, result)

        td["step_states"] = step_states
        s = json.dumps(td)
        logger.flush(state, result, conversions, s)
        return result, conversions, s
