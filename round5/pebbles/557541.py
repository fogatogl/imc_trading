"""
PEBBLES-only — 556852 MM params (tight).

Isolation file: trades ONLY PEBBLES (5 products, 4-pair star around XL).
No SNACKPACK, no MR_OTHER, no SLEEP_POD. Lets PEB PnL be measured cleanly
without other-product noise.

MM params: BASE_QTY=5, INV_SKEW=2.0, MR_SKEW=1.0, Z_TOXIC=2.0 (556852).
Pair entry/exit: ENTER_Z=1.0, EXIT_Z=0.5, unit=2 per pair.

Compare against `strat_pebbles_only_555mm.py` (same scope, looser MM).
"""
try:
    from datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Observation, Trade, ProsperityEncoder
except ImportError:
    from prosperity4bt.datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Observation, Trade, ProsperityEncoder
from typing import List, Dict, Tuple, Any
import json
import math


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


PEB_L  = "PEBBLES_L"
PEB_XS = "PEBBLES_XS"
PEB_S  = "PEBBLES_S"
PEB_M  = "PEBBLES_M"
PEB_XL = "PEBBLES_XL"

PEBBLES: List[str] = [PEB_L, PEB_XS, PEB_S, PEB_M, PEB_XL]
ALL_PRODUCTS: List[str] = PEBBLES
CORR_PRODUCTS: List[str] = PEBBLES


PAIRS: List[Tuple[str, str, float, int, float, float]] = [
    (PEB_L,  PEB_XL, -1.0, 2, 1.0, 0.5),
    (PEB_M,  PEB_XL, -1.0, 2, 1.0, 0.5),
    (PEB_S,  PEB_XL, -1.0, 2, 1.0, 0.5),
    (PEB_XS, PEB_XL, -1.0, 2, 1.0, 0.5),
]


WINDOW    = 200
MIN_HIST  = 50
MAX_POS   = 10

# 556852 MM params (tight)
BASE_QTY = 5
INV_SKEW = 2.0
MR_SKEW  = 1.0
Z_TOXIC  = 2.0


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

        for sym, m in mids.items():
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

        target_corr: Dict[str, int] = {p: 0 for p in CORR_PRODUCTS}

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

        for p in CORR_PRODUCTS:
            target_corr[p] = max(-MAX_POS, min(MAX_POS, target_corr[p]))

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

        return _flush()