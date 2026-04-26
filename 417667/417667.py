"""
Stratégie expérimentale — pricing d'options sous l'hypothèse d'un sous-jacent
mean-reverting (Ornstein-Uhlenbeck).

Idée : la variance du sous-jacent sur l'horizon T n'est pas σ²T (GBM) mais
       Var(S_T) = (σ²/2κ)(1 - e^(-2κT))
       et l'espérance dérive vers la moyenne :
       E[S_T] = μ + (S_t - μ) e^(-κT)

On part du prix Black-Scholes BS(S, K, T, σ_implied) et on applique une
correction d'ordre 1 via les Grecs (delta, vega) :

    theo = BS + delta * E[ΔS] + vega * (σ_eff - σ_implied)

où σ_eff < σ_implied est la vol "équivalente flat" sur l'horizon T sous OU.
Theta n'entre pas explicitement dans la formule de prix instantané — on
l'expose pour pouvoir filtrer les trades quand la décroissance temporelle
domine la correction MR (T_rem trop petit).
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


# ─── Paramètres ────────────────────────────────────────────────────────────
UNDERLYING = "VELVETFRUIT_EXTRACT"
STRIKES = {"VEV_4000": 4000, "VEV_4500": 4500,
           "VEV_5000": 5000, "VEV_5100": 5100, "VEV_5200": 5200,
           "VEV_5300": 5300, "VEV_5400": 5400, "VEV_5500": 5500}
OPTIONS = list(STRIKES.keys())
ATM_STRIKES = ("VEV_5200", "VEV_5300")

POS_LIMIT = 300
TOTAL_TICKS = 30000
DEFAULT_SIGMA = 0.000207

# Hyperparams mean-reversion
MEAN_WINDOW   = 10000   # v9 : fenêtre élargie pour μ
HALF_LIFE     = 30000   # demi-vie de retour à la moyenne (en ticks)
MR_STRENGTH   = 1.5     # v16 : MR boosté à 1.5
EDGE          = 1.5     # marge minimale (seashells) pour prendre le book
TAKE_CAP      = 30
MIN_T_REM     = 200


# ─── BS pure (sans rate ni dividende) + Grecs ─────────────────────────────
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


# ─── Trader ────────────────────────────────────────────────────────────────
class Trader:
    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0
        td = json.loads(state.traderData) if state.traderData else {}

        prev_ts = td.get("prev_ts", -1)
        days    = td.get("days", 0)
        s_hist  = td.get("s_hist", [])

        if prev_ts >= 0 and state.timestamp < prev_ts:
            days += 1
        tick  = days * 10000 + state.timestamp // 100
        T_rem = max(TOTAL_TICKS - tick, 100)

        def _flush():
            td["prev_ts"] = state.timestamp
            td["days"] = days
            td["s_hist"] = s_hist
            s = json.dumps(td)
            logger.flush(state, result, conversions, s)
            return result, conversions, s

        if UNDERLYING not in state.order_depths:
            return _flush()
        s_od = state.order_depths[UNDERLYING]
        if not s_od.buy_orders or not s_od.sell_orders:
            return _flush()

        S = (max(s_od.buy_orders.keys()) + min(s_od.sell_orders.keys())) / 2.0
        s_hist.append(S)
        if len(s_hist) > MEAN_WINDOW:
            s_hist.pop(0)

        if len(s_hist) < 50:
            return _flush()

        mu      = sum(s_hist) / len(s_hist)
        kappa   = math.log(2.0) / HALF_LIFE
        decay   = math.exp(-kappa * T_rem)
        E_dS    = (mu - S) * (1.0 - decay)
        var_kT  = 2.0 * kappa * T_rem
        var_rat = (1.0 - math.exp(-var_kT)) / var_kT if var_kT > 1e-9 else 1.0

        # IV de référence depuis ATM
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

            if K <= 5000:
                # Deep ITM : stratégie originale inchangée
                edge = 1.5
                theo_bs = bs_call(S, K, T_rem, sigma)
                d = bs_delta(S, K, T_rem, sigma)
                v = bs_vega(S, K, T_rem, sigma)
                if use_mr:
                    theo = theo_bs + MR_STRENGTH * (d * E_dS + v * (sigma_eff - sigma))
                else:
                    theo = theo_bs
            else:
                # ATM : utiliser le mid price actuel + delta empirique × E_dS
                edge = 0.5
                mid = (max(od.buy_orders.keys()) + min(od.sell_orders.keys())) / 2.0
                intrinsic = max(S - K, 0)
                if S > K:
                    d_emp = 0.3 + 0.4 * min(intrinsic / 100.0, 1.0)
                else:
                    d_emp = 0.1 + 0.2 * max(1.0 - (K - S) / 200.0, 0.0)
                theo = mid + d_emp * E_dS

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
        result[UNDERLYING] = []
        return _flush()