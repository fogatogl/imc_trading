"""
Ensemble — disjoint stack of per-family live D5 winners.

Composition (per round5/best_strategies/MANIFEST.md, theoretical stack +53,681):

  Block A — naive MM, qty=1, no spread gate          (from 549159)
    TRANS_GRAPHITE_MIST, TRANS_VOID_BLUE,
    ROBOT_IRONING, ROBOT_MOPPING,
    OXYGEN_SHAKE_CHOCOLATE, MICROCHIP_CIRCLE
    (GALAXY_SOUNDS_SOLAR_FLAMES moved to Block F oracle)

  Block B — naive MM, qty=capacity, spread>=2 gate   (from 558897 + 560161)
    UV_VISOR_RED, UV_VISOR_ORANGE, UV_VISOR_MAGENTA,
    MICROCHIP_OVAL

  Block C — smart MM (mr_tune base + OBI graft +
             SNK basket + PEB star + slp_cp pair +
             per-product params + inv-taper)         (from 555509 + 556909 + 556852)
    SNACKPACK x5, PEBBLES x5  (TIGHT params 5/2.0/1.0/2.0 per 556852/557541)
    SLEEP_POD COTTON / POLYESTER / NYLON,
    OXYGEN_SHAKE_GARLIC (OBI),
    GALAXY_SOUNDS_BLACK_HOLES (OBI),
    MICROCHIP_TRIANGLE,
    ROBOT_VACUUMING, TRANSLATOR_ASTRO_BLACK
    SNK pair units 2/2/3/3 per 556852 (live winner spec).

  Block E — spike-fade taker (4σ, hold=20)             (from strat_combined_v7_spike)
    ROBOT_DISHES (FADE side, qty=10, BT +16,250)

  Block F — galaxy cointegration oracle               (from final/566031)
    GALAXY_SOUNDS_SOLAR_FLAMES, GALAXY_SOUNDS_DARK_MATTER
    fair = const + Σ wᵢ·midᵢ ; |z|>2.0 take, else post inside fair±dyn

Blocks share traderData via disjoint sub-keys (no cross-state).
PANEL family removed (live submission underperformed website BT).
All dropped products from manifest are intentionally excluded:
  UV_YELLOW (-214), ROBOT_LAUNDRY (-391), OXY_EVENING_BREATH (-255),
  MIC_SQUARE (BT-bad), MIC_RECTANGLE (live -849, dropped per manifest).
"""
from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Tuple

try:
    from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
except ImportError:
    from prosperity4bt.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


# ────── Logger (kevin-fu1 visualizer) ─────────────────────────────────────
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
        return [state.timestamp, td,
                [[l.symbol, l.product, l.denomination] for l in state.listings.values()],
                {s: [od.buy_orders, od.sell_orders] for s, od in state.order_depths.items()},
                [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
                 for arr in state.own_trades.values() for t in arr],
                [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
                 for arr in state.market_trades.values() for t in arr],
                state.position,
                [state.observations.plainValueObservations,
                 {p: [getattr(o, k, None) for k in
                      ("bidPrice", "askPrice", "transportFees", "exportTariff",
                       "importTariff", "sugarPrice", "sunlightIndex")]
                  for p, o in state.observations.conversionObservations.items()}]]

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


# ────── Block A — naive MM, qty=1, no gate (549159) ───────────────────────
A_PRODUCTS: List[str] = [
    "TRANSLATOR_GRAPHITE_MIST",
    "TRANSLATOR_VOID_BLUE",
    "ROBOT_IRONING",
    "ROBOT_MOPPING",
    "OXYGEN_SHAKE_CHOCOLATE",
    "MICROCHIP_CIRCLE",
]
A_QTY = 1

