"""
Multi-product MM (round 5) — v5. mr_tune base + v4 OBI graft + pairs_v2 grafts.

3-day BT: D2 34,481 / D3 74,006 / D4 143,452 → 251,939 (Rust 251,939, agree).
mr_tune base: 222,332. Δ = +29,607 (+13.3%). Live expectation per
[feedback_bt_inflation_round5_mm](feedback_bt_inflation_round5_mm.md): ~25k.

D4 attribution vs mr_tune (the dominant gain):
  - SLEEP_POD_COTTON (new, MM + slp_cp pair):       +11,990
  - PEBBLES_XL (4-pair star topology vs 1-pair):    + 6,629
  - PEBBLES_L (new, MM + peb_lx pair):              + 5,180
  - PEBBLES_M (peb_mx pair direct vs indirect):     + 4,360
  - SLEEP_POD_POLYESTER (slp_cp hedge):             + 1,871
  - PEBBLES_XS / PEBBLES_S (star drops 2 indirect): −2,468

Composition of "best of three":

  Base (mr_tune.py, +13k live):
    - Quote always inside touch (bid+1 / ask-1).
    - Fair anchor = rolling mean of log-mid, pulled to mean via mr_bias.
    - Pair-corr overlay biases inventory target via target_corr (no cross).
    - Z-toxic gate: freeze one side when |z| > Z_TOXIC (adaptive σ).
    - Per-product (INV_SKEW, MR_SKEW, Z_TOXIC, BASE_QTY).

  v4 grafts kept (only the BT-neutral / structurally-defensible ones):
    - OBI follow on 3 high-IC MR_OTHER (no pair-corr conflict):
      DARK_MATTER (+0.052), BLACK_HOLES (+0.059), GARLIC (+0.066).
      All FDR-significant, |IC| > 0.05.
    - Inventory taper at 0.9: fires only near |pos|=9-10. Safety net.

  v4 grafts REJECTED (BT regression):
    - OBI on SNACKPACK: −9,000 BT. Conflicts with SNACKPACK pair-corr.
    - Inventory taper at 0.5/0.8: fights pair-corr targets.
    - Dynamic K_VOL spread: widens during vol spikes, drops fills.
    - Asymmetric size tilt + per-IC OBI gain scaling: BT-tuned.

  pairs_v2 grafts (the +29k lift):
    - PEBBLES star topology around XL (4 pairs L/XL, M/XL, S/XL, XS/XL).
      Replaces v5's 5-pair config. Universe extends to include PEBBLES_L.
    - SLEEP_POD slp_cp pair (COTTON / POLYESTER, β-fitted weight=-0.795).
      Per pairs_v2 §slp_cp: ±1 sign earned +83 vs the β-fitted +14,481 in
      pairs_v2's standalone test. Real-valued weight added to PAIRS schema.
    - SLEEP_POD_COTTON added to MM universe (was previously unquoted).

Universe = 20 products (5 SNACKPACK + 5 PEBBLES + 10 MR_OTHER incl. SLP_COT).
PAIRS = 9 (4 SNACKPACK + 4 PEBBLES star + 1 SLEEP_POD slp_cp).
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

#1129 de pnl sur snackpack


SNACKPACK: List[str] = []

PEB_L  = "PEBBLES_L"     # added for pairs_v2 star topology around XL
PEB_XS = "PEBBLES_XS"
PEB_S  = "PEBBLES_S"
PEB_M  = "PEBBLES_M"
PEB_XL = "PEBBLES_XL"

#4405 de pnl


PEBBLES: List[str] = []

SLP_COT = "SLEEP_POD_COTTON"     # added for pairs_v2 slp_cp pair

# 5904 de pnl 


# Produits MR autres (Hurst<0.35 sur log-ret trade price, hors SNACKPACK/PEBBLES_S).
# on enlève ROBOT_DISHES : problématique.

MR_OTHER: List[str] = [
    "ROBOT_VACUUMING", #-227 pnl
    "MICROCHIP_TRIANGLE", #2198 pnl
    "TRANSLATOR_ASTRO_BLACK", #-223
    "GALAXY_SOUNDS_BLACK_HOLES",  #2214 pnl
    "SLEEP_POD_NYLON", #87 pnl
    "SLEEP_POD_POLYESTER", #880 pnl
    SLP_COT,            # 5904 de pnl            # quoted as MM, also half of slp_cp pair
    "OXYGEN_SHAKE_GARLIC" #1749pnl
]


# Univers global pour MM (corr a une surface d'exécution sur tous ceux-ci).
ALL_PRODUCTS: List[str] = SNACKPACK + PEBBLES + MR_OTHER

# Produits sur lesquels alpha_corr peut placer un target.
# Includes SLP_COT + SLP_POL via slp_cp pair (SLEEP_POD level-corr only,
# β-fitted weight per pairs_v2 §slp_cp).
CORR_PRODUCTS: List[str] = SNACKPACK + PEBBLES + [SLP_COT, "SLEEP_POD_POLYESTER"]


# ─── Pairs (a, b, weight, unit, ent_z, ext_z) ─────────────────────────────
# weight: spread = mid_a + weight·mid_b. ±1.0 for return-corr pairs;
# real-valued (e.g. -0.795) for level-corr pairs (= -β_OLS hedge).
# unit:   contribution to per-symbol target_corr when state ≠ 0.
PAIRS: List[Tuple[str, str, float, int, float, float]] = [
    # SNACKPACK basket — strong return-corr (|ρ_r| 0.83-0.92), weight = sign(ρ_r), unit=5
    # ENTER_Z=2.0 (mr_tune original SNACKPACK threshold).
    (CHOC, VAN,   -1.0,  5, 2.0, 0.5),    # ρ_ret = -0.92
    (PIST, RASP,  -1.0,  5, 2.0, 0.5),    # ρ_ret = -0.83
    (PIST, STRAW, +1.0,  5, 2.0, 0.5),    # ρ_ret = +0.91
    (RASP, STRAW, -1.0,  5, 2.0, 0.5),    # ρ_ret = -0.92
    # PEBBLES — pairs_v2 star around XL (replaces v5's 5-pair config).
    # ENTER_Z=1.0 (mr_tune PEBBLES threshold).
    (PEB_L,  PEB_XL, -1.0,  2, 1.0, 0.5),
    (PEB_M,  PEB_XL, -1.0,  2, 1.0, 0.5),
    (PEB_S,  PEB_XL, -1.0,  2, 1.0, 0.5),
    (PEB_XS, PEB_XL, -1.0,  2, 1.0, 0.5),
    # SLEEP_POD slp_cp — level-corr only (ρ_ret≈0, ρ_mid=+0.88). Weight=-β_OLS=-0.795
    # so spread = COT - 0.795·POL (OLS residual). pairs_v2 ENTER_Z=1.6.
    (SLP_COT, "SLEEP_POD_POLYESTER", -0.795, 5, 1.6, 0.5),
]


# ─── Paramètres communs ───────────────────────────────────────────────────
WINDOW    = 200
MIN_HIST  = 50
MAX_POS   = 10
PASSIVE_OFFSET = 1

# ─── Paramètres MM spécifiques par produit ────────────────────────────────
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
}

# Paramètres MM par défaut (pour les autres produits comme SNACKPACK ou PEBBLES)
DEFAULT_MM_PARAMS = {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10}


# v5: OBI follow only on MR_OTHER products with high FDR-IC (no pair-corr conflict).
# Restricted to obi_l1 IC ≥ 0.05 (large-effect threshold). SNACKPACK and PEBBLES
# excluded — pair-corr overlay already biases their inventory.
OBI_PRODUCTS: dict[str, float] = {
    "GALAXY_SOUNDS_DARK_MATTER":  +0.052,
    "GALAXY_SOUNDS_BLACK_HOLES":  +0.059,
    "OXYGEN_SHAKE_GARLIC":        +0.066,
}
OBI_GAIN: float = 4.0              # constant, structural
INV_TAPER_START: float = 0.9       # near-limit safety net (rarely fires)


FAMILLE = ["MICROCHIP_TRIANGLE","SLEEP_POD_NYLON","SLEEP_POD_COTTON","OXYGEN_SHAKE_GARLIC"]

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
            # mids (raw) pour alpha_corr (SNACKPACK + PEBBLES)
            if sym in CORR_PRODUCTS:
                hist = mids_hist.get(sym, [])
                hist.append(m)
                if len(hist) > WINDOW:
                    hist = hist[-WINDOW:]
                mids_hist[sym] = hist
            # log-mid pour MM (tous les produits qu'on quote)
            hp = prices_hist.get(sym, [])
            hp.append(math.log(m))
            if len(hp) > WINDOW:
                hp = hp[-WINDOW:]
            prices_hist[sym] = hp

        # ── 3) ALPHA CORR : update pair states + target_corr (overlay) ───
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
                # Real-valued weight (β-fitted hedge for level-corr pairs).
                target_corr[b] = target_corr.get(b, 0) + int(round(st * weight * unit))
                diag_corr.append(f"{a.split('_')[-1]}/{b.split('_')[-1]}(w={weight:+.2f}) z={z:+.2f} st={st:+d}")

        # Clip target_corr aux limites
        for p in CORR_PRODUCTS:
            target_corr[p] = max(-MAX_POS, min(MAX_POS, target_corr[p]))

        # ── 4) MM sur tous les produits, biais corr sur SNACKPACK + PEBBLES ──
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
                MR_SKEW = DEFAULT_MM_PARAMS["MR_SKEW"]
                Z_TOXIC = DEFAULT_MM_PARAMS["Z_TOXIC"]
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

            # Overlay corr : pretend pos = pos - target_corr → MM dérive vers target
            tc = target_corr.get(sym, 0)
            inv_off = int(round(INV_SKEW * (pos - tc) / MAX_POS))
            mr_bias = int(round(MR_SKEW * (mu_px - mid) / max(sigma_px, 1)))

            # OBI follow on high-IC MR_OTHER products only (no pair-corr conflict).
            # IC sign is positive (follow) for these three — sign() not needed.
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

            # v5: inventory taper — shrink the side that worsens |pos| past the
            # taper threshold. Defensive layer on top of z-toxic.
            if sym in FAMILLE :
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