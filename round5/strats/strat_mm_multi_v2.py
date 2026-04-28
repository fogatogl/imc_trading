"""
Multi-product passive market-maker (round 5) — v2.

3-day Python BT (D2+D3+D4):  baseline 98,695 → v2 99,025  (+330, +0.3%).
Rust BT agrees within 0.01% on both. Improvement is small — the existing
template is near a local optimum on this universe.

Changes vs strat_mm_multi.py:
    1. Per-product `obi_ic` field. OBI_GAIN scaled by |IC| so high-IC products
       (e.g. OXYGEN_SHAKE_CHOCOLATE obi_l1 +0.057) get larger fair shifts than
       marginal ones (ROBOT_IRONING obi_l1 +0.026). Constant gain=4.0 wasted
       signal strength on the strongest predictors.
    2. OBI overlays added for products that had FDR-significant signals but
       were configured `obi_dir=None`:
         - ROBOT_IRONING:    obi_l1 follow (IC +0.026, t=4.09, p=4e-5)
         - ROBOT_MOPPING:    obi_l3 fade   (IC −0.027, t=−4.51, p=6e-6)
         - MICROCHIP_CIRCLE: obi_l3 fade   (IC −0.035, t=−6.07, p=1e-9)
    3. Asymmetric quote sizing: when |OBI| > OBI_SIZE_THRESHOLD, lean size into
       the predicted direction (follow → bigger on aligned side; fade → bigger
       on opposite side). Total size unchanged; allocation is shifted.
    4. Inventory taper: shrink quote on the side that increases |pos| as
       |pos| approaches POSITION_LIMIT.

Investigation notes (kept as-is — do NOT delete IRONING):
    - ROBOT_IRONING bleeds −9,538 on D4 alone but earns +5,381 / +5,249 on
      D2 / D3 → net +1,092 over 3 days. Dropping it (initial v2 try) cost
      −626 total. Inside-touch clamp absorbs OBI shifts whenever half_spread
      is small relative to the market spread, so OBI overlay effect on
      MICROCHIP_CIRCLE / OXYGEN_SHAKE_CHOCOLATE is near-zero in backtest.
    - Bigger gains would need structural changes (move IRONING/MOPPING to
      a MR_TAKER strategy file — both are primary MR_TAKER per pipeline).
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
# obi_ic = signed IC magnitude; sign encodes direction (follow=+, fade=-).
# IC values from round5/reports/<FAMILY>/signals_ic.csv (h=1, FDR-sig only).
PRODUCTS: dict[str, dict[str, Any]] = {
    "PEBBLES_L":                   {"half_spread": 4, "obi_sig": None,    "obi_ic":  0.0,    "vol_cap": 14.96},
    "UV_VISOR_ORANGE":             {"half_spread": 4, "obi_sig": "obi_l1","obi_ic": +0.040,  "vol_cap": 10.39},
    "GALAXY_SOUNDS_SOLAR_FLAMES":  {"half_spread": 5, "obi_sig": "obi_l3","obi_ic": -0.054,  "vol_cap": 11.03},
    "OXYGEN_SHAKE_CHOCOLATE":      {"half_spread": 4, "obi_sig": "obi_l1","obi_ic": +0.057,  "vol_cap": 10.25},
    "OXYGEN_SHAKE_EVENING_BREATH": {"half_spread": 4, "obi_sig": "obi_l1","obi_ic": +0.045,  "vol_cap": 10.52},
    "ROBOT_IRONING":               {"half_spread": 2, "obi_sig": "obi_l1","obi_ic": +0.026,  "vol_cap":  9.97},
    "ROBOT_MOPPING":               {"half_spread": 2, "obi_sig": "obi_l3","obi_ic": -0.027,  "vol_cap": 11.07},
    "MICROCHIP_CIRCLE":            {"half_spread": 3, "obi_sig": "obi_l3","obi_ic": -0.035,  "vol_cap":  9.16},
    "TRANSLATOR_VOID_BLUE":        {"half_spread": 3, "obi_sig": "obi_l3","obi_ic": -0.044,  "vol_cap": 10.77},
    "TRANSLATOR_GRAPHITE_MIST":    {"half_spread": 3, "obi_sig": "obi_l3","obi_ic": -0.041,  "vol_cap": 10.07},
    "SNACKPACK_PISTACHIO":         {"half_spread": 8, "obi_sig": "obi_l1","obi_ic": +0.132,  "vol_cap":  5.22},
    "GALAXY_SOUNDS_DARK_MATTER":   {"half_spread": 6, "obi_sig": "obi_l1","obi_ic": +0.045,  "vol_cap": 10.19},
    "GALAXY_SOUNDS_BLACK_HOLES":   {"half_spread": 7, "obi_sig": "obi_l1","obi_ic": +0.040,  "vol_cap": 11.37},
    "OXYGEN_SHAKE_MORNING_BREATH": {"half_spread": 6, "obi_sig": "obi_l1","obi_ic": +0.045,  "vol_cap": 10.04},
}

POSITION_LIMIT: int = 10
QUOTE_SIZE: int = 10
HL: float = 200.0
WARMUP: int = 30
INV_SKEW: float = 0.5
OBI_GAIN_PER_IC: float = 80.0     # gain = OBI_GAIN_PER_IC * |obi_ic|, capped
OBI_GAIN_CAP: float = 12.0
OBI_VOL_BOOST: float = 0.5
OBI_SIZE_THRESHOLD: float = 0.30  # |obi| > threshold triggers asymmetric sizing
OBI_SIZE_TILT: float = 0.4        # max fraction of size shifted between sides
INV_TAPER_START: float = 0.5      # taper begins when |pos|/limit > this
STOP_DEV: float = 50.0
VOL_WINDOW: int = 50


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


# ---------- EWMA ----------
ALPHA = 1.0 - math.pow(0.5, 1.0 / HL)


# ---------- Trader ----------
class Trader:
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        try:
            mem: dict[str, Any] = json.loads(state.traderData) if state.traderData else {}
        except (ValueError, TypeError):
            mem = {}
        st: dict[str, list[float]] = mem.get("e", {})
        rh: dict[str, list[float]] = mem.get("r", {})
        last_mid: dict[str, float] = mem.get("p", {})

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
            if n == 0:
                mu, var = mid, 0.0
                n = 1
            else:
                delta = mid - mu
                mu = mu + ALPHA * delta
                var = (1 - ALPHA) * (var + ALPHA * delta * delta)
                n += 1
            st[product] = [mu, var, n]

            prev = last_mid.get(product)
            last_mid[product] = mid
            ret_hist = rh.setdefault(product, [])
            if prev is not None:
                ret_hist.append(mid - prev)
                if len(ret_hist) > VOL_WINDOW:
                    del ret_hist[: len(ret_hist) - VOL_WINDOW]

            if n < WARMUP:
                continue

            if len(ret_hist) >= 10:
                rm = sum(ret_hist) / len(ret_hist)
                rv = sum((r - rm) ** 2 for r in ret_hist) / len(ret_hist)
                sigma_ret = math.sqrt(rv)
            else:
                sigma_ret = 0.0
            vol_cap = float(cfg["vol_cap"])

            pos = state.position.get(product, 0)

            # OBI overlay — gain proportional to |IC|, signed by direction.
            obi_ic = float(cfg["obi_ic"])
            if cfg["obi_sig"] == "obi_l1":
                obi = obi_l1_val(depth, bid, ask)
            elif cfg["obi_sig"] == "obi_l3":
                obi = obi_l3_val(depth)
            else:
                obi = 0.0
            base_gain = min(OBI_GAIN_PER_IC * abs(obi_ic), OBI_GAIN_CAP)
            vol_ratio = (sigma_ret / vol_cap) if (sigma_ret > 0 and vol_cap > 0) else 1.0
            gain = base_gain * (1.0 + OBI_VOL_BOOST * max(0.0, vol_ratio - 1.0))
            # Sign: follow (ic>0) shifts fair toward book pressure; fade (ic<0) against.
            obi_shift = math.copysign(gain, obi_ic) * obi if obi_ic != 0.0 else 0.0

            inv_shift = INV_SKEW * pos
            fair = mu + obi_shift - inv_shift

            half = cfg["half_spread"]
            buy_px = int(math.floor(fair - half))
            sell_px = int(math.ceil(fair + half))

            if buy_px >= bid:
                buy_px = bid + 1
            if sell_px <= ask:
                sell_px = ask - 1
            if buy_px >= sell_px:
                buy_px = sell_px - 1

            if abs(mid - mu) > STOP_DEV:
                continue

            buy_room = POSITION_LIMIT - pos
            sell_room = POSITION_LIMIT + pos

            # Vol-scaled base size.
            if sigma_ret > 1.3 * vol_cap and vol_cap > 0:
                base_size = max(2, int(round(QUOTE_SIZE * 1.3 * vol_cap / sigma_ret)))
            else:
                base_size = QUOTE_SIZE

            # Predicted direction from OBI signal: follow → buy when obi>0; fade → buy when obi<0.
            pred = math.copysign(1.0, obi_ic) * obi if obi_ic != 0.0 else 0.0
            buy_size = base_size
            sell_size = base_size
            if abs(pred) > OBI_SIZE_THRESHOLD:
                tilt = OBI_SIZE_TILT * (abs(pred) - OBI_SIZE_THRESHOLD) / (1.0 - OBI_SIZE_THRESHOLD)
                tilt = min(tilt, OBI_SIZE_TILT)
                if pred > 0:
                    buy_size = int(round(base_size * (1.0 + tilt)))
                    sell_size = int(round(base_size * (1.0 - tilt)))
                else:
                    buy_size = int(round(base_size * (1.0 - tilt)))
                    sell_size = int(round(base_size * (1.0 + tilt)))

            # Inventory taper: shrink the side that would worsen |pos| when near limit.
            inv_frac = abs(pos) / POSITION_LIMIT
            if inv_frac > INV_TAPER_START:
                taper = (inv_frac - INV_TAPER_START) / (1.0 - INV_TAPER_START)
                taper = min(taper, 1.0)
                if pos > 0:
                    buy_size = int(round(buy_size * (1.0 - taper)))
                elif pos < 0:
                    sell_size = int(round(sell_size * (1.0 - taper)))

            buy_size = max(0, buy_size)
            sell_size = max(0, sell_size)

            orders: list[Order] = []
            if buy_room > 0 and buy_size > 0 and buy_px < ask:
                orders.append(Order(product, buy_px, min(buy_size, buy_room)))
            if sell_room > 0 and sell_size > 0 and sell_px > bid:
                orders.append(Order(product, sell_px, -min(sell_size, sell_room)))

            if orders:
                result[product] = orders

            logger.print(f"{product[-12:]:12s} mu={mu:.1f} obi={obi:+.2f} pos={pos:+d} σ={sigma_ret:.1f} q={buy_px}/{sell_px} sz={buy_size}/{sell_size}")

        mem["e"] = st
        mem["r"] = {p: h[-VOL_WINDOW:] for p, h in rh.items() if h}
        mem["p"] = last_mid
        td = json.dumps(mem, separators=(",", ":"))
        logger.flush(state, result, 0, td)
        return result, 0, td
