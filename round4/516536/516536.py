"""
Stratégie multi-produit — Round 2

Exploite 5 anomalies identifiées :
1. VEF (sous-jacent) : mean-reversion autour de 5247, MM classique
2. VEV_5200 : surcote massive (50 de time value), vendre
3. VEV_5300 : surcote structurelle d'IV, vendre  
4. VEV_6000 / VEV_6500 : deep OTM à 0.5, arb / lottery tickets
5. HGP : drift haussier intraday, acheter tôt vendre tard
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


# ═══════════════════════════════════════════════════════════════════════════
# PARAMÈTRES GLOBAUX
# ═══════════════════════════════════════════════════════════════════════════
UNDERLYING = "VELVETFRUIT_EXTRACT"
HYDROGEL   = "HYDROGEL"

STRIKES = {
    "VEV_5100": 5100,
    "VEV_5200": 5200,
    "VEV_5300": 5300,
    "VEV_6000": 6000,
    "VEV_6500": 6500,
}
OPTIONS = list(STRIKES.keys())

POS_LIMIT    = 300
TOTAL_TICKS  = 30000
DEFAULT_SIGMA = 0.000207

# Mean-reversion sous-jacent
VEF_MEAN     = 5247.0   # mean-reversion anchor
MEAN_WINDOW  = 2000
HALF_LIFE    = 30000
MIN_T_REM    = 200

# ═══════════════════════════════════════════════════════════════════════════
# GESTION INVENTAIRE (par produit)
# ═══════════════════════════════════════════════════════════════════════════
INVENTORY_SKEW  = 0.015
EDGE_PER_POS    = 0.008
SOFT_LIMIT      = 200
TAKE_CAP        = 30
UNWIND_EDGE     = 0.2
PASSIVE_WIDTH   = 1.5
PASSIVE_QTY     = 20

# ═══════════════════════════════════════════════════════════════════════════
# PARAMÈTRES HYDROGEL
# ═══════════════════════════════════════════════════════════════════════════
HGP_POS_LIMIT   = 300     # à vérifier selon les règles du round
HGP_MEAN        = 9986.0  # milieu du range 9891-10081
HGP_SIGMA       = 34.6
HGP_MM_EDGE     = 2.0     # edge pour market making
HGP_INV_SKEW    = 0.03    # skew inventaire
HGP_TAKE_CAP    = 30
HGP_DRIFT_BIAS  = 0.5     # biais haussier : on est légèrement plus agressif à l'achat

# ═══════════════════════════════════════════════════════════════════════════
# PARAMÈTRES DEEP OTM (6000, 6500)
# ═══════════════════════════════════════════════════════════════════════════
DEEP_OTM_FAIR   = 0.5     # valeur théorique quasi-nulle
DEEP_OTM_SELL_ABOVE = 1.0 # vendre au-dessus de 1
DEEP_OTM_BUY_BELOW  = 0.5 # acheter en-dessous (lottery tickets)

# ═══════════════════════════════════════════════════════════════════════════
# BLACK-SCHOLES
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
# HELPERS INVENTAIRE
# ═══════════════════════════════════════════════════════════════════════════
def compute_edge_option(pos: int, adding: bool, base_edge: float = 0.8) -> float:
    if not adding:
        return UNWIND_EDGE
    abs_pos = abs(pos)
    edge = base_edge + EDGE_PER_POS * abs_pos
    if abs_pos > SOFT_LIMIT:
        overshoot = abs_pos - SOFT_LIMIT
        edge += 0.0005 * overshoot * overshoot
    return edge


def take_book_side(od_side, theo_adj, pos, is_buy, pos_limit, orders, symbol):
    """
    Marche dans un côté du book (asks pour acheter, bids pour vendre).
    """
    if not od_side:
        return
    
    remaining = pos_limit - pos if is_buy else pos_limit + pos
    if remaining <= 0:
        return
    
    filled = 0
    prices = sorted(od_side.keys()) if is_buy else sorted(od_side.keys(), reverse=True)
    
    for price in prices:
        current_pos = pos + filled if is_buy else pos - filled
        adding = (current_pos >= 0) if is_buy else (current_pos <= 0)
        edge = compute_edge_option(current_pos, adding)
        
        if is_buy and price < theo_adj - edge:
            vol = abs(od_side[price])
            qty = min(remaining - filled, vol, TAKE_CAP)
            if qty > 0:
                orders.append(Order(symbol, price, qty))
                filled += qty
        elif not is_buy and price > theo_adj + edge:
            vol = od_side[price] if is_buy else abs(od_side.get(price, 0)) if price in od_side else od_side[price]
            # pour les bids, la valeur est positive
            vol = od_side[price]
            qty = min(remaining - filled, vol, TAKE_CAP)
            if qty > 0:
                orders.append(Order(symbol, price, -qty))
                filled += qty
        else:
            break
        
        if filled >= remaining:
            break


# ═══════════════════════════════════════════════════════════════════════════
# TRADER
# ═══════════════════════════════════════════════════════════════════════════
class Trader:
    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0
        td = json.loads(state.traderData) if state.traderData else {}

        prev_ts  = td.get("prev_ts", -1)
        days     = td.get("days", 0)
        s_hist   = td.get("s_hist", [])
        hgp_hist = td.get("hgp_hist", [])

        if prev_ts >= 0 and state.timestamp < prev_ts:
            days += 1
        tick  = days * 10000 + state.timestamp // 100
        T_rem = max(TOTAL_TICKS - tick, 100)
        # Position dans la journée (0 = début, 1 = fin)
        intraday_pct = (state.timestamp % 1000000) / 999900.0

        def _flush():
            td["prev_ts"]  = state.timestamp
            td["days"]     = days
            td["s_hist"]   = s_hist
            td["hgp_hist"] = hgp_hist
            s = json.dumps(td)
            logger.flush(state, result, conversions, s)
            return result, conversions, s

        # ══════════════════════════════════════════════════════════════
        # 1) SOUS-JACENT VEF — Market Making mean-reversion
        # ══════════════════════════════════════════════════════════════
        S = None
        if UNDERLYING in state.order_depths:
            s_od = state.order_depths[UNDERLYING]
            if s_od.buy_orders and s_od.sell_orders:
                S = (max(s_od.buy_orders.keys()) + min(s_od.sell_orders.keys())) / 2.0
                s_hist.append(S)
                if len(s_hist) > MEAN_WINDOW:
                    s_hist.pop(0)

        if S is None or len(s_hist) < 20:
            # Pas assez de data, on trade quand même HGP et deep OTM
            pass
        else:
            # Mean-reversion
            mu    = sum(s_hist) / len(s_hist)
            kappa = math.log(2.0) / HALF_LIFE
            decay = math.exp(-kappa * T_rem)
            E_dS  = (mu - S) * (1.0 - decay)

            var_kT  = 2.0 * kappa * T_rem
            var_rat = (1.0 - math.exp(-var_kT)) / var_kT if var_kT > 1e-9 else 1.0

            # IV de référence — médiane des strikes ITM/ATM (exclure deep OTM)
            ivs = []
            for opt in ["VEV_5100", "VEV_5200"]:  # strikes fiables
                K = STRIKES[opt]
                if opt in state.order_depths:
                    od = state.order_depths[opt]
                    if od.buy_orders and od.sell_orders:
                        mid_opt = (max(od.buy_orders.keys()) + min(od.sell_orders.keys())) / 2.0
                        iv = implied_vol(mid_opt, S, K, T_rem)
                        ivs.append(iv)
            sigma = sum(ivs) / len(ivs) if ivs else DEFAULT_SIGMA
            sigma_eff = sigma * math.sqrt(var_rat)
            use_mr = T_rem >= MIN_T_REM

            # ══════════════════════════════════════════════════════════
            # 2) OPTIONS ITM/ATM — BS + MR + vente de surcote
            # ══════════════════════════════════════════════════════════
            for opt in ["VEV_5100", "VEV_5200", "VEV_5300"]:
                if opt not in state.order_depths:
                    continue
                K   = STRIKES[opt]
                od  = state.order_depths[opt]
                pos = state.position.get(opt, 0)
                orders: List[Order] = []

                # Prix théorique
                theo_bs = bs_call(S, K, T_rem, sigma)
                d = bs_delta(S, K, T_rem, sigma)
                v = bs_vega(S, K, T_rem, sigma)

                if use_mr:
                    theo = theo_bs + d * E_dS + v * (sigma_eff - sigma)
                else:
                    theo = theo_bs

                # Skew inventaire
                skew = -pos * INVENTORY_SKEW
                theo_adj = theo + skew

                remaining_buy  = POS_LIMIT - pos
                remaining_sell = POS_LIMIT + pos

                # Prendre le book — acheter les asks cheap
                if od.sell_orders and remaining_buy > 0:
                    bought = 0
                    for ask_price in sorted(od.sell_orders.keys()):
                        adding = (pos + bought) >= 0
                        edge = compute_edge_option(pos + bought, adding)
                        if ask_price < theo_adj - edge:
                            qty = min(remaining_buy - bought, abs(od.sell_orders[ask_price]), TAKE_CAP)
                            if qty > 0:
                                orders.append(Order(opt, ask_price, qty))
                                bought += qty
                        else:
                            break
                        if bought >= remaining_buy:
                            break

                # Prendre le book — vendre les bids chers
                if od.buy_orders and remaining_sell > 0:
                    sold = 0
                    for bid_price in sorted(od.buy_orders.keys(), reverse=True):
                        adding = (pos - sold) <= 0
                        edge = compute_edge_option(pos - sold, adding)
                        if bid_price > theo_adj + edge:
                            qty = min(remaining_sell - sold, od.buy_orders[bid_price], TAKE_CAP)
                            if qty > 0:
                                orders.append(Order(opt, bid_price, -qty))
                                sold += qty
                        else:
                            break
                        if sold >= remaining_sell:
                            break

                # Quoting passif pour déboucler
                if abs(pos) > 30:
                    if pos > 0:
                        ask_passif = round(theo_adj + PASSIVE_WIDTH)
                        qty = min(pos, PASSIVE_QTY, remaining_sell)
                        if qty > 0:
                            orders.append(Order(opt, ask_passif, -qty))
                    elif pos < 0:
                        bid_passif = round(theo_adj - PASSIVE_WIDTH)
                        qty = min(-pos, PASSIVE_QTY, remaining_buy)
                        if qty > 0:
                            orders.append(Order(opt, bid_passif, qty))

                result[opt] = orders

            # ══════════════════════════════════════════════════════════
            # 3) DEEP OTM — VEV_6000 & VEV_6500
            #    Valeur théorique ≈ 0, marché à 0.5
            #    Stratégie : vendre si bid > 0.5, acheter si ask < 0.5
            # ══════════════════════════════════════════════════════════
            for opt in ["VEV_6000", "VEV_6500"]:
                if opt not in state.order_depths:
                    continue
                od  = state.order_depths[opt]
                pos = state.position.get(opt, 0)
                orders: List[Order] = []

                # Ces options valent presque rien — BS donne ~0
                K = STRIKES[opt]
                theo_deep = bs_call(S, K, T_rem, sigma)
                # En pratique theo_deep ≈ 0, le marché cote 0.5

                remaining_buy  = POS_LIMIT - pos
                remaining_sell = POS_LIMIT + pos

                # Vendre si quelqu'un bid au-dessus de la fair value
                if od.buy_orders and remaining_sell > 0:
                    for bid_price in sorted(od.buy_orders.keys(), reverse=True):
                        if bid_price >= DEEP_OTM_SELL_ABOVE:
                            qty = min(remaining_sell, od.buy_orders[bid_price], TAKE_CAP)
                            if qty > 0:
                                orders.append(Order(opt, bid_price, -qty))
                                remaining_sell -= qty

                # Acheter très cheap comme lottery ticket (optionnel, petit size)
                if od.sell_orders and remaining_buy > 0 and pos <= 50:
                    for ask_price in sorted(od.sell_orders.keys()):
                        if ask_price <= DEEP_OTM_BUY_BELOW:
                            qty = min(10, remaining_buy, abs(od.sell_orders[ask_price]))
                            if qty > 0:
                                orders.append(Order(opt, ask_price, qty))
                            break

                # Débouclage passif
                if pos > 30:
                    orders.append(Order(opt, 1, -min(pos, PASSIVE_QTY)))
                elif pos < -30:
                    orders.append(Order(opt, 0, min(-pos, PASSIVE_QTY)))

                result[opt] = orders

        # ══════════════════════════════════════════════════════════════
        # 4) HYDROGEL — Drift haussier intraday + MM
        # ══════════════════════════════════════════════════════════════
        if HYDROGEL in state.order_depths:
            hgp_od = state.order_depths[HYDROGEL]
            if hgp_od.buy_orders and hgp_od.sell_orders:
                hgp_bid = max(hgp_od.buy_orders.keys())
                hgp_ask = min(hgp_od.sell_orders.keys())
                hgp_mid = (hgp_bid + hgp_ask) / 2.0
                hgp_hist.append(hgp_mid)
                if len(hgp_hist) > MEAN_WINDOW:
                    hgp_hist.pop(0)

                pos = state.position.get(HYDROGEL, 0)
                orders: List[Order] = []

                # Fair value : moyenne mobile + biais directionnel
                if len(hgp_hist) >= 20:
                    hgp_mu = sum(hgp_hist[-200:]) / len(hgp_hist[-200:])
                else:
                    hgp_mu = hgp_mid

                # Biais haussier intraday : en début de journée on veut être long
                # En fin de journée on déboucle
                drift_adjustment = HGP_DRIFT_BIAS * (1.0 - 2.0 * intraday_pct)
                # Début: +0.5, Fin: -0.5

                theo_hgp = hgp_mu + drift_adjustment

                # Skew inventaire
                skew_hgp = -pos * HGP_INV_SKEW
                theo_hgp_adj = theo_hgp + skew_hgp

                remaining_buy  = HGP_POS_LIMIT - pos
                remaining_sell = HGP_POS_LIMIT + pos

                # Acheter
                if hgp_od.sell_orders and remaining_buy > 0:
                    for ask_price in sorted(hgp_od.sell_orders.keys()):
                        if ask_price < theo_hgp_adj - HGP_MM_EDGE:
                            qty = min(remaining_buy, abs(hgp_od.sell_orders[ask_price]), HGP_TAKE_CAP)
                            if qty > 0:
                                orders.append(Order(HYDROGEL, ask_price, qty))
                                remaining_buy -= qty
                        else:
                            break

                # Vendre
                if hgp_od.buy_orders and remaining_sell > 0:
                    for bid_price in sorted(hgp_od.buy_orders.keys(), reverse=True):
                        if bid_price > theo_hgp_adj + HGP_MM_EDGE:
                            qty = min(remaining_sell, hgp_od.buy_orders[bid_price], HGP_TAKE_CAP)
                            if qty > 0:
                                orders.append(Order(HYDROGEL, bid_price, -qty))
                                remaining_sell -= qty
                        else:
                            break

                # Débouclage passif
                if abs(pos) > 50:
                    if pos > 0:
                        orders.append(Order(HYDROGEL, round(theo_hgp_adj + 1), -min(pos, 20)))
                    else:
                        orders.append(Order(HYDROGEL, round(theo_hgp_adj - 1), min(-pos, 20)))

                result[HYDROGEL] = orders

        return _flush()