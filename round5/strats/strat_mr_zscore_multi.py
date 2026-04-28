"""
Multi-product mean-reversion z-score taker.

Universe — 11 MR_TAKER products selected by teammates' parallel research:
    PEBBLES_L
    UV_VISOR_ORANGE
    GALAXY_SOUNDS_SOLAR_FLAMES
    OXYGEN_SHAKE_CHOCOLATE
    OXYGEN_SHAKE_EVENING_BREATH
    ROBOT_IRONING / LAUNDRY / MOPPING
    MICROCHIP_CIRCLE
    TRANSLATOR_VOID_BLUE / GRAPHITE_MIST

Most are pipeline-flagged MR_TAKER with negative ACF₁ and Hurst < 0.5.
UV_VISOR_ORANGE is NO_EDGE primary but carries OBI_TAKER (follow, IC=+0.058)
— the z-score signal is noisy on it; the OBI overlay carries the alpha.

Mechanics — per product, per tick:
    z = (mid - μ) / σ        (μ, σ from EWMA with halflife = HL)
    z > +ENTRY_Z   → take the bid down (sell)
    z < -ENTRY_Z   → lift the ask    (buy)
    |z| > STOP_Z   → freeze (regime break)
    |z| < EXIT_Z   → flatten inventory at touch + post passive maker pair around μ

OBI overlay (only on products with HAC+FDR-passing OBI IC, see PIPELINE_REPORT.md §5.5):
    +obi_dir signal nudges fair toward book pressure (follow), and gates
    z-takes that disagree with current book pressure.

State persistence:
    Per product (μ, S) Welford-style EWMA — 2 floats per product, ~250 bytes
    of traderData total, well under the budget.
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
# obi_dir: "follow" / "fade" / None. Source: archetype_assignment.csv.
# obi_sig: "obi_l1" / "obi_l3".
PRODUCTS: dict[str, dict[str, Any]] = {
    "PEBBLES_L":                   {"obi_dir": None,     "obi_sig": None},
    "UV_VISOR_ORANGE":             {"obi_dir": "follow", "obi_sig": "obi_l1"},
    "GALAXY_SOUNDS_SOLAR_FLAMES":  {"obi_dir": "fade",   "obi_sig": "obi_l3"},
    "OXYGEN_SHAKE_CHOCOLATE":      {"obi_dir": "follow", "obi_sig": "obi_l1"},
    "OXYGEN_SHAKE_EVENING_BREATH": {"obi_dir": "follow", "obi_sig": "obi_l1"},
    "ROBOT_IRONING":               {"obi_dir": None,     "obi_sig": None},
    "ROBOT_LAUNDRY":               {"obi_dir": None,     "obi_sig": None},
    "ROBOT_MOPPING":               {"obi_dir": None,     "obi_sig": None},
    "MICROCHIP_CIRCLE":            {"obi_dir": None,     "obi_sig": None},
    "TRANSLATOR_VOID_BLUE":        {"obi_dir": "fade",   "obi_sig": "obi_l3"},
    "TRANSLATOR_GRAPHITE_MIST":    {"obi_dir": "fade",   "obi_sig": "obi_l3"},
}

POSITION_LIMIT: int = 10
HL: float = 100.0                # EWMA halflife in ticks (≈ rolling window of 200)
WARMUP: int = 30                 # ticks before any trading
ENTRY_Z: float = 1.5             # |z| above this → take liquidity
EXIT_Z: float = 0.3              # |z| below this → flatten + maker
STOP_Z: float = 4.0              # |z| above this → freeze
MAKER_OFFSET: int = 1            # ticks beyond μ for passive maker
MAKER_SIZE: int = 5
OBI_GATE: float = 0.25           # min |obi| for overlay to gate / push


# ---------- Logger ----------
class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state, orders, conversions, trader_data):
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


def obi_l1_val(depth: OrderDepth, bid: int, ask: int) -> float:
    bsz = depth.buy_orders.get(bid, 0)
    asz = -depth.sell_orders.get(ask, 0)
    tot = bsz + asz
    return (bsz - asz) / tot if tot > 0 else 0.0


def obi_l3_val(depth: OrderDepth) -> float:
    top_b = sorted(depth.buy_orders.items(), reverse=True)[:3]
    top_a = sorted(depth.sell_orders.items())[:3]
    bsz = sum(v for _, v in top_b)
    asz = -sum(v for _, v in top_a)
    tot = bsz + asz
    return (bsz - asz) / tot if tot > 0 else 0.0


# ---------- EWMA Welford ----------
# EWMA with smoothing α = 1 - 0.5^(1/HL) gives a halflife of HL ticks.
ALPHA = 1.0 - math.pow(0.5, 1.0 / HL)


def ewma_update(mu: float, var: float, n: int, x: float) -> tuple[float, float, int]:
    """Bias-corrected EWMA mean / variance; n is sample count for warmup."""
    if n == 0:
        return x, 0.0, 1
    delta = x - mu
    new_mu = mu + ALPHA * delta
    new_var = (1 - ALPHA) * (var + ALPHA * delta * delta)
    return new_mu, new_var, n + 1


# ---------- Trader ----------
class Trader:
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        try:
            mem: dict[str, Any] = json.loads(state.traderData) if state.traderData else {}
        except (ValueError, TypeError):
            mem = {}
        st: dict[str, list[float]] = mem.get("e", {})  # {product: [mu, var, n]}

        result: dict[Symbol, list[Order]] = {}

        for product, cfg in PRODUCTS.items():
            depth = state.order_depths.get(product)
            if depth is None:
                continue
            bid, ask = best_bid_ask(depth)
            mid = mid_of(depth)
            if mid is None or bid is None or ask is None:
                continue

            mu, var, n = st.get(product, [0.0, 0.0, 0])
            mu, var, n = ewma_update(mu, var, n, mid)
            st[product] = [mu, var, n]

            if n < WARMUP:
                continue

            sigma = math.sqrt(var) if var > 0 else 1e-9
            z = (mid - mu) / sigma
            pos = state.position.get(product, 0)

            # OBI overlay
            obi = 0.0
            if cfg["obi_sig"] == "obi_l1":
                obi = obi_l1_val(depth, bid, ask)
            elif cfg["obi_sig"] == "obi_l3":
                obi = obi_l3_val(depth)
            obi_signed = obi if cfg["obi_dir"] == "follow" else (-obi if cfg["obi_dir"] == "fade" else 0.0)

            orders: list[Order] = []

            if abs(z) > STOP_Z:
                pass  # regime break — no new trades

            elif z > ENTRY_Z:
                # SELL: hit the bid. Skip if OBI overlay says strong buy pressure (follow + obi>0 ⇒ price likely to keep rising).
                if obi_signed > OBI_GATE:
                    pass  # disagrees — skip take
                else:
                    room = POSITION_LIMIT + pos
                    bid_size = depth.buy_orders.get(bid, 0)
                    fill = min(room, bid_size)
                    if fill > 0:
                        orders.append(Order(product, bid, -fill))

            elif z < -ENTRY_Z:
                # BUY: lift the ask. Skip if OBI overlay says strong sell pressure.
                if obi_signed < -OBI_GATE:
                    pass
                else:
                    room = POSITION_LIMIT - pos
                    ask_size = -depth.sell_orders.get(ask, 0)
                    fill = min(room, ask_size)
                    if fill > 0:
                        orders.append(Order(product, ask, fill))

            elif abs(z) < EXIT_Z:
                # flatten any inventory at touch
                if pos > 0:
                    orders.append(Order(product, bid, -pos))
                elif pos < 0:
                    orders.append(Order(product, ask, -pos))
                # passive maker around μ — earns spread when range-bound
                buy_px = int(round(mu - MAKER_OFFSET))
                sell_px = int(round(mu + MAKER_OFFSET))
                # inside-touch clamp (feedback_maker_quote_inside_touch)
                if buy_px >= bid:
                    buy_px = bid + 1
                if sell_px <= ask:
                    sell_px = ask - 1
                if buy_px >= sell_px:
                    buy_px = sell_px - 1
                buy_room = POSITION_LIMIT - pos
                sell_room = POSITION_LIMIT + pos
                if buy_room > 0 and buy_px < ask:
                    orders.append(Order(product, buy_px, min(MAKER_SIZE, buy_room)))
                if sell_room > 0 and sell_px > bid:
                    orders.append(Order(product, sell_px, -min(MAKER_SIZE, sell_room)))

            if orders:
                result[product] = orders

            logger.print(f"{product[-12:]:12s} z={z:+.2f} mu={mu:.1f} pos={pos:+d} obi={obi:+.2f}")

        mem["e"] = st
        td = json.dumps(mem, separators=(",", ":"))
        logger.flush(state, result, 0, td)
        return result, 0, td
