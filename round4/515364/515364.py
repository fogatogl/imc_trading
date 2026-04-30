"""
Round 4 — VEV options trader, graduated-inventory variant.

Branched from `trader_r3options_improved.py`. Same R3 OTM/ITM core +
research-aligned gates (Mark14 BUYER on K=4000, Mark67/49 VE-up pull on
K≥5200). Inventory control reworked to mirror `trader_hp9999eu_gradinv_hydrogel.py`.

Hypothesis (2026-04-27 user): position chart whips between +OPT_POS_LIMIT
and -OPT_POS_LIMIT in a few ticks because the taker quotes the full
residual capacity (or OPT_TAKE_CAP=30) the moment `bid > theo + edge` /
`ask < theo - edge` flips. Live fills are partial → realised entries are
worse than BT, exits then stuck. Self-capping to OPT_POS_LIMIT=100 was a
blunt patch — bang-bang dynamics persist at any cap.

Three structural changes vs `trader_r3options_improved.py` (port of the
HP gradinv levers — see `trader_hp9999eu_gradinv_hydrogel.py` lines 11-32):

1. Vol armor on the underlying:
   `vol_scale = min(1, VEV_VOL_TARGET / std(opt_s_hist[-50:]))`. Effective
   per-strike limit shrinks when realised VE vol spikes. Same shape as
   HP_VOL_TARGET / std(hp_hist[-50:]).

2. Graduated taker size (per side, per strike):
   `qty = min(cap, book_vol, VEV_TAKER_SIZE_K * (|edge_excess|), VEV_MAX_DELTA)`
   where `edge_excess = (theo - ba) - edge` on the buy side and
   `(bb - theo) - edge` on the sell side. Replaces the flat OPT_TAKE_CAP=30
   one-shot snap. Fills proportional to mispricing.

3. Per-tick Δ-position hard rail per strike: `VEV_MAX_DELTA = 5`. Forces
   accumulation across ticks → live partial-fill geometry matches BT.
   HP uses 15 on a 200 cap (7.5%/tick); 5 on a 300 cap is 1.7%/tick — more
   conservative because 7 correlated strikes share the same VE underlying
   and could otherwise compound to ~35/tick of net VE delta.

OPT_POS_LIMIT bumped 100 → 300 (exchange cap). Vol armor + Δ-cap +
graduated sizing now manage inventory, not a fixed self-cap. Mirrors HP
bumping HP_BASE_LIMIT back to 200 (competition cap) once the machinery
was in place.

OPT_TAKE_CAP removed — superseded by VEV_MAX_DELTA.
"""

from typing import List, Dict, Tuple, Any
import json
import math
import statistics

try:
    from datamodel import (
        OrderDepth, TradingState, Order, Symbol, Listing,
        Observation, Trade, ProsperityEncoder,
    )
except ImportError:
    from prosperity4bt.datamodel import (
        OrderDepth, TradingState, Order, Symbol, Listing,
        Observation, Trade, ProsperityEncoder,
    )


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


# Ablation toggles (carried from trader_r3options_improved.py)
USE_VE_BLOCK   = False
USE_VEV_BLOCK  = True
USE_CP_GATE    = False
USE_VEV4000    = True
USE_GATE_4000  = True
GATE_4000_BUY_PULL_CP  = None
GATE_4000_SELL_PULL_CP = "Mark 14"

USE_MARK67_GATE  = True
MARK67_BOOST     = 1
MARK67_PULL_SELL = True


VEL_UNDERLYING   = "VELVETFRUIT_EXTRACT"
VEL_POS_LIMIT    = 200
VEL_MEAN_WINDOW  = 3000
VEL_TAKE_CAP     = 40
VEL_Z_TAKER      = 1.5
VEL_MM_HALF      = 1.5
VEL_MM_SIZE      = 7
VEL_SKEW_DIV     = 30


_BASE_STRIKES = {
    "VEV_5000": 5000, "VEV_5100": 5100, "VEV_5200": 5200,
    "VEV_5300": 5300, "VEV_5400": 5400, "VEV_5500": 5500,
}
if USE_VEV4000:
    STRIKES = {"VEV_4000": 4000, **_BASE_STRIKES}
