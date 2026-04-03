"""
IMC Prosperity 4 — Interactive Strategy Dashboard
==================================================
Run:
    pip install dash plotly pandas numpy
    python TUTORIAL_ROUND_1/interactive_dashboard.py
Then open: http://127.0.0.1:8050
"""

import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import dash
from dash import dcc, html, Input, Output

BASE = os.path.dirname(os.path.abspath(__file__))

# ── 1. Data Loading ───────────────────────────────────────────────────────────

def load_prices():
    frames = []
    for day in [-2, -1]:
        path = os.path.join(BASE, f"prices_round_0_day_{day}.csv")
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, sep=";")
        df.columns = df.columns.str.strip()
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    for col in df.columns:
        if col != "product":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def load_trades():
    frames = []
    for day in [-2, -1]:
        path = os.path.join(BASE, f"trades_round_0_day_{day}.csv")
        if not os.path.exists(path):
            continue
        df = pd.read_csv(path, sep=";")
        df.columns = df.columns.str.strip()
        df["price"]    = pd.to_numeric(df["price"],    errors="coerce")
        df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
        df["timestamp"]= pd.to_numeric(df["timestamp"],errors="coerce")
        df["day"] = day
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)

PRICES_RAW = load_prices()
TRADES_RAW = load_trades()

# Global timeline: day -2 → offset 0, day -1 → offset (MAX_TS + 100)
if not PRICES_RAW.empty:
    MAX_TS = PRICES_RAW["timestamp"].max()
    DAYS_SORTED = sorted(PRICES_RAW["day"].dropna().unique())
    DAY_OFFSET = {d: i * (MAX_TS + 100) for i, d in enumerate(DAYS_SORTED)}
    PRICES_RAW["t_global"] = PRICES_RAW["timestamp"] + PRICES_RAW["day"].map(DAY_OFFSET)
    if not TRADES_RAW.empty:
        TRADES_RAW["t_global"] = TRADES_RAW["timestamp"] + TRADES_RAW["day"].map(DAY_OFFSET)
    PRODUCTS = sorted(PRICES_RAW["product"].dropna().unique().tolist())
else:
    PRODUCTS = ["EMERALDS", "TOMATOES"]

# ── 2. Helpers ────────────────────────────────────────────────────────────────

def wall_mid(row):
    """Mid of the highest-volume bid and highest-volume ask levels."""
    max_bv, wall_bid = -1, float("nan")
    max_av, wall_ask = -1, float("nan")
    for i in range(1, 4):
        bp = row.get(f"bid_price_{i}", float("nan"))
        bv = row.get(f"bid_volume_{i}", float("nan"))
        ap = row.get(f"ask_price_{i}", float("nan"))
        av = row.get(f"ask_volume_{i}", float("nan"))
        if not pd.isna(bp) and not pd.isna(bv) and bv > max_bv:
            max_bv, wall_bid = bv, bp
        if not pd.isna(ap) and not pd.isna(av) and av > max_av:
            max_av, wall_ask = av, ap
    if not pd.isna(wall_bid) and not pd.isna(wall_ask):
        return (wall_bid + wall_ask) / 2.0
    return float("nan")

def enrich(df):
    df = df.copy().sort_values("t_global").reset_index(drop=True)
    df["wallmid"]        = df.apply(wall_mid, axis=1)
    df["spread"]         = df["ask_price_1"] - df["bid_price_1"]
    df["roll_vol_mid"]   = df["mid_price"].rolling(50, min_periods=1).std()
    df["roll_vol_diff"]  = df["mid_price"].diff().rolling(50, min_periods=1).std()
    df["spread_ma200"]   = df["spread"].rolling(200, min_periods=1).mean()
    return df

def get_fv_series(df, product):
    if product == "EMERALDS":
        return pd.Series(10000.0, index=df.index)
    return df["wallmid"]

# ── 3. Strategy Simulation ────────────────────────────────────────────────────

