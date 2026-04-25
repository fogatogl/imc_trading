"""
Stratégie options v1 — long-gamma carry sur le basket VEV ATM, delta-hedgé.

Refonte de l'ancienne stratégie OU-corrigée à la lumière des findings round 3
(`round3_findings.md`, `round3_strategy.md`).

Ce que les données *autorisent* :
  - σ_realised ≈ 0.325 (asymptote two-scale) > σ_implied ≈ 0.234 (niveau du smile).
    Edge ≈ +0.09 vol-pt → carry long-gamma délta-hedgé positif (§9-10).
  - Le niveau du smile c ≈ 0.234 est stable jour-à-jour ; sa courbure (a) flippe de
    signe entre les jours → bruit. On utilise 0.234 *constant* pour les deltas (§3-4).
  - Univers tradable : VEV_5100 / 5200 / 5300 / 5400 uniquement (§2).
    4000/4500 = intrinsèque ; 5500 = 8 SeaShells dominés par le tick 0.5 ; 6000/6500
    plancher 0.5 → IV solver renvoie NaN, aucun signal.
  - Résidus IV (v - 0.234) avec σ ≈ 0.007 vol-pt, communs aux 4 strikes (§4-5).
    Overlay : quand surface chère, on shrink le long ; quand surface bon marché, max long.

Ce que l'on jette de l'ancienne stratégie :
  - La correction OU `δ·E[ΔS]` repose sur l'AC lag-1 négative de VE (-0.155). Le
    findings §7 montre que c'est du bid-ask bounce (lags ≥ 2 ≈ 0). Pas de vrai
    mean-reversion. La correction OU est un signal fantôme → supprimée.
  - L'IV ATM live comme "fair vol" : c'est tautologiquement le mid du marché, donc
    aucun edge. On la remplace par σ_FAIR = 0.325 (réalisé, dé-bruité).
  - TOTAL_TICKS = 30000 : faux. VEV expire fin de la journée 7, donc TTE = 5j en
    début de Round 3 live (50000 ticks).

Architecture (3 couches) :
  L1  — Take long-gamma  : si ask < theo - EDGE → buy ; si bid > theo + EDGE → sell.
        theo = BS(S, K, T_yr, σ_FAIR). À σ_FAIR > σ_implied, theo > mid → biais long.
  L1b — Delta hedge VE   : target_VE = -round(basket_delta) avec δ calculé à σ_DELTA.
        Bande de tolérance HEDGE_BAND pour ne pas saigner le spread de VE.
  L2  — Overlay IV-dev   : ḋev = mean(IV - 0.234) sur les 4 strikes. ḋev > +1σ →
        écrase la prise (et autorise la vente plus tôt) ; ḋev < -1σ → prise max.

Hypothèses :
  - 1 tick = 100 ms ; 1 jour = 10 000 ticks = 1 000 000 ms.
  - TTE_AT_START_DAYS = 5 en live, 8 en backtest historique.
  - Pas de coût de transaction modélisé par le moteur. Le hedge band sert à limiter
    la consommation de spread VE (~1 SeaShell par traversée).
"""

from datamodel import OrderDepth, TradingState, Order, Symbol, Listing, Observation, Trade, ProsperityEncoder
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

# Univers tradable (round3 §2). Les autres strikes sont soit à l'intrinsèque,
# soit plancher-pegged à 0.5, soit dominés par le bruit de quantification.
STRIKES: Dict[str, int] = {
    "VEV_5100": 5100,
    "VEV_5200": 5200,
    "VEV_5300": 5300,
    "VEV_5400": 5400,
}
OPTIONS = list(STRIKES.keys())

# Vols (annualisées). σ_DELTA = niveau du smile stable (round3 §4).
# σ_FAIR = vol réalisée after two-scale noise correction (round3 strategy doc §1).
SIGMA_DELTA = 0.234
SIGMA_FAIR  = 0.325

# Time-to-expiry. VEV expire fin du jour 7 (round3 background).
# Live = 5 j ; backtest sur les 3 jours historiques = 8 j.
TTE_AT_START_DAYS = 5
TICKS_PER_DAY_MS  = 1_000_000          # 10 000 ticks × 100 ms
DAYS_PER_YEAR     = 365.0

# Position limits (du brief).
VOUCHER_LIMIT = 300
VE_LIMIT      = 200