else:
    STRIKES = dict(_BASE_STRIKES)
OPTIONS         = list(STRIKES.keys())
ATM_STRIKES     = ("VEV_5200", "VEV_5300")

# Inventory levers (port of HP gradinv block — see file header).
OPT_BASE_LIMIT      = 300       # exchange cap; vol armor + Δ cap manage exposure.
VEV_VOL_TARGET      = 8.0       # std of S_opt over VEV_VOL_WINDOW.
                                # When VE realised vol > target, effective limit shrinks.
VEV_VOL_WINDOW      = 50        # mirrors HP_VOL_WINDOW.
VEV_TAKER_SIZE_K    = 2.0       # graduated qty per unit edge_excess. At 1-tick over
                                # edge: qty=2; at 5 ticks over: qty=10 (capped by Δ).
VEV_MAX_DELTA       = 5         # hard cap on |Δposition| per tick PER STRIKE.
                                # Conservative vs HP's 7.5%/tick because 7 correlated
                                # strikes share the same VE delta.

TOTAL_TICKS     = 40000
DEFAULT_SIGMA   = 0.000207
OPT_MEAN_WINDOW = 2000
HALF_LIFE       = 30000
MR_STRENGTH     = 1.0
MIN_T_REM       = 200


CP_LOOKBACK_TICKS = 50
CP_BUF_MAX        = 30


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


def _cp_buyer_match(buf, current_tick, name):
    for entry in buf:
        ts = entry[0]
        if current_tick - ts <= CP_LOOKBACK_TICKS and entry[1] == name:
            return True
    return False

def _cp_seller_match(buf, current_tick, name):
    for entry in buf:
        ts = entry[0]
        if current_tick - ts <= CP_LOOKBACK_TICKS and entry[2] == name:
            return True
    return False


