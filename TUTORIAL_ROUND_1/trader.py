from datamodel import OrderDepth, TradingState, Order
import json
import math

# ── PARAMETERS ────────────────────────────────────────────────────────────────

# EMERALDS
EME_PRODUCT               = "EMERALDS"
EME_FAIR_VALUE            = 10_000
EME_MAKER_OFFSET          = 1
EME_ORDER_SIZE            = 10
EME_MAX_POSITION          = 50
EME_LIQUIDATION_THRESHOLD = 30

# TOMATOES
TOM_PRODUCT          = "TOMATOES"
TOM_AR_COEFS         = [-0.549, -0.317, -0.174, -0.093, -0.043]  # [L1..L5]
TOM_HALF_SPREAD      = 4.5
TOM_SKEW_PER_UNIT    = 0.2
TOM_MAX_POSITION     = 20
TOM_ORDER_SIZE       = 5
TOM_REQUOTE_THRESH   = 2.0
TOM_WARMUP_TICKS     = 10
TOM_SIGNAL_CAP       = 0.05

# ── EMERALDS FUNCTIONS ────────────────────────────────────────────────────────

def eme_scan_taker(
    depth: OrderDepth,
    position: int,
    max_position: int,
    fair_value: int,
) -> list:
    """
    Layer 1: Take all immediately profitable volume.
    Buy every ask strictly below fair_value; sell every bid strictly above fair_value.
    Processes most-profitable prices first (furthest from fair_value).
    """
    orders = []
    pos = position

    # Buy asks below fair value — sorted ascending (cheapest = most profitable first)
    for price in sorted(depth.sell_orders.keys()):
        if price >= fair_value:
            break
        available = abs(depth.sell_orders[price])  # sell_orders stored as negative ints
        room = max_position - pos
        if room <= 0:
            break
        qty = min(available, room)
        orders.append(Order(EME_PRODUCT, price, qty))
        pos += qty

    # Sell bids above fair value — sorted descending (highest = most profitable first)
    for price in sorted(depth.buy_orders.keys(), reverse=True):
        if price <= fair_value:
            break
        available = depth.buy_orders[price]  # buy_orders stored as positive ints
        room = max_position + pos
        if room <= 0:
            break
        qty = min(available, room)
        orders.append(Order(EME_PRODUCT, price, -qty))
        pos -= qty

    return orders


def eme_liquidation(
    position: int,
    threshold: int,
    fair_value: int,
) -> list:
    """
    Layer 3: Reduce excess inventory by crossing at fair value.
    Sell down to +threshold if long; buy up to -threshold if short.
    """
    if position > threshold:
        return [Order(EME_PRODUCT, fair_value, -(position - threshold))]
    if position < -threshold:
        return [Order(EME_PRODUCT, fair_value, (-position - threshold))]
    return []


def eme_maker_quotes(
    depth: OrderDepth,
    position: int,
    max_position: int,
    fair_value: int,
    offset: int,
    size: int,
) -> list:
    """
    Layer 2: Place passive bid/ask one point better than the best existing market maker.
    Never quote at or through fair_value.
    """
    orders = []

    # Best existing maker bid strictly below fair value
    maker_bids = [p for p in depth.buy_orders.keys() if p < fair_value]
    if maker_bids:
        our_bid = min(max(maker_bids) + offset, fair_value - 1)
    else:
        our_bid = fair_value - 1

    # Best existing maker ask strictly above fair value
    maker_asks = [p for p in depth.sell_orders.keys() if p > fair_value]
    if maker_asks:
        our_ask = max(min(maker_asks) - offset, fair_value + 1)
    else:
        our_ask = fair_value + 1

    if position < max_position:
        orders.append(Order(EME_PRODUCT, our_bid, size))
    if position > -max_position:
        orders.append(Order(EME_PRODUCT, our_ask, -size))

    return orders


# ── TOMATOES FUNCTIONS ────────────────────────────────────────────────────────

def tom_log_return(prev_mid: float, curr_mid: float) -> float:
    return math.log(curr_mid / prev_mid)


def tom_ar_signal(
    return_history: list,
    coefs: list,
    signal_cap: float,
) -> float:
    """
    AR(5) predicted next log return.
    return_history[0] = most recent return.
    Returns 0.0 if not enough history yet.
    """
    if len(return_history) < len(coefs):
        return 0.0
    signal = sum(coefs[i] * return_history[i] for i in range(len(coefs)))
    return max(-signal_cap, min(signal_cap, signal))


def tom_fair_value(mid: float, signal: float) -> float:
    return mid * (1.0 + signal)