def simulate_strategy(df, product, mkt_trades_df=None):
    """
    Two-layer strategy simulation:
      1. Opportunistic taking  — sweep any book orders that cross FV
      2. Passive market making — simulate fills against our posted quotes
         using the historical market trade stream as a fill proxy.

    EMERALDS → FV = 10,000 (static), spread ±1 (quotes at 9999 / 10001)
    others   → FV = WallMid (dynamic), spread ±1

    Returns (trades_df, position_series, final_position, cash).
    """
    POS_LIMIT  = 80
    HALF_SPREAD = 1          # maker quote offset from FV
    position = 0
    cash = 0.0
    records = []
    positions = []

    fv_series  = get_fv_series(df, product)
    price_ts   = df["t_global"].values
    mid_arr    = df["mid_price"].values

    # ── Layer 1: opportunistic taking from price snapshots ─────────────────────
    for idx, row in df.iterrows():
        fv = fv_series.loc[idx]
        if pd.isna(fv):
            positions.append(position)
            continue
        ts = row["t_global"]

        for i in range(1, 4):
            ap = row.get(f"ask_price_{i}", float("nan"))
            av = row.get(f"ask_volume_{i}", float("nan"))
            if pd.isna(ap) or pd.isna(av) or av <= 0:
                continue
            if ap < fv and position < POS_LIMIT:
                qty = min(int(av), POS_LIMIT - position)
                if qty > 0:
                    records.append({"ts": ts, "side": "BUY", "price": ap,
                                    "qty": qty, "edge": fv - ap, "type": "take"})
                    position += qty
                    cash -= ap * qty

        for i in range(1, 4):
            bp = row.get(f"bid_price_{i}", float("nan"))
            bv = row.get(f"bid_volume_{i}", float("nan"))
            if pd.isna(bp) or pd.isna(bv) or bv <= 0:
                continue
            if bp > fv and position > -POS_LIMIT:
                qty = min(int(bv), POS_LIMIT + position)
                if qty > 0:
                    records.append({"ts": ts, "side": "SELL", "price": bp,
                                    "qty": qty, "edge": bp - fv, "type": "take"})
                    position -= qty
                    cash += bp * qty

        positions.append(position)

    # ── Layer 2: passive MM fills via market trade proxy ──────────────────────
    # When a market trade occurs at/below our bid  → seller chose us over the wall
    # When a market trade occurs at/above our ask → buyer  chose us over the wall
    if mkt_trades_df is not None and not mkt_trades_df.empty:
        mt = mkt_trades_df.sort_values("t_global").copy()
        for _, tr in mt.iterrows():
            ts       = tr["t_global"]
            tp       = tr["price"]
            qty_mkt  = int(tr.get("quantity", 1))
            # Find FV at the time of this trade
            book_idx = int(np.searchsorted(price_ts, ts, side="left").clip(0, len(price_ts) - 1))
            fv = float(fv_series.iloc[book_idx]) if product != "EMERALDS" else 10000.0
            if pd.isna(fv):
                continue
            our_bid = round(fv) - HALF_SPREAD
            our_ask = round(fv) + HALF_SPREAD

            # Trade at/below our bid → seller hits our bid (we buy)
            if tp <= our_bid and position < POS_LIMIT:
                qty = min(qty_mkt, POS_LIMIT - position)
                if qty > 0:
                    records.append({"ts": ts, "side": "BUY", "price": our_bid,
                                    "qty": qty, "edge": fv - our_bid, "type": "make"})
                    position += qty
                    cash -= our_bid * qty

            # Trade at/above our ask → buyer hits our ask (we sell)
            elif tp >= our_ask and position > -POS_LIMIT:
                qty = min(qty_mkt, POS_LIMIT + position)
                if qty > 0:
                    records.append({"ts": ts, "side": "SELL", "price": our_ask,
                                    "qty": qty, "edge": our_ask - fv, "type": "make"})
                    position -= qty
                    cash += our_ask * qty

    strat_df = pd.DataFrame(records)
    if not strat_df.empty:
        strat_df = strat_df.sort_values("ts").reset_index(drop=True)
        strat_df["cash_flow"] = strat_df.apply(
            lambda r: -r["price"] * r["qty"] if r["side"] == "BUY"
                      else r["price"] * r["qty"], axis=1
        )
        strat_df["cum_cash"] = strat_df["cash_flow"].cumsum()
        strat_df["cum_pos"]  = strat_df.apply(
            lambda r: r["qty"] if r["side"] == "BUY" else -r["qty"], axis=1
        ).cumsum()
        idx_arr = np.searchsorted(price_ts, strat_df["ts"].values, side="left")
        idx_arr = idx_arr.clip(0, len(price_ts) - 1)
        strat_df["mid_at"]  = mid_arr[idx_arr]
        strat_df["mtm_pnl"] = strat_df["cum_cash"] + strat_df["cum_pos"] * strat_df["mid_at"]

    position_series = pd.Series(positions, index=df.index[:len(positions)])
    return strat_df, position_series, position, cash

