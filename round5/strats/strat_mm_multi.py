"""
Multi-product passive market-maker (round 5).

Universe — 14 products: 10 from teammates' research (mostly MR_TAKER with wide
mean spreads of 6-14 ticks) + 4 pipeline MM_CANDIDATEs (GALAXY_SOUNDS_DARK_MATTER /
BLACK_HOLES, OXYGEN_SHAKE_MORNING_BREATH, SNACKPACK_PISTACHIO).

Why MM, not z-score taker:
    Earlier z-score taker on these products lost ~75k over the 3 days. Reason:
    HAC+FDR alpha IC at h=1 is ~0.04-0.06 (PIPELINE_REPORT.md §2.3), which is
    below the cost of crossing the (6-14 tick) spread. Passive MM inverts this —
    we COLLECT the spread instead of paying it.

Strategy — per product, per tick:
    1. Update EWMA fair μ (halflife = HL) and rolling σ of 1-tick returns.
    2. obi_skew = gain * obi_signal     (follow: shift fair toward book pressure;
                                          fade: shift fair against;
                                          gain boosted in high-vol regimes)
    3. inv_skew = INV_SKEW * pos        (when long, lower fair → bias toward selling)
    4. fair = μ + obi_skew - inv_skew
    5. buy_px  = floor(fair) - half_spread
       sell_px = ceil(fair)  + half_spread
    6. Inside-touch clamp: pull buy_px to bid+1, sell_px to ask-1 if outside.
    7. Vol-throttle quote size when σ > 1.3 × rv_50_mean (PIPELINE_REPORT.md §2.5).
    8. Stop quoting if |mid - μ| > STOP_DEV (regime break).

Volatility integration — per-product `vol_cap` (= rv_50_mean from
`round5/reports/<FAMILY>/volatility.csv`) drives:
  - Vol-conditioned OBI boost (gain raised when σ > vol_cap; some products show
    stronger OBI IC in the high-vol regime per vol_conditioned_ic.csv).
  - Quote-size throttle (size halved when σ > 1.3 × vol_cap, real spike only).
On this universe `vol_p90_p10_ratio` is ~1.3-1.4 — vol distribution narrow
enough that the active triggers fire rarely on the 3 backtest days, leaving
realised PnL ≈ no-vol baseline. The mechanisms are defensive scaffolding for
live regime shifts more violent than what the 3 days saw.

OBI overlay sources: archetype_assignment.csv per product (PIPELINE_REPORT.md §5.5).
"""
from __future__ import annotations

import json
import math
from typing import Any

try:
    from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
except ImportError:
    from prosperity4bt.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


# ---------- per-product config ----------
# half_spread:   how far from fair to post passive quotes (ticks)
# obi_dir/sig:   from archetype_assignment.csv — None where no OBI flag
PRODUCTS: dict[str, dict[str, Any]] = {
    # Per-product volatility config — sourced from round5/reports/<FAMILY>/volatility.csv:
    #   vol_cap = rv_50_mean (used by OBI-vol-boost + quote-size throttle)
    #   gamma   = 0.5 / rv_50_mean² (Template-A skew coeff — currently unused;
    #             tested as quadratic σ skew but didn't beat linear INV_SKEW
    #             on the 3 backtest days; kept here for live retuning).
    "PEBBLES_L":                   {"half_spread": 4, "obi_dir": None,     "obi_sig": None,    "vol_cap": 14.96, "gamma": 0.0022},
    "UV_VISOR_ORANGE":             {"half_spread": 4, "obi_dir": "follow", "obi_sig": "obi_l1","vol_cap": 10.39, "gamma": 0.0046},
    "GALAXY_SOUNDS_SOLAR_FLAMES":  {"half_spread": 5, "obi_dir": "fade",   "obi_sig": "obi_l3","vol_cap": 11.03, "gamma": 0.0041},
    "OXYGEN_SHAKE_CHOCOLATE":      {"half_spread": 4, "obi_dir": "follow", "obi_sig": "obi_l1","vol_cap": 10.25, "gamma": 0.0048},
    "OXYGEN_SHAKE_EVENING_BREATH": {"half_spread": 4, "obi_dir": "follow", "obi_sig": "obi_l1","vol_cap": 10.52, "gamma": 0.0045},
    "ROBOT_IRONING":               {"half_spread": 2, "obi_dir": None,     "obi_sig": None,    "vol_cap":  9.97, "gamma": 0.0050},
    "ROBOT_MOPPING":               {"half_spread": 2, "obi_dir": None,     "obi_sig": None,    "vol_cap": 11.07, "gamma": 0.0041},
    "MICROCHIP_CIRCLE":            {"half_spread": 3, "obi_dir": None,     "obi_sig": None,    "vol_cap":  9.16, "gamma": 0.0060},
    "TRANSLATOR_VOID_BLUE":        {"half_spread": 3, "obi_dir": "fade",   "obi_sig": "obi_l3","vol_cap": 10.77, "gamma": 0.0043},
    "TRANSLATOR_GRAPHITE_MIST":    {"half_spread": 3, "obi_dir": "fade",   "obi_sig": "obi_l3","vol_cap": 10.07, "gamma": 0.0049},
    "SNACKPACK_PISTACHIO":         {"half_spread": 8, "obi_dir": "follow", "obi_sig": "obi_l1","vol_cap":  5.22, "gamma": 0.0182},
    "GALAXY_SOUNDS_DARK_MATTER":   {"half_spread": 6, "obi_dir": "follow", "obi_sig": "obi_l1","vol_cap": 10.19, "gamma": 0.0048},
    "GALAXY_SOUNDS_BLACK_HOLES":   {"half_spread": 7, "obi_dir": "follow", "obi_sig": "obi_l1","vol_cap": 11.37, "gamma": 0.0039},
    "OXYGEN_SHAKE_MORNING_BREATH": {"half_spread": 6, "obi_dir": "follow", "obi_sig": "obi_l1","vol_cap": 10.04, "gamma": 0.0050},
    # Dropped after backtest revealed bleeding:
    #   UV_VISOR_YELLOW   (-16,844 net), UV_VISOR_MAGENTA (-4,880 net),
    #   GALAXY_SOUNDS_SOLAR_WINDS (-2,281 net) — all whipsawed by big intraday moves.
}

