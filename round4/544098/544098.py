"""
Concatenation of three independent traders:
  - final_hydro.py        -> HYDROGEL_PACK
  - final_voucher.py      -> VEV_5000..VEV_5500 (uses VELVETFRUIT_EXTRACT as underlying)
  - round4/final_ve.py    -> VELVETFRUIT_EXTRACT (with M67 boost)

Strategies are NOT modified. State keys are disjoint and merged in a single
mem dict. Single Logger.flush() at end of run().
"""

import json
import math
import numpy as np
from typing import Any, Dict, List, Tuple

try:
    from datamodel import (Listing, Observation, Order, OrderDepth,
                           ProsperityEncoder, Symbol, Trade, TradingState)
except ImportError:
    from prosperity4bt.datamodel import (Listing, Observation, Order, OrderDepth,
                                         ProsperityEncoder, Symbol, Trade, TradingState)


# ─── Logger (kevin-fu1 visualizer contract) ───────────────────────────────
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
# VOUCHER MODULE (from final_voucher.py)
# ═══════════════════════════════════════════════════════════════════════════
UNDERLYING = "VELVETFRUIT_EXTRACT"
STRIKES = {"VEV_5000": 5000, "VEV_5100": 5100, "VEV_5200": 5200,
           "VEV_5300": 5300, "VEV_5400": 5400, "VEV_5500": 5500}
OPTIONS = list(STRIKES.keys())
ATM_STRIKES = ("VEV_5200", "VEV_5300")

POS_LIMIT = 300
TOTAL_TICKS = 30000
DEFAULT_SIGMA = 0.000207

MEAN_WINDOW   = 2000
HALF_LIFE     = 30000
MR_STRENGTH   = 1.0
EDGE          = 1.5
TAKE_CAP      = 30
MIN_T_REM     = 200

INVENTORY_SKEW = 0.015
EDGE_PER_POS   = 0.008
SOFT_LIMIT     = 200
UNWIND_EDGE    = 0.2
PASSIVE_WIDTH  = 1.5
PASSIVE_QTY    = 20


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


def compute_edge(pos: int, adding: bool) -> float:
    if not adding:
        return UNWIND_EDGE
    abs_pos = abs(pos)
    edge = 0.8 + EDGE_PER_POS * abs_pos
    if abs_pos > SOFT_LIMIT:
        overshoot = abs_pos - SOFT_LIMIT
        edge += 0.0005 * overshoot * overshoot
    return edge