# Spike-skip overlay: for spike-prone products in Block A, suppress naive
# quote on tick where |Δmid| ≥ k·σ (rolling). Defensive — keeps the
# naive live edge but avoids posting straight into a spike.
# ROBOT_IRONING: 50 events/3d, FADE h=50 BT +9,190 unrealised — naive live +1,508 kept.
# Other A products (CHOC, MOP, TRANS, MIC_CIRCLE) not spike-heavy per
# round5_research.md:255 — no overlay needed.
A_SPIKE_SKIP_PRODUCTS: Dict[str, Dict[str, float]] = {
    "ROBOT_IRONING": {"window": 500, "warmup": 50, "k_sigma": 4.0},
}


# ────── Block B — naive MM, qty=cap, spread>=2 (558897 / 560161) ──────────
B_PRODUCTS: List[str] = [
    "UV_VISOR_RED",
    "UV_VISOR_ORANGE",
    "UV_VISOR_MAGENTA",
    "MICROCHIP_OVAL",
]
B_SPREAD_GATE = 2


# ────── Block C — smart MM (555509 / 556909) ──────────────────────────────
CHOC = "SNACKPACK_CHOCOLATE"
VAN = "SNACKPACK_VANILLA"
PIST = "SNACKPACK_PISTACHIO"
RASP = "SNACKPACK_RASPBERRY"
STRAW = "SNACKPACK_STRAWBERRY"
SNACKPACK: List[str] = [CHOC, VAN, PIST, RASP, STRAW]

PEB_L = "PEBBLES_L"
PEB_XS = "PEBBLES_XS"
PEB_S = "PEBBLES_S"
PEB_M = "PEBBLES_M"
PEB_XL = "PEBBLES_XL"
PEBBLES: List[str] = [PEB_L, PEB_XS, PEB_S, PEB_M, PEB_XL]

SLP_COT = "SLEEP_POD_COTTON"
SLP_POL = "SLEEP_POD_POLYESTER"
SLP_NYL = "SLEEP_POD_NYLON"

C_MR_OTHER: List[str] = [
    "ROBOT_VACUUMING",
    "MICROCHIP_TRIANGLE",
    "TRANSLATOR_ASTRO_BLACK",
    "GALAXY_SOUNDS_BLACK_HOLES",
    SLP_NYL,
    SLP_POL,
    SLP_COT,
    "OXYGEN_SHAKE_GARLIC",
]

C_PRODUCTS: List[str] = SNACKPACK + PEBBLES + C_MR_OTHER
C_CORR_PRODUCTS: List[str] = SNACKPACK + PEBBLES + [SLP_COT, SLP_POL]

# Pairs: (a, b, weight, unit, ent_z, ext_z)
# SNACKPACK units 2/2/3/3 per 556852 (live winner). PEB star unit=2 per 555509.
# slp_cp unit=5 per 555509 (live winner).
C_PAIRS: List[Tuple[str, str, float, int, float, float]] = [
    (CHOC, VAN, -1.0, 2, 2.0, 0.5),
    (PIST, RASP, -1.0, 2, 2.0, 0.5),
    (PIST, STRAW, +1.0, 3, 2.0, 0.5),
    (RASP, STRAW, -1.0, 3, 2.0, 0.5),
    (PEB_L, PEB_XL, -1.0, 2, 1.0, 0.5),
    (PEB_M, PEB_XL, -1.0, 2, 1.0, 0.5),
    (PEB_S, PEB_XL, -1.0, 2, 1.0, 0.5),
    (PEB_XS, PEB_XL, -1.0, 2, 1.0, 0.5),
    (SLP_COT, SLP_POL, -0.795, 5, 1.6, 0.5),
]

C_WINDOW = 200
C_MIN_HIST = 50
C_MAX_POS = 10

# MR_OTHER block: 909 per-product params (live winner for VAC/TRIANGLE/ASTRO/etc.)
# SNACKPACK / PEBBLES: 556852 tight params (5/2.0/1.0/2.0) per
# `feedback_pebbles_tight_mm_live` — tight beats loose live by +2k on PEB.
C_TIGHT_PARAMS: Dict[str, float] = {"INV_SKEW": 2.0, "MR_SKEW": 1.0, "Z_TOXIC": 2.0, "BASE_QTY": 5}

