"""
Stratégie combinée — regroupe les trois sous-stratégies :
  1. HYDROGEL_PACK  (mean-reversion taker/maker avec volatility armor)
  2. VELVETFRUIT_EXTRACT (taker z-score + maker autour de μ)
  3. Options VEV_*  (pricing OU / correction BS + Grecs)

Aucune logique de trading n'est modifiée.
"""

from datamodel import (
    OrderDepth, TradingState, Order, Symbol, Listing,
    Observation, Trade, ProsperityEncoder,
)
from typing import List, Dict, Tuple, Any
import json
import math
import numpy as np


# ═══════════════════════════════════════════════════════════════════════════
#  Logger (unique, partagé)
# ═══════════════════════════════════════════════════════════════════════════
class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state, orders, conversions, trader_data):
        base = len(self.to_json([
            self.compress_state(state, ""),
            self.compress_orders(orders), conversions, "", "",
        ]))
        max_item = (self.max_log_length - base) // 3
        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item)),
            self.compress_orders(orders), conversions,
            self.truncate(trader_data, max_item),
            self.truncate(self.logs, max_item),
        ]))
        self.logs = ""

    def compress_state(self, state, td):
        return [
            state.timestamp, td,
            [[l.symbol, l.product, l.denomination] for l in state.listings.values()],
            {s: [od.buy_orders, od.sell_orders] for s, od in state.order_depths.items()},
            [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
             for arr in state.own_trades.values() for t in arr],
            [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
             for arr in state.market_trades.values() for t in arr],
            state.position,
            [state.observations.plainValueObservations,
             {p: [o.bidPrice, o.askPrice, o.transportFees, o.exportTariff,
                  o.importTariff, getattr(o, "sugarPrice", 0),
                  getattr(o, "sunlightIndex", 0)]
              for p, o in state.observations.conversionObservations.items()}],
        ]

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


# ═══════════════════════════════════════════════════════════════════════════
#  Constantes HYDROGEL_PACK
# ═══════════════════════════════════════════════════════════════════════════
HP_MEAN          = 9991.0
HP_BASE_LIMIT    = 200
HP_SHARK_DEV     = 22.0
HP_MAKER_DEV     = 14.0
HP_PASSIVE_OFFSET = 5
HP_VOL_TARGET    = 30.0

# ═══════════════════════════════════════════════════════════════════════════
#  Constantes VELVETFRUIT_EXTRACT (sous-jacent)
# ═══════════════════════════════════════════════════════════════════════════
VEL_UNDERLYING   = "VELVETFRUIT_EXTRACT"
VEL_POS_LIMIT    = 200
VEL_MEAN_WINDOW  = 3000
VEL_TAKE_CAP     = 40
VEL_Z_TAKER      = 1.5
VEL_MM_HALF      = 1.5
VEL_MM_SIZE      = 7
VEL_SKEW_DIV     = 30

# ═══════════════════════════════════════════════════════════════════════════
#  Constantes OPTIONS (voucher)
# ═══════════════════════════════════════════════════════════════════════════
STRIKES = {
    "VEV_4000": 4000, "VEV_4500": 4500,
    "VEV_5000": 5000, "VEV_5100": 5100, "VEV_5200": 5200,
    "VEV_5300": 5300, "VEV_5400": 5400, "VEV_5500": 5500,
}
OPTIONS        = list(STRIKES.keys())
ATM_STRIKES    = ("VEV_5200", "VEV_5300")
OPT_POS_LIMIT  = 300
TOTAL_TICKS    = 30000
DEFAULT_SIGMA  = 0.000207
OPT_MEAN_WINDOW = 2000
HALF_LIFE      = 30000
MR_STRENGTH    = 1.0
OPT_EDGE       = 1.5
OPT_TAKE_CAP   = 30
MIN_T_REM      = 200


# ═══════════════════════════════════════════════════════════════════════════
#  Black-Scholes helpers
# ═══════════════════════════════════════════════════════════════════════════
def norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