# ── 4. Filter Helpers ─────────────────────────────────────────────────────────

def filter_prices(product, day):
    df = PRICES_RAW[PRICES_RAW["product"] == product].copy()
    if day != "all":
        df = df[df["day"] == int(day)]
    return enrich(df)

def filter_trades(product, day):
    if TRADES_RAW.empty:
        return pd.DataFrame()
    sym_col = "symbol" if "symbol" in TRADES_RAW.columns else None
    if sym_col is None:
        return pd.DataFrame()
    df = TRADES_RAW[TRADES_RAW[sym_col] == product].copy()
    if day != "all":
        df = df[df["day"] == int(day)]
    return df

# ── 5. Colour Palette ─────────────────────────────────────────────────────────

C = {
    "bg":           "#0d1117",
    "panel":        "#161b22",
    "border":       "#30363d",
    "text":         "#c9d1d9",
    "subtext":      "#8b949e",
    "EMERALDS":     "#2ECC71",
    "TOMATOES":     "#E74C3C",
    "mid":          "#58a6ff",
    "wallmid":      "#F39C12",
    "bid":          "#3fb950",
    "ask":          "#f85149",
    "spread_fill":  "rgba(88,166,255,0.07)",
    "strat_buy":    "#79c0ff",
    "strat_sell":   "#ffa657",
    "mkt_buy":      "#56d364",
    "mkt_sell":     "#ff7b72",
    "vol_pos":      "rgba(63,185,80,0.12)",
    "vol_neg":      "rgba(248,81,73,0.12)",
    "pnl_pos":      "rgba(63,185,80,0.15)",
    "pnl_neg":      "rgba(248,81,73,0.15)",
}

_LEGEND = dict(bgcolor=C["panel"], bordercolor=C["border"], borderwidth=1, font=dict(size=11))

CHART_LAYOUT = dict(
    template="plotly_dark",
    paper_bgcolor=C["bg"],
    plot_bgcolor=C["panel"],
    font=dict(color=C["text"], family="'Inter', 'Segoe UI', sans-serif"),
    xaxis=dict(showgrid=True, gridcolor=C["border"], gridwidth=0.5,
               zeroline=False, showspikes=True, spikethickness=1),
    yaxis=dict(showgrid=True, gridcolor=C["border"], gridwidth=0.5,
               zeroline=False),
)

# ── 6. UI Helpers ─────────────────────────────────────────────────────────────

def kpi_card(label, value, unit="", color=None, sub=None):
    color = color or C["text"]
    return html.Div([
        html.Div(label, style={
            "fontSize": "10px", "color": C["subtext"],
            "textTransform": "uppercase", "letterSpacing": "0.1em",
            "marginBottom": "4px",
        }),
        html.Div([
            html.Span(str(value), style={
                "fontSize": "20px", "fontWeight": "700", "color": color
            }),
            html.Span(f" {unit}" if unit else "", style={
                "fontSize": "12px", "color": C["subtext"], "marginLeft": "3px"
            }),
        ]),
        *([] if sub is None else [html.Div(sub, style={
            "fontSize": "10px", "color": C["subtext"], "marginTop": "2px"
        })]),
    ], style={
        "background": C["panel"],
        "border":     f"1px solid {C['border']}",
        "borderRadius": "8px",
        "padding":    "12px 16px",
        "minWidth":   "130px",
        "flex":       "1",
    })

