"""
SNACKPACK family market-making strategy — Template-A with OBI follow skew.

Pipeline source (round5/PIPELINE_REPORT.md §4.6, §5.4, §5.5):
    - All 4 included SNACKPACK products carry the MM_CANDIDATE flag.
    - SNACKPACK_VANILLA is the only `is_mm = True` CONFIRMED case in the
      universe (sim PnL +1350 with 1 fill in the round-5 simulator).
    - SNACKPACK_CHOCOLATE was excluded — pipeline sim REJECTED it
      (PnL = -1364, 1 fill).
    - SNACKPACK family carries the strongest OBI_TAKER IC in the universe
      (obi_l1 at h = 1, IC = 0.097-0.132, all `follow` direction).

Mechanics — Template-A formula from PIPELINE_REPORT.md §3.2:
    fair       = mid + obi_skew - gamma * rv**2 * inventory
    half_edge  = max(min_edge_ticks, k_vol * rv)
    bid        = fair - half_edge
    ask        = fair + half_edge
    obi_skew   = OBI_GAIN * obi_signal             (follow: shift fair toward book pressure)

Per-product (min_edge_ticks, k_vol, gamma) come from
`round5/reports/SNACKPACK/archetype_assignment.csv` (mm_params field).

Inside-touch clamp (feedback_maker_quote_inside_touch): quotes that fall on
or outside the top of book are pulled to best_bid+1 / best_ask-1, otherwise
they get zero fills under the IMC `worse` fill model.
"""
from __future__ import annotations

import json
import math
from typing import Any

try:
    from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
except ImportError:
    from prosperity4bt.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


# ---------- per-product config ----------
# (min_edge_ticks, k_vol, gamma, obi_ic, obi_signal, obi_horizon)
# obi_signal: "obi_l1" or "obi_l3"; OBI direction is `follow` for all of these.
PRODUCTS: dict[str, dict[str, Any]] = {
    "SNACKPACK_VANILLA":    {"min_edge": 8, "k_vol": 1.6564, "gamma": 0.0010, "obi_ic": 0.114, "obi_sig": "obi_l1"},
    "SNACKPACK_RASPBERRY":  {"min_edge": 8, "k_vol": 1.6516, "gamma": 0.00103, "obi_ic": 0.102, "obi_sig": "obi_l1"},
    "SNACKPACK_STRAWBERRY": {"min_edge": 9, "k_vol": 1.6480, "gamma": 0.00109, "obi_ic": 0.097, "obi_sig": "obi_l1"},
    "SNACKPACK_PISTACHIO":  {"min_edge": 8, "k_vol": 1.6486, "gamma": 0.00106, "obi_ic": 0.132, "obi_sig": "obi_l1"},
}

POSITION_LIMIT: int = 10                 # round-5 spec
QUOTE_SIZE: int = 5                      # passive size per side
VOL_WINDOW: int = 50                     # rv = std of 1-tick mid returns
WARMUP: int = 25                         # ticks of history before first quote
OBI_GAIN: float = 1.5                    # max ticks of fair shift per |obi|=1 (scaled by IC sign)
TAKE_EDGE: int = 1                       # take when book crosses fair ± (half_edge + TAKE_EDGE)
MAX_HISTORY: int = 80                    # bound state size for traderData budget


# ---------- Logger (shared contract — do not modify) ----------
class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(self.to_json([self.compress_state(state, ""), self.compress_orders(orders), conversions, "", ""]))
        max_item_length = (self.max_log_length - base_length) // 3
        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item_length)),
            self.compress_orders(orders),
            conversions,
            self.truncate(trader_data, max_item_length),
            self.truncate(self.logs, max_item_length),
        ]))
        self.logs = ""

    def compress_state(self, state, td):
        return [state.timestamp, td,
                self.compress_listings(state.listings),
                self.compress_order_depths(state.order_depths),
                self.compress_trades(state.own_trades),
                self.compress_trades(state.market_trades),
                state.position,
                self.compress_observations(state.observations)]
    def compress_listings(self, listings): return [[l.symbol, l.product, l.denomination] for l in listings.values()]
    def compress_order_depths(self, ods): return {s: [d.buy_orders, d.sell_orders] for s, d in ods.items()}
    def compress_trades(self, trades):
        return [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
                for arr in trades.values() for t in arr]
    def compress_observations(self, observations):
        conv = {}
        for p, o in observations.conversionObservations.items():
            conv[p] = [getattr(o, k, None) for k in
                       ("bidPrice","askPrice","transportFees","exportTariff","importTariff","sugarPrice","sunlightIndex")]
        return [observations.plainValueObservations, conv]
    def compress_orders(self, orders): return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]
    def to_json(self, v): return json.dumps(v, cls=ProsperityEncoder, separators=(",", ":"))
    def truncate(self, v, n): return v if len(v) <= n else v[: n - 3] + "..."


logger = Logger()