def bs_d1(S, K, T, sig):
    return (math.log(S / K) + 0.5 * sig * sig * T) / (sig * math.sqrt(T))

def bs_call(S, K, T, sig):
    if T <= 0 or sig <= 0:
        return max(S - K, 0.0)
    d1 = bs_d1(S, K, T, sig)
    d2 = d1 - sig * math.sqrt(T)
    return S * norm_cdf(d1) - K * norm_cdf(d2)

def bs_delta(S, K, T, sig):
    if T <= 0 or sig <= 0:
        return 1.0 if S > K else 0.0
    return norm_cdf(bs_d1(S, K, T, sig))

def bs_vega(S, K, T, sig):
    if T <= 0 or sig <= 0:
        return 0.0
    return S * math.sqrt(T) * norm_pdf(bs_d1(S, K, T, sig))

def bs_theta(S, K, T, sig):
    if T <= 0 or sig <= 0:
        return 0.0
    return -S * norm_pdf(bs_d1(S, K, T, sig)) * sig / (2 * math.sqrt(T))

def implied_vol(target, S, K, T, lo=1e-6, hi=0.01):
    if target <= max(S - K, 0.0):
        return lo
    for _ in range(30):
        mid = (lo + hi) / 2
        if bs_call(S, K, T, mid) > target:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


# ═══════════════════════════════════════════════════════════════════════════
#  WAP helper (hydro)
# ═══════════════════════════════════════════════════════════════════════════
def _wap(od):
    if not od or not od.buy_orders or not od.sell_orders:
        return None
    bp, ap = max(od.buy_orders.keys()), min(od.sell_orders.keys())
    bv, av = od.buy_orders[bp], abs(od.sell_orders[ap])
    return (bp * av + ap * bv) / (bv + av)