def separator():
    return html.Div(style={
        "height": "1px", "background": C["border"],
        "margin": "0 24px",
    })

# ── 7. App Layout ─────────────────────────────────────────────────────────────

app = dash.Dash(__name__, title="IMC Prosperity 4 — Strategy Dashboard")
app.layout = html.Div([

    # Header
    html.Div([
        html.Div([
            html.Span("IMC Prosperity 4", style={
                "fontSize": "18px", "fontWeight": "800", "color": C["text"],
                "letterSpacing": "-0.02em",
            }),
            html.Span("  Strategy Dashboard", style={
                "fontSize": "14px", "color": C["subtext"],
            }),
        ]),
        html.Div([
            html.Div([
                html.Label("Product", style={"fontSize": "11px", "color": C["subtext"],
                                             "marginBottom": "2px", "display": "block"}),
                dcc.Dropdown(
                    id="product-select",
                    options=[{"label": p, "value": p} for p in PRODUCTS],
                    value=PRODUCTS[0] if PRODUCTS else "EMERALDS",
                    clearable=False,
                    style={"width": "180px", "fontSize": "13px"},
                ),
            ]),
            html.Div(style={"width": "16px"}),
            html.Div([
                html.Label("Day", style={"fontSize": "11px", "color": C["subtext"],
                                         "marginBottom": "2px", "display": "block"}),
                dcc.Dropdown(
                    id="day-select",
                    options=[
                        {"label": "All Days", "value": "all"},
                        {"label": "Day −2",   "value": "-2"},
                        {"label": "Day −1",   "value": "-1"},
                    ],
                    value="all",
                    clearable=False,
                    style={"width": "140px", "fontSize": "13px"},
                ),
            ]),
            html.Div(style={"width": "16px"}),
            html.Div([
                html.Label("Overlays", style={"fontSize": "11px", "color": C["subtext"],
                                              "marginBottom": "2px", "display": "block"}),
                dcc.Checklist(
                    id="overlay-select",
                    options=[
                        {"label": " WallMid",       "value": "wallmid"},
                        {"label": " Market Trades",  "value": "mkt_trades"},
                        {"label": " Strategy Trades","value": "strat_trades"},
                        {"label": " Book Levels 2&3","value": "levels"},
                    ],
                    value=["wallmid", "mkt_trades", "strat_trades"],
                    inline=True,
                    style={"fontSize": "12px", "color": C["text"]},
                    inputStyle={"marginRight": "4px", "marginLeft": "12px"},
                ),
            ]),
        ], style={"display": "flex", "alignItems": "flex-end"}),
    ], style={
        "display":        "flex",
        "justifyContent": "space-between",
        "alignItems":     "center",
        "padding":        "14px 24px",
        "borderBottom":   f"1px solid {C['border']}",
        "background":     C["panel"],
    }),

    # KPI row
    html.Div(id="kpi-row", style={
        "display":    "flex",
        "gap":        "10px",
        "padding":    "14px 24px",
        "flexWrap":   "wrap",
    }),

    separator(),

    # Charts
    html.Div([
        # Main price chart
        dcc.Graph(id="price-chart",  config={"displayModeBar": True},
                  style={"height": "440px"}),
        separator(),
        # Volume + Spread side by side
        html.Div([
            dcc.Graph(id="volume-chart", config={"displayModeBar": False},
                      style={"height": "230px", "flex": "1"}),
            html.Div(style={"width": "1px", "background": C["border"]}),
            dcc.Graph(id="spread-chart", config={"displayModeBar": False},
                      style={"height": "230px", "flex": "1"}),
        ], style={"display": "flex"}),
        separator(),
        # PnL + Position side by side
        html.Div([
            dcc.Graph(id="pnl-chart",      config={"displayModeBar": False},
                      style={"height": "200px", "flex": "2"}),
            html.Div(style={"width": "1px", "background": C["border"]}),
            dcc.Graph(id="position-chart", config={"displayModeBar": False},
                      style={"height": "200px", "flex": "1"}),
        ], style={"display": "flex"}),
    ], style={"padding": "0 8px 12px 8px"}),

], style={
    "background":  C["bg"],
    "fontFamily":  "'Inter', 'Segoe UI', sans-serif",
    "minHeight":   "100vh",
    "color":       C["text"],
})