# ═══════════════════════════════════════════════════════════════════════════
# COMBINED TRADER
# ═══════════════════════════════════════════════════════════════════════════
class Trader:
    # ── HP constants (final_hydro.py) ──
    HP_MEAN = 9994
    BASE_LIMIT = 200
    HP_SHARK_DEV = 22.0
    HP_MAKER_DEV = 14.0
    HP_PASSIVE_OFFSET = 5
    VOL_TARGET = 30.0

    # ── VE constants (round4/final_ve.py) ──
    VEF = "VELVETFRUIT_EXTRACT"
    VEF_LIMIT = 200
    VEF_ANCHOR_INIT = 5247
    VEF_EMA_SPAN    = 5000
    VEF_DEV_MAKE    = 20
    VEF_DEV_EXIT    = 4
    VEF_DEV_TAKE    = 30
    VEF_SIZE        = 20
    VEF_SOFT_CAP    = 100
    VEF_COOLDOWN    = 50

    M67_NAME             = "Mark 67"
    M67_WINDOW_TICKS     = 10
    M67_VEF_BOOST_SIZE   = 30
    M67_VEF_DRIFT        = 2.24
    M67_VEV_DRIFT_RATIO  = 0.83
    M67_VEV_TAKE_CAP     = 30

    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        try:
            mem = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            mem = {}

        result: Dict[Symbol, List[Order]] = {}
        conversions = 0

        self._trade_hp(state, mem, result)
        self._trade_vouchers(state, mem, result)
        self._trade_ve(state, mem, result)

        trader_data = json.dumps(mem)
        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data

    # ─────────────────────────────────────────────────────────────────────
    # HP block (final_hydro.py)
    # ─────────────────────────────────────────────────────────────────────
    def _trade_hp(self, state, mem, result):
        hp_hist = mem.get("hp_hist", [])
        pos = state.position or {}
        depths = state.order_depths

        hp_book = depths.get("HYDROGEL_PACK")
        hp_price = self._wap(hp_book)

        if hp_price:
            hp_hist.append(hp_price)
            hp_hist = hp_hist[-50:]

            current_vol = np.std(hp_hist) if len(hp_hist) > 10 else 15.0
            vol_scale = min(1.0, self.VOL_TARGET / current_vol)
            curr_limit = int(self.BASE_LIMIT * vol_scale)

            hp_curr = pos.get("HYDROGEL_PACK", 0)

            fair_anchor = self.HP_MEAN - int((hp_curr / curr_limit) * 6)
            dev = hp_price - fair_anchor

            if abs(dev) > self.HP_SHARK_DEV:
                side_volume = sum(abs(v) for v in (hp_book.buy_orders if dev > 0 else hp_book.sell_orders).values())
                qty = min(curr_limit - abs(hp_curr), side_volume)

                if qty > 0:
                    price = max(hp_book.buy_orders.keys()) if dev > 0 else min(hp_book.sell_orders.keys())
                    result["HYDROGEL_PACK"] = [Order("HYDROGEL_PACK", int(price), int(-qty if dev > 0 else qty))]

            elif abs(dev) > self.HP_MAKER_DEV:
                if dev > 0 and hp_curr > -curr_limit:
                    result["HYDROGEL_PACK"] = [Order("HYDROGEL_PACK",
                                                     int(math.ceil(hp_price + self.HP_PASSIVE_OFFSET)),
                                                     int(-(curr_limit + hp_curr)))]
                elif dev < 0 and hp_curr < curr_limit:
                    result["HYDROGEL_PACK"] = [Order("HYDROGEL_PACK",
                                                     int(math.floor(hp_price - self.HP_PASSIVE_OFFSET)),
                                                     int(curr_limit - hp_curr))]

        mem["hp_hist"] = hp_hist

    def _wap(self, od):
        if not od or not od.buy_orders or not od.sell_orders:
            return None
        bp, ap = max(od.buy_orders.keys()), min(od.sell_orders.keys())
        bv, av = od.buy_orders[bp], abs(od.sell_orders[ap])
        return (bp * av + ap * bv) / (bv + av)

    # ─────────────────────────────────────────────────────────────────────
    # Voucher block (final_voucher.py)
    # ─────────────────────────────────────────────────────────────────────
    def _trade_vouchers(self, state, mem, result):
        prev_ts = mem.get("prev_ts", -1)
        days    = mem.get("days", 0)
        s_hist  = mem.get("s_hist", [])

        if prev_ts >= 0 and state.timestamp < prev_ts:
            days += 1
        tick  = days * 10000 + state.timestamp // 100
        T_rem = max(TOTAL_TICKS - tick, 100)

        # Persist tick state every call (matches original behavior pre-flush)
        mem["prev_ts"] = state.timestamp
        mem["days"] = days
        mem["s_hist"] = s_hist

        if UNDERLYING not in state.order_depths:
            return
        s_od = state.order_depths[UNDERLYING]
        if not s_od.buy_orders or not s_od.sell_orders:
            return

        S = (max(s_od.buy_orders.keys()) + min(s_od.sell_orders.keys())) / 2.0
        s_hist.append(S)
        if len(s_hist) > MEAN_WINDOW:
            s_hist.pop(0)
        mem["s_hist"] = s_hist

        if len(s_hist) < 50:
            return

        mu      = sum(s_hist) / len(s_hist)
        kappa   = math.log(2.0) / HALF_LIFE
        decay   = math.exp(-kappa * T_rem)
        E_dS    = (mu - S) * (1.0 - decay)
        var_kT  = 2.0 * kappa * T_rem
        var_rat = (1.0 - math.exp(-var_kT)) / var_kT if var_kT > 1e-9 else 1.0

        ivs = []
        for opt in ATM_STRIKES:
            if opt in state.order_depths:
                od = state.order_depths[opt]
                if od.buy_orders and od.sell_orders:
                    mid = (max(od.buy_orders.keys()) + min(od.sell_orders.keys())) / 2.0
                    ivs.append(implied_vol(mid, S, STRIKES[opt], T_rem))
        sigma     = sum(ivs) / len(ivs) if ivs else DEFAULT_SIGMA
        sigma_eff = sigma * math.sqrt(var_rat)

        use_mr = T_rem >= MIN_T_REM

        for opt in OPTIONS:
            if opt not in state.order_depths:
                continue
            K   = STRIKES[opt]
            od  = state.order_depths[opt]
            pos = state.position.get(opt, 0)
            orders: List[Order] = []

            theo_bs = bs_call(S, K, T_rem, sigma)
            d = bs_delta(S, K, T_rem, sigma)
            v = bs_vega(S, K, T_rem, sigma)
            if use_mr:
                theo = theo_bs + MR_STRENGTH * (d * E_dS + v * (sigma_eff - sigma))
            else:
                theo = theo_bs

            if K in (5200, 5300):
                skew     = -pos * INVENTORY_SKEW
                theo_adj = theo + skew
                remaining_buy  = POS_LIMIT - pos
                remaining_sell = POS_LIMIT + pos

                if od.sell_orders and remaining_buy > 0:
                    bought = 0
                    for ask_price in sorted(od.sell_orders.keys()):
                        adding = (pos + bought) >= 0
                        edge = compute_edge(pos + bought, adding)
                        if ask_price < theo_adj - edge:
                            qty = min(remaining_buy - bought, abs(od.sell_orders[ask_price]), TAKE_CAP)
                            if qty > 0:
                                orders.append(Order(opt, ask_price, qty))
                                bought += qty
                        else:
                            break
                        if bought >= remaining_buy:
                            break

                if od.buy_orders and remaining_sell > 0:
                    sold = 0
                    for bid_price in sorted(od.buy_orders.keys(), reverse=True):
                        adding = (pos - sold) <= 0
                        edge = compute_edge(pos - sold, adding)
                        if bid_price > theo_adj + edge:
                            qty = min(remaining_sell - sold, od.buy_orders[bid_price], TAKE_CAP)
                            if qty > 0:
                                orders.append(Order(opt, bid_price, -qty))
                                sold += qty
                        else:
                            break
                        if sold >= remaining_sell:
                            break

                if abs(pos) > 30:
                    if pos > 0:
                        qty = min(pos, PASSIVE_QTY, remaining_sell)
                        if qty > 0:
                            orders.append(Order(opt, round(theo_adj + PASSIVE_WIDTH), -qty))
                    else:
                        qty = min(-pos, PASSIVE_QTY, remaining_buy)
                        if qty > 0:
                            orders.append(Order(opt, round(theo_adj - PASSIVE_WIDTH), qty))

            elif K == 5100:
                if od.buy_orders and od.sell_orders:
                    mid = (max(od.buy_orders.keys()) + min(od.sell_orders.keys())) / 2.0
                    intrinsic = max(S - K, 0)
                    if S > K:
                        d_emp = 0.3 + 0.4 * min(intrinsic / 100.0, 1.0)
                    else:
                        d_emp = 0.1 + 0.2 * max(1.0 - (K - S) / 200.0, 0.0)
                    theo = mid + d_emp * E_dS
                edge = 0.5
                if od.sell_orders:
                    ba = min(od.sell_orders.keys())
                    if ba < theo - edge:
                        qty = min(POS_LIMIT - pos, abs(od.sell_orders[ba]), TAKE_CAP)
                        if qty > 0:
                            orders.append(Order(opt, ba, qty))
                if od.buy_orders:
                    bb = max(od.buy_orders.keys())
                    if bb > theo + edge:
                        qty = min(POS_LIMIT + pos, od.buy_orders[bb], TAKE_CAP)
                        if qty > 0:
                            orders.append(Order(opt, bb, -qty))

            else:
                edge = EDGE
                if od.sell_orders:
                    ba = min(od.sell_orders.keys())
                    if ba < theo - edge:
                        qty = min(POS_LIMIT - pos, abs(od.sell_orders[ba]), TAKE_CAP)
                        if qty > 0:
                            orders.append(Order(opt, ba, qty))
                if od.buy_orders:
                    bb = max(od.buy_orders.keys())
                    if bb > theo + edge:
                        qty = min(POS_LIMIT + pos, od.buy_orders[bb], TAKE_CAP)
                        if qty > 0:
                            orders.append(Order(opt, bb, -qty))

            result[opt] = orders

    # ─────────────────────────────────────────────────────────────────────
    # VE block (round4/final_ve.py)
    # ─────────────────────────────────────────────────────────────────────
    def _trade_ve(self, state, mem, result):
        m67_signal = self._detect_m67(state, mem)
        vef_orders = self._trade_vef(state, mem, m67_signal)
        if vef_orders:
            result[self.VEF] = vef_orders

    def _detect_m67(self, state: TradingState, mem: dict) -> int:
        last_processed = mem.get("m67_last_processed", -1)
        m67_buy_ts     = mem.get("m67_buy_ts", -10**9)

        for t in state.market_trades.get(self.VEF, []):
            if t.timestamp <= last_processed:
                continue
            if t.buyer == self.M67_NAME:
                if t.timestamp > m67_buy_ts:
                    m67_buy_ts = t.timestamp

        mem["m67_last_processed"] = state.timestamp
        mem["m67_buy_ts"]         = m67_buy_ts

        age_ticks = (state.timestamp - m67_buy_ts) // 100
        return 1 if 0 <= age_ticks <= self.M67_WINDOW_TICKS else 0

    def _scaled_size(self, pos: int, side: str,
                     base: int, soft_cap: int, limit: int) -> int:
        exposure = pos if side == "BUY" else -pos
        if exposure <= soft_cap:
            return base
        ratio = max(0.0, 1.0 - (exposure - soft_cap) / (limit - soft_cap))
        return max(1, int(base * ratio))

    def _trade_vef(self, state: TradingState, mem: dict, m67_signal: int):
        od: OrderDepth = state.order_depths.get(self.VEF)
        if not od or not od.buy_orders or not od.sell_orders:
            return []

        bb  = max(od.buy_orders.keys())
        ba  = min(od.sell_orders.keys())
        bv  = abs(od.buy_orders[bb])
        av  = abs(od.sell_orders[ba])
        mid = (bb + ba) / 2.0
        pos = state.position.get(self.VEF, 0)
        ts  = state.timestamp

        ema   = mem.get("vf_ema", self.VEF_ANCHOR_INIT)
        alpha = 2.0 / (self.VEF_EMA_SPAN + 1)
        ema   = ema + alpha * (mid - ema)
        mem["vf_ema"] = ema

        dev = mid - ema
        last_entry_ts = mem.get("vf_last_entry_ts", -10**9)
        orders: List[Order] = []

        if m67_signal == 1 and pos < self.VEF_LIMIT:
            qty = min(self.M67_VEF_BOOST_SIZE, self.VEF_LIMIT - pos, av)
            if qty > 0:
                orders.append(Order(self.VEF, ba, qty))
                mem["vf_last_entry_ts"] = ts
            return orders

        if pos > 0 and dev >= -self.VEF_DEV_EXIT:
            orders.append(Order(self.VEF, ba - 1, -pos))
            return orders
        if pos < 0 and dev <= self.VEF_DEV_EXIT:
            orders.append(Order(self.VEF, bb + 1, -pos))
            return orders

        if dev < -self.VEF_DEV_TAKE and pos < self.VEF_LIMIT:
            qty = min(self._scaled_size(pos, "BUY", self.VEF_SIZE,
                                        self.VEF_SOFT_CAP, self.VEF_LIMIT),
                      self.VEF_LIMIT - pos, av)
            if qty > 0:
                orders.append(Order(self.VEF, ba, qty))
                mem["vf_last_entry_ts"] = ts
            return orders
        if dev > self.VEF_DEV_TAKE and pos > -self.VEF_LIMIT:
            qty = min(self._scaled_size(pos, "SELL", self.VEF_SIZE,
                                        self.VEF_SOFT_CAP, self.VEF_LIMIT),
                      self.VEF_LIMIT + pos, bv)
            if qty > 0:
                orders.append(Order(self.VEF, bb, -qty))
                mem["vf_last_entry_ts"] = ts
            return orders

        if (ts - last_entry_ts) < self.VEF_COOLDOWN * 100:
            return orders

        if dev < -self.VEF_DEV_MAKE and pos < self.VEF_LIMIT:
            qty = min(self._scaled_size(pos, "BUY", self.VEF_SIZE,
                                        self.VEF_SOFT_CAP, self.VEF_LIMIT),
                      self.VEF_LIMIT - pos)
            if qty > 0:
                orders.append(Order(self.VEF, bb + 1, qty))
                mem["vf_last_entry_ts"] = ts
        elif dev > self.VEF_DEV_MAKE and pos > -self.VEF_LIMIT:
            qty = min(self._scaled_size(pos, "SELL", self.VEF_SIZE,
                                        self.VEF_SOFT_CAP, self.VEF_LIMIT),
                      self.VEF_LIMIT + pos)
            if qty > 0:
                orders.append(Order(self.VEF, ba - 1, -qty))
                mem["vf_last_entry_ts"] = ts

        return orders