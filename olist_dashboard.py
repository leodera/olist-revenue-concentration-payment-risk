"""
Olist Revenue Concentration & Payment Risk Dashboard  (built with Dash)

DATA (two CSVs, produced by your SQL queries)
    dashboard_state.csv      one row per state    (27 states)
    dashboard_products.csv   one row per category (74 categories)

HOW TO RUN
    1. Keep this file next to the CSVs, or next to a folder named csv_files_from_queries
       that holds them. File names like "dashboard_state.csv" or "dashboard_state.csv.csv" both work.
    2. In a terminal:   pip install dash pandas
    3. Then:            python olist_dashboard.py
    4. Open http://127.0.0.1:8050 in your browser.

DASH VOCABULARY
    component   A building block of the page: a title (html.H1), a box (html.Div),
                a chart holder (dcc.Graph), a dropdown (dcc.Dropdown)...
    layout      The tree of components = what the page looks like. Set with app.layout.
    figure      The chart itself (a Plotly object). dcc.Graph just displays a figure.
    trace       One series inside a figure (one set of bars, one line...).
    id          A name you give a component so callbacks can find it.
    callback    A function Dash runs automatically when the user touches a control.
                Input  = the control that was changed (e.g. a slider)
                Output = the thing that gets updated (e.g. a chart)
"""
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html

# =====================================================================
# 0. SETTINGS YOU MAY WANT TO EDIT
# =====================================================================
DATA_DIR = Path(__file__).parent

# EDIT THIS so it matches exactly how revenue was built in your SQL
# (include the order-status filter you used, e.g. "delivered orders only").
REVENUE_DEFINITION = "Revenue = sum of item price (freight excluded)."

# A core category is a "promotion candidate" if it has enough orders to trust
# and a big share of its orders use 6+ credit-card installments.
MIN_ORDERS = 1000
MIN_6PLUS_PCT = 25.0

# Colours (one place, so the whole dashboard stays consistent)
NAVY, BLUE, LIGHT, ORANGE, GREY = "#1E3A8A", "#2563EB", "#BFD4FB", "#F97316", "#94A3B8"
PALE_GREY = "#CBD5E1"
TEXT, MUTED, BG = "#0F172A", "#64748B", "#F8FAFC"

TIER_LABELS = {
    "A": "A · Core (top ~80%)",
    "B": "B · Mid (next ~15%)",
    "C": "C · Tail (last ~5%)",
}


# =====================================================================
# 1. LOAD + CLEAN THE DATA
# =====================================================================
def find_csv(stem: str) -> Path:
    """Find e.g. dashboard_state.csv (or dashboard_state.csv.csv) next to this script
    or inside a csv_files_from_queries folder."""
    folders = [DATA_DIR, DATA_DIR / "csv_files_from_queries"]
    for folder in folders:
        hits = sorted(folder.glob(f"{stem}*.csv"))
        if hits:
            return hits[0]
    searched = ", ".join(str(f) for f in folders)
    raise FileNotFoundError(f"Could not find {stem}*.csv. Looked in: {searched}")


states = pd.read_csv(find_csv("dashboard_state"))
states = states.sort_values("state_revenue", ascending=False).reset_index(drop=True)
states["tier_letter"] = states["state_tier"].str[0]
states["tier"] = states["tier_letter"].map(TIER_LABELS)
states = states.rename(columns={"pct_cc_6plus_installments": "pct_6plus"})

cats = pd.read_csv(find_csv("dashboard_products"))
cats = cats.sort_values("category_revenue", ascending=False).reset_index(drop=True)
cats["tier_letter"] = cats["revenue_tier"].str[0]
cats["tier"] = cats["tier_letter"].map(TIER_LABELS)
cats = cats.rename(columns={"pct_orders_with_6plus_installments": "pct_6plus"})
cats["label"] = cats["category_name"].str.replace("_", " ", regex=False)


def money(x: float) -> str:
    """Format a number as Brazilian Real, e.g. R$ 13.59M"""
    if x >= 1e6:
        return f"R$ {x / 1e6:.2f}M"
    if x >= 1e3:
        return f"R$ {x / 1e3:.0f}K"
    return f"R$ {x:,.0f}"


# =====================================================================
# 2. DATA CHECKS (printed in the terminal when the app starts)
# =====================================================================
TOTAL_REVENUE = cats["category_revenue"].sum()
STATES_REVENUE = states["state_revenue"].sum()


