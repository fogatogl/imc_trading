"""
v8 — 555509 base + 556852's PEBBLES MM params (only).

Per user: 556852 is better ONLY on PEBBLES market-making, NOT on pairs.
=> Keep 555509's PEBBLES pairs (4-pair star around XL, incl PEB_L).
=> Override PEBBLES MM params with 556852's tighter values.

Diff vs 555509 (PEBBLES only):
  - PRODUCT_PARAMS now has explicit per-PEBBLES entries:
      BASE_QTY=5, INV_SKEW=2.0, MR_SKEW=1.0, Z_TOXIC=2.0
    (vs 555509 defaults 10/1.5/1.0/2.5)

Everything else identical to 555509: SNACKPACK basket, PEBBLES star (L/XL,
M/XL, S/XL, XS/XL), MR_OTHER, OBI graft, slp_cp pair, inventory taper, logger.
"""
try:
    from datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Observation, Trade, ProsperityEncoder
except ImportError:
    from prosperity4bt.datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Observation, Trade, ProsperityEncoder
from typing import List, Dict, Tuple, Any
import json
import math


# ─── Logger (compatible visualizer kevin-fu1) ─────────────────────────────
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


# ─── Univers ──────────────────────────────────────────────────────────────
CHOC   = "SNACKPACK_CHOCOLATE"
VAN    = "SNACKPACK_VANILLA"
PIST   = "SNACKPACK_PISTACHIO"
RASP   = "SNACKPACK_RASPBERRY"
STRAW  = "SNACKPACK_STRAWBERRY"

SNACKPACK: List[str] = [CHOC, VAN, PIST, RASP, STRAW]

PEB_L  = "PEBBLES_L"
PEB_XS = "PEBBLES_XS"
PEB_S  = "PEBBLES_S"
PEB_M  = "PEBBLES_M"
PEB_XL = "PEBBLES_XL"

PEBBLES: List[str] = [PEB_L, PEB_XS, PEB_S, PEB_M, PEB_XL]

SLP_COT = "SLEEP_POD_COTTON"

MR_OTHER: List[str] = [
    "ROBOT_VACUUMING",
    "MICROCHIP_TRIANGLE",
    "TRANSLATOR_ASTRO_BLACK",
    "GALAXY_SOUNDS_BLACK_HOLES",
    "SLEEP_POD_NYLON",
    "SLEEP_POD_POLYESTER",
    SLP_COT,
    "OXYGEN_SHAKE_GARLIC",
]


ALL_PRODUCTS: List[str] = SNACKPACK + PEBBLES + MR_OTHER

CORR_PRODUCTS: List[str] = SNACKPACK + PEBBLES + [SLP_COT, "SLEEP_POD_POLYESTER"]


# ─── Pairs (a, b, weight, unit, ent_z, ext_z) ─────────────────────────────
PAIRS: List[Tuple[str, str, float, int, float, float]] = [
    # SNACKPACK basket — unchanged from 555509
    (CHOC, VAN,   -1.0,  5, 2.0, 0.5),
    (PIST, RASP,  -1.0,  5, 2.0, 0.5),
    (PIST, STRAW, +1.0,  5, 2.0, 0.5),
    (RASP, STRAW, -1.0,  5, 2.0, 0.5),
    # PEBBLES — 555509's star around XL (kept; pairs side was better)
    (PEB_L,  PEB_XL, -1.0,  2, 1.0, 0.5),
    (PEB_M,  PEB_XL, -1.0,  2, 1.0, 0.5),
    (PEB_S,  PEB_XL, -1.0,  2, 1.0, 0.5),
    (PEB_XS, PEB_XL, -1.0,  2, 1.0, 0.5),
    # SLEEP_POD slp_cp — unchanged from 555509
    (SLP_COT, "SLEEP_POD_POLYESTER", -0.795, 5, 1.6, 0.5),
]


# ─── Paramètres communs ───────────────────────────────────────────────────
WINDOW    = 200
MIN_HIST  = 50
MAX_POS   = 10
PASSIVE_OFFSET = 1

# ─── Paramètres MM spécifiques par produit ────────────────────────────────
PEB_MM = {"INV_SKEW": 2.0, "MR_SKEW": 1.0, "Z_TOXIC": 2.0, "BASE_QTY": 5}