# ═══════════════════════════════════════════════════════════════════════════
#  Trader principal
# ═══════════════════════════════════════════════════════════════════════════
class Trader:

    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0

        try:
            td = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            td = {}

        # ── Persistence buckets ──
        hp_hist       = td.get("hp_hist", [])        # hydro price history
        vel_s_hist    = td.get("vel_s_hist", [])      # velvet mid history
        opt_s_hist    = td.get("opt_s_hist", [])      # voucher underlying history
        opt_prev_ts   = td.get("opt_prev_ts", -1)
        opt_days      = td.get("opt_days", 0)

        depths = state.order_depths
        pos    = state.position if state.position else {}

        # ───────────────────────────────────────────────────────────────────
        #  1) HYDROGEL_PACK
        # ───────────────────────────────────────────────────────────────────
        hp_book = depths.get("HYDROGEL_PACK")
        hp_price = _wap(hp_book)

        if hp_price is not None:
            hp_hist.append(hp_price)
            hp_hist = hp_hist[-50:]

            current_vol = np.std(hp_hist) if len(hp_hist) > 10 else 15.0
            vol_scale = min(1.0, HP_VOL_TARGET / current_vol)
            curr_limit = int(HP_BASE_LIMIT * vol_scale)

            hp_curr = pos.get("HYDROGEL_PACK", 0)
            fair_anchor = HP_MEAN - int((hp_curr / curr_limit) * 6)
            dev = hp_price - fair_anchor

            # SHARK (taker)
            if abs(dev) > HP_SHARK_DEV:
                side_volume = sum(
                    abs(v) for v in (
                        hp_book.buy_orders if dev > 0 else hp_book.sell_orders
                    ).values()
                )
                qty = min(curr_limit - abs(hp_curr), side_volume)
                if qty > 0:
                    price = (max(hp_book.buy_orders.keys()) if dev > 0
                             else min(hp_book.sell_orders.keys()))
                    result["HYDROGEL_PACK"] = [
                        Order("HYDROGEL_PACK", int(price), int(-qty if dev > 0 else qty))
                    ]

            # MAKER (passive)
            elif abs(dev) > HP_MAKER_DEV:
                if dev > 0 and hp_curr > -curr_limit:
                    result["HYDROGEL_PACK"] = [
                        Order("HYDROGEL_PACK",
                              int(math.ceil(hp_price + HP_PASSIVE_OFFSET)),
                              -(curr_limit + hp_curr))
                    ]
                elif dev < 0 and hp_curr < curr_limit:
                    result["HYDROGEL_PACK"] = [
                        Order("HYDROGEL_PACK",
                              int(math.floor(hp_price - HP_PASSIVE_OFFSET)),
                              curr_limit - hp_curr)
                    ]

        # ───────────────────────────────────────────────────────────────────
        #  2) VELVETFRUIT_EXTRACT (sous-jacent)
        # ───────────────────────────────────────────────────────────────────
        if VEL_UNDERLYING in depths:
            s_od = depths[VEL_UNDERLYING]
            if s_od.buy_orders and s_od.sell_orders:
                s_bid = max(s_od.buy_orders.keys())
                s_ask = min(s_od.sell_orders.keys())
                S_vel = (s_bid + s_ask) / 2.0
                spread = s_ask - s_bid

                vel_s_hist.append(S_vel)
                if len(vel_s_hist) > VEL_MEAN_WINDOW:
                    vel_s_hist.pop(0)

                if len(vel_s_hist) >= 100:
                    mu_vel   = sum(vel_s_hist) / len(vel_s_hist)
                    var_s    = sum((x - mu_vel) ** 2 for x in vel_s_hist) / (len(vel_s_hist) - 1)
                    sigma_s  = math.sqrt(var_s)
                    z        = (S_vel - mu_vel) / sigma_s if sigma_s > 1e-9 else 0.0

                    und_pos = pos.get(VEL_UNDERLYING, 0)
                    vel_orders: List[Order] = []
                    taker_fired = False

                    # TAKER
                    if z > VEL_Z_TAKER and und_pos > -VEL_POS_LIMIT:
                        qty = min(VEL_POS_LIMIT + und_pos, s_od.buy_orders[s_bid], VEL_TAKE_CAP)
                        if qty > 0:
                            vel_orders.append(Order(VEL_UNDERLYING, s_bid, -qty))
                            taker_fired = True
                    elif z < -VEL_Z_TAKER and und_pos < VEL_POS_LIMIT:
                        qty = min(VEL_POS_LIMIT - und_pos, abs(s_od.sell_orders[s_ask]), VEL_TAKE_CAP)
                        if qty > 0:
                            vel_orders.append(Order(VEL_UNDERLYING, s_ask, qty))
                            taker_fired = True

                    # MAKER
                    if not taker_fired and spread > 1:
                        skew   = und_pos / VEL_SKEW_DIV
                        my_bid = int(round(mu_vel - VEL_MM_HALF - skew))
                        my_ask = int(round(mu_vel + VEL_MM_HALF - skew))
                        my_bid = min(my_bid, s_ask - 1)
                        my_ask = max(my_ask, s_bid + 1)

                        buy_cap  = VEL_POS_LIMIT - und_pos
                        sell_cap = VEL_POS_LIMIT + und_pos
                        if buy_cap > 0:
                            vel_orders.append(Order(VEL_UNDERLYING, my_bid, min(buy_cap, VEL_MM_SIZE)))
                        if sell_cap > 0:
                            vel_orders.append(Order(VEL_UNDERLYING, my_ask, -min(sell_cap, VEL_MM_SIZE)))

                    result[VEL_UNDERLYING] = vel_orders

        # ───────────────────────────────────────────────────────────────────
        #  3) OPTIONS VEV_* (voucher)
        # ───────────────────────────────────────────────────────────────────
        if opt_prev_ts >= 0 and state.timestamp < opt_prev_ts:
            opt_days += 1
        tick    = opt_days * 10000 + state.timestamp // 100
        T_rem   = max(TOTAL_TICKS - tick, 100)

        if VEL_UNDERLYING in depths:
            s_od = depths[VEL_UNDERLYING]
            if s_od.buy_orders and s_od.sell_orders:
                S_opt = (max(s_od.buy_orders.keys()) + min(s_od.sell_orders.keys())) / 2.0

                opt_s_hist.append(S_opt)
                if len(opt_s_hist) > OPT_MEAN_WINDOW:
                    opt_s_hist.pop(0)

                if len(opt_s_hist) >= 50:
                    mu_opt  = sum(opt_s_hist) / len(opt_s_hist)
                    kappa   = math.log(2.0) / HALF_LIFE
                    decay   = math.exp(-kappa * T_rem)
                    E_dS    = (mu_opt - S_opt) * (1.0 - decay)
                    var_kT  = 2.0 * kappa * T_rem
                    var_rat = (1.0 - math.exp(-var_kT)) / var_kT if var_kT > 1e-9 else 1.0

                    # IV de référence ATM
                    ivs = []
                    for opt_name in ATM_STRIKES:
                        if opt_name in depths:
                            od = depths[opt_name]
                            if od.buy_orders and od.sell_orders:
                                mid = (max(od.buy_orders.keys()) + min(od.sell_orders.keys())) / 2.0
                                ivs.append(implied_vol(mid, S_opt, STRIKES[opt_name], T_rem))
                    sigma     = sum(ivs) / len(ivs) if ivs else DEFAULT_SIGMA
                    sigma_eff = sigma * math.sqrt(var_rat)

                    use_mr = T_rem >= MIN_T_REM

                    for opt_name in OPTIONS:
                        if opt_name not in depths:
                            continue
                        K   = STRIKES[opt_name]
                        od  = depths[opt_name]
                        o_pos = pos.get(opt_name, 0)
                        opt_orders: List[Order] = []

                        if K <= 5000:
                            edge = 1.5
                            theo_bs = bs_call(S_opt, K, T_rem, sigma)
                            d = bs_delta(S_opt, K, T_rem, sigma)
                            v = bs_vega(S_opt, K, T_rem, sigma)
                            if use_mr:
                                theo = theo_bs + MR_STRENGTH * (d * E_dS + v * (sigma_eff - sigma))
                            else:
                                theo = theo_bs
                        else:
                            edge = 0.5
                            mid = (max(od.buy_orders.keys()) + min(od.sell_orders.keys())) / 2.0
                            intrinsic = max(S_opt - K, 0)
                            if S_opt > K:
                                d_emp = 0.3 + 0.4 * min(intrinsic / 100.0, 1.0)
                            else:
                                d_emp = 0.1 + 0.2 * max(1.0 - (K - S_opt) / 200.0, 0.0)
                            theo = mid + d_emp * E_dS

                        if od.sell_orders:
                            ba = min(od.sell_orders.keys())
                            if ba < theo - edge:
                                qty = min(OPT_POS_LIMIT - o_pos, abs(od.sell_orders[ba]), OPT_TAKE_CAP)
                                if qty > 0:
                                    opt_orders.append(Order(opt_name, ba, qty))
                        if od.buy_orders:
                            bb = max(od.buy_orders.keys())
                            if bb > theo + edge:
                                qty = min(OPT_POS_LIMIT + o_pos, od.buy_orders[bb], OPT_TAKE_CAP)
                                if qty > 0:
                                    opt_orders.append(Order(opt_name, bb, -qty))

                        result[opt_name] = opt_orders

        # ── Persist ──
        td["hp_hist"]     = hp_hist
        td["vel_s_hist"]  = vel_s_hist
        td["opt_s_hist"]  = opt_s_hist
        td["opt_prev_ts"] = state.timestamp
        td["opt_days"]    = opt_days

        trader_data_str = json.dumps(td)
        logger.flush(state, result, conversions, trader_data_str)
        return result, conversions, trader_data_str