def run_data_checks() -> None:
    gap = abs(TOTAL_REVENUE - STATES_REVENUE) / TOTAL_REVENUE * 100
    print(f"[check] total revenue from categories : {money(TOTAL_REVENUE)}")
    print(f"[check] total revenue from states     : {money(STATES_REVENUE)}  (gap {gap:.2f}%)")
    if gap > 1:
        print("[WARNING] State and category totals disagree by more than 1%. Re-check your joins.")
    print(f"[check] category shares add up to {cats['pct_of_total_revenue'].sum():.1f}% (should be about 100%)")
    print(f"[check] state shares add up to    {states['pct_of_total_revenue'].sum():.1f}% (should be about 100%)")


run_data_checks()

# =====================================================================
# 3. NUMBERS THE TEXT BOXES USE (never typed by hand, so they can't go stale)
# =====================================================================
n_cats, n_states = len(cats), len(states)

core_cats = cats[cats["tier_letter"] == "A"]
tail_cats = cats[cats["tier_letter"] == "C"]
n_core_cats, n_tail_cats = len(core_cats), len(tail_cats)
core_cat_share = core_cats["category_revenue"].sum() / TOTAL_REVENUE * 100
tail_cat_share = tail_cats["category_revenue"].sum() / TOTAL_REVENUE * 100
top5_cat_share = cats["pct_of_total_revenue"].head(5).sum()

core_states = states[states["tier_letter"] == "A"]
n_core_states = len(core_states)
core_state_share = core_states["pct_of_total_revenue"].sum()

top3_states = list(states["customer_state"].head(3))
top3_share = states["pct_of_total_revenue"].head(3).sum()
first_state = states.loc[0, "customer_state"]
first_share = states.loc[0, "pct_of_total_revenue"]
next_states = list(core_states["customer_state"].iloc[3:6])  # core states after the top 3

cc_min, cc_max = states["pct_credit_card"].min(), states["pct_credit_card"].max()

inst_low = core_states.loc[core_states["avg_cc_installments"].idxmin()]
inst_high = core_states.loc[core_states["avg_cc_installments"].idxmax()]
top_inst = states.nlargest(3, "avg_cc_installments")  # states with the highest installment use overall
top_inst_share = top_inst["pct_of_total_revenue"].sum()
boleto_top2 = core_states.nlargest(2, "pct_boleto")

# Which core categories are worth testing installment offers in?
promo = core_cats[
    (core_cats["total_orders"] >= MIN_ORDERS) & (core_cats["pct_6plus"] >= MIN_6PLUS_PCT)
].sort_values("category_revenue", ascending=False)
small_sample = core_cats[core_cats["total_orders"] < MIN_ORDERS]["label"].tolist()

unc = cats[cats["category_name"] == "Uncategorized"]
unc_share = unc["pct_of_total_revenue"].iloc[0] if len(unc) else 0.0


# =====================================================================
# 4. CHART BUILDERS (each function returns one Plotly figure)
# =====================================================================
def style(fig: go.Figure, title: str, height: int = 380) -> go.Figure:
    """Apply the same look to every chart."""
    fig.update_layout(
        title=dict(text=title, x=0.01, font=dict(size=16, color=TEXT)),
        template="plotly_white",
        height=height,
        margin=dict(l=55, r=30, t=60, b=50),
        font=dict(family="Segoe UI, Arial, sans-serif", size=12, color=TEXT),
        legend=dict(orientation="h", y=-0.22),
        paper_bgcolor="white",
        plot_bgcolor="white",
    )
    return fig


TIER_COLORS = {"A": BLUE, "B": LIGHT, "C": PALE_GREY}


def fig_states(top_n: int = 10) -> go.Figure:
    """Revenue by state. Core states are dark blue, mid light blue, tail grey."""
    df = states.head(top_n)
    fig = go.Figure(
        go.Bar(
            x=df["customer_state"],
            y=df["state_revenue"] / 1e6,
            marker_color=[TIER_COLORS[t] for t in df["tier_letter"]],
            text=[f"{p:.1f}%" for p in df["pct_of_total_revenue"]],
            textposition="outside",
            customdata=df[["tier", "total_orders"]],
            hovertemplate="<b>%{x}</b><br>Revenue: R$ %{y:.2f}M<br>%{customdata[0]}<br>Orders: %{customdata[1]:,}<extra></extra>",
        )
    )
    fig.update_yaxes(title_text="Revenue (R$ millions)", rangemode="tozero")
    return style(fig, f"Top {len(df)} states by revenue (label = share of total revenue)")