C_PRODUCT_PARAMS: Dict[str, Dict[str, float]] = {
    "ROBOT_VACUUMING":           {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "MICROCHIP_TRIANGLE":        {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "TRANSLATOR_ASTRO_BLACK":    {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "GALAXY_SOUNDS_BLACK_HOLES": {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    SLP_NYL:                     {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    SLP_POL:                     {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    SLP_COT:                     {"INV_SKEW": 2.0, "MR_SKEW": 1.5, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    "OXYGEN_SHAKE_GARLIC":       {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10},
    # SNACKPACK + PEBBLES — tight (live winners 556852 / 557541)
    CHOC: C_TIGHT_PARAMS, VAN: C_TIGHT_PARAMS, PIST: C_TIGHT_PARAMS,
    RASP: C_TIGHT_PARAMS, STRAW: C_TIGHT_PARAMS,
    PEB_L: C_TIGHT_PARAMS, PEB_XS: C_TIGHT_PARAMS, PEB_S: C_TIGHT_PARAMS,
    PEB_M: C_TIGHT_PARAMS, PEB_XL: C_TIGHT_PARAMS,
}
C_DEFAULT_PARAMS: Dict[str, float] = {"INV_SKEW": 1.5, "MR_SKEW": 1.0, "Z_TOXIC": 2.5, "BASE_QTY": 10}

C_OBI_PRODUCTS: Dict[str, float] = {
    "GALAXY_SOUNDS_BLACK_HOLES": +0.059,
    "OXYGEN_SHAKE_GARLIC":        +0.066,
}
C_OBI_GAIN = 4.0

C_TAPER_FAMILY: List[str] = [
    "MICROCHIP_TRIANGLE",
    SLP_NYL,
    SLP_COT,
    "OXYGEN_SHAKE_GARLIC",
]
C_INV_TAPER_START = 0.9


# ────── Block E — spike-fade taker (strat_combined_v7_spike) ──────────────
# ROBOT_DISHES has 117 spikes / 90k ticks, FADE h=20 4σ = +16,250 BT (best
# of all configs). Per `feedback_post_spike_passive_direction`: aggressor
# flow is opposite to a passive limit, so use TAKER (cross book).
# Disjoint from MM universe — DISHES never quoted by Block C.
E_TAKERS: List[Tuple[str, str, int, int, float, int, int]] = [
    # (key, product, sigma_window, warmup, k_sigma, hold, position_limit)
    ("DISHES", "ROBOT_DISHES", 500, 50, 4.0, 20, 10),
]
E_TS_PER_TICK = 100

# HIGH-2 mitigation: per-trade stop-loss within hold window.
# Calibrated from spike_strategy_pnl.csv ROBOT_DISHES FADE h=20:
#   n=117, mean +138.89, median -80, std 687.58, hit-rate 36%
# 1.5σ of P&L distribution ≈ -1000. Caches catastrophic tail (~5-10% of events)
# without cutting normal drawdown→recovery cycles (median trade ends at -80).
E_STOP_LOSS = 1000.0  # SeaShells per spike trade


# ────── Block F — galaxy cointegration oracle (final/566031) ──────────────
# fair = const + Σ wᵢ·midᵢ on full GALAXY family.
# |z| > z_thr → take aggressively against fair; else post inside fair ± dyn
# with inventory skew. Position-limit 10 each. Pair products
# (PLANETARY_RINGS, BLACK_HOLES, SOLAR_WINDS) are READ ONLY here — they
# are features in the oracle, not traded. BLACK_HOLES still trades via
# Block C (smart MM + OBI).
F_GALAXY_ORACLES: Dict[str, Dict[str, Any]] = {
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

# Online residual recalibration parameters (HIGH-1 mitigation).
# DESIGN (BT-safe):
#   - Maker post uses OFFLINE fair (cointegration anchor) — never de-centered.
#   - Take decision uses online z = (residual - μ_r) / max(σ_r, spread_std_offline)
#     so μ_r adjusts for drift, σ_r tightens during calm but FLOOR at offline σ
#     ensures we never take more aggressively than offline calibration.
# Asymmetric protection: handles drift + regime stress, but cannot over-fire
# vs offline (which is BT-validated).
F_RESID_WINDOW = 200
F_RESID_WARMUP = 50
F_SIGMA_FLOOR_FRAC = 1.0     # σ_floor = spread_std_offline (full)

# Feature-leg liquidity gate: skip oracle if any feature leg has spread
# wider than this threshold (signals stale/illiquid book).
F_FEATURE_SPREAD_CAP = 30


# ────── Block E helpers ───────────────────────────────────────────────────
def _take_sell(product: str, depth, room: int) -> List[Order]:
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


def _take_buy(product: str, depth, room: int) -> List[Order]:
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


# ────── Trader ────────────────────────────────────────────────────────────
class Trader:

    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0

        try:
            td = json.loads(state.traderData) if state.traderData else {}
        except json.JSONDecodeError:
            td = {}

        # ── Block A : naive qty=1, no gate (+ spike-skip overlay) ──
        a_spike_skip: Dict[str, Dict[str, Any]] = td.get("a_spike_skip", {})
        for sym in A_PRODUCTS:
            if sym not in state.order_depths:
                continue
            od = state.order_depths[sym]
            if not od.buy_orders or not od.sell_orders:
                continue
            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys())
            my_bid = best_bid + 1
            my_ask = best_ask - 1
            if my_bid >= my_ask:
                continue
            mid = (best_bid + best_ask) / 2.0

            # Spike-skip overlay (defensive): if mid jumped ≥ k·σ this tick,
            # suppress naive quote — wait for vol to clear before posting again.
            skip_quote = False
            if sym in A_SPIKE_SKIP_PRODUCTS:
                cfg = A_SPIKE_SKIP_PRODUCTS[sym]
                ss = a_spike_skip.get(sym, {})
                prev_mid = ss.get("prev_mid")
                rets: List[float] = ss.get("rets", [])
                prev_sigma: float = ss.get("prev_sigma", 0.0)

                ret_now = (mid - prev_mid) if prev_mid is not None else None
                if (ret_now is not None and len(rets) >= cfg["warmup"]
                        and prev_sigma > 0
                        and abs(ret_now) >= cfg["k_sigma"] * prev_sigma):
                    skip_quote = True
                    logger.print(f"A_SKIP {sym} t={state.timestamp} ret={ret_now:.2f} sigma={prev_sigma:.2f}")

                if ret_now is not None:
                    rets.append(ret_now)
                    if len(rets) > cfg["window"]:
                        rets = rets[-int(cfg["window"]):]
                    new_sigma = _rolling_std(rets) if len(rets) >= cfg["warmup"] else 0.0
                else:
                    new_sigma = prev_sigma
                a_spike_skip[sym] = {"prev_mid": mid, "rets": rets, "prev_sigma": new_sigma}

            if skip_quote:
                continue

            pos = state.position.get(sym, 0)
            orders: List[Order] = []
            if pos < C_MAX_POS:
                orders.append(Order(sym, my_bid, A_QTY))
            if pos > -C_MAX_POS:
                orders.append(Order(sym, my_ask, -A_QTY))
            if orders:
                result[sym] = orders

        # ── Block B : naive qty=cap, spread>=2 ──
        for sym in B_PRODUCTS:
            if sym not in state.order_depths:
                continue
            od = state.order_depths[sym]
            if not od.buy_orders or not od.sell_orders:
                continue
            best_bid = max(od.buy_orders.keys())
            best_ask = min(od.sell_orders.keys())
            if best_ask - best_bid < B_SPREAD_GATE:
                continue
            pos = state.position.get(sym, 0)
            buy_cap = C_MAX_POS - pos
            sell_cap = C_MAX_POS + pos
            orders: List[Order] = []
            if buy_cap > 0:
                orders.append(Order(sym, best_bid + 1, buy_cap))
            if sell_cap > 0:
                orders.append(Order(sym, best_ask - 1, -sell_cap))
            if orders:
                result[sym] = orders

        # ── Block C : smart MM with pair-corr overlay ──
        mids_hist:   Dict[str, List[float]] = td.get("c_mids", {})
        prices_hist: Dict[str, List[float]] = td.get("c_prices", {})
        pair_state:  Dict[str, int]         = td.get("c_pair_state", {})

        bb: Dict[str, int] = {}
        ba: Dict[str, int] = {}
        mids: Dict[str, float] = {}
        for sym in C_PRODUCTS:
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
            if sym in C_CORR_PRODUCTS:
                h = mids_hist.get(sym, [])
                h.append(m)
                if len(h) > C_WINDOW:
                    h = h[-C_WINDOW:]
                mids_hist[sym] = h
            hp = prices_hist.get(sym, [])
            hp.append(math.log(m))
            if len(hp) > C_WINDOW:
                hp = hp[-C_WINDOW:]
            prices_hist[sym] = hp

        target_corr: Dict[str, int] = {p: 0 for p in C_CORR_PRODUCTS}
        diag_corr: List[str] = []

        for a, b, weight, unit, ent, ext in C_PAIRS:
            key = f"{a}|{b}"
            st = pair_state.get(key, 0)

            ha = mids_hist.get(a, [])
            hb = mids_hist.get(b, [])
            n = min(len(ha), len(hb))
            if n < C_MIN_HIST or a not in mids or b not in mids:
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

        for p in C_CORR_PRODUCTS:
            target_corr[p] = max(-C_MAX_POS, min(C_MAX_POS, target_corr[p]))

        for sym in C_PRODUCTS:
            if sym not in mids:
                continue
            params = C_PRODUCT_PARAMS.get(sym, C_DEFAULT_PARAMS)
            INV_SKEW = params["INV_SKEW"]
            MR_SKEW  = params["MR_SKEW"]
            Z_TOXIC  = params["Z_TOXIC"]
            BASE_QTY = params["BASE_QTY"]

            hist = prices_hist.get(sym, [])
            if len(hist) < C_MIN_HIST:
                continue

            n = len(hist)
            mu = sum(hist) / n
            var = sum((x - mu) ** 2 for x in hist) / max(n - 1, 1)
            std = var ** 0.5
            if std <= 0.0:
                continue

            mid = mids[sym]
            log_mid = math.log(mid)
            mu_px = math.exp(mu)
            sigma_px = mid * std
            z = (log_mid - mu) / std
            pos = state.position.get(sym, 0)

            tc = target_corr.get(sym, 0)
            inv_off = int(round(INV_SKEW * (pos - tc) / C_MAX_POS))
            mr_bias = int(round(MR_SKEW * (mu_px - mid) / max(sigma_px, 1)))

            obi_shift = 0
            if sym in C_OBI_PRODUCTS:
                od_sym = state.order_depths[sym]
                bsz = od_sym.buy_orders.get(bb[sym], 0)
                asz = -od_sym.sell_orders.get(ba[sym], 0)
                tot = bsz + asz
                obi = (bsz - asz) / tot if tot > 0 else 0.0
                obi_shift = int(round(C_OBI_GAIN * obi))

            bid_px = bb[sym] + 1 - inv_off + mr_bias + obi_shift
            ask_px = ba[sym] - 1 - inv_off + mr_bias + obi_shift
            bid_px = min(bid_px, ba[sym] - 1)
            ask_px = max(ask_px, bb[sym] + 1)
            if bid_px >= ask_px:
                continue

            cap_bid = max(0, C_MAX_POS - pos)
            cap_ask = max(0, C_MAX_POS + pos)
            qty_bid = min(BASE_QTY, cap_bid)
            qty_ask = min(BASE_QTY, cap_ask)
            if z >= Z_TOXIC:
                qty_bid = 0
            elif z <= -Z_TOXIC:
                qty_ask = 0

            if sym in C_TAPER_FAMILY:
                inv_frac = abs(pos) / C_MAX_POS
                if inv_frac > C_INV_TAPER_START:
                    taper = (inv_frac - C_INV_TAPER_START) / (1.0 - C_INV_TAPER_START)
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

        # ── Block F : galaxy cointegration oracle (HIGH-1 mitigated) ──
        # HIGH-1 fix:
        #   A) rolling residual mean (fair - mid) over N=200 → re-centers fair
        #      against intraday drift in feature legs
        #   B) rolling residual σ → replaces frozen spread_std (with floor)
        #   C) feature-leg liquidity gate → skip if any feature spread > cap
        galaxy_resid_hist: Dict[str, List[float]] = td.get("f_resid", {})

        galaxy_mids: Dict[str, float] = {}
        galaxy_bb: Dict[str, int] = {}
        galaxy_ba: Dict[str, int] = {}
        galaxy_syms = set(F_GALAXY_ORACLES.keys())
        for cfg in F_GALAXY_ORACLES.values():
            galaxy_syms.update(cfg["weights"].keys())
        for sym in galaxy_syms:
            od_g = state.order_depths.get(sym)
            if od_g is None or not od_g.buy_orders or not od_g.sell_orders:
                continue
            gb = max(od_g.buy_orders.keys())
            ga = min(od_g.sell_orders.keys())
            galaxy_bb[sym] = gb
            galaxy_ba[sym] = ga
            galaxy_mids[sym] = (gb + ga) / 2.0

        for target, cfg in F_GALAXY_ORACLES.items():
            if target not in galaxy_mids:
                continue
            # Liquidity gate (C): skip if any feature leg missing or wide-spread
            stale_leg = False
            for s in cfg["weights"]:
                if s not in galaxy_mids:
                    stale_leg = True
                    break
                if galaxy_ba[s] - galaxy_bb[s] > F_FEATURE_SPREAD_CAP:
                    stale_leg = True
                    break
            if stale_leg:
                logger.print(f"F_SKIP {target} stale_leg")
                continue

            fair = cfg["const"] + sum(w * galaxy_mids[s] for s, w in cfg["weights"].items())
            residual = fair - galaxy_mids[target]

            # Update rolling residual history
            rh = galaxy_resid_hist.get(target, [])
            rh.append(residual)
            if len(rh) > F_RESID_WINDOW:
                rh = rh[-F_RESID_WINDOW:]
            galaxy_resid_hist[target] = rh

            # Online z-score (A+B): use rolling μ + σ after warmup, else fallback.
            # Maker post always uses OFFLINE fair (cointegration anchor) — z
            # adjustment only affects taker decision, not maker pricing.
            sigma_floor = cfg["spread_std"] * F_SIGMA_FLOOR_FRAC
            if len(rh) >= F_RESID_WARMUP:
                μ_r = sum(rh) / len(rh)
                var_r = sum((x - μ_r) ** 2 for x in rh) / max(len(rh) - 1, 1)
                σ_r = max(var_r ** 0.5, sigma_floor)
                z = (residual - μ_r) / σ_r
            else:
                z = residual / cfg["spread_std"]  # fallback during warmup

            pos = state.position.get(target, 0)
            bid_t = galaxy_bb[target]; ask_t = galaxy_ba[target]
            mkt_spread = ask_t - bid_t
            buy_qty = cfg["position_limit"] - pos
            sell_qty = cfg["position_limit"] + pos
            orders: List[Order] = []
            if z > cfg["z_score_threshold"] and buy_qty > 0:
                orders.append(Order(target, ask_t, buy_qty))
            elif z < -cfg["z_score_threshold"] and sell_qty > 0:
                orders.append(Order(target, bid_t, -sell_qty))
            else:
                dyn = max(1.0, mkt_spread / 2.0)
                skew = -pos * dyn * 0.15
                my_bid = min(int(math.floor(fair - dyn + skew)), ask_t - 1)
                my_ask = max(int(math.ceil(fair  + dyn + skew)), bid_t + 1)
                if buy_qty  > 0: orders.append(Order(target, my_bid,  buy_qty))
                if sell_qty > 0: orders.append(Order(target, my_ask, -sell_qty))
            if orders:
                result[target] = orders

        # ── Block E : spike-fade taker (HIGH-2 stop-loss) ──
        spike_state: Dict[str, Dict[str, Any]] = td.get("e_spike", {})
        for key, product, sigma_window, warmup, k_sigma, hold, pos_limit in E_TAKERS:
            depth = state.order_depths.get(product)
            if depth is None:
                continue

            st = spike_state.get(key, {})
            prev_mid = st.get("prev_mid")
            rets: List[float] = st.get("rets", [])
            prev_sigma: float = st.get("prev_sigma", 0.0)
            entry_tick = st.get("entry_tick")
            entry_mid = st.get("entry_mid")

            bid = max(depth.buy_orders.keys()) if depth.buy_orders else None
            ask = min(depth.sell_orders.keys()) if depth.sell_orders else None
            mid = (bid + ask) / 2.0 if (bid is not None and ask is not None) else None
            pos = state.position.get(product, 0)

            ret_now = None
            if mid is not None and prev_mid is not None:
                ret_now = mid - prev_mid

            is_spike = False
            spike_sign = 0
            if ret_now is not None and len(rets) >= warmup and prev_sigma > 0:
                if abs(ret_now) >= k_sigma * prev_sigma:
                    is_spike = True
                    spike_sign = 1 if ret_now > 0 else -1

            orders: List[Order] = []

            # HIGH-2: stop-loss within hold window. Exit early if mark-to-mid
            # unrealised P&L falls below -E_STOP_LOSS. Calibrated to ~1.5σ of
            # per-event P&L distribution (caps catastrophic tail).
            if pos != 0 and entry_mid is not None and mid is not None:
                unrealised = pos * (mid - entry_mid)
                if unrealised < -E_STOP_LOSS:
                    if pos > 0 and bid is not None:
                        orders += _take_sell(product, depth, pos)
                    elif pos < 0 and ask is not None:
                        orders += _take_buy(product, depth, -pos)
                    logger.print(f"{key} STOPLOSS t={state.timestamp} unrealised={unrealised:.0f} entry={entry_mid:.0f} mid={mid:.0f}")
                    entry_tick = None
                    entry_mid = None

            # Hold-period hard exit
            if pos != 0 and entry_tick is not None:
                if state.timestamp - entry_tick >= hold * E_TS_PER_TICK:
                    if pos > 0 and bid is not None:
                        orders += _take_sell(product, depth, pos)
                    elif pos < 0 and ask is not None:
                        orders += _take_buy(product, depth, -pos)
                    entry_tick = None
                    entry_mid = None

            # Enter on spike: FADE = trade opposite of spike direction
            if is_spike and pos == 0 and bid is not None and ask is not None:
                target_sign = -spike_sign
                if target_sign > 0:
                    orders += _take_buy(product, depth, pos_limit)
                else:
                    orders += _take_sell(product, depth, pos_limit)
                entry_tick = state.timestamp
                entry_mid = mid
                logger.print(f"{key} SPIKE t={state.timestamp} ret={ret_now:.2f} sigma={prev_sigma:.2f} sign={spike_sign} take={target_sign}")

            if ret_now is not None:
                rets.append(ret_now)
                if len(rets) > sigma_window:
                    rets = rets[-sigma_window:]
                new_sigma = _rolling_std(rets) if len(rets) >= warmup else 0.0
            else:
                new_sigma = prev_sigma

            spike_state[key] = {
                "prev_mid": mid if mid is not None else prev_mid,
                "rets": rets,
                "prev_sigma": new_sigma,
                "entry_tick": entry_tick,
                "entry_mid": entry_mid,
            }
            if orders:
                if product in result:
                    result[product].extend(orders)
                else:
                    result[product] = orders

        # ── Persist state ──
        td["a_spike_skip"] = a_spike_skip
        td["c_mids"] = mids_hist
        td["c_prices"] = prices_hist
        td["c_pair_state"] = pair_state
        td["e_spike"] = spike_state
        td["f_resid"] = galaxy_resid_hist
        trader_data = json.dumps(td)

        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data