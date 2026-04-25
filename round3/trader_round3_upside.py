"""
Round 3 Trader - UPSIDE variant (scenario K).

Backtest PnL: +57,812 over 3 days (round 3, server_like fill mode).
  HYDROGEL_PACK v7 MM      : +26,173
  VELVETFRUIT_EXTRACT v7 MM:  +6,228
  VEV_4000 v7 MM           :  +8,810
  VEV_5100 v7 MM           :      +0
  VEV_5200 long scalp (300):  +11,872
  VEV_5300 long scalp (300):   +4,729

How the scalp PnL actually decomposes (critical to understand)
--------------------------------------------------------------
Of the +16,601 voucher-side PnL, ~80% is directional long-delta
exposure riding VE's +42.5 total drift in the backtest window.
The real gamma+spread edge is only ~+3.5k for these two strikes.

Hypothetical worst case if live VE drifts DOWN -30 instead of UP +42:
  - Scalp-side directional loss: 309 delta * (-72 drift swing) = -22k
  - Backtest shows +57.8k -> worst-case would be ~+35.4k

If live is roughly flat (VE range-bound): ~+51k expected.
Risk-reward compared to robust variant:
  Strategy  Best-case   Expected   Worst-case   Range
  robust    +43.9k      +43.9k     +43.9k       0
  upside    +57.8k      ~+46.6k    +35.4k       ~22k

Choose this variant if you want ranking upside and can afford the downside.

Architecture
------------
  1. Long-only scalp on VEV_5200 and VEV_5300 (post bid at best_bid+1
     when spread >= 2; fall back to take-at-ask when spread = 1).
     Accumulates toward +300 each, then holds.
  2. v7 MM on HYDROGEL_PACK, VELVETFRUIT_EXTRACT, VEV_4000, VEV_5100.

Why these two scalp strikes?
  - VEV_5200 (spread mode 3): highest gamma/contract in notebook study.
  - VEV_5300 (spread mode 2): second-highest gamma, spread too tight
    for aggressive scalp-MM combination but still contributes.
  - VEV_5100 was tested but contributes near-zero real edge;
    its fills are almost entirely on spread=1 ticks via fallback,
    so it's pure directional exposure with no spread capture. Dropped.
  - VEV_5400/5500 have spread mode = 1, can't post inside at all.
"""
import json
from typing import Any

try:
    from datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState
except ImportError:
    from prosperity4bt.datamodel import Listing, Observation, Order, OrderDepth, ProsperityEncoder, Symbol, Trade, TradingState


class Logger:
    def __init__(self) -> None:
        self.logs = ""
        self.max_log_length = 3750

    def print(self, *objects: Any, sep: str = " ", end: str = "\n") -> None:
        self.logs += sep.join(map(str, objects)) + end

    def flush(self, state: TradingState, orders: dict[Symbol, list[Order]], conversions: int, trader_data: str) -> None:
        base_length = len(
            self.to_json(
                [
                    self.compress_state(state, ""),
                    self.compress_orders(orders),
                    conversions,
                    "",
                    "",
                ]
            )
        )

        max_item_length = (self.max_log_length - base_length) // 3

        print(
            self.to_json(
                [
                    self.compress_state(state, self.truncate(state.traderData, max_item_length)),
                    self.compress_orders(orders),
                    conversions,
                    self.truncate(trader_data, max_item_length),
                    self.truncate(self.logs, max_item_length),
                ]
            )
        )

        self.logs = ""

    def compress_state(self, state: TradingState, trader_data: str) -> list[Any]:
        return [
            state.timestamp,
            trader_data,
            self.compress_listings(state.listings),
            self.compress_order_depths(state.order_depths),
            self.compress_trades(state.own_trades),
            self.compress_trades(state.market_trades),
            state.position,
            self.compress_observations(state.observations),
        ]

    def compress_listings(self, listings: dict[Symbol, Listing]) -> list[list[Any]]:
        compressed = []
        for listing in listings.values():
            compressed.append([listing.symbol, listing.product, listing.denomination])
        return compressed

    def compress_order_depths(self, order_depths: dict[Symbol, OrderDepth]) -> dict[Symbol, list[Any]]:
        compressed = {}
        for symbol, order_depth in order_depths.items():
            compressed[symbol] = [order_depth.buy_orders, order_depth.sell_orders]
        return compressed

    def compress_trades(self, trades: dict[Symbol, list[Trade]]) -> list[list[Any]]:
        compressed = []
        for arr in trades.values():
            for trade in arr:
                compressed.append(
                    [
                        trade.symbol,
                        trade.price,
                        trade.quantity,
                        trade.buyer,
                        trade.seller,
                        trade.timestamp,
                    ]
                )
        return compressed

    def compress_observations(self, observations: Observation) -> list[Any]:
        conversion_observations = {}
        for product, observation in observations.conversionObservations.items():
            conversion_observations[product] = [
                observation.bidPrice,
                observation.askPrice,
                observation.transportFees,
                observation.exportTariff,
                observation.importTariff,
                observation.sugarPrice,
                observation.sunlightIndex,
            ]
        return [observations.plainValueObservations, conversion_observations]

    def compress_orders(self, orders: dict[Symbol, list[Order]]) -> list[list[Any]]:
        compressed = []
        for arr in orders.values():
            for order in arr:
                compressed.append([order.symbol, order.price, order.quantity])
        return compressed

    def to_json(self, value: Any) -> str:
        return json.dumps(value, cls=ProsperityEncoder, separators=(",", ":"))

    def truncate(self, value: str, max_length: int) -> str:
        lo, hi = 0, min(len(value), max_length)
        out = ""
        while lo <= hi:
            mid = (lo + hi) // 2
            candidate = value[:mid]
            if len(candidate) < len(value):
                candidate += "..."
            encoded_candidate = json.dumps(candidate)
            if len(encoded_candidate) <= max_length:
                out = candidate
                lo = mid + 1
            else:
                hi = mid - 1
        return out