def fig_categories(top_n: int = 10) -> go.Figure:
    """Top N categories by revenue (horizontal bars, biggest on top)."""
    df = cats.head(top_n)
    fig = go.Figure(
        go.Bar(
            x=df["category_revenue"] / 1e6,
            y=df["label"],
            orientation="h",
            marker_color=BLUE,
            text=[f"R$ {v / 1e6:.2f}M" for v in df["category_revenue"]],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Revenue: R$ %{x:.2f}M<extra></extra>",
        )
    )
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title_text="Revenue (R$ millions)", rangemode="tozero")
    fig.update_layout(margin=dict(l=150, r=70, t=60, b=50))
    return style(fig, f"Top {top_n} categories by revenue", height=max(340, 28 * top_n + 120))


def fig_payment(selected_states: list) -> go.Figure:
    """Payment type mix for the chosen states (grouped bars)."""
    df = states[states["customer_state"].isin(selected_states)]
    fig = go.Figure()
    if df.empty:
        fig.add_annotation(text="Pick at least one state", showarrow=False, font=dict(size=14, color=MUTED))
        return style(fig, "Payment mix by state")
    for col, name, color in [
        ("pct_credit_card", "Credit card", NAVY),
        ("pct_boleto", "Boleto", ORANGE),
        ("pct_voucher", "Voucher", GREY),
    ]:
        fig.add_trace(
            go.Bar(
                name=name,
                x=df["customer_state"],
                y=df[col],
                marker_color=color,
                text=[f"{v:.1f}%" for v in df[col]],
                textposition="outside",
                hovertemplate=f"<b>%{{x}}</b><br>{name}: %{{y:.1f}}% of orders<extra></extra>",
            )
        )
    fig.update_layout(barmode="group")
    fig.update_yaxes(title_text="% of orders", ticksuffix="%", range=[0, 100])
    return style(fig, "Payment mix by state (% of orders using each type)")


def fig_state_pareto() -> go.Figure:
    """Pareto chart: bars = revenue, line = running total %. Shows how few states carry the business."""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=states["customer_state"],
            y=states["state_revenue"] / 1e6,
            name="Revenue (R$ M)",
            marker_color=[TIER_COLORS[t] for t in states["tier_letter"]],
            hovertemplate="<b>%{x}</b><br>R$ %{y:.2f}M<extra></extra>",
        )
    )
    # Label only the first few points on the line so the chart stays readable
    labels = [f"{v:.0f}%" if i < n_core_states else "" for i, v in enumerate(states["cum_pct_revenue"])]
    fig.add_trace(
        go.Scatter(
            x=states["customer_state"],
            y=states["cum_pct_revenue"],
            name="Running total %",
            yaxis="y2",
            mode="lines+markers+text",
            line=dict(color=ORANGE, width=3),
            text=labels,
            textposition="top center",
            hovertemplate="<b>%{x}</b><br>Running total: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_shape(
        type="line", xref="paper", x0=0, x1=1, yref="y2", y0=80, y1=80,
        line=dict(dash="dot", color=GREY),
    )
    fig.update_layout(
        yaxis=dict(title=dict(text="Revenue (R$ millions)"), rangemode="tozero"),
        yaxis2=dict(overlaying="y", side="right", range=[0, 105], ticksuffix="%", showgrid=False),
    )
    return style(fig, f"Revenue by state and running total (dotted line = 80%; first {n_core_states} states reach it)")


def fig_abc_donut() -> go.Figure:
    """ABC split: how much revenue the core / mid / tail categories bring in."""
    order = list(TIER_LABELS.values())
    grp = cats.groupby("tier").agg(revenue=("category_revenue", "sum"), n=("category_name", "count")).reindex(order)
    labels = [f"{t} ({int(n)} categories)" for t, n in zip(grp.index, grp["n"])]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=grp["revenue"],
            hole=0.58,
            sort=False,
            marker=dict(colors=[NAVY, BLUE, ORANGE]),
            textinfo="percent",
            hovertemplate="<b>%{label}</b><br>R$ %{value:,.0f}<br>%{percent}<extra></extra>",
        )
    )
    fig.add_annotation(
        text=f"<b>{money(TOTAL_REVENUE)}</b><br>total revenue", x=0.5, y=0.5, showarrow=False, font=dict(size=14)
    )
    fig.update_layout(legend=dict(orientation="h", y=-0.1))
    return style(fig, "Category revenue split (ABC analysis)")