def tom_quotes(
    fair_value: float,
    position: int,
    half_spread: float,
    skew_per_unit: float,
    max_position: int,
    order_size: int,
) -> list:
    """
    AR-adjusted, inventory-skewed bid and ask.
    inv_adj shifts both quotes down when long, up when short.
    """
    inv_adj = skew_per_unit * position
    bid_px  = round(fair_value - half_spread - inv_adj)
    ask_px  = round(fair_value + half_spread - inv_adj)

    orders = []
    if position < max_position:
        orders.append(Order(TOM_PRODUCT, bid_px,  order_size))
    if position > -max_position:
        orders.append(Order(TOM_PRODUCT, ask_px, -order_size))
    return orders


def tom_should_requote(prev_fv: float, curr_fv: float, threshold: float) -> bool:
    return abs(curr_fv - prev_fv) > threshold


# ── TRADER ────────────────────────────────────────────────────────────────────

class Trader:

    def run(self, state: TradingState):
        # ── Load persistent memory ─────────────────────────────────────────────
        try:
            memory = json.loads(state.traderData) if state.traderData else {}
        except Exception:
            memory = {}

        # Tomatoes state (must survive across ticks via traderData)
        tom = memory.get("tom", {
            "return_history": [],   # list[float], index 0 = most recent, max len 5
            "prev_mid":        None,
            "prev_fair_value": None,
            "tick_count":      0,
        })

        result      = {}
        conversions = 0

        # ── EMERALDS ──────────────────────────────────────────────────────────
        try:
            if EME_PRODUCT in state.order_depths:
                depth    = state.order_depths[EME_PRODUCT]
                position = state.position.get(EME_PRODUCT, 0)
                eme_orders = []

                # Layer 1: taker scan (highest priority)
                taker = eme_scan_taker(depth, position, EME_MAX_POSITION, EME_FAIR_VALUE)
                eme_orders += taker
                sim_pos = position + sum(o.quantity for o in taker)

                # Layer 3: liquidation (before placing new maker orders)
                liq = eme_liquidation(sim_pos, EME_LIQUIDATION_THRESHOLD, EME_FAIR_VALUE)
                eme_orders += liq
                sim_pos  += sum(o.quantity for o in liq)

                # Layer 2: passive maker quotes
                eme_orders += eme_maker_quotes(
                    depth, sim_pos, EME_MAX_POSITION,
                    EME_FAIR_VALUE, EME_MAKER_OFFSET, EME_ORDER_SIZE,
                )

                if eme_orders:
                    result[EME_PRODUCT] = eme_orders
        except Exception:
            pass

        # ── TOMATOES ──────────────────────────────────────────────────────────
        try:
            if TOM_PRODUCT in state.order_depths:
                depth    = state.order_depths[TOM_PRODUCT]
                position = state.position.get(TOM_PRODUCT, 0)

                best_bid = max(depth.buy_orders.keys(),  default=None)
                best_ask = min(depth.sell_orders.keys(), default=None)

                if best_bid is not None and best_ask is not None:
                    mid = (best_bid + best_ask) / 2.0

                    # Update return history (index 0 = most recent)
                    prev_mid = tom["prev_mid"]
                    if prev_mid is not None:
                        lr = tom_log_return(prev_mid, mid)
                        tom["return_history"].insert(0, lr)
                        tom["return_history"] = tom["return_history"][:5]

                    tom["prev_mid"]   = mid
                    tom["tick_count"] += 1

                    # AR(5) signal — zero during warmup
                    if tom["tick_count"] < TOM_WARMUP_TICKS:
                        signal = 0.0
                    else:
                        signal = tom_ar_signal(
                            tom["return_history"], TOM_AR_COEFS, TOM_SIGNAL_CAP
                        )

                    fv = tom_fair_value(mid, signal)

                    # Requote check (informational — IMC orders already expire each tick,
                    # but logging the condition is useful for future taker-suppression logic)
                    prev_fv = tom["prev_fair_value"]
                    # stale = prev_fv is not None and tom_should_requote(prev_fv, fv, TOM_REQUOTE_THRESH)

                    tom["prev_fair_value"] = fv

                    # Place quotes
                    tom_orders = tom_quotes(
                        fv, position,
                        TOM_HALF_SPREAD, TOM_SKEW_PER_UNIT,
                        TOM_MAX_POSITION, TOM_ORDER_SIZE,
                    )
                    if tom_orders:
                        result[TOM_PRODUCT] = tom_orders
        except Exception:
            pass

        # ── Save persistent memory ─────────────────────────────────────────────
        memory["tom"] = tom
        trader_data   = json.dumps(memory)

        return result, conversions, trader_data