POSITION_LIMIT: int = 10
QUOTE_SIZE: int = 10
HL: float = 200.0                 # EWMA halflife (slow enough not to chase)
WARMUP: int = 30
INV_SKEW: float = 0.5             # ticks of fair shift per unit of inventory
OBI_GAIN: float = 4.0
OBI_VOL_BOOST: float = 0.5        # OBI_GAIN multiplied by (1 + this * max(0, σ/vol_cap - 1))
STOP_DEV: float = 50.0            # freeze when |mid - μ| > STOP_DEV
VOL_WINDOW: int = 50              # window for realised σ of 1-tick returns


# ---------- Logger ----------
class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state, orders, conversions, trader_data):
        base_length = len(self.to_json([self.compress_state(state, ""), self.compress_orders(orders), conversions, "", ""]))
        max_item_length = (self.max_log_length - base_length) // 3
        print(self.to_json([
            self.compress_state(state, self.truncate(state.traderData, max_item_length)),
            self.compress_orders(orders),
            conversions,
            self.truncate(trader_data, max_item_length),
            self.truncate(self.logs, max_item_length),
        ]))
        self.logs = ""

    def compress_state(self, state, td):
        return [state.timestamp, td,
                self.compress_listings(state.listings),
                self.compress_order_depths(state.order_depths),
                self.compress_trades(state.own_trades),
                self.compress_trades(state.market_trades),
                state.position,
                self.compress_observations(state.observations)]
    def compress_listings(self, listings): return [[l.symbol, l.product, l.denomination] for l in listings.values()]
    def compress_order_depths(self, ods): return {s: [d.buy_orders, d.sell_orders] for s, d in ods.items()}
    def compress_trades(self, trades):
        return [[t.symbol, t.price, t.quantity, t.buyer, t.seller, t.timestamp]
                for arr in trades.values() for t in arr]
    def compress_observations(self, observations):
        conv = {}
        for p, o in observations.conversionObservations.items():
            conv[p] = [getattr(o, k, None) for k in
                       ("bidPrice","askPrice","transportFees","exportTariff","importTariff","sugarPrice","sunlightIndex")]
        return [observations.plainValueObservations, conv]
    def compress_orders(self, orders): return [[o.symbol, o.price, o.quantity] for arr in orders.values() for o in arr]
    def to_json(self, v): return json.dumps(v, cls=ProsperityEncoder, separators=(",", ":"))
    def truncate(self, v, n): return v if len(v) <= n else v[: n - 3] + "..."


logger = Logger()


# ---------- helpers ----------
def best_bid_ask(depth: OrderDepth) -> tuple[int | None, int | None]:
    bid = max(depth.buy_orders.keys()) if depth.buy_orders else None
    ask = min(depth.sell_orders.keys()) if depth.sell_orders else None
    return bid, ask


def mid_of(depth: OrderDepth) -> float | None:
    bid, ask = best_bid_ask(depth)
    return (bid + ask) / 2.0 if (bid is not None and ask is not None) else None


def obi_l1_val(depth: OrderDepth, bid: int, ask: int) -> float:
    bsz = depth.buy_orders.get(bid, 0)
    asz = -depth.sell_orders.get(ask, 0)
    tot = bsz + asz
    return (bsz - asz) / tot if tot > 0 else 0.0


def obi_l3_val(depth: OrderDepth) -> float:
    top_b = sorted(depth.buy_orders.items(), reverse=True)[:3]
    top_a = sorted(depth.sell_orders.items())[:3]
    bsz = sum(v for _, v in top_b)
    asz = -sum(v for _, v in top_a)
    tot = bsz + asz
    return (bsz - asz) / tot if tot > 0 else 0.0