def fig_state_scatter() -> go.Figure:
    """Every state: revenue (log scale) vs average credit-card installments."""
    fig = go.Figure()
    for is_core, name, color in [(True, "Core states", BLUE), (False, "Other states", GREY)]:
        df = states[(states["tier_letter"] == "A") == is_core]
        hover = [
            f"<b>{r.customer_state}</b><br>Avg installments: {r.avg_cc_installments:.1f}"
            f"<br>Orders with 6+ installments: {r.pct_6plus:.1f}%"
            f"<br>Revenue: {money(r.state_revenue)}<br>Orders: {r.total_orders:,}"
            for r in df.itertuples()
        ]
        fig.add_trace(
            go.Scatter(
                x=df["state_revenue"] / 1e6,
                y=df["avg_cc_installments"],
                mode="markers+text",
                name=name,
                text=df["customer_state"],
                textposition="top center",
                textfont=dict(size=10),
                marker=dict(
                    size=[max(7, (n ** 0.5) / 5) for n in df["total_orders"]],
                    color=color,
                    opacity=0.85,
                    line=dict(width=1, color="white"),
                ),
                hovertext=hover,
                hoverinfo="text",
            )
        )
    fig.update_xaxes(title_text="State revenue (R$ millions, log scale)", type="log")
    fig.update_yaxes(
        title_text="Avg credit-card installments",
        range=[states["avg_cc_installments"].min() - 0.4, states["avg_cc_installments"].max() + 0.5],
    )
    return style(fig, "States: revenue vs. installment use (bubble size = orders)", height=420)


def fig_category_scatter() -> go.Figure:
    """Big AND installment-heavy core categories = best places to test installment offers."""
    fig = go.Figure()
    others = core_cats.drop(promo.index)
    for df, name, color, tcolor in [
        (others, "Other core categories", GREY, MUTED),
        (promo, "Promotion candidates", ORANGE, TEXT),
    ]:
        hover = [
            f"<b>{r.label}</b><br>Avg installments: {r.avg_cc_installments:.1f}"
            f"<br>Orders with 6+ installments: {r.pct_6plus:.1f}%"
            f"<br>Revenue: {money(r.category_revenue)}<br>Orders: {r.total_orders:,}"
            for r in df.itertuples()
        ]
        fig.add_trace(
            go.Scatter(
                x=df["avg_cc_installments"],
                y=df["category_revenue"] / 1e6,
                mode="markers+text",
                name=name,
                text=df["label"],
                textposition="top center",
                textfont=dict(size=9, color=tcolor),
                marker=dict(
                    size=[max(8, (n ** 0.5) / 2.2) for n in df["total_orders"]],
                    color=color,
                    opacity=0.8,
                    line=dict(width=1, color="white"),
                ),
                hovertext=hover,
                hoverinfo="text",
            )
        )
    fig.update_xaxes(title_text="Average credit-card installments")
    fig.update_yaxes(title_text="Revenue (R$ millions)", rangemode="tozero")
    return style(fig, "Core categories: revenue vs. installment use (bubble size = orders)", height=420)


# =====================================================================
# 5. PAGE PIECES (cards, text boxes)
# =====================================================================
CARD = dict(background="white", border="1px solid #E2E8F0", borderRadius="10px", padding="14px 18px")
LABEL = dict(color=MUTED, fontSize="13px", padding="6px 6px 0")


def kpi(title: str, value: str, sub: str = "") -> html.Div:
    return html.Div(
        [
            html.Div(title, style=dict(color=MUTED, fontSize="13px")),
            html.Div(value, style=dict(fontSize="28px", fontWeight="700", color=NAVY)),
            html.Div(sub, style=dict(color=MUTED, fontSize="12px")),
        ],
        style={**CARD, "flex": "1", "minWidth": "190px"},
    )


def text_box(title: str, lines: list) -> html.Div:
    return html.Div(
        [
            html.H4(title, style=dict(margin="0 0 8px 0", color=NAVY)),
            html.Ul([html.Li(l) for l in lines], style=dict(margin=0, paddingLeft="20px", lineHeight="1.6")),
        ],
        style={**CARD, "background": "#EFF6FF", "borderColor": "#BFDBFE"},
    )


def graph(figure: go.Figure) -> html.Div:
    """A static chart in a white card."""
    return html.Div(dcc.Graph(figure=figure, config=dict(displayModeBar=False)), style={**CARD, "padding": "6px"})