# ---------- helpers ----------
def best_bid_ask(depth: OrderDepth) -> tuple[int | None, int | None]:
    bid = max(depth.buy_orders.keys()) if depth.buy_orders else None
    ask = min(depth.sell_orders.keys()) if depth.sell_orders else None
    return bid, ask


def mid_of(depth: OrderDepth) -> float | None:
    bid, ask = best_bid_ask(depth)
    return (bid + ask) / 2.0 if (bid is not None and ask is not None) else None


def obi_l1(depth: OrderDepth, bid: int, ask: int) -> float:
    bsz = depth.buy_orders.get(bid, 0)
    asz = -depth.sell_orders.get(ask, 0)
    tot = bsz + asz
    return (bsz - asz) / tot if tot > 0 else 0.0


def obi_l3(depth: OrderDepth) -> float:
    top_b = sorted(depth.buy_orders.items(), reverse=True)[:3]
    top_a = sorted(depth.sell_orders.items())[:3]
    bsz = sum(v for _, v in top_b)
    asz = -sum(v for _, v in top_a)
    tot = bsz + asz
    return (bsz - asz) / tot if tot > 0 else 0.0


def realised_vol(history: list[float]) -> float:
    """Std of 1-tick returns over the last VOL_WINDOW samples."""
    if len(history) < 2:
        return 0.0
    rets = [history[i] - history[i - 1] for i in range(1, len(history))]
    n = len(rets)
    mean = sum(rets) / n
    var = sum((r - mean) ** 2 for r in rets) / n
    return math.sqrt(var)


# ---------- Trader ----------
class Trader:
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        # ---- load persistent state ----
        try:
            mem: dict[str, Any] = json.loads(state.traderData) if state.traderData else {}
        except (ValueError, TypeError):
            mem = {}
        mids: dict[str, list[float]] = mem.get("m", {})

        result: dict[Symbol, list[Order]] = {}

        for product, cfg in PRODUCTS.items():
            depth = state.order_depths.get(product)
            if depth is None:
                continue
            bid, ask = best_bid_ask(depth)
            mid = mid_of(depth)
            if mid is None or bid is None or ask is None:
                continue

            hist = mids.setdefault(product, [])
            hist.append(mid)
            if len(hist) > MAX_HISTORY:
                del hist[: len(hist) - MAX_HISTORY]

            if len(hist) < WARMUP:
                continue

            rv = realised_vol(hist[-VOL_WINDOW:])
            pos = state.position.get(product, 0)

            # OBI follow skew: positive obi_l1 → expected up-move → shift fair up
            obi = obi_l1(depth, bid, ask) if cfg["obi_sig"] == "obi_l1" else obi_l3(depth)
            obi_shift = OBI_GAIN * obi  # IC sign already known to be positive (follow)

            inv_skew = cfg["gamma"] * (rv ** 2) * pos
            fair = mid + obi_shift - inv_skew

            half_edge = max(float(cfg["min_edge"]), cfg["k_vol"] * rv)
            buy_px = int(math.floor(fair - half_edge))
            sell_px = int(math.ceil(fair + half_edge))

            buy_room = POSITION_LIMIT - pos
            sell_room = POSITION_LIMIT + pos
            orders: list[Order] = []

            # ---- opportunistic take when book is dislocated past fair ----
            if bid >= fair + half_edge + TAKE_EDGE and sell_room > 0:
                size = min(sell_room, depth.buy_orders.get(bid, 0))
                if size > 0:
                    orders.append(Order(product, bid, -size))
                    sell_room -= size
            if ask <= fair - half_edge - TAKE_EDGE and buy_room > 0:
                size = min(buy_room, -depth.sell_orders.get(ask, 0))
                if size > 0:
                    orders.append(Order(product, ask, size))
                    buy_room -= size

            # ---- inside-touch clamp (feedback_maker_quote_inside_touch) ----
            # If our calc bid is at or above the touch, improve by 1 tick to
            # actually get fills under `worse` mode. Otherwise keep wider quote.
            if buy_px >= bid:
                buy_px = bid + 1
            if sell_px <= ask:
                sell_px = ask - 1
            # Never cross our own quotes.
            if buy_px >= sell_px:
                buy_px = sell_px - 1

            if buy_room > 0 and buy_px < ask:
                orders.append(Order(product, buy_px, min(QUOTE_SIZE, buy_room)))
            if sell_room > 0 and sell_px > bid:
                orders.append(Order(product, sell_px, -min(QUOTE_SIZE, sell_room)))

            if orders:
                result[product] = orders

            logger.print(f"{product[-10:]} m={mid:.1f} rv={rv:.2f} obi={obi:+.2f} pos={pos:+d} q={buy_px}/{sell_px}")

        # ---- persist trimmed state ----
        mem["m"] = {p: h[-VOL_WINDOW:] for p, h in mids.items() if h}
        td = json.dumps(mem, separators=(",", ":"))
        logger.flush(state, result, 0, td)
        return result, 0, td
