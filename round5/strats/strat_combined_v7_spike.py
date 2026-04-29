"""
Combined trader — v7 MM + spike taker in one file (single submission).

Background: 556502 (= v6) live +18,899 vs 555509 (= v5+3 edits) live +21,881
(−2,982). Per-product attribution showed:
  - v6 BT-tuned dials (SNACKPACK ENTER_Z 2.0→1.6, INV_SKEW 0.5, PIS-fade)
    didn't generalise to live D5. SP family lost ~−791 vs 555509. PEBBLES
    star-XL bled non-XL legs (PEB_S −2,287 alone). Inflation dropped
    9.08% → 7.72%.
  - The only v6 changes that *did* survive live were: drop ASTRO_BLACK
    (live-validated −470 → 0), clean DARK_MATTER refs (hygiene), keep
    INV_TAPER global (already v5 default).

v7 MM = v5 base − {ASTRO_BLACK, DARK_MATTER} only. No SNACKPACK retuning.
No PIS-fade. No PEBBLES topology rework (kept star — high variance but
live-acceptable per 555509 PEB_S +1,699; redesign needs more data).

Spike taker = port from `round5/strat_spike_takers_multi.py`. ROBOT_DISHES
+ ROBOT_IRONING, FADE side, 4σ spike, hold 20 ticks. Pure taker, disjoint
from MM universe (DISHES/IRONING never quoted as MM in v7 — explicit no
overlap).

Standalone BT references (independent runs):
  v5 (full)              D2 34,481 D3 74,006 D4 143,452 → 251,939
  555509 (v5+3)          D2 ?      D3 ?      D4 ?       → 241,080 (live 21,881)
  spike taker            D2  7,659 D3    452 D4  16,058 →  24,169 (Δ-engine 0%)
  v7 expected ≈ 555509 BT minus the FAMILLE-only INV_TAPER restriction
  (v7 reverts to global), plus removal of TRANSLATOR_ASTRO_BLACK from
  MR_OTHER (saves teammate's measured −223 live signal). Total combined
  BT ≈ 240k + 24k ≈ 264k → live projection ≈ 24-26k SS at 9% inflation.

Universe = 18 products MM (5 SNACKPACK + 5 PEBBLES + 8 MR_OTHER w/o
ASTRO_BLACK/DARK_MATTER) + 2 spike-only (DISHES/IRONING). PAIRS = 9
(unchanged from v5).
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


# ═══════════════════════════════════════════════════════════════════════════
# v7 MM — v5 base minus {ASTRO_BLACK, DARK_MATTER}
# ═══════════════════════════════════════════════════════════════════════════

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

# v7: MR_OTHER drops TRANSLATOR_ASTRO_BLACK (live −470 in 555509, −284 in 550714)
# and GALAXY_SOUNDS_DARK_MATTER (live −1,295 in 550714; was already pulled in 555509).
MR_OTHER: List[str] = [
    "ROBOT_VACUUMING",
    "MICROCHIP_TRIANGLE",
    "GALAXY_SOUNDS_BLACK_HOLES",
    "SLEEP_POD_NYLON",
    "SLEEP_POD_POLYESTER",
    SLP_COT,
    "OXYGEN_SHAKE_GARLIC",
]

ALL_PRODUCTS: List[str] = SNACKPACK + PEBBLES + MR_OTHER

CORR_PRODUCTS: List[str] = SNACKPACK + PEBBLES + [SLP_COT, "SLEEP_POD_POLYESTER"]


# ─── Pairs (a, b, weight, unit, ent_z, ext_z) ─────────────────────────────
# v5 baseline — no SNACKPACK ENTER_Z retuning, no PIS-fade.
PAIRS: List[Tuple[str, str, float, int, float, float]] = [
    (CHOC, VAN,   -1.0,  5, 2.0, 0.5),
    (PIST, RASP,  -1.0,  5, 2.0, 0.5),
    (PIST, STRAW, +1.0,  5, 2.0, 0.5),
    (RASP, STRAW, -1.0,  5, 2.0, 0.5),
    (PEB_L,  PEB_XL, -1.0,  2, 1.0, 0.5),
    (PEB_M,  PEB_XL, -1.0,  2, 1.0, 0.5),
    (PEB_S,  PEB_XL, -1.0,  2, 1.0, 0.5),
    (PEB_XS, PEB_XL, -1.0,  2, 1.0, 0.5),
    (SLP_COT, "SLEEP_POD_POLYESTER", -0.795, 5, 1.6, 0.5),
]


WINDOW    = 200
MIN_HIST  = 50
MAX_POS   = 10
PASSIVE_OFFSET = 1

# v7: no INV_SKEW=0.5 SNACKPACK overrides. SNACKPACK uses DEFAULT_MM_PARAMS.
PRODUCT_PARAMS = {
    "ROBOT_VACUUMING":           {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "MICROCHIP_TRIANGLE":        {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "GALAXY_SOUNDS_BLACK_HOLES": {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "SLEEP_POD_NYLON":           {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "SLEEP_POD_POLYESTER":       {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "SLEEP_POD_COTTON":          {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "OXYGEN_SHAKE_GARLIC":       {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
}

DEFAULT_MM_PARAMS = {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10}

# v7: OBI_PRODUCTS — DARK_MATTER removed (no longer in universe). Two left.
OBI_PRODUCTS: dict[str, float] = {
    "GALAXY_SOUNDS_BLACK_HOLES":  +0.059,
    "OXYGEN_SHAKE_GARLIC":        +0.066,
}
OBI_GAIN: float = 4.0
INV_TAPER_START: float = 0.9   # global — applies to every quoted symbol


# ═══════════════════════════════════════════════════════════════════════════
# Spike taker — DISHES + IRONING (port from strat_spike_takers_multi.py)
# ═══════════════════════════════════════════════════════════════════════════

class TakerCfg:
    __slots__ = ("key", "product", "side", "sigma_window", "warmup", "k_sigma", "hold", "position_limit")
    def __init__(self, key, product, side, sigma_window, warmup, k_sigma, hold, position_limit):
        self.key = key; self.product = product; self.side = side
        self.sigma_window = sigma_window; self.warmup = warmup
        self.k_sigma = k_sigma; self.hold = hold; self.position_limit = position_limit


TAKERS: List[TakerCfg] = [
    TakerCfg("DISHES",  "ROBOT_DISHES",  "FADE", 500, 50, 4.0, 20, 10),
    TakerCfg("IRONING", "ROBOT_IRONING", "FADE", 500, 50, 4.0, 20, 10),
]
TS_PER_TICK: int = 100

SPIKE_PRODUCTS = {cfg.product for cfg in TAKERS}
assert SPIKE_PRODUCTS.isdisjoint(set(ALL_PRODUCTS)), "spike taker products must not overlap MM universe"


def _take_sell(product: str, depth: OrderDepth, room: int) -> List[Order]:
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


def _step_taker(cfg: TakerCfg, state: TradingState, st: dict, result: Dict[Symbol, List[Order]]) -> dict:
    depth = state.order_depths.get(cfg.product)
    if depth is None:
        return st

    prev_mid = st.get("prev_mid")
    rets: List[float] = st.get("rets", [])
    prev_sigma: float = st.get("prev_sigma", 0.0)
    entry_tick = st.get("entry_tick")
    entry_sign: int = st.get("entry_sign", 0)

    bid = max(depth.buy_orders.keys()) if depth.buy_orders else None
    ask = min(depth.sell_orders.keys()) if depth.sell_orders else None
    mid = (bid + ask) / 2.0 if (bid is not None and ask is not None) else None
    pos = state.position.get(cfg.product, 0)
    orders: List[Order] = []

    ret_now = None
    if mid is not None and prev_mid is not None:
        ret_now = mid - prev_mid

    is_spike = False
    spike_sign = 0
    if ret_now is not None and len(rets) >= cfg.warmup and prev_sigma > 0:
        if abs(ret_now) >= cfg.k_sigma * prev_sigma:
            is_spike = True
            spike_sign = 1 if ret_now > 0 else -1

    if pos != 0 and entry_tick is not None:
        if state.timestamp - entry_tick >= cfg.hold * TS_PER_TICK:
            if pos > 0 and bid is not None:
                orders += _take_sell(cfg.product, depth, pos)
            elif pos < 0 and ask is not None:
                orders += _take_buy(cfg.product, depth, -pos)
            entry_tick = None
            entry_sign = 0

    if is_spike and pos == 0 and bid is not None and ask is not None:
        target_sign = -spike_sign if cfg.side == "FADE" else spike_sign
        if target_sign > 0:
            orders += _take_buy(cfg.product, depth, cfg.position_limit)
        else:
            orders += _take_sell(cfg.product, depth, cfg.position_limit)
        entry_tick = state.timestamp
        entry_sign = target_sign
        logger.print(f"{cfg.key} SPIKE t={state.timestamp} ret={ret_now:.2f} sigma={prev_sigma:.2f} sign={spike_sign} take={target_sign}")

    if ret_now is not None:
        rets.append(ret_now)
        if len(rets) > cfg.sigma_window:
            rets = rets[-cfg.sigma_window:]
        new_sigma = _rolling_std(rets) if len(rets) >= cfg.warmup else 0.0
    else:
        new_sigma = prev_sigma

    if mid is not None:
        prev_mid = mid

    if orders:
        result.setdefault(cfg.product, []).extend(orders)

    return {
        "prev_mid": prev_mid,
        "rets": rets,
        "prev_sigma": new_sigma,
        "entry_tick": entry_tick,
        "entry_sign": entry_sign,
    }


# ═══════════════════════════════════════════════════════════════════════════
# Trader — runs MM loop then spike-taker loop, single result dict
# ═══════════════════════════════════════════════════════════════════════════

class Trader:
    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0
        td = json.loads(state.traderData) if state.traderData else {}

        mids_hist:    Dict[str, List[float]] = td.get("mids",       {})
        prices_hist:  Dict[str, List[float]] = td.get("prices",     {})
        pair_state:   Dict[str, int]         = td.get("pair_state", {})
        taker_states: Dict[str, dict]        = td.get("taker_states", {})

        def _flush():
            td["mids"]         = mids_hist
            td["prices"]       = prices_hist
            td["pair_state"]   = pair_state
            td["taker_states"] = taker_states
            s = json.dumps(td)
            logger.flush(state, result, conversions, s)
            return result, conversions, s

        # ── 1) Snapshot books for MM universe ──
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

        # ── 3) Pair states + target_corr overlay ──
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

        # ── 4) MM loop ──
        for sym in ALL_PRODUCTS:
            if sym not in mids:
                continue
            params = PRODUCT_PARAMS.get(sym, DEFAULT_MM_PARAMS)
            INV_SKEW = params["INV_SKEW"]
            MR_SKEW  = params["MR_SKEW"]
            Z_TOXIC  = params["Z_TOXIC"]
            BASE_QTY = params["BASE_QTY"]

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

        # ── 5) Spike taker loop (DISHES, IRONING — disjoint from MM) ──
        for cfg in TAKERS:
            ts = taker_states.get(cfg.key, {})
            taker_states[cfg.key] = _step_taker(cfg, state, ts, result)

        if diag_corr:
            logger.print("CORR " + " | ".join(diag_corr))

        return _flush()