def control_card(label: str, control, graph_id: str, figure: go.Figure) -> html.Div:
    """A card with a control (slider/dropdown) on top and a chart that the control updates."""
    return html.Div(
        [
            html.Div(label, style=LABEL),
            control,
            dcc.Graph(id=graph_id, figure=figure, config=dict(displayModeBar=False)),
        ],
        style={**CARD, "padding": "10px"},
    )


ROW = dict(display="flex", gap="16px", flexWrap="wrap", marginBottom="16px")
HALF = dict(flex="1", minWidth="420px")


# ---- Page 1: Executive Overview ----------------------------------------
def overview_page() -> html.Div:
    findings = [
        f"{', '.join(top3_states)} bring in {top3_share:.1f}% of revenue. {first_state} alone brings in {first_share:.1f}%.",
        f"{n_core_states} of {n_states} states bring in {core_state_share:.1f}% of revenue.",
        f"{n_core_cats} of {n_cats} categories ({n_core_cats / n_cats * 100:.0f}%) bring in {core_cat_share:.1f}% of revenue. The top 5 bring in {top5_cat_share:.1f}%.",
        f"Credit card is the main payment type in every state ({cc_min:.0f}-{cc_max:.0f}% of orders).",
    ]
    return html.Div(
        [
            html.Div(
                [
                    kpi("Total revenue", money(TOTAL_REVENUE), REVENUE_DEFINITION),
                    kpi(f"Top 3 states ({', '.join(top3_states)})", f"{top3_share:.1f}%", "share of total revenue"),
                    kpi("Core states", f"{n_core_states} of {n_states}", f"bring in {core_state_share:.1f}% of revenue"),
                    kpi("Core categories", f"{n_core_cats} of {n_cats}", f"bring in {core_cat_share:.1f}% of revenue"),
                ],
                style=ROW,
            ),
            text_box("Key findings", findings),
            html.Div(style=dict(height="16px")),
            html.Div(
                [
                    html.Div(
                        control_card(
                            "Show top N states:",
                            dcc.Slider(id="top-n-states", min=5, max=n_states, step=1, value=10,
                                       marks={5: "5", 10: "10", 15: "15", 20: "20", n_states: str(n_states)}),
                            "state-bar",
                            fig_states(10),
                        ),
                        style=HALF,
                    ),
                    html.Div(
                        control_card(
                            "Show top N categories:",
                            dcc.Slider(id="top-n-cats", min=5, max=20, step=1, value=10,
                                       marks={5: "5", 10: "10", 15: "15", 20: "20"}),
                            "category-bar",
                            fig_categories(10),
                        ),
                        style=HALF,
                    ),
                ],
                style=ROW,
            ),
            control_card(
                "Choose states to compare:",
                dcc.Dropdown(
                    id="state-picker",
                    options=[{"label": s, "value": s} for s in states["customer_state"]],
                    value=top3_states,
                    multi=True,
                ),
                "payment-mix",
                fig_payment(top3_states),
            ),
        ],
        style=dict(padding="16px 0"),
    )