logger = Logger()


class Trader:
    LIMITS = {
        "HYDROGEL_PACK": 200, "VELVETFRUIT_EXTRACT": 200,
        "VEV_4000": 300, "VEV_5100": 300,
        "VEV_5200": 300, "VEV_5300": 300,
    }
    MM_SYMS = ["HYDROGEL_PACK", "VELVETFRUIT_EXTRACT", "VEV_4000", "VEV_5100"]
    SCALP_SYMS = ["VEV_5200", "VEV_5300"]
    SCALP_POS_CAP = 300
    SCALP_PASSIVE_SIZE = 50
    SCALP_TAKE_SIZE = 15

    INV_MAX_SKEW = 2
    QUOTE_SIZE = 25
    OF_THRESH = 1.5
    OF_EXTREME = 5.0
    SKEW_SHRINK = 0.3

    # v9 hydrogel aggressive overlay (HYDROGEL_PACK only).
    HG_INV_MAX_SKEW = 20
    HG_ANCHOR = 10000
    HG_K_FV = 6.0
    HG_CAP = 200
    HG_ANCHOR_BREAK_TOL = 200

    def run(self, state: TradingState) -> tuple[dict[Symbol, list[Order]], int, str]:
        result: dict[Symbol, list[Order]] = {}
        conversions = 0
        try:
            mem = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            mem = {}
        for sym in self.SCALP_SYMS:
            result[sym] = self._scalp(state, sym)
        for sym in self.MM_SYMS:
            result[sym] = self._v7(state, sym, mem)
        try:
            trader_data = json.dumps(mem)
        except Exception:
            trader_data = ""
        logger.flush(state, result, conversions, trader_data)
        return result, conversions, trader_data

    def _scalp(self, state, sym):
        if sym not in state.order_depths:
            return []
        od = state.order_depths[sym]
        pos = state.position.get(sym, 0)
        room = self.SCALP_POS_CAP - pos
        if room <= 0:
            return []
        if not (od.buy_orders and od.sell_orders):
            return []
        best_bid = max(od.buy_orders.keys())
        best_ask = min(od.sell_orders.keys())
        if best_ask - best_bid >= 2:
            size = min(self.SCALP_PASSIVE_SIZE, room)
            return [Order(sym, int(best_bid + 1), int(size))] if size > 0 else []
        ask_vol = abs(od.sell_orders[best_ask])
        take = min(room, self.SCALP_TAKE_SIZE, ask_vol)
        return [Order(sym, int(best_ask), int(take))] if take > 0 else []

    def _v7(self, state, sym, mem):
        if sym not in state.order_depths:
            return []
        od = state.order_depths[sym]
        pos = state.position.get(sym, 0)
        limit = self.LIMITS[sym]
        if not (od.buy_orders and od.sell_orders):
            return []
        bs_ = sorted(od.buy_orders.items(), key=lambda kv: -kv[0])
        as_ = sorted(od.sell_orders.items(), key=lambda kv: kv[0])
        best_bid = bs_[0][0]; best_ask = as_[0][0]

        prev_bv = mem.get(f"{sym}_pb", [0, 0, 0])
        prev_av = mem.get(f"{sym}_pa", [0, 0, 0])
        cur_bv = [abs(bs_[i][1]) if i < len(bs_) else 0 for i in range(3)]
        cur_av = [abs(as_[i][1]) if i < len(as_) else 0 for i in range(3)]
        of_dir = (sum(c - p for c, p in zip(cur_bv, prev_bv))
                - sum(c - p for c, p in zip(cur_av, prev_av)))
        mem[f"{sym}_pb"] = cur_bv
        mem[f"{sym}_pa"] = cur_av

        target = 0
        skew_max = self.INV_MAX_SKEW
        if sym == "HYDROGEL_PACK":
            mid = (best_bid + best_ask) / 2.0
            if abs(mid - self.HG_ANCHOR) <= self.HG_ANCHOR_BREAK_TOL:
                raw = -self.HG_K_FV * (mid - self.HG_ANCHOR)
                target = max(-self.HG_CAP, min(self.HG_CAP, int(round(raw))))
            skew_max = self.HG_INV_MAX_SKEW

        inv_skew = round(-skew_max * ((pos - target) / limit))
        orders = []
        if best_ask - best_bid >= 2:
            our_bid = best_bid + 1 + inv_skew
            our_ask = best_ask - 1 + inv_skew
            if our_bid >= our_ask:
                if inv_skew > 0: our_bid = our_ask - 1
                else:            our_ask = our_bid + 1
            bsz = asz = self.QUOTE_SIZE
            if of_dir >= self.OF_THRESH:
                bsz = int(self.QUOTE_SIZE * self.SKEW_SHRINK)
            if of_dir <= -self.OF_THRESH:
                asz = int(self.QUOTE_SIZE * self.SKEW_SHRINK)
            if of_dir >= self.OF_EXTREME: bsz = 0
            if of_dir <= -self.OF_EXTREME: asz = 0
            bsz = min(bsz, limit - pos)
            asz = min(asz, limit + pos)
            if bsz > 0:
                orders.append(Order(sym, int(our_bid), int(bsz)))
            if asz > 0:
                orders.append(Order(sym, int(our_ask), -int(asz)))
        return orders
