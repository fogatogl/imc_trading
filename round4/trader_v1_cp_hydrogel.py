"""
Round 4 — HYDROGEL_PACK only, with counterparty-conditioned taker gate.

Derived from round-3 winner (`round3/486411/486411.py`) hydrogel block, applying
the closed findings in `round4/research_round4.ipynb` §11:

  - Anchor:        keep HP_MEAN = 9991       (sub-noise across candidates)
  - Dev thresholds: keep MAKER=14, SHARK=22  (spread structurally unchanged R3->R4)
  - Vol-armor:     removed                   (0% activation in 6 days; dead lever)
  - Counterparty:  taker gate (maker gate ablated — see verdict below)

Counterparty gate maps the latest HYDROGEL_PACK market trade to the predicted
sign of the next ~50-tick mid drift:

  Mark 14 = informed       (buy-drift +8, sell-drift +8 — they win both ways)
  Mark 38 = passive / LP   (buy-drift -8, sell-drift -8 — anti-informed)
  Mark 22 = ignore         (n=19 across 3 days, sub-sample)

  Mark 14 buying  -> mid rising   (sig = +1)
  Mark 14 selling -> mid falling  (sig = -1)
  Mark 38 buying  -> mid falling  (sig = -1)
  Mark 38 selling -> mid rising   (sig = +1)
  else            -> sig =  0

Gate: skip our intended taker buy when sig=-1; skip our intended taker sell
when sig=+1. Maker tier is NOT gated. Signal decays after HP_SIGNAL_TTL ticks.

==============================================================================
  Backtest verdict (2026-04-27, R4 days 1/2/3, match-trades=worse)
==============================================================================
  baseline (no gate)          : 19,714 + 17,680 + 19,669 =  57,063
  v1 full gate (take + make)  : 17,914 + 15,534 + 14,865 =  48,313  (-8,750)
  v1 taker-only gate (this)   : 17,989 + 18,591 + 19,435 =  56,015  (-1,048)

The CP drift signal is real (notebook §7), but our PnL is anchor-relative with
HP_MEAN fixed at 9991. Mid drifting +/-8 after an informed print does NOT move
the anchor, so our quote at hp_price +/- 5 retains its edge versus anchor
regardless of mid direction. Skipping = pure opportunity cost. The maker gate
loses 8.7k; the taker-only gate is within noise.

Net: this file is a documented negative result. Promote `trader_baseline_hydrogel.py`
unless a different CP application (e.g., adaptive anchor) is found.
"""

from typing import List, Dict, Tuple, Any
import json
import math

try:
    from datamodel import (
        OrderDepth, TradingState, Order, Symbol, Listing,
        Observation, Trade, ProsperityEncoder,
    )
except ImportError:
    from prosperity4bt.datamodel import (
        OrderDepth, TradingState, Order, Symbol, Listing,
        Observation, Trade, ProsperityEncoder,
    )


# ===========================================================================
#  Logger (CLAUDE.md contract — copy verbatim, do not modify)
# ===========================================================================
class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state, orders, conversions, trader_data):
        base = len(self.to_json([
            self.compress_state(state, ""),
            self.compress_orders(orders), conversions, "", "",
        ]))
        max_item = (self.max_log_length - base) // 3
        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item)),
            self.compress_orders(orders), conversions,
            self.truncate(trader_data, max_item),
            self.truncate(self.logs, max_item),
        ]))
        self.logs = ""

    def compress_state(self, state, td):
        return [
            state.timestamp, td,
            [[l.symbol, l.product, l.denomination] for l in state.listings.values()],
            {s: [od.buy_orders, od.sell_orders] for s, od in state.order_depths.items()},
            [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
             for arr in state.own_trades.values() for t in arr],
            [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
             for arr in state.market_trades.values() for t in arr],
            state.position,
            [state.observations.plainValueObservations,
             {p: [o.bidPrice, o.askPrice, o.transportFees, o.exportTariff,
                  o.importTariff, getattr(o, "sugarPrice", 0),
                  getattr(o, "sunlightIndex", 0)]
              for p, o in state.observations.conversionObservations.items()}],
        ]

    def compress_orders(self, orders):
        return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]

    def to_json(self, v):
        return json.dumps(v, cls=ProsperityEncoder, separators=(",", ":"))

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


# ===========================================================================
#  Hydrogel parameters
# ===========================================================================
HP_PRODUCT        = "HYDROGEL_PACK"
HP_MEAN           = 9991.0
HP_LIMIT          = 200
HP_SHARK_DEV      = 22.0   # take threshold = MAKER + spread/2  (median spread = 16)
HP_MAKER_DEV      = 14.0   # make threshold = median_spread - 2
HP_PASSIVE_OFFSET = 5
HP_SKEW_TICKS     = 6      # inventory-skew strength on fair_anchor