# ---- Page 2: Risk Analysis -----------------------------------------------
def risk_page() -> html.Div:
    promo_names = ", ".join(promo["label"]) if len(promo) else "none met the rule"
    findings = [
        f"Revenue depends heavily on {first_state} ({first_share:.1f}%). The {n_core_states} core states together bring in {core_state_share:.1f}%.",
        f"{n_tail_cats} tail categories bring in only {tail_cat_share:.1f}% of revenue combined.",
        f"In the core states, average installments run from {inst_low['avg_cc_installments']:.1f} ({inst_low['customer_state']}) "
        f"to {inst_high['avg_cc_installments']:.1f} ({inst_high['customer_state']}).",
        f"The highest installment use is in {', '.join(top_inst['customer_state'])} "
        f"({top_inst['avg_cc_installments'].min():.1f}-{top_inst['avg_cc_installments'].max():.1f} on average), "
        f"but together they bring in only {top_inst_share:.1f}% of revenue.",
        f"Among core states, boleto use is highest in {boleto_top2.iloc[0]['customer_state']} ({boleto_top2.iloc[0]['pct_boleto']:.1f}%) "
        f"and {boleto_top2.iloc[1]['customer_state']} ({boleto_top2.iloc[1]['pct_boleto']:.1f}%).",
    ]
    recs = [
        f"Reduce dependence on {first_state}: test growth campaigns in {', '.join(top3_states[1:])} and then {', '.join(next_states)}.",
        f"Test 'pay in 6x' offers in: {promo_names} (big revenue and many 6+ installment orders).",
        f"Test boleto-friendly options (clear boleto discount, payment reminders) in {boleto_top2.iloc[0]['customer_state']} and {boleto_top2.iloc[1]['customer_state']}.",
        "These are patterns, not proof. Run small A/B tests before scaling any offer.",
    ]
    notes = [
        REVENUE_DEFINITION,
        "Payment percentages can add to slightly more than 100% because one order can use more than one payment type. Debit card is not shown.",
        f"Tiers: A = the states or categories that make up the first ~80% of revenue, B = the next ~15%, C = the last ~5%.",
        f"'Uncategorized' (products with a missing category) is {unc_share:.1f}% of revenue.",
    ]
    if small_sample:
        notes.append(
            f"Excluded from promotion candidates (fewer than {MIN_ORDERS:,} orders, too small to trust): {', '.join(small_sample)}."
        )
    return html.Div(
        [
            html.Div(
                [
                    kpi("Biggest state", f"{first_share:.1f}%", f"{first_state} share of revenue"),
                    kpi("Top 3 states", f"{top3_share:.1f}%", ", ".join(top3_states)),
                    kpi("Tail categories", f"{tail_cat_share:.1f}%", f"{n_tail_cats} categories combined"),
                    kpi("Promotion candidates", str(len(promo)), f"core categories with {MIN_6PLUS_PCT:.0f}%+ orders on 6+ installments"),
                ],
                style=ROW,
            ),
            html.Div(
                [
                    html.Div(text_box("Key findings", findings), style=HALF),
                    html.Div(text_box("Recommendations", recs), style=HALF),
                ],
                style=ROW,
            ),
            html.Div(
                [html.Div(graph(fig_state_pareto()), style=HALF), html.Div(graph(fig_abc_donut()), style=HALF)],
                style=ROW,
            ),
            html.Div(
                [html.Div(graph(fig_state_scatter()), style=HALF), html.Div(graph(fig_category_scatter()), style=HALF)],
                style=ROW,
            ),
            html.Div(
                [
                    html.Div("Notes", style=dict(fontWeight="700", color=MUTED)),
                    html.Ul(
                        [html.Li(n) for n in notes],
                        style=dict(color=MUTED, fontSize="13px", margin="4px 0 0", paddingLeft="20px"),
                    ),
                ],
                style=dict(padding="4px 8px"),
            ),
        ],
        style=dict(padding="16px 0"),
    )


# =====================================================================
# 6. THE APP: layout + callbacks
# =====================================================================
app = Dash(__name__, title="Olist Revenue & Payment Risk")
server = app.server  # lets a hosting service (e.g. Render, using gunicorn) find the app

app.layout = html.Div(
    [
        html.H1("Olist E-Commerce: Revenue Concentration & Payment Risk", style=dict(margin="0", color=NAVY, fontSize="26px")),
        html.Div(
            "Which categories and states bring in the most money, how dependent are we on a few of them, and how do customers pay?",
            style=dict(color=MUTED, margin="4px 0 14px"),
        ),
        dcc.Tabs(
            id="tabs",
            value="overview",
            children=[
                dcc.Tab(label="Executive Overview", value="overview", children=overview_page()),
                dcc.Tab(label="Risk Analysis", value="risk", children=risk_page()),
            ],
        ),
    ],
    style=dict(maxWidth="1300px", margin="0 auto", padding="20px", background=BG, fontFamily="Segoe UI, Arial, sans-serif", color=TEXT),
)


# Callback 1: the states slider (Input) redraws the state chart (Output)
@app.callback(Output("state-bar", "figure"), Input("top-n-states", "value"))
def update_state_chart(top_n):
    return fig_states(int(top_n))


# Callback 2: the categories slider (Input) redraws the category chart (Output)
@app.callback(Output("category-bar", "figure"), Input("top-n-cats", "value"))
def update_category_chart(top_n):
    return fig_categories(int(top_n))


# Callback 3: the state dropdown (Input) redraws the payment chart (Output)
@app.callback(Output("payment-mix", "figure"), Input("state-picker", "value"))
def update_payment_chart(selected_states):
    return fig_payment(selected_states or [])


if __name__ == "__main__":
    app.run(debug=True)