# ---------- EWMA ----------
ALPHA = 1.0 - math.pow(0.5, 1.0 / HL)


# ---------- Trader ----------
class Trader:
    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        try:
            mem: dict[str, Any] = json.loads(state.traderData) if state.traderData else {}
        except (ValueError, TypeError):
            mem = {}
        st: dict[str, list[float]] = mem.get("e", {})        # {product: [mu, var, n]}
        rh: dict[str, list[float]] = mem.get("r", {})        # {product: last VOL_WINDOW returns}
        last_mid: dict[str, float] = mem.get("p", {})        # {product: prev mid}

        result: dict[Symbol, list[Order]] = {}

        for product, cfg in PRODUCTS.items():
            depth = state.order_depths.get(product)
            if depth is None:
                continue
            bid, ask = best_bid_ask(depth)
            mid = mid_of(depth)
            if mid is None or bid is None or ask is None:
                continue

            mu, var, n = st.get(product, [0.0, 0.0, 0])
            if n == 0:
                mu, var = mid, 0.0
                n = 1
            else:
                delta = mid - mu
                mu = mu + ALPHA * delta
                var = (1 - ALPHA) * (var + ALPHA * delta * delta)
                n += 1
            st[product] = [mu, var, n]

            # rolling 1-tick returns for realised σ
            prev = last_mid.get(product)
            last_mid[product] = mid
            ret_hist = rh.setdefault(product, [])
            if prev is not None:
                ret_hist.append(mid - prev)
                if len(ret_hist) > VOL_WINDOW:
                    del ret_hist[: len(ret_hist) - VOL_WINDOW]

            if n < WARMUP:
                continue

            # Realised σ of 1-tick mid returns over rolling VOL_WINDOW.
            # Drives vol-conditioned OBI boost and quote-size throttle below.
            if len(ret_hist) >= 10:
                rm = sum(ret_hist) / len(ret_hist)
                rv = sum((r - rm) ** 2 for r in ret_hist) / len(ret_hist)
                sigma_ret = math.sqrt(rv)
            else:
                sigma_ret = 0.0
            vol_cap = float(cfg["vol_cap"])

            dev = mid - mu

            pos = state.position.get(product, 0)

            # OBI overlay
            if cfg["obi_sig"] == "obi_l1":
                obi = obi_l1_val(depth, bid, ask)
            elif cfg["obi_sig"] == "obi_l3":
                obi = obi_l3_val(depth)
            else:
                obi = 0.0
            # OBI gain boosted in high-vol regimes (vol_conditioned_ic.csv shows
            # several products carry stronger OBI IC when σ exceeds the mean).
            vol_ratio = (sigma_ret / vol_cap) if (sigma_ret > 0 and vol_cap > 0) else 1.0
            gain = OBI_GAIN * (1.0 + OBI_VOL_BOOST * max(0.0, vol_ratio - 1.0))
            if cfg["obi_dir"] == "follow":
                obi_shift = gain * obi
            elif cfg["obi_dir"] == "fade":
                obi_shift = -gain * obi
            else:
                obi_shift = 0.0

            inv_shift = INV_SKEW * pos
            fair = mu + obi_shift - inv_shift

            half = cfg["half_spread"]
            buy_px = int(math.floor(fair - half))
            sell_px = int(math.ceil(fair + half))

            # Inside-touch clamp (feedback_maker_quote_inside_touch).
            # If our quote is at or worse than the touch, pull it inside by 1 tick.
            if buy_px >= bid:
                buy_px = bid + 1
            if sell_px <= ask:
                sell_px = ask - 1
            if buy_px >= sell_px:
                buy_px = sell_px - 1

            # Regime break: don't quote when mid is far from μ
            if abs(mid - mu) > STOP_DEV:
                continue

            buy_room = POSITION_LIMIT - pos
            sell_room = POSITION_LIMIT + pos
            orders: list[Order] = []

            # Vol-scaled QUOTE_SIZE. Full size at calm vol; halved when σ > 1.3× vol_cap.
            # Threshold chosen so the throttle fires only on real spikes (top ~15% of vol).
            if sigma_ret > 1.3 * vol_cap and vol_cap > 0:
                size = max(2, int(round(QUOTE_SIZE * 1.3 * vol_cap / sigma_ret)))
            else:
                size = QUOTE_SIZE

            if buy_room > 0 and buy_px < ask:
                orders.append(Order(product, buy_px, min(size, buy_room)))
            if sell_room > 0 and sell_px > bid:
                orders.append(Order(product, sell_px, -min(size, sell_room)))

            if orders:
                result[product] = orders

            logger.print(f"{product[-12:]:12s} mu={mu:.1f} obi={obi:+.2f} pos={pos:+d} σ={sigma_ret:.1f} q={buy_px}/{sell_px}")

        mem["e"] = st
        mem["r"] = {p: h[-VOL_WINDOW:] for p, h in rh.items() if h}
        mem["p"] = last_mid
        td = json.dumps(mem, separators=(",", ":"))
        logger.flush(state, result, 0, td)
        return result, 0, td
