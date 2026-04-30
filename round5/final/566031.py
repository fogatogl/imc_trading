"""
Round 5 — stratégie fusionnée.

Sections (ordre d'exécution, en cas de conflit la dernière écrase) :
  1. mr_bien       — MM mean-reversion + pair overlay pour MR_OTHER.
  2. simple_mm     — MM passif qty=1 pour produits divers.
  3. galaxy_oracle — Oracles de cointégration pour famille GALAXY.
  4. uv_mm         — MM passif full-capacity pour famille UV_VISOR.
  5. robot_oracle  — Oracles de cointégration pour famille ROBOT.

Conflits résolus par last-write-wins (oracle > simple MM) :
  ROBOT_VACUUMING         : mr_bien  → robot_oracle
  ROBOT_IRONING/LAUNDRY/MOPPING : simple_mm → robot_oracle
  GALAXY_SOUNDS_SOLAR_FLAMES    : simple_mm → galaxy_oracle
  UV_VISOR_ORANGE               : simple_mm → uv_mm
"""
try:
    from datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Observation, Trade, ProsperityEncoder
except ImportError:
    from prosperity4bt.datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Observation, Trade, ProsperityEncoder
from typing import List, Dict, Tuple, Any
import json
import math


# ─── Logger (compatible visualizer kevin-fu1) ─────────────────────────────────
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


# ═══════════════════════════════════════════════════════════════════════════════
#  Constantes mr_bien
# ═══════════════════════════════════════════════════════════════════════════════
CHOC  = "SNACKPACK_CHOCOLATE"
VAN   = "SNACKPACK_VANILLA"
PIST  = "SNACKPACK_PISTACHIO"
RASP  = "SNACKPACK_RASPBERRY"
STRAW = "SNACKPACK_STRAWBERRY"

SNACKPACK: List[str] = []

PEB_L  = "PEBBLES_L"
PEB_XS = "PEBBLES_XS"
PEB_S  = "PEBBLES_S"
PEB_M  = "PEBBLES_M"
PEB_XL = "PEBBLES_XL"

PEBBLES: List[str] = []

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

PAIRS: List[Tuple[str, str, float, int, float, float]] = [
    (CHOC, VAN,   -1.0, 5, 2.0, 0.5),
    (PIST, RASP,  -1.0, 5, 2.0, 0.5),
    (PIST, STRAW, +1.0, 5, 2.0, 0.5),
    (RASP, STRAW, -1.0, 5, 2.0, 0.5),
    (PEB_L,  PEB_XL, -1.0, 2, 1.0, 0.5),
    (PEB_M,  PEB_XL, -1.0, 2, 1.0, 0.5),
    (PEB_S,  PEB_XL, -1.0, 2, 1.0, 0.5),
    (PEB_XS, PEB_XL, -1.0, 2, 1.0, 0.5),
    (SLP_COT, "SLEEP_POD_POLYESTER", -0.795,  5, 1.6, 0.5),
    ("SLEEP_POD_SUEDE", "SLEEP_POD_POLYESTER", -0.9337, 5, 1.6, 0.5),
]

WINDOW         = 200
MIN_HIST       = 50
MAX_POS        = 10
PASSIVE_OFFSET = 1