# Take logic.
EDGE_TAKE  = 1.5      # SeaShells de marge minimum pour traverser le book
TAKE_CAP   = 50       # taille max d'un take en un tick

# Delta-hedge band. Le rebalancing VE consomme le spread (~1 SeaShell par tour).
# Bande = 3 → ~ une trade VE par mouvement de 2 SeaShells (round3 strategy §5.2).
HEDGE_BAND      = 3
HARD_HEDGE_BAND = 30   # cross VE spread si la dérive explose

# Couche 2 : overlay IV-residual. Modulation du PLAFOND de position long.
# Edge modulation est inutile ici : σ_FAIR > σ_IMPL crée un écart theo-mid de
# 15-20 SeaShells, donc EDGE_TAKE=1.5 est trivialement franchi. Pour réellement
# laisser de la place à la mean-reversion de l'IV-dev, on borne la position long
# en fonction de z_dev (cf. round3 strategy §4.2 : "rich → réduire de 30%").
IV_DEV_SIGMA  = 0.007       # std typique des résidus (round3 §4)
RICH_THRESH   = +1.0        # surface ≥ +1σ chère → cap réduit
CHEAP_THRESH  = -1.0        # surface ≤ -1σ bon marché → cap max
RICH_CAP_MULT = 0.7         # 70% de VOUCHER_LIMIT quand rich

# Sécurité fin de partie : T très court → carry diminue, theta domine, fermer.
MIN_TTE_DAYS = 2.0


# ─── BS pure ───────────────────────────────────────────────────────────────
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

def implied_vol(target, S, K, T, lo=1e-4, hi=2.0):
    """IV solver, σ en unités annualisées (T = years). Renvoie None si non solvable."""
    intrinsic = max(S - K, 0.0)
    if target <= intrinsic + 1e-6:
        return None
    if bs_call(S, K, T, hi) < target:
        return None
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if bs_call(S, K, T, mid) > target:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def best_bid_ask(od: OrderDepth):
    if od is None or not od.buy_orders or not od.sell_orders:
        return None, None, 0, 0
    bid = max(od.buy_orders.keys())
    ask = min(od.sell_orders.keys())
    return bid, ask, od.buy_orders[bid], abs(od.sell_orders[ask])


