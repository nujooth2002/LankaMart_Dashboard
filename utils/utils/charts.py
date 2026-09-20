"""Plotly figures built only from the shared filtered transaction data."""

import pandas as pd
import plotly.graph_objects as go

from utils.data_processing import DELIVERY_BANDS, monthly_summary, summarize_by
from utils.themes import categorical_colors, get_theme

CHANNEL_SYMBOLS = {"Online": "circle", "Mobile App": "diamond", "Store": "square"}


def style_chart(fig: go.Figure, title: str, height: int = 340, theme="Light Mode") -> go.Figure:
    palette = get_theme(theme)
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=palette["text"]), x=0.04),
        template=palette["template"], height=height,
        font=dict(family="Inter, Segoe UI, sans-serif", size=12, color=palette["text"]),
        paper_bgcolor=palette["surface"], plot_bgcolor=palette["surface"],
        margin=dict(l=24, r=24, t=75, b=35),
        legend=dict(orientation="h", yanchor="top", y=-0.22, xanchor="left", x=0,
                    font=dict(size=11), title_text=""),
        hoverlabel=dict(bgcolor=palette["surface_alt"], font_color=palette["text"], font_size=12),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, automargin=True, tickfont=dict(color=palette["muted"]))
    fig.update_yaxes(gridcolor=palette["grid"], zerolinecolor=palette["border"], automargin=True,
                     tickfont=dict(color=palette["muted"]))
    return fig


def revenue_profit_trend(data: pd.DataFrame, start_date, end_date, theme="Light Mode") -> go.Figure:
    palette = get_theme(theme)
    monthly = monthly_summary(data, start_date, end_date)
    fig = go.Figure()
    for column, name, color, dash, symbol in [
        ("revenue_lkr", "Revenue", palette["blue"], "solid", "circle"),
        ("profit_lkr", "Profit", palette["green"], "dash", "diamond"),
    ]:
        fig.add_trace(go.Scatter(
            x=monthly["month"].tolist(), y=monthly[column].tolist(), name=name,
            mode="lines+markers", line=dict(color=color, width=3, dash=dash),
            marker=dict(size=7, symbol=symbol),
            fill="tozeroy" if column == "revenue_lkr" else None,
            fillcolor="rgba(" + ",".join(str(int(color[i:i+2], 16)) for i in (1, 3, 5)) + ",0.07)",
            hovertemplate="%{x|%B %Y}<br>" + name + ": LKR %{y:,.0f}<extra></extra>",
        ))
    style_chart(fig, "Monthly revenue and profit", 305, theme)
    fig.update_layout(hovermode="x unified")
    fig.update_xaxes(title=None, tickformat="%b %Y", dtick="M1")
    fig.update_yaxes(title="LKR", tickformat="~s", rangemode="tozero")
    return fig


def category_profit(data: pd.DataFrame, theme="Light Mode", domain=None) -> go.Figure:
    palette = get_theme(theme)
    summary = summarize_by(data, "category_clean").sort_values("profit_lkr")
    labels = list(domain) if domain is not None else sorted(summary["category_clean"])
    colors = categorical_colors(palette)
    mapping = {label: colors[i % len(colors)] for i, label in enumerate(labels)}
    fig = go.Figure(go.Bar(
        x=summary["profit_lkr"].tolist(), y=summary["category_clean"].tolist(), orientation="h",
        marker_color=[mapping[label] if value >= 0 else palette["red"]
                      for label, value in zip(summary["category_clean"], summary["profit_lkr"])],
        customdata=summary[["revenue_lkr", "profit_margin", "transactions"]].to_numpy().tolist(),
        hovertemplate="<b>%{y}</b><br>Profit: LKR %{x:,.0f}<br>Revenue: LKR %{customdata[0]:,.0f}"
                      "<br>Margin: %{customdata[1]:.2f}%<br>Transactions: %{customdata[2]:,.0f}<extra></extra>",
        text=summary["profit_lkr"].tolist(), texttemplate="%{text:.3s}", textposition="inside",
        textfont=dict(color=palette["on_accent"]), marker_line_width=0,
    ))
    style_chart(fig, "Profit by product category", theme=theme)
    fig.update_xaxes(title="Profit (LKR)", tickformat="~s", rangemode="tozero")
    return fig


def province_revenue(data: pd.DataFrame, theme="Light Mode") -> go.Figure:
    palette = get_theme(theme)
    summary = summarize_by(data, "province").sort_values("revenue_lkr")
    fig = go.Figure(go.Bar(
        x=summary["revenue_lkr"].tolist(), y=summary["province"].tolist(), orientation="h",
        marker=dict(color=summary["revenue_lkr"].tolist(),
                    colorscale=[[0,palette["purple"]],[.5,palette["blue"]],[1,palette["cyan"]]], showscale=False),
        customdata=summary[["profit_lkr", "transactions"]].to_numpy().tolist(),
        hovertemplate="<b>%{y}</b><br>Revenue: LKR %{x:,.0f}<br>Profit: LKR %{customdata[0]:,.0f}"
                      "<br>Transactions: %{customdata[1]:,.0f}<extra></extra>",
    ))
    style_chart(fig, "Revenue by province", theme=theme)
    fig.update_xaxes(title="Revenue (LKR)", tickformat="~s", rangemode="tozero")
    return fig