class Trader:

    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0

        try:
            td = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            td = {}

        vel_s_hist  = td.get("vel_s_hist", [])
        opt_s_hist  = td.get("opt_s_hist", [])
        opt_prev_ts = td.get("opt_prev_ts", -1)
        opt_days    = td.get("opt_days", 0)
        cp_seen     = td.get("cp_seen", {})

        depths = state.order_depths
        pos    = state.position if state.position else {}

        if opt_prev_ts >= 0 and state.timestamp < opt_prev_ts:
            opt_days += 1
        tick = opt_days * 10000 + state.timestamp // 100

        for sym in (*OPTIONS, VEL_UNDERLYING):
            buf = cp_seen.get(sym, [])
            for t in state.market_trades.get(sym, []):
                buf.append([tick, t.buyer, t.seller])
            buf = [e for e in buf if tick - e[0] <= CP_LOOKBACK_TICKS][-CP_BUF_MAX:]
            cp_seen[sym] = buf

        ve_up_signal = USE_MARK67_GATE and any(
            tick - e[0] <= CP_LOOKBACK_TICKS and (e[1] == "Mark 67" or e[2] == "Mark 49")
            for e in cp_seen.get(VEL_UNDERLYING, [])
        )

        # ───────────────────────────────────────────────────────────────────
        # 1) VELVETFRUIT_EXTRACT — z-score taker + maker (R3 verbatim)
        # ───────────────────────────────────────────────────────────────────
        if USE_VE_BLOCK and VEL_UNDERLYING in depths:
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
                    mu_vel  = sum(vel_s_hist) / len(vel_s_hist)
                    var_s   = sum((x - mu_vel) ** 2 for x in vel_s_hist) / (len(vel_s_hist) - 1)
                    sigma_s = math.sqrt(var_s)
                    z       = (S_vel - mu_vel) / sigma_s if sigma_s > 1e-9 else 0.0

                    und_pos = pos.get(VEL_UNDERLYING, 0)
                    vel_orders: List[Order] = []
                    taker_fired = False

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
        # 2) VEV options — graduated-inventory taker on K∈{4000..5500}
        # ───────────────────────────────────────────────────────────────────
        if USE_VEV_BLOCK and VEL_UNDERLYING in depths:
            s_od = depths[VEL_UNDERLYING]
            if s_od.buy_orders and s_od.sell_orders:
                S_opt = (max(s_od.buy_orders.keys()) + min(s_od.sell_orders.keys())) / 2.0

                opt_s_hist.append(S_opt)
                if len(opt_s_hist) > OPT_MEAN_WINDOW:
                    opt_s_hist.pop(0)

                # Vol armor on the underlying: shrinks per-strike effective limit
                # when VE realised vol exceeds the target. Mirrors HP block.
                vol_window = opt_s_hist[-VEV_VOL_WINDOW:]
                if len(vol_window) >= 10:
                    current_vol = statistics.pstdev(vol_window)
                else:
                    current_vol = VEV_VOL_TARGET
                current_vol = max(current_vol, 1e-6)
                vol_scale = min(1.0, VEV_VOL_TARGET / current_vol)
                curr_limit = max(1, int(OPT_BASE_LIMIT * vol_scale))

                T_rem = max(TOTAL_TICKS - tick, 100)

                if len(opt_s_hist) >= 50:
                    mu_opt  = sum(opt_s_hist) / len(opt_s_hist)
                    kappa   = math.log(2.0) / HALF_LIFE
                    decay   = math.exp(-kappa * T_rem)
                    E_dS    = (mu_opt - S_opt) * (1.0 - decay)
                    var_kT  = 2.0 * kappa * T_rem
                    var_rat = (1.0 - math.exp(-var_kT)) / var_kT if var_kT > 1e-9 else 1.0

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

                        # ─── BUY-side taker: graduated by edge_excess ─────
                        if od.sell_orders:
                            ba = min(od.sell_orders.keys())
                            edge_excess = (theo - edge) - ba   # >0 → mispriced cheap
                            if edge_excess > 0:
                                graduated = VEV_TAKER_SIZE_K * edge_excess
                                cap = max(0, curr_limit - o_pos)
                                book_vol = abs(od.sell_orders[ba])
                                buy_delta_cap = VEV_MAX_DELTA
                                if ve_up_signal and K >= 5200:
                                    buy_delta_cap = VEV_MAX_DELTA * MARK67_BOOST
                                qty = int(min(cap, book_vol, graduated, buy_delta_cap))
                                if qty > 0:
                                    pull_4000_buy = (USE_GATE_4000 and K == 4000 and
                                                     GATE_4000_BUY_PULL_CP is not None and
                                                     _cp_seller_match(cp_seen.get(opt_name, []),
                                                                      tick, GATE_4000_BUY_PULL_CP))
                                    if not pull_4000_buy:
                                        opt_orders.append(Order(opt_name, ba, qty))

                        # ─── SELL-side taker: graduated by edge_excess ────
                        if od.buy_orders:
                            bb = max(od.buy_orders.keys())
                            edge_excess = bb - (theo + edge)   # >0 → mispriced rich
                            if edge_excess > 0:
                                graduated = VEV_TAKER_SIZE_K * edge_excess
                                cap = max(0, curr_limit + o_pos)
                                book_vol = od.buy_orders[bb]
                                qty = int(min(cap, book_vol, graduated, VEV_MAX_DELTA))
                                if qty > 0:
                                    pull = USE_CP_GATE and _cp_buyer_match(
                                        cp_seen.get(opt_name, []), tick, "Mark 01")
                                    pull_4000_sell = (USE_GATE_4000 and K == 4000 and
                                                      GATE_4000_SELL_PULL_CP is not None and
                                                      _cp_buyer_match(cp_seen.get(opt_name, []),
                                                                      tick, GATE_4000_SELL_PULL_CP))
                                    pull_mark67 = (MARK67_PULL_SELL and ve_up_signal and K >= 5200)
                                    if not (pull or pull_4000_sell or pull_mark67):
                                        opt_orders.append(Order(opt_name, bb, -qty))

                        result[opt_name] = opt_orders

        td["vel_s_hist"]  = vel_s_hist
        td["opt_s_hist"]  = opt_s_hist
        td["opt_prev_ts"] = state.timestamp
        td["opt_days"]    = opt_days
        td["cp_seen"]     = cp_seen

        trader_data = json.dumps(td, separators=(",", ":"))
        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data