# ─── Trader ────────────────────────────────────────────────────────────────
class Trader:
    def run(self, state: TradingState) -> Tuple[Dict[Symbol, List[Order]], int, str]:
        result: Dict[Symbol, List[Order]] = {}
        conversions = 0
        td = json.loads(state.traderData) if state.traderData else {}

        # Tracking jour : `state.timestamp` se reset chaque jour à 0.
        prev_ts = td.get("prev_ts", -1)
        days    = td.get("days", 0)
        if prev_ts >= 0 and state.timestamp < prev_ts:
            days += 1

        elapsed_days = days + state.timestamp / TICKS_PER_DAY_MS
        tte_days = max(0.01, TTE_AT_START_DAYS - elapsed_days)
        T = tte_days / DAYS_PER_YEAR

        flatten_mode = tte_days <= MIN_TTE_DAYS

        def _flush():
            td["prev_ts"] = state.timestamp
            td["days"] = days
            s = json.dumps(td)
            logger.flush(state, result, conversions, s)
            return result, conversions, s

        # Underlying mid.
        ve_od = state.order_depths.get(UNDERLYING)
        ve_bid, ve_ask, ve_bid_sz, ve_ask_sz = best_bid_ask(ve_od)
        if ve_bid is None:
            return _flush()
        S = 0.5 * (ve_bid + ve_ask)

        # ─ Layer 2 — overlay IV-residual (mesuré sur l'instant).
        # On invertit BS sur chaque strike viable et on regarde la moyenne du
        # déviation par rapport à 0.234. Si le solver échoue (NaN), strike skippé.
        ivs = []
        for sym in OPTIONS:
            od = state.order_depths.get(sym)
            bid, ask, _, _ = best_bid_ask(od)
            if bid is None:
                continue
            mid = 0.5 * (bid + ask)
            iv = implied_vol(mid, S, STRIKES[sym], T)
            if iv is not None:
                ivs.append(iv)
        iv_dev = (sum(ivs) / len(ivs) - SIGMA_DELTA) if ivs else 0.0
        z_dev  = iv_dev / IV_DEV_SIGMA

        # Plafond long modulé par la richesse du surface : on laisse une marge
        # quand c'est cher pour pouvoir racheter quand ça revient à la moyenne.
        long_cap = VOUCHER_LIMIT
        if z_dev > RICH_THRESH:
            long_cap = int(VOUCHER_LIMIT * RICH_CAP_MULT)

        # ─ Layer 1 — take long-gamma sur les 4 strikes ATM.
        target_basket_delta = 0.0
        for sym in OPTIONS:
            K = STRIKES[sym]
            od = state.order_depths.get(sym)
            if od is None:
                continue
            pos = state.position.get(sym, 0)

            # Pricing : σ_FAIR > σ_implied → theo > mid systématiquement → biais long.
            theo = bs_call(S, K, T, SIGMA_FAIR)
            d_for_hedge = bs_delta(S, K, T, SIGMA_DELTA)
            target_basket_delta += pos * d_for_hedge   # delta du portefeuille existant

            if flatten_mode:
                # Fin de partie : couper aux deux côtés sans biais, on flatten.
                bid, ask, bid_sz, ask_sz = best_bid_ask(od)
                if bid is None:
                    continue
                if pos > 0 and bid_sz > 0:
                    qty = min(pos, bid_sz, TAKE_CAP)
                    result[sym] = [Order(sym, bid, -qty)]
                elif pos < 0 and ask_sz > 0:
                    qty = min(-pos, ask_sz, TAKE_CAP)
                    result[sym] = [Order(sym, ask, qty)]
                continue

            orders: List[Order] = []
            # BUY : ask < theo - EDGE_TAKE, plafonné par long_cap (modulé par z_dev).
            if od.sell_orders and pos < long_cap:
                ask = min(od.sell_orders.keys())
                if ask < theo - EDGE_TAKE:
                    qty = min(long_cap - pos, abs(od.sell_orders[ask]), TAKE_CAP)
                    if qty > 0:
                        orders.append(Order(sym, ask, qty))
            # SELL : bid > theo + EDGE_TAKE. Rare quand σ_FAIR > σ_IMPL, sauf
            # excursion d'IV très large (z >> 0).
            if od.buy_orders:
                bid = max(od.buy_orders.keys())
                if bid > theo + EDGE_TAKE:
                    qty = min(VOUCHER_LIMIT + pos, od.buy_orders[bid], TAKE_CAP)
                    if qty > 0:
                        orders.append(Order(sym, bid, -qty))
            # Si surface chère et pos > long_cap, libérer l'excédent au bid.
            if pos > long_cap and od.buy_orders:
                bid = max(od.buy_orders.keys())
                qty = min(pos - long_cap, od.buy_orders[bid], TAKE_CAP)
                if qty > 0:
                    orders.append(Order(sym, bid, -qty))
            if orders:
                result[sym] = orders

        # ─ Layer 1b — Delta-hedge VE.
        # On hedge sur la base de la POSITION COURANTE (pas du target) : la prise
        # est probabiliste, on n'anticipe pas les fills. Cohérent avec un strict
        # take + hedge sans market making.
        ve_pos = state.position.get(UNDERLYING, 0)
        target_ve = -int(round(target_basket_delta))
        target_ve = max(-VE_LIMIT, min(VE_LIMIT, target_ve))
        ve_gap = target_ve - ve_pos

        if abs(ve_gap) > HEDGE_BAND:
            hard_cross = abs(ve_gap) > HARD_HEDGE_BAND
            if ve_gap > 0:
                price = ve_ask if hard_cross else ve_bid + 1
                qty = min(ve_gap, VE_LIMIT - ve_pos)
                if hard_cross and ve_ask_sz > 0:
                    qty = min(qty, ve_ask_sz)
                if qty > 0:
                    result[UNDERLYING] = [Order(UNDERLYING, price, qty)]
            else:
                price = ve_bid if hard_cross else ve_ask - 1
                qty = min(-ve_gap, VE_LIMIT + ve_pos)
                if hard_cross and ve_bid_sz > 0:
                    qty = min(qty, ve_bid_sz)
                if qty > 0:
                    result[UNDERLYING] = [Order(UNDERLYING, price, -qty)]
        else:
            result.setdefault(UNDERLYING, [])

        logger.print(f"S={S:.1f} T={tte_days:.2f}d ivdev={iv_dev:+.4f} z={z_dev:+.2f} "
                     f"basket_delta={target_basket_delta:+.1f} target_ve={target_ve:+d} "
                     f"ve_pos={ve_pos:+d}")

        return _flush()