PRODUCT_PARAMS = {
    "ROBOT_VACUUMING":           {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "MICROCHIP_TRIANGLE":        {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "TRANSLATOR_ASTRO_BLACK":    {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "GALAXY_SOUNDS_DARK_MATTER": {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "GALAXY_SOUNDS_BLACK_HOLES": {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "SLEEP_POD_NYLON":           {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "SLEEP_POD_POLYESTER":       {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "SLEEP_POD_COTTON":          {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "SLEEP_POD_SUEDE":           {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "OXYGEN_SHAKE_GARLIC":       {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
}

DEFAULT_MM_PARAMS = {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10}

OBI_PRODUCTS: dict[str, float] = {
    "GALAXY_SOUNDS_DARK_MATTER": +0.052,
    "GALAXY_SOUNDS_BLACK_HOLES": +0.059,
    "OXYGEN_SHAKE_GARLIC":       +0.066,
}
OBI_GAIN: float        = 4.0
INV_TAPER_START: float = 0.9

FAMILLE = ["MICROCHIP_TRIANGLE", "SLEEP_POD_NYLON", "SLEEP_POD_COTTON", "OXYGEN_SHAKE_GARLIC", "SLEEP_POD_SUEDE"]


# ═══════════════════════════════════════════════════════════════════════════════
#  Trader
# ═══════════════════════════════════════════════════════════════════════════════
class Trader:
    def __init__(self):
        # ── Galaxy oracles (Galaxy_strat.py) ──────────────────────────────────
        self.galaxy_oracles = {
            "GALAXY_SOUNDS_SOLAR_FLAMES": {
                "position_limit": 10,
                "spread_std": 350.0,
                "z_score_threshold": 2.0,
                "const": 14350.293324,
                "weights": {
                    "GALAXY_SOUNDS_DARK_MATTER":    -0.060498,
                    "GALAXY_SOUNDS_PLANETARY_RINGS": 0.022509,
                    "GALAXY_SOUNDS_BLACK_HOLES":     0.022528,
                    "GALAXY_SOUNDS_SOLAR_WINDS":    -0.300809,
                },
            },
            "GALAXY_SOUNDS_DARK_MATTER": {
                "position_limit": 10,
                "spread_std": 200.0,
                "z_score_threshold": 2.0,
                "const": 8960.332147,
                "weights": {
                    "GALAXY_SOUNDS_SOLAR_FLAMES":    -0.029807,
                    "GALAXY_SOUNDS_PLANETARY_RINGS":  0.190165,
                    "GALAXY_SOUNDS_BLACK_HOLES":     -0.006149,
                    "GALAXY_SOUNDS_SOLAR_WINDS":     -0.036404,
                },
            },
        }

        # ── Robot oracles (robot_trader.py) ───────────────────────────────────
        self.robot_oracles = {
            "ROBOT_IRONING": {
                "position_limit": 10,
                "spread_std": 300.0,
                "z_score_threshold": 2.0,
                "const": 18545.658913,
                "weights": {
                    "ROBOT_VACUUMING": 0.121331,
                    "ROBOT_MOPPING":  -0.603526,
                    "ROBOT_DISHES":   -0.440273,
                    "ROBOT_IRONING":   0.015652,
                },
            },
            "ROBOT_VACUUMING": {
                "position_limit": 10,
                "spread_std": 230.0,
                "z_score_threshold": 2.0,
                "const": 13467.059215,
                "weights": {
                    "ROBOT_MOPPING":  -0.317054,
                    "ROBOT_DISHES":   -0.287002,
                    "ROBOT_LAUNDRY":   0.162072,
                    "ROBOT_IRONING":   0.057734,
                },
            },
            "ROBOT_MOPPING": {
                "position_limit": 10,
                "spread_std": 300.0,
                "z_score_threshold": 2.0,
                "const": 30082.601346,
                "weights": {
                    "ROBOT_VACUUMING": -0.600280,
                    "ROBOT_DISHES":    -0.545890,
                    "ROBOT_LAUNDRY":   -0.333884,
                    "ROBOT_IRONING":   -0.543718,
                },
            },
            "ROBOT_DISHES": {
                "position_limit": 10,
                "spread_std": 270.0,
                "z_score_threshold": 2.0,
                "const": 26351.856113,
                "weights": {
                    "ROBOT_VACUUMING": -0.447985,
                    "ROBOT_MOPPING":   -0.450052,
                    "ROBOT_LAUNDRY":   -0.446494,
                    "ROBOT_IRONING":   -0.327007,
                },
            },
            "ROBOT_LAUNDRY": {
                "position_limit": 10,
                "spread_std": 300.0,
                "z_score_threshold": 2.0,
                "const": 14981.250452,
                "weights": {
                    "ROBOT_VACUUMING":  0.255456,
                    "ROBOT_MOPPING":   -0.277961,
                    "ROBOT_DISHES":    -0.450866,
                    "ROBOT_IRONING":    0.011739,
                },
            },
        }

        # ── Simple MM (market_making_simple.py) ───────────────────────────────
        self.simple_mm_products = [
            "UV_VISOR_ORANGE",             # overwritten by uv_mm
            "GALAXY_SOUNDS_SOLAR_FLAMES",  # overwritten by galaxy_oracle
            "OXYGEN_SHAKE_CHOCOLATE",
            "OXYGEN_SHAKE_EVENING_BREATH",
            "ROBOT_IRONING",               # overwritten by robot_oracle
            "ROBOT_LAUNDRY",               # overwritten by robot_oracle
            "ROBOT_MOPPING",               # overwritten by robot_oracle
            "MICROCHIP_CIRCLE",
            "TRANSLATOR_VOID_BLUE",
            "TRANSLATOR_GRAPHITE_MIST",
        ]
        self.simple_mm_qty       = 1
        self.simple_mm_pos_limit = 10

        # ── UV MM (MM_UV_sans_AMBER.py) ───────────────────────────────────────
        self.uv_products  = ["UV_VISOR_YELLOW", "UV_VISOR_ORANGE", "UV_VISOR_RED", "UV_VISOR_MAGENTA"]
        self.uv_pos_limit = 10

    # ─────────────────────────────────────────────────────────────────────────
    def _run_oracle(self, oracles: dict, mids: Dict[str, float],
                    bb: Dict[str, int], ba: Dict[str, int],
                    state: TradingState, result: Dict[Symbol, List[Order]]) -> None:
        for target, cfg in oracles.items():
            if target not in mids:
                continue
            if any(s not in mids for s in cfg["weights"]):
                continue
            fair = cfg["const"] + sum(w * mids[s] for s, w in cfg["weights"].items())
            z    = (fair - mids[target]) / cfg["spread_std"]
            pos  = state.position.get(target, 0)
            bid_t, ask_t   = bb[target], ba[target]
            mkt_spread     = ask_t - bid_t
            buy_qty        = cfg["position_limit"] - pos
            sell_qty       = cfg["position_limit"] + pos
            orders: List[Order] = []
            if z > cfg["z_score_threshold"] and buy_qty > 0:
                orders.append(Order(target, ask_t, buy_qty))
            elif z < -cfg["z_score_threshold"] and sell_qty > 0:
                orders.append(Order(target, bid_t, -sell_qty))
            else:
                dyn  = max(1.0, mkt_spread / 2.0)
                skew = -pos * dyn * 0.15
                my_bid = min(int(math.floor(fair - dyn + skew)), ask_t - 1)
                my_ask = max(int(math.ceil(fair  + dyn + skew)), bid_t + 1)
                if buy_qty  > 0: orders.append(Order(target, my_bid,  buy_qty))
                if sell_qty > 0: orders.append(Order(target, my_ask, -sell_qty))
            if orders:
                result[target] = orders

    # ─────────────────────────────────────────────────────────────────────────
    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result:      Dict[Symbol, List[Order]] = {}
        conversions = 0
        td = json.loads(state.traderData) if state.traderData else {}

        mids_hist:  Dict[str, List[float]] = td.get("mids",       {})
        prices_hist: Dict[str, List[float]] = td.get("prices",    {})
        pair_state:  Dict[str, int]         = td.get("pair_state", {})

        # ── Snapshot global de tous les carnets ──────────────────────────────
        bb:   Dict[str, int]   = {}
        ba:   Dict[str, int]   = {}
        mids: Dict[str, float] = {}
        for sym, od in state.order_depths.items():
            if od.buy_orders and od.sell_orders:
                bid       = max(od.buy_orders.keys())
                ask       = min(od.sell_orders.keys())
                bb[sym]   = bid
                ba[sym]   = ask
                mids[sym] = (bid + ask) / 2.0

        # ══════════════════════════════════════════════════════════════════════
        #  Section 1 : mr_bien — Rolling histories + Alpha corr + MM
        # ══════════════════════════════════════════════════════════════════════

        for sym, m in mids.items():
            if sym in CORR_PRODUCTS:
                hist = mids_hist.get(sym, [])
                hist.append(m)
                if len(hist) > WINDOW:
                    hist = hist[-WINDOW:]
                mids_hist[sym] = hist
            if sym in ALL_PRODUCTS:
                hp = prices_hist.get(sym, [])
                hp.append(math.log(m))
                if len(hp) > WINDOW:
                    hp = hp[-WINDOW:]
                prices_hist[sym] = hp

        target_corr: Dict[str, int] = {p: 0 for p in CORR_PRODUCTS}
        diag_corr:   List[str]      = []

        for a, b, weight, unit, ent, ext in PAIRS:
            key = f"{a}|{b}"
            st  = pair_state.get(key, 0)
            ha  = mids_hist.get(a, [])
            hb  = mids_hist.get(b, [])
            n   = min(len(ha), len(hb))
            if n < MIN_HIST or a not in mids or b not in mids:
                continue
            ha = ha[-n:]; hb = hb[-n:]
            spread_hist = [ha[i] + weight * hb[i] for i in range(n)]
            mu  = sum(spread_hist) / n
            var = sum((x - mu) ** 2 for x in spread_hist) / max(n - 1, 1)
            std = var ** 0.5
            if std <= 0.0:
                continue
            z = (mids[a] + weight * mids[b] - mu) / std
            if st == 0:
                if z <= -ent:   st = +1
                elif z >= +ent: st = -1
            elif st == +1:
                if z >= -ext:   st = 0
            elif st == -1:
                if z <= +ext:   st = 0
            pair_state[key] = st
            if st != 0:
                target_corr[a] = target_corr.get(a, 0) + st * unit
                target_corr[b] = target_corr.get(b, 0) + int(round(st * weight * unit))
                diag_corr.append(f"{a.split('_')[-1]}/{b.split('_')[-1]}(w={weight:+.2f}) z={z:+.2f} st={st:+d}")

        for p in CORR_PRODUCTS:
            target_corr[p] = max(-MAX_POS, min(MAX_POS, target_corr[p]))

        for sym in ALL_PRODUCTS:
            if sym not in mids:
                continue
            p = PRODUCT_PARAMS.get(sym, DEFAULT_MM_PARAMS)
            INV_SKEW = p["INV_SKEW"]; MR_SKEW = p["MR_SKEW"]
            Z_TOXIC  = p["Z_TOXIC"];  BASE_QTY = p["BASE_QTY"]

            hist = prices_hist.get(sym, [])
            if len(hist) < MIN_HIST:
                continue
            n   = len(hist)
            mu  = sum(hist) / n
            var = sum((x - mu) ** 2 for x in hist) / max(n - 1, 1)
            std = var ** 0.5
            if std <= 0.0:
                continue

            mid      = mids[sym]
            mu_px    = math.exp(mu)
            sigma_px = mid * std
            z        = (math.log(mid) - mu) / std
            pos      = state.position.get(sym, 0)
            tc       = target_corr.get(sym, 0)
            inv_off  = int(round(INV_SKEW * (pos - tc) / MAX_POS))
            mr_bias  = int(round(MR_SKEW  * (mu_px - mid) / max(sigma_px, 1)))

            obi_shift = 0
            if sym in OBI_PRODUCTS:
                od_sym = state.order_depths[sym]
                bsz    = od_sym.buy_orders.get(bb[sym], 0)
                asz    = -od_sym.sell_orders.get(ba[sym], 0)
                tot    = bsz + asz
                obi    = (bsz - asz) / tot if tot > 0 else 0.0
                obi_shift = int(round(OBI_GAIN * obi))

            bid_px = min(bb[sym] + 1 - inv_off + mr_bias + obi_shift, ba[sym] - 1)
            ask_px = max(ba[sym] - 1 - inv_off + mr_bias + obi_shift, bb[sym] + 1)
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
                    taper = min((inv_frac - INV_TAPER_START) / (1.0 - INV_TAPER_START), 1.0)
                    if pos > 0:
                        qty_bid = int(round(qty_bid * (1.0 - taper)))
                    elif pos < 0:
                        qty_ask = int(round(qty_ask * (1.0 - taper)))

            orders: List[Order] = []
            if qty_bid > 0: orders.append(Order(sym, bid_px,  qty_bid))
            if qty_ask > 0: orders.append(Order(sym, ask_px, -qty_ask))
            if orders:
                result[sym] = orders

        if diag_corr:
            logger.print("CORR " + " | ".join(diag_corr))

        # ══════════════════════════════════════════════════════════════════════
        #  Section 2 : simple_mm — MM passif qty=1 pour produits divers
        # ══════════════════════════════════════════════════════════════════════
        for product in self.simple_mm_products:
            if product not in state.order_depths:
                continue
            od  = state.order_depths[product]
            pos = state.position.get(product, 0)
            if not od.buy_orders or not od.sell_orders:
                continue
            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys())
            my_bid   = best_bid + 1
            my_ask   = best_ask - 1
            if my_bid >= my_ask:
                continue
            orders = []
            if pos < self.simple_mm_pos_limit:
                orders.append(Order(product, my_bid,  self.simple_mm_qty))
            if pos > -self.simple_mm_pos_limit:
                orders.append(Order(product, my_ask, -self.simple_mm_qty))
            if orders:
                result[product] = orders

        # ══════════════════════════════════════════════════════════════════════
        #  Section 3 : galaxy_oracle — Oracles de cointégration GALAXY
        # ══════════════════════════════════════════════════════════════════════
        self._run_oracle(self.galaxy_oracles, mids, bb, ba, state, result)

        # ══════════════════════════════════════════════════════════════════════
        #  Section 4 : uv_mm — MM passif full-capacity UV_VISOR
        # ══════════════════════════════════════════════════════════════════════
        for product in self.uv_products:
            if product not in state.order_depths:
                continue
            od  = state.order_depths[product]
            pos = state.position.get(product, 0)
            if not od.buy_orders or not od.sell_orders:
                continue
            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys())
            if best_ask - best_bid < 2:
                continue
            buy_cap  = self.uv_pos_limit - pos
            sell_cap = self.uv_pos_limit + pos
            orders   = []
            if buy_cap  > 0: orders.append(Order(product, best_bid + 1,  buy_cap))
            if sell_cap > 0: orders.append(Order(product, best_ask - 1, -sell_cap))
            if orders:
                result[product] = orders

        # ══════════════════════════════════════════════════════════════════════
        #  Section 5 : robot_oracle — Oracles de cointégration ROBOT
        # ══════════════════════════════════════════════════════════════════════
        self._run_oracle(self.robot_oracles, mids, bb, ba, state, result)

        # ── Flush & return ────────────────────────────────────────────────────
        td["mids"]       = mids_hist
        td["prices"]     = prices_hist
        td["pair_state"] = pair_state
        s = json.dumps(td)
        logger.flush(state, result, conversions, s)
        return result, conversions, s