PRODUCT_PARAMS = {
    "ROBOT_VACUUMING":           {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "MICROCHIP_TRIANGLE":        {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "TRANSLATOR_ASTRO_BLACK":    {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "GALAXY_SOUNDS_DARK_MATTER": {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "GALAXY_SOUNDS_BLACK_HOLES": {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "SLEEP_POD_NYLON":           {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "SLEEP_POD_POLYESTER":       {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "SLEEP_POD_COTTON":          {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "OXYGEN_SHAKE_GARLIC":       {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    # v8: PEBBLES tighter MM (556852 params)
    PEB_L:  PEB_MM,
    PEB_XS: PEB_MM,
    PEB_S:  PEB_MM,
    PEB_M:  PEB_MM,
    PEB_XL: PEB_MM,
}

DEFAULT_MM_PARAMS = {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10}


OBI_PRODUCTS: dict[str, float] = {
    "GALAXY_SOUNDS_DARK_MATTER":  +0.052,
    "GALAXY_SOUNDS_BLACK_HOLES":  +0.059,
    "OXYGEN_SHAKE_GARLIC":        +0.066,
}
OBI_GAIN: float = 4.0
INV_TAPER_START: float = 0.9


FAMILLE = ["MICROCHIP_TRIANGLE", "SLEEP_POD_NYLON", "SLEEP_POD_COTTON", "OXYGEN_SHAKE_GARLIC"]

# ─── Trader ───────────────────────────────────────────────────────────────
class Trader:
    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0
        td = json.loads(state.traderData) if state.traderData else {}

        mids_hist:    Dict[str, List[float]] = td.get("mids",       {})
        prices_hist:  Dict[str, List[float]] = td.get("prices",     {})
        pair_state:   Dict[str, int]         = td.get("pair_state", {})

        def _flush():
            td["mids"]       = mids_hist
            td["prices"]     = prices_hist
            td["pair_state"] = pair_state
            s = json.dumps(td)
            logger.flush(state, result, conversions, s)
            return result, conversions, s

        # ── 1) Snapshot books ──
        bb: Dict[str, int] = {}
        ba: Dict[str, int] = {}
        mids: Dict[str, float] = {}
        for sym in ALL_PRODUCTS:
            if sym not in state.order_depths:
                continue
            od = state.order_depths[sym]
            if not od.buy_orders or not od.sell_orders:
                continue
            bid = max(od.buy_orders.keys())
            ask = min(od.sell_orders.keys())
            bb[sym] = bid
            ba[sym] = ask
            mids[sym] = (bid + ask) / 2.0

        # ── 2) Update rolling histories ──
        for sym, m in mids.items():
            if sym in CORR_PRODUCTS:
                hist = mids_hist.get(sym, [])
                hist.append(m)
                if len(hist) > WINDOW:
                    hist = hist[-WINDOW:]
                mids_hist[sym] = hist
            hp = prices_hist.get(sym, [])
            hp.append(math.log(m))
            if len(hp) > WINDOW:
                hp = hp[-WINDOW:]
            prices_hist[sym] = hp

        # ── 3) ALPHA CORR ───
        target_corr: Dict[str, int] = {p: 0 for p in CORR_PRODUCTS}
        diag_corr: List[str] = []

        for a, b, weight, unit, ent, ext in PAIRS:
            key = f"{a}|{b}"
            st  = pair_state.get(key, 0)

            ha = mids_hist.get(a, [])
            hb = mids_hist.get(b, [])
            n = min(len(ha), len(hb))
            if n < MIN_HIST or a not in mids or b not in mids:
                continue
            ha = ha[-n:]; hb = hb[-n:]
            spread_hist = [ha[i] + weight * hb[i] for i in range(n)]
            mu = sum(spread_hist) / n
            var = sum((x - mu) ** 2 for x in spread_hist) / max(n - 1, 1)
            std = var ** 0.5
            if std <= 0.0:
                continue

            spread_now = mids[a] + weight * mids[b]
            z = (spread_now - mu) / std

            if st == 0:
                if z <= -ent:    st = +1
                elif z >= +ent:  st = -1
            elif st == +1:
                if z >= -ext:    st = 0
            elif st == -1:
                if z <= +ext:    st = 0

            pair_state[key] = st

            if st != 0:
                target_corr[a] = target_corr.get(a, 0) + st * unit
                target_corr[b] = target_corr.get(b, 0) + int(round(st * weight * unit))
                diag_corr.append(f"{a.split('_')[-1]}/{b.split('_')[-1]}(w={weight:+.2f}) z={z:+.2f} st={st:+d}")

        for p in CORR_PRODUCTS:
            target_corr[p] = max(-MAX_POS, min(MAX_POS, target_corr[p]))

        # ── 4) MM ──
        for sym in ALL_PRODUCTS:
            if sym not in mids:
                continue
            if sym in PRODUCT_PARAMS:
                INV_SKEW = PRODUCT_PARAMS[sym]["INV_SKEW"]
                MR_SKEW  = PRODUCT_PARAMS[sym]["MR_SKEW"]
                Z_TOXIC  = PRODUCT_PARAMS[sym]["Z_TOXIC"]
                BASE_QTY = PRODUCT_PARAMS[sym]["BASE_QTY"]
            else:
                INV_SKEW = DEFAULT_MM_PARAMS["INV_SKEW"]
                MR_SKEW  = DEFAULT_MM_PARAMS["MR_SKEW"]
                Z_TOXIC  = DEFAULT_MM_PARAMS["Z_TOXIC"]
                BASE_QTY = DEFAULT_MM_PARAMS["BASE_QTY"]
            hist = prices_hist.get(sym, [])
            if len(hist) < MIN_HIST:
                continue

            n = len(hist)
            mu = sum(hist) / n
            var = sum((x - mu) ** 2 for x in hist) / max(n - 1, 1)
            std = var ** 0.5
            if std <= 0.0:
                continue

            mid = mids[sym]
            log_mid = math.log(mid)
            mu_px    = math.exp(mu)
            sigma_px = mid * std
            z        = (log_mid - mu) / std
            pos = state.position.get(sym, 0)

            tc = target_corr.get(sym, 0)
            inv_off = int(round(INV_SKEW * (pos - tc) / MAX_POS))
            mr_bias = int(round(MR_SKEW * (mu_px - mid) / max(sigma_px, 1)))

            obi_shift = 0
            if sym in OBI_PRODUCTS:
                od_sym = state.order_depths[sym]
                bsz = od_sym.buy_orders.get(bb[sym], 0)
                asz = -od_sym.sell_orders.get(ba[sym], 0)
                tot = bsz + asz
                obi = (bsz - asz) / tot if tot > 0 else 0.0
                obi_shift = int(round(OBI_GAIN * obi))

            bid_px = bb[sym] + 1 - inv_off + mr_bias + obi_shift
            ask_px = ba[sym] - 1 - inv_off + mr_bias + obi_shift
            bid_px = min(bid_px, ba[sym] - 1)
            ask_px = max(ask_px, bb[sym] + 1)
            if bid_px >= ask_px:
                continue

            cap_bid = max(0, MAX_POS - pos)
            cap_ask = max(0, MAX_POS + pos)
            qty_bid = min(BASE_QTY, cap_bid)
            qty_ask = min(BASE_QTY, cap_ask)
            if z >= Z_TOXIC:
                qty_bid = 0
            elif z <= -Z_TOXIC:
                qty_ask = 0

            if sym in FAMILLE:
                inv_frac = abs(pos) / MAX_POS
                if inv_frac > INV_TAPER_START:
                    taper = (inv_frac - INV_TAPER_START) / (1.0 - INV_TAPER_START)
                    taper = min(taper, 1.0)
                    if pos > 0:
                        qty_bid = int(round(qty_bid * (1.0 - taper)))
                    elif pos < 0:
                        qty_ask = int(round(qty_ask * (1.0 - taper)))

            orders: List[Order] = []
            if qty_bid > 0:
                orders.append(Order(sym, bid_px, qty_bid))
            if qty_ask > 0:
                orders.append(Order(sym, ask_px, -qty_ask))
            if orders:
                result[sym] = orders

        if diag_corr:
            logger.print("CORR " + " | ".join(diag_corr))

        return _flush()