# Counterparty conditioning
HP_INFORMED       = frozenset({"Mark 14"})
HP_PASSIVE_CP     = frozenset({"Mark 38"})
HP_SIGNAL_TTL     = 100    # ticks; drift half-life ~50 ticks (notebook §7)


# ===========================================================================
#  Helpers
# ===========================================================================
def _wap(od: OrderDepth):
    if not od or not od.buy_orders or not od.sell_orders:
        return None
    bp = max(od.buy_orders.keys())
    ap = min(od.sell_orders.keys())
    bv = od.buy_orders[bp]
    av = abs(od.sell_orders[ap])
    return (bp * av + ap * bv) / (bv + av)


def _hp_drift_sign(trades: List[Trade]) -> int:
    """Predicted sign of next ~50-tick mid drift from the most recent market trade.
    +1 = up, -1 = down, 0 = no information."""
    if not trades:
        return 0
    latest = max(trades, key=lambda t: t.timestamp)
    b, s = latest.buyer, latest.seller
    if b in HP_INFORMED:
        return +1   # informed buyer  -> mid rising
    if s in HP_INFORMED:
        return -1   # informed seller -> mid falling
    if b in HP_PASSIVE_CP:
        return -1   # passive buyer = anti-informed -> mid falling
    if s in HP_PASSIVE_CP:
        return +1   # passive seller = anti-informed -> mid rising
    return 0


# ===========================================================================
#  Trader
# ===========================================================================
class Trader:

    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0

        try:
            td = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            td = {}

        hp_sig     = int(td.get("hp_sig", 0))
        hp_sig_ttl = int(td.get("hp_sig_ttl", 0))

        # Update CP drift signal from market trades observed since last tick.
        new_sig = _hp_drift_sign(state.market_trades.get(HP_PRODUCT, []))
        if new_sig != 0:
            hp_sig, hp_sig_ttl = new_sig, HP_SIGNAL_TTL
        else:
            hp_sig_ttl = max(0, hp_sig_ttl - 1)
            if hp_sig_ttl == 0:
                hp_sig = 0

        depths = state.order_depths
        pos    = state.position or {}
        hp_book = depths.get(HP_PRODUCT)
        hp_price = _wap(hp_book)

        if hp_book is not None and hp_price is not None:
            hp_curr = pos.get(HP_PRODUCT, 0)
            fair_anchor = HP_MEAN - int((hp_curr / HP_LIMIT) * HP_SKEW_TICKS)
            dev = hp_price - fair_anchor

            blocked_buy  = (hp_sig == -1)  # mid falling -> our buy will be expensive
            blocked_sell = (hp_sig == +1)  # mid rising  -> our sell will be cheap

            # ---- SHARK taker ----
            if abs(dev) > HP_SHARK_DEV:
                want_sell = dev > 0
                want_buy  = dev < 0
                if (want_sell and not blocked_sell) or (want_buy and not blocked_buy):
                    side_volume = sum(
                        abs(v) for v in (
                            hp_book.buy_orders if dev > 0 else hp_book.sell_orders
                        ).values()
                    )
                    qty = min(HP_LIMIT - abs(hp_curr), side_volume)
                    if qty > 0:
                        px = (max(hp_book.buy_orders.keys()) if dev > 0
                              else min(hp_book.sell_orders.keys()))
                        result[HP_PRODUCT] = [
                            Order(HP_PRODUCT, int(px), int(-qty if dev > 0 else qty))
                        ]

            # ---- MAKER passive (no CP gate — anchor-relative PnL nullifies signal) ----
            elif abs(dev) > HP_MAKER_DEV:
                if dev > 0 and hp_curr > -HP_LIMIT:
                    result[HP_PRODUCT] = [
                        Order(HP_PRODUCT,
                              int(math.ceil(hp_price + HP_PASSIVE_OFFSET)),
                              -(HP_LIMIT + hp_curr))
                    ]
                elif dev < 0 and hp_curr < HP_LIMIT:
                    result[HP_PRODUCT] = [
                        Order(HP_PRODUCT,
                              int(math.floor(hp_price - HP_PASSIVE_OFFSET)),
                              HP_LIMIT - hp_curr)
                    ]

        # Persist signal state.
        td["hp_sig"]     = hp_sig
        td["hp_sig_ttl"] = hp_sig_ttl
        trader_data = json.dumps(td, separators=(",", ":"))

        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data
