"""
Stratégie combinée — priorité MM, alpha_corr biaise l'inventaire :
  1. MARKET MAKING (priorité) — quote en continu top-of-book sur tous les
     produits MR + extension PEBBLES pour exécuter le signal corr. Capture
     le spread.
  2. ALPHA CORR (overlay) sur deux baskets :
        - SNACKPACK : 4 paires |ρ_returns| ≥ 0.8 (CHOC/VAN, PIST/RASP,
          PIST/STRAW, RASP/STRAW)
        - PEBBLES   : 5 paires sur log-price corr (S/XL, S/XS, XS/M,
          XL/XS, M/S)
     target_corr injecté comme offset d'inventaire :

         inv_off = INV_SKEW * (pos - target_corr) / MAX_POS

     Effet : quand corr veut pos = +6, le skew traite le book comme s'il
     était short de 6 → quotes décalées vers le haut → on accumule long.
     Pas de cross, pas d'override.

Univers :
  - SNACKPACK : CHOC, VAN, PIST, RASP, STRAW (MR + corr)
  - PEBBLES   : XS, S, M, XL (S est MR ; XS/M/XL RW mais MM pour exec corr)
  - Autres MR : ROBOT_DISHES, ROBOT_VACUUMING, MICROCHIP_TRIANGLE

État conservé dans traderData :
  - mids[sym]           : deque des derniers WINDOW mids (pour alpha_corr)
  - prices[sym]         : deque des derniers WINDOW log-mids (pour MM)
  - pair_state[a|b]     : -1 / 0 / +1 par pair
"""
from datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Observation, Trade, ProsperityEncoder
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

PEB_XS = "PEBBLES_XS"
PEB_S  = "PEBBLES_S"
PEB_M  = "PEBBLES_M"
PEB_XL = "PEBBLES_XL"

PEBBLES: List[str] = [PEB_XS, PEB_S, PEB_M, PEB_XL]

# Produits MR autres (Hurst<0.35 sur log-ret trade price, hors SNACKPACK/PEBBLES_S).
# on enlève ROBOT_DISHES : problématique.

MR_OTHER: List[str] = [
    "ROBOT_VACUUMING",
    "MICROCHIP_TRIANGLE",
]

# Univers global pour MM (corr a une surface d'exécution sur tous ceux-ci).
ALL_PRODUCTS: List[str] = SNACKPACK + PEBBLES + MR_OTHER

# Produits sur lesquels alpha_corr peut placer un target.
CORR_PRODUCTS: List[str] = SNACKPACK + PEBBLES


# ─── Pairs (a, b, sign, unit) ─────────────────────────────────────────────
# SNACKPACK : unit unifié = UNIT_SP (placeholder 0 → résolu plus bas).
# PEBBLES   : unit pondéré par |vol_corr| trade w=250 (cf alpha_corr_pebble).
PAIRS: List[Tuple[str, str, int, int]] = [
    # SNACKPACK : ρ_returns ≥ 0.8 (unit=UNIT_SP via placeholder 0)
    (CHOC, VAN,   -1, 2),    # ρ_ret = -0.92
    (PIST, RASP,  -1, 2),    # ρ_ret = -0.83
    (PIST, STRAW, +1, 3),    # ρ_ret = +0.91
    (RASP, STRAW, -1, 3),    # ρ_ret = -0.92
    # PEBBLES : log-price corr (vol-weighting per-pair testée mais
    # n'améliore pas combined → uniform UNIT=2)
    (PEB_S,  PEB_XL, -1, 2),
    (PEB_S,  PEB_XS, +1, 2),
    (PEB_XS, PEB_M,  -1, 2),
    (PEB_XL, PEB_XS, -1, 2),
    (PEB_M,  PEB_S,  -1, 2),
]



# ─── Paramètres communs ───────────────────────────────────────────────────
WINDOW    = 200
MIN_HIST  = 50
MAX_POS   = 10
PASSIVE_OFFSET = 1


# ─── Paramètres alpha corr (split par basket) ─────────────────────────────
# SNACKPACK (paires |ρ_returns| ≥ 0.8)
ENTER_Z_SP = 2.0
EXIT_Z_SP  = 0.5
UNIT_SP    = 3       # appliqué aux pairs avec unit=0 (placeholder)

ENTER_Z_PEB = 1.0
EXIT_Z_PEB  = 0.5
# (unit par-pair, défini directement dans PAIRS)


# ─── Paramètres MM fallback ───────────────────────────────────────────────
INV_SKEW  = 2.0
MR_SKEW   = 1.0
Z_TOXIC   = 2.0
BASE_QTY  = 5


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

        for a, b, sign, unit_pair in PAIRS:
            key = f"{a}|{b}"
            st  = pair_state.get(key, 0)

            # Sélection params selon basket (SNACKPACK vs PEBBLES) ;
            # unit = unit_pair si non-zéro (PEBBLES per-pair), sinon UNIT_SP.
            if a in PEBBLES or b in PEBBLES:
                ent, ext = ENTER_Z_PEB, EXIT_Z_PEB
                unit = unit_pair
            else:
                ent, ext = ENTER_Z_SP, EXIT_Z_SP
                unit = unit_pair if unit_pair > 0 else UNIT_SP

            ha = mids_hist.get(a, [])
            hb = mids_hist.get(b, [])
            n = min(len(ha), len(hb))
            if n < MIN_HIST or a not in mids or b not in mids:
                continue
            ha = ha[-n:]; hb = hb[-n:]
            spread_hist = [ha[i] + sign * hb[i] for i in range(n)]
            mu = sum(spread_hist) / n
            var = sum((x - mu) ** 2 for x in spread_hist) / max(n - 1, 1)
            std = var ** 0.5
            if std <= 0.0:
                continue

            spread_now = mids[a] + sign * mids[b]
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
                target_corr[a] += st * unit
                target_corr[b] += st * sign * unit
                diag_corr.append(f"{a.split('_')[-1]}/{b.split('_')[-1]}(s={sign:+d}) z={z:+.2f} st={st:+d}")

        # Clip target_corr aux limites
        for p in CORR_PRODUCTS:
            target_corr[p] = max(-MAX_POS, min(MAX_POS, target_corr[p]))

        # ── 4) MM sur tous les produits, biais corr sur SNACKPACK + PEBBLES ──
        for sym in ALL_PRODUCTS:
            if sym not in mids:
                continue
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

            bid_px = bb[sym] + 1 - inv_off + mr_bias
            ask_px = ba[sym] - 1 - inv_off + mr_bias
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