def rating_distribution(data: pd.DataFrame, theme="Light Mode") -> go.Figure:
    ratings = data["customer_rating"].dropna()
    fig = go.Figure(go.Histogram(
        x=ratings.tolist(), xbins=dict(start=0.5, end=5.5, size=1), marker_color=get_theme(theme)["purple"],
        hovertemplate="Rating: %{x}<br>Responses: %{y:,.0f}<extra></extra>",
    ))
    style_chart(fig, "Customer rating distribution", theme=theme)
    fig.update_layout(bargap=0.22)
    fig.update_xaxes(title="Customer rating (1–5)", tickmode="linear", dtick=1, range=[0.5, 5.5])
    fig.update_yaxes(title="Rated transactions", rangemode="tozero", dtick=1 if len(ratings) < 10 else None)
    if ratings.empty:
        fig.add_annotation(text="No customer ratings in this selection", x=0.5, y=0.5,
                           xref="paper", yref="paper", showarrow=False)
    return fig


def delivery_profit(data: pd.DataFrame, theme="Light Mode") -> go.Figure:
    palette = get_theme(theme)
    band_colors = dict(zip(DELIVERY_BANDS, [palette["green"], palette["blue"], palette["amber"]]))
    fig = go.Figure()
    for band in DELIVERY_BANDS:
        part = data.loc[data["delivery_performance_band"].eq(band)]
        if part.empty:
            continue
        fig.add_trace(go.Scatter(
            x=part["delivery_days"].tolist(), y=part["profit_lkr"].tolist(),
            name=band, mode="markers",
            marker=dict(color=band_colors[band], size=8, opacity=0.75,
                        symbol=part["sales_channel"].map(CHANNEL_SYMBOLS).tolist(),
                        line=dict(width=0.6, color=palette["surface"])),
            customdata=part[["order_id", "revenue_lkr", "category_clean", "sales_channel", "returned"]].to_numpy().tolist(),
            hovertemplate="<b>%{customdata[0]}</b><br>Delivery: %{x} days<br>Profit: LKR %{y:,.0f}"
                          "<br>Revenue: LKR %{customdata[1]:,.0f}<br>%{customdata[2]} · %{customdata[3]}"
                          "<br>Returned: %{customdata[4]}<extra>" + band + "</extra>",
        ))
    style_chart(fig, "Delivery days vs. transaction profit", theme=theme)
    fig.update_xaxes(title="Delivery time (days)", dtick=1, rangemode="tozero")
    fig.update_yaxes(title="Profit (LKR)", tickformat="~s", rangemode="tozero")
    return fig


def distribution_chart(data, column, title, *, measure="transactions", hole=0,
                       theme="Light Mode", domain=None):
    """A single implementation for revenue shares and transaction proportions."""
    palette = get_theme(theme)
    summary = summarize_by(data, column)
    labels = summary[column].astype(str).tolist()
    values = summary["revenue_lkr" if measure == "revenue" else "transactions"].tolist()
    domain = list(domain) if domain is not None else sorted(labels)
    colors = categorical_colors(palette)
    mapping = {label: colors[i % len(colors)] for i, label in enumerate(domain)}
    if column == "return_status":
        mapping = {"Returned Orders": palette["red"], "Successful Orders": palette["green"]}
    fig = go.Figure()
    if sum(values) > 0:
        # Percentages are calculated by Plotly from these grouped CSV amounts.
        fig.add_trace(go.Pie(
            labels=labels, values=values, hole=hole, sort=False, direction="clockwise",
            marker=dict(colors=[mapping[label] for label in labels], line=dict(color=palette["surface"], width=3)),
            textinfo="label+percent", texttemplate="%{label}<br>%{percent:.1%}",
            textposition="outside", automargin=True, textfont=dict(size=12, color=palette["text"]),
            hovertemplate="<b>%{label}</b><br>" + ("Revenue: LKR %{value:,.0f}" if measure == "revenue" else "Transactions: %{value:,.0f}")
                          + "<br>Share: %{percent:.2%}<extra></extra>",
        ))
        if hole:
            total = f"LKR {sum(values):,.0f}" if measure == "revenue" else f"{sum(values):,.0f}"
            fig.add_annotation(text=f"<b>{total}</b><br>{'revenue' if measure == 'revenue' else 'transactions'}",
                               x=.5, y=.5, xref="paper", yref="paper", showarrow=False,
                               font=dict(size=12, color=palette["text"]))
    else:
        fig.add_annotation(text="No values for this selection", x=.5, y=.5, showarrow=False)
    style_chart(fig, title, 405, theme)
    fig.update_layout(showlegend=False, margin=dict(l=30, r=30, t=65, b=40))
    return fig


def sales_channel_distribution(data, theme="Light Mode", domain=None):
    return distribution_chart(data, "sales_channel", "Sales channel distribution", measure="revenue",
                              hole=.64, theme=theme, domain=domain)


def return_analysis(data, theme="Light Mode"):
    view = data.assign(return_status=data["is_returned"].map({True: "Returned Orders", False: "Successful Orders"}))
    return distribution_chart(view, "return_status", "Return analysis", hole=.64, theme=theme)


def customer_segment_distribution(data, theme="Light Mode", domain=None):
    return distribution_chart(data, "customer_segment", "Customer segment distribution", hole=.64,
                              theme=theme, domain=domain)


def payment_method_distribution(data, theme="Light Mode", domain=None):
    return distribution_chart(data, "payment_method", "Payment method distribution", theme=theme, domain=domain)


def product_category_share(data, theme="Light Mode", domain=None):
    return distribution_chart(data, "category_clean", "Product category share", measure="revenue",
                              theme=theme, domain=domain)