# ── 8. Callbacks ──────────────────────────────────────────────────────────────

@app.callback(
    [Output("price-chart",    "figure"),
     Output("volume-chart",   "figure"),
     Output("spread-chart",   "figure"),
     Output("pnl-chart",      "figure"),
     Output("position-chart", "figure"),
     Output("kpi-row",        "children")],
    [Input("product-select", "value"),
     Input("day-select",     "value"),
     Input("overlay-select", "value")],
)
def update_all(product, day, overlays):
    overlays = overlays or []
    df = filter_prices(product, day)
    mkt_trades = filter_trades(product, day)

    empty = go.Figure()
    empty.update_layout(**CHART_LAYOUT)

    if df.empty:
        no_data = [kpi_card("No data", "—")]
        return empty, empty, empty, empty, empty, no_data

    strat_df, pos_series, final_pos, _ = simulate_strategy(df, product, mkt_trades)
    fv_series = get_fv_series(df, product)
    p_color = C.get(product, C["mid"])
    ts = df["t_global"]

    # ── Price Chart ────────────────────────────────────────────────────────────
    pf = go.Figure()

    # Spread band (best bid/ask fill)
    pf.add_trace(go.Scatter(
        x=pd.concat([ts, ts[::-1]]),
        y=pd.concat([df["ask_price_1"], df["bid_price_1"][::-1]]),
        fill="toself", fillcolor=C["spread_fill"],
        line=dict(width=0), name="Spread Band",
        hoverinfo="skip", showlegend=True,
    ))

    # Book levels 2 & 3
    if "levels" in overlays:
        for i in [2, 3]:
            alpha = 0.55 if i == 2 else 0.35
            for side, color in [("bid", C["bid"]), ("ask", C["ask"])]:
                col = f"{side}_price_{i}"
                if col in df.columns:
                    pf.add_trace(go.Scatter(
                        x=ts, y=df[col], name=f"{side.title()} {i}",
                        line=dict(color=color, width=0.6, dash="dot"),
                        opacity=alpha,
                        hovertemplate=f"{side.title()} {i}: %{{y}}<extra></extra>",
                    ))

    # Best bid / ask
    pf.add_trace(go.Scatter(
        x=ts, y=df["bid_price_1"], name="Best Bid",
        line=dict(color=C["bid"], width=1.2),
        hovertemplate="Bid: %{y}<extra></extra>",
    ))
    pf.add_trace(go.Scatter(
        x=ts, y=df["ask_price_1"], name="Best Ask",
        line=dict(color=C["ask"], width=1.2),
        hovertemplate="Ask: %{y}<extra></extra>",
    ))

    # Mid price
    pf.add_trace(go.Scatter(
        x=ts, y=df["mid_price"], name="Mid Price",
        line=dict(color=C["mid"], width=1.8),
        hovertemplate="Mid: %{y:.2f}<extra></extra>",
    ))

    # WallMid / FV
    if "wallmid" in overlays:
        label = "WallMid (FV)" if product != "EMERALDS" else "Fair Value (10,000)"
        pf.add_trace(go.Scatter(
            x=ts, y=fv_series, name=label,
            line=dict(color=C["wallmid"], width=1.8, dash="dash"),
            hovertemplate="FV: %{y:.2f}<extra></extra>",
        ))

    # EMERALDS static FV line
    if product == "EMERALDS":
        pf.add_hline(y=10000,
                     line=dict(color="rgba(243,156,18,0.3)", dash="dot", width=1),
                     annotation_text="FV 10,000", annotation_font_color=C["wallmid"],
                     annotation_position="bottom left")

    # Market trade dots
    if "mkt_trades" in overlays and not mkt_trades.empty:
        mt = mkt_trades.copy()
        # Classify direction via nearest mid price
        price_ts_arr = ts.values
        mid_arr = df["mid_price"].values
        idx = np.searchsorted(price_ts_arr, mt["t_global"].values, side="left")
        idx = idx.clip(0, len(price_ts_arr) - 1)
        mt["mid_at"] = mid_arr[idx]

        mt_buy  = mt[mt["price"] >= mt["mid_at"]]
        mt_sell = mt[mt["price"] <  mt["mid_at"]]

        for subset, name, symbol, color in [
            (mt_buy,  "Market Buy (at ask)", "triangle-up",   C["mkt_buy"]),
            (mt_sell, "Market Sell (at bid)", "triangle-down", C["mkt_sell"]),
        ]:
            if subset.empty:
                continue
            pf.add_trace(go.Scatter(
                x=subset["t_global"], y=subset["price"],
                mode="markers", name=name,
                marker=dict(color=color, size=7, symbol=symbol,
                            line=dict(width=0.8, color="rgba(255,255,255,0.6)")),
                hovertemplate=f"{name}<br>Price: %{{y}}<br>Qty: %{{customdata}}<extra></extra>",
                customdata=subset["quantity"],
            ))

    # Strategy trade dots (take = star, make = diamond; buy = blue, sell = orange)
    if "strat_trades" in overlays and not strat_df.empty:
        for side, ttype, name, symbol, color in [
            ("BUY",  "take", "Strat Buy (take)",  "star",           C["strat_buy"]),
            ("SELL", "take", "Strat Sell (take)", "star",           C["strat_sell"]),
            ("BUY",  "make", "Strat Buy (make)",  "diamond",        C["strat_buy"]),
            ("SELL", "make", "Strat Sell (make)", "diamond",        C["strat_sell"]),
        ]:
            col = "type" if "type" in strat_df.columns else None
            if col:
                sub = strat_df[(strat_df["side"] == side) & (strat_df["type"] == ttype)]
            else:
                sub = strat_df[strat_df["side"] == side] if ttype == "take" else pd.DataFrame()
            if sub.empty:
                continue
            pf.add_trace(go.Scatter(
                x=sub["ts"], y=sub["price"],
                mode="markers", name=name,
                marker=dict(color=color, size=9 if ttype == "take" else 7, symbol=symbol,
                            line=dict(width=1, color="white")),
                hovertemplate=(f"{name}<br>Price: %{{y}}<br>"
                               f"Qty: %{{customdata[0]}}<br>"
                               f"Edge: %{{customdata[1]:.2f}}<extra></extra>"),
                customdata=np.stack([sub["qty"], sub["edge"]], axis=1),
            ))

    # Day separator
    if day == "all" and len(DAYS_SORTED) > 1:
        sep_ts = DAY_OFFSET[DAYS_SORTED[1]]
        pf.add_vline(x=sep_ts, line=dict(color="rgba(150,150,150,0.4)", dash="dot"),
                     annotation_text="day −2 | day −1",
                     annotation_font=dict(color=C["subtext"], size=10))

    pf.update_layout(
        **CHART_LAYOUT,
        title=dict(text=f"{product} — Price Action & Order Book", font=dict(size=14)),
        xaxis_title="Timestamp",
        yaxis_title="Price (XIRECs)",
        legend=_LEGEND,
        margin=dict(l=65, r=20, t=50, b=40),
        hovermode="x unified",
    )

    # ── Volume Chart ───────────────────────────────────────────────────────────
    vf = go.Figure()
    for i, opacity in [(1, 0.85), (2, 0.55), (3, 0.35)]:
        bv = df.get(f"bid_volume_{i}", pd.Series(dtype=float))
        av = df.get(f"ask_volume_{i}", pd.Series(dtype=float))
        vf.add_trace(go.Bar(
            x=ts, y=bv.where(bv > 0),
            name=f"Bid Depth {i}", marker_color=C["bid"], opacity=opacity,
            hovertemplate=f"Bid Vol {i}: %{{y}}<extra></extra>", showlegend=(i == 1),
        ))
        vf.add_trace(go.Bar(
            x=ts, y=(-av).where(av > 0),
            name=f"Ask Depth {i}", marker_color=C["ask"], opacity=opacity,
            hovertemplate=f"Ask Vol {i}: %{{y}}<extra></extra>", showlegend=(i == 1),
        ))

    vf.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Order Book Depth  (Bid ↑ / Ask ↓)", font=dict(size=13)),
        barmode="relative",
        xaxis_title="Timestamp",
        yaxis_title="Volume",
        margin=dict(l=65, r=20, t=40, b=35),
        hovermode="x",
    )
    vf.update_layout(legend=dict(**_LEGEND, x=1, xanchor="right"))

    # ── Spread & Volatility Chart ──────────────────────────────────────────────
    sf = go.Figure()
    sf.add_trace(go.Scatter(
        x=ts, y=df["spread"],
        fill="tozeroy", fillcolor="rgba(88,166,255,0.1)",
        line=dict(color=C["mid"], width=1),
        name="Spread", hovertemplate="Spread: %{y}<extra></extra>",
    ))
    sf.add_trace(go.Scatter(
        x=ts, y=df["spread_ma200"],
        line=dict(color=C["wallmid"], width=1.5, dash="dash"),
        name="200-tick MA", hovertemplate="MA: %{y:.2f}<extra></extra>",
    ))
    sf.add_trace(go.Scatter(
        x=ts, y=df["roll_vol_diff"],
        line=dict(color=p_color, width=1.2, dash="dot"),
        name="Δprice Vol (50t)", yaxis="y2",
        hovertemplate="Vol: %{y:.2f}<extra></extra>",
    ))
    if product == "TOMATOES":
        sf.add_hline(y=20, line=dict(color="rgba(231,76,60,0.5)", dash="dot"),
                     annotation_text="spike σ=20",
                     annotation_font=dict(color=C["ask"], size=9),
                     annotation_position="top right")

    sf.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Spread & Price Volatility", font=dict(size=13)),
        xaxis_title="Timestamp",
        yaxis_title="Spread",
        yaxis2=dict(title="Vol (Δprice)", overlaying="y", side="right",
                    showgrid=False, zeroline=False),
        margin=dict(l=65, r=65, t=40, b=35),
        hovermode="x",
    )
    sf.update_layout(legend=dict(**_LEGEND, x=0, xanchor="left"))

    # ── PnL Chart ──────────────────────────────────────────────────────────────
    pnl_fig = go.Figure()
    if not strat_df.empty and "mtm_pnl" in strat_df.columns:
        final_pnl_val = strat_df["mtm_pnl"].iloc[-1]
        fill_color = C["pnl_pos"] if final_pnl_val >= 0 else C["pnl_neg"]
        line_color  = C["bid"]    if final_pnl_val >= 0 else C["ask"]

        pnl_fig.add_trace(go.Scatter(
            x=strat_df["ts"], y=strat_df["mtm_pnl"],
            fill="tozeroy", fillcolor=fill_color,
            line=dict(color=line_color, width=2),
            name="MTM PnL",
            hovertemplate="PnL: %{y:.1f} XIRECs<extra></extra>",
        ))
        pnl_fig.add_hline(y=0, line=dict(color="rgba(255,255,255,0.25)", width=1))
    else:
        pnl_fig.add_annotation(text="No strategy trades in this window",
                               showarrow=False, font=dict(color=C["subtext"], size=13))

    pnl_fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Strategy Mark-to-Market PnL (XIRECs)", font=dict(size=13)),
        xaxis_title="Timestamp",
        yaxis_title="PnL (XIRECs)",
        showlegend=False,
        margin=dict(l=65, r=20, t=40, b=35),
    )

    # ── Position Chart ─────────────────────────────────────────────────────────
    pos_fig = go.Figure()
    if not pos_series.empty:
        pos_vals = pos_series.values[:len(ts)]
        pos_colors = [C["bid"] if v >= 0 else C["ask"] for v in pos_vals]
        pos_fig.add_trace(go.Scatter(
            x=ts[:len(pos_vals)], y=pos_vals,
            fill="tozeroy",
            fillcolor="rgba(88,166,255,0.1)",
            line=dict(color=C["mid"], width=1.5),
            name="Position",
            hovertemplate="Position: %{y} units<extra></extra>",
        ))
        pos_fig.add_hline(y=80,   line=dict(color="rgba(248,81,73,0.4)", dash="dot"),
                          annotation_text="+80 limit", annotation_position="top left",
                          annotation_font=dict(color=C["ask"], size=9))
        pos_fig.add_hline(y=-80,  line=dict(color="rgba(248,81,73,0.4)", dash="dot"),
                          annotation_text="−80 limit", annotation_position="bottom left",
                          annotation_font=dict(color=C["ask"], size=9))
        pos_fig.add_hline(y=0,    line=dict(color="rgba(255,255,255,0.2)", width=1))

    pos_fig.update_layout(
        **CHART_LAYOUT,
        title=dict(text="Strategy Position", font=dict(size=13)),
        xaxis_title="Timestamp",
        yaxis_title="Units",
        showlegend=False,
        margin=dict(l=65, r=20, t=40, b=35),
    )

    # ── KPIs ───────────────────────────────────────────────────────────────────
    final_pnl  = strat_df["mtm_pnl"].iloc[-1] if (not strat_df.empty and "mtm_pnl" in strat_df.columns) else 0
    n_strat    = len(strat_df)
    n_take     = int((strat_df["type"] == "take").sum()) if (not strat_df.empty and "type" in strat_df.columns) else 0
    n_make     = int((strat_df["type"] == "make").sum()) if (not strat_df.empty and "type" in strat_df.columns) else 0
    avg_edge   = strat_df["edge"].mean() if not strat_df.empty else 0.0
    avg_spread = df["spread"].mean()
    avg_vol    = df["roll_vol_diff"].mean()
    n_mkt      = len(mkt_trades)
    pnl_color  = C["bid"] if final_pnl >= 0 else C["ask"]

    # Max drawdown
    if not strat_df.empty and "mtm_pnl" in strat_df.columns:
        pnl_series_ = strat_df["mtm_pnl"]
        running_max = pnl_series_.cummax()
        drawdown    = (pnl_series_ - running_max).min()
    else:
        drawdown = 0.0

    kpis = html.Div([
        kpi_card("MTM PnL", f"{final_pnl:+,.0f}", "XIRECs", pnl_color,
                 sub=f"Max drawdown: {drawdown:,.0f}"),
        kpi_card("Strategy Trades", str(n_strat), "",
                 sub=f"{n_take} take / {n_make} make"),
        kpi_card("Avg Edge", f"{avg_edge:.2f}", "pts/trade",
                 sub="captured vs FV"),
        kpi_card("Avg Spread", f"{avg_spread:.2f}", "pts",
                 sub=f"median {df['spread'].median():.0f}"),
        kpi_card("Δprice Vol", f"{avg_vol:.2f}", "pts",
                 sub="σ of Δmid (50t)"),
        kpi_card("Final Position", f"{final_pos:+d}", "units",
                 color=C["bid"] if final_pos >= 0 else C["ask"]),
        kpi_card("Market Trades", str(n_mkt), "",
                 sub=f"observed in {product}"),
    ], style={"display": "flex", "gap": "10px", "flexWrap": "wrap", "width": "100%"})

    return pf, vf, sf, pnl_fig, pos_fig, [kpis]

# ── 9. Run ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  IMC Prosperity 4 — Interactive Strategy Dashboard")
    print("  http://127.0.0.1:8050")
    print("=" * 55)
    app.run(debug=True, port=8050)
