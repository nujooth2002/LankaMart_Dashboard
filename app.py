"""Run locally with: python -m streamlit run app.py"""

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from utils.charts import (
    category_profit, delivery_profit, province_revenue,
    rating_distribution, revenue_profit_trend,
    sales_channel_distribution, return_analysis, customer_segment_distribution,
    payment_method_distribution, product_category_share,
)
from utils.data_processing import (
    DATA_PATH, calculate_kpis, filter_data, load_dataset,
    management_insights, prepare_data, compare_previous_period,
)
from utils.themes import get_theme, dashboard_css
from utils.tables import render_table

st.set_page_config(
    page_title="LankaMart Retail Performance Dashboard",
    page_icon="📊", layout="wide", initial_sidebar_state="expanded",
)

@st.cache_data(show_spinner=False)
def get_prepared_data(path: str, modified_ns: int):
    """Invalidate the cache when the source file changes."""
    return prepare_data(load_dataset(Path(path)))


def reset_filters(start, end, channels, categories):
    st.session_state["date_range"] = (start, end)
    st.session_state["channels"] = channels.copy()
    st.session_state["categories"] = categories.copy()


def format_percent(value: float) -> str:
    return f"{value:.2f}%" if pd.notna(value) else "N/A"


def render_sidebar(data: pd.DataFrame):
    start, end = data["order_date"].min().date(), data["order_date"].max().date()
    channels = sorted(data["sales_channel"].unique().tolist())
    categories = sorted(data["category_clean"].unique().tolist())
    st.session_state.setdefault("date_range", (start, end))
    st.session_state.setdefault("channels", channels.copy())
    st.session_state.setdefault("categories", categories.copy())
    with st.sidebar:
        st.markdown('<div class="brand-lockup"><div class="brand-mark" aria-hidden="true">LM</div>'
                    '<div><div class="brand">Lanka<span>Mart</span></div>'
                    '<div class="brand-sub">RETAIL INTELLIGENCE</div></div></div>', unsafe_allow_html=True)
        theme_name = st.radio("Dashboard Theme", ["Light Mode", "Dark Mode"], key="dashboard_theme", horizontal=True)
        animations = st.toggle("Animations", value=True, key="animations_enabled",
                               help="Card entrances, hover movement and a gentle header glow. Your device's reduced-motion preference is always respected.")
        st.divider()
        st.subheader("Make it your view")
        st.caption("Choose a period and focus on the sales that matter to you.")
        dates = st.date_input("Date range", min_value=start, max_value=end,
                              format="DD/MM/YYYY", key="date_range")
        selected_channels = st.multiselect("Sales Channel", channels, key="channels")
        selected_categories = st.multiselect("Product Category", categories, key="categories")
        st.button("Reset all filters", on_click=reset_filters,
                  args=(start, end, channels, categories), width="stretch", key="reset")
        st.divider()
        st.markdown("**Dataset coverage**")
        st.caption(f"{start:%d %b %Y} — {end:%d %b %Y}\n\n{len(data):,} unique transactions · LKR")
        st.caption("Source: supplied CIT308 LankaMart retail transactions. Preparation details are available in the Data quality tab.")
    return dates, selected_channels, selected_categories, theme_name, animations


def render_kpis(filtered: pd.DataFrame, comparison):
    kpis = calculate_kpis(filtered)
    columns = st.columns(4)
    metrics = [
        ("Total Revenue (LKR)", f"{kpis['revenue']:,.0f}", "Sum of recorded revenue after discount, including returned records; not adjusted for refunds."),
        ("Total Profit (LKR)", f"{kpis['profit']:,.0f}", "Sum of source profit_lkr for the selected transactions, including returned records."),
        ("Profit Margin (%)", format_percent(kpis["profit_margin"]), "Total profit / total revenue × 100. N/A when revenue is zero; not an average of row margins."),
        ("Return Rate (%)", format_percent(kpis["return_rate"]), "Returned transactions / all selected transactions × 100. N/A for an empty selection."),
    ]
    for column, (label, value, help_text), key in zip(columns, metrics,
            ["revenue", "profit", "profit_margin", "return_rate"]):
        change = comparison["deltas"][key]
        delta = None if change is None else f"{change:+.2f}{'%' if key in ('revenue', 'profit') else ' pp'} vs prior"
        with column:
            with st.container(key=f"kpi_{key}"):
                st.metric(label, value, help=help_text, delta=delta,
                          delta_color="inverse" if key == "return_rate" else "normal")
    if comparison["available"]:
        st.caption(f"Change vs {comparison['start']:%d %b %Y} — {comparison['end']:%d %b %Y}, with the same channel/category filters. Margin and return changes are percentage points (pp); lower return rate is favorable.")
    else:
        st.caption("Prior-period changes are unavailable: the dataset does not cover a complete preceding window with matching transactions. Choose a later, shorter date range to compare.")


def show_chart(figure, key):
    figure.update_layout(meta={"dashboard_key": key})
    st.plotly_chart(figure, width="stretch", theme=None, key=key,
                    config={"displaylogo": False, "responsive": True,
                            "toImageButtonOptions": {"format": "png", "scale": 2}})


def render_insights(filtered):
    st.subheader("Management insights")
    st.caption("Evidence and suggested actions for the current selection.")
    insights = management_insights(filtered)
    for offset in range(0, len(insights), 2):
        for index, (column, insight) in enumerate(zip(st.columns(2, gap="medium"), insights[offset:offset + 2])):
            with column:
                st.markdown(
                    f'<div class="insight" data-insight="{offset + index}"><div class="insight-heading">'
                    f'<span class="insight-number" aria-hidden="true">{offset + index + 1:02d}</span>'
                    f'<div class="insight-title">{escape(insight["title"].split(" / ", 1)[-1])}</div></div>'
                    f'<p>{escape(insight["finding"])}</p>'
                    f'<p class="action"><strong>Next step</strong> {escape(insight["action"])}</p></div>',
                    unsafe_allow_html=True,
                )


def render_sales(filtered, start, end, theme, domains):
    st.subheader("Sales Performance")
    st.caption("Track momentum, category contribution and the channel mix.")
    show_chart(revenue_profit_trend(filtered, start, end, theme), "monthly_trend")
    st.caption("Recorded LKR amounts, including returned orders. Boundary months may be partial; k = thousand and M = million.")
    left, right = st.columns(2, gap="medium")
    with left:
        show_chart(category_profit(filtered, theme, domains["category_clean"]), "category_profit")
    with right:
        show_chart(sales_channel_distribution(filtered, theme, domains["sales_channel"]), "channel_distribution")
        st.caption("Share of selected revenue (LKR), after discount.")
    show_chart(product_category_share(filtered, theme, domains["category_clean"]), "category_share")
    st.caption("Each slice = category revenue / total selected revenue × 100.")


def render_customers(filtered, theme, domains):
    st.subheader("Customer Behaviour")
    st.caption("Understand who buys, how they pay and the experience they report.")
    left, right = st.columns(2, gap="medium")
    with left:
        show_chart(customer_segment_distribution(filtered, theme, domains["customer_segment"]), "segment_distribution")
        st.caption("Share of transactions by customer segment; this is not a count of unique customers.")
    with right:
        show_chart(payment_method_distribution(filtered, theme, domains["payment_method"]), "payment_distribution")
        st.caption("Share of selected transactions. Payment method names are taken directly from the CSV.")
    show_chart(rating_distribution(filtered, theme), "rating_distribution")
    rated = int(filtered["rating_available"].sum())
    st.caption(f"{rated:,} rated · {len(filtered)-rated:,} unrated · {rated / len(filtered) * 100:.1f}% coverage. Missing ratings are excluded, never filled with zero.")


def render_operations(filtered, theme):
    st.subheader("Operations & Risk")
    st.caption("Monitor returns, fulfilment performance and regional concentration.")
    left, right = st.columns(2, gap="medium")
    with left:
        show_chart(return_analysis(filtered, theme), "return_analysis")
        returned = int(filtered.is_returned.sum())
        st.caption(f"{returned:,} returned orders · {len(filtered)-returned:,} successful orders. Successful means returned = No; return rate uses all selected transactions.")
    with right:
        show_chart(province_revenue(filtered, theme), "province_revenue")
    show_chart(delivery_profit(filtered, theme), "delivery_profit")
    st.caption("Fast ≤ 3 days · Normal 4–7 · Slow > 7. Circle = Online, diamond = Mobile App, square = Store. Store orders can take 0 days; association does not establish causation.")


def render_transactions(filtered: pd.DataFrame, theme):
    st.subheader("Transactions behind the numbers")
    st.caption(f"{len(filtered):,} selected transactions. Click a column header to sort, search any column, or browse pages. Table search affects this table only.")
    columns = {
        "order_id": "Order ID", "order_date": "Date", "province": "Province",
        "sales_channel": "Channel", "category_clean": "Category",
        "revenue_lkr": "Revenue (LKR)", "profit_lkr": "Profit (LKR)", "returned": "Returned Status",
    }
    table = filtered.sort_values(["order_date", "order_id"], ascending=[False, True])[list(columns)].rename(columns=columns)
    render_table(table, theme, "transactions")
    st.download_button("Download filtered transactions (CSV)",
                       data=filtered.to_csv(index=False).encode("utf-8-sig"),
                       file_name="LankaMart_filtered_transactions.csv", mime="text/csv", key="download_csv")
    st.caption("The download includes all original fields and calculated fields. Category in this table uses the corrected analysis label; product_category is retained in the export.")


def render_quality(filtered: pd.DataFrame, audit: dict, theme):
    st.subheader("Data quality & preparation")
    st.caption("Source audit covers the complete CSV before sidebar filtering. Selected-view rating coverage is shown separately below.")
    summary = pd.DataFrame([
        ("Source rows", audit["source_rows"], "Loaded programmatically; supplied CSV is unchanged."),
        ("Exact duplicate rows removed", audit["exact_duplicates"], "Keep the first occurrence to avoid double-counting."),
        ("Prepared transactions", audit["prepared_rows"], "Shared base for all dashboard filters."),
        ("Category labels normalized", audit["category_corrections"], "electronic → Electronics in category_clean only."),
        ("Missing ratings in source", audit["source_missing_ratings"], "Retain NaN; do not impute a satisfaction score."),
        ("Missing ratings after deduplication", audit["prepared_missing_ratings"], "Exclude only from rating analysis, not sales KPIs."),
        ("Conflicting order IDs", audit["conflicting_order_ids"], "Nonidentical duplicate IDs prevent aggregation."),
        ("Profit identity mismatches", audit["profit_identity_mismatches"], "profit = revenue − cost; LKR 1 rounding tolerance."),
        ("Revenue formula mismatches", audit["revenue_formula_mismatches"], "units × unit price × (1 − discount); LKR 1 tolerance."),
        ("Store orders with nonzero delivery", audit["store_nonzero_delivery"], "Flag for review; do not automatically alter."),
        ("Zero-revenue transactions", audit["zero_revenue_rows"], "Row profit margin is undefined (NaN)."),
    ], columns=["Check", "Count", "Treatment / interpretation"])
    render_table(summary, theme, "source_audit", height=540)
    rated = int(filtered["rating_available"].sum())
    coverage = f"{rated / len(filtered) * 100:.1f}%" if len(filtered) else "N/A"
    st.info(f"Selected view: {len(filtered):,} transactions · {rated:,} rated · {len(filtered) - rated:,} unrated · coverage {coverage}.")
    with st.expander("Column types, missing values and numerical ranges"):
        st.markdown("**Source data types**")
        render_table(audit["types"], theme, "types")
        st.markdown("**Missing values before deduplication**")
        render_table(audit["missing"], theme, "missing")
        st.markdown("**Numerical ranges**")
        render_table(audit["ranges"], theme, "ranges")
    with st.expander("Definitions and interpretation", expanded=True):
        st.markdown("""
- **Profit margin:** total profit ÷ total revenue × 100; calculated row margins are available in the export. Zero revenue gives an undefined margin.
- **Return rate:** transactions marked `Yes` ÷ selected transactions × 100, after removing exact duplicates.
- **Month:** the first day of the order's calendar month, retaining its year. No-order months inside the selected period appear as zero.
- **Delivery band:** Fast ≤ 3 days, Normal 4–7 days, Slow > 7 days. Zero-day Store orders remain valid.
- **Preservation:** source CSV is unchanged; original category is retained, and original date text is kept in `order_date_raw` alongside the converted datetime.
- **Limitations:** recorded revenue and profit include returned orders, with no extra refund adjustment; missing ratings may bias satisfaction findings; channel and product mix can confound delivery/profit comparisons. This assessment dataset covers a limited period and cannot establish annual seasonality or causation.
""")


def main():
    try:
        data, audit = get_prepared_data(str(DATA_PATH), DATA_PATH.stat().st_mtime_ns)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        st.error(f"The supplied dataset could not be prepared. {error}")
        st.info("Place CIT308_LankaMart_Retail_Transactions.csv in the project's data folder and check its original column names.")
        st.stop()

    dates, channels, categories, theme_name, animations = render_sidebar(data)
    theme = get_theme(theme_name)
    st.markdown(dashboard_css(theme, animations), unsafe_allow_html=True)
    with st.container(key="dashboard_hero"):
        st.markdown('<div class="eyebrow">LANKAMART / BUSINESS OVERVIEW</div>', unsafe_allow_html=True)
        st.title("Retail performance, at a glance.")
        st.markdown("See what drives your sales. Understand your customers. Find your next move.")
        st.markdown('<div class="hero-tags"><span>Sri Lanka</span><span>Retail analytics</span>'
                    '<span>Currency · LKR</span></div>', unsafe_allow_html=True)
    if not isinstance(dates, (tuple, list)) or len(dates) != 2:
        st.info("Select both a start and an end date to update the dashboard.")
        st.stop()
    start, end = dates
    filtered = filter_data(data, start, end, channels, categories)
    channel_scope = "All channels" if len(channels) == data["sales_channel"].nunique() else ", ".join(channels) or "No channels"
    category_scope = "All categories" if len(categories) == data["category_clean"].nunique() else ", ".join(categories) or "No categories"
    st.markdown(
        f'<div class="scope"><span class="scope-count">{len(filtered):,} transactions</span>'
        f'<span>{start:%d %b %Y} — {end:%d %b %Y}</span>'
        f'<span>{escape(channel_scope)}</span><span>{escape(category_scope)}</span></div>',
        unsafe_allow_html=True,
    )
    comparison = compare_previous_period(data, filtered, start, end, channels, categories)
    st.subheader("Your business in numbers")
    render_kpis(filtered, comparison)
    st.caption("Financial KPIs show recorded amounts, including returned orders. Hover over a KPI's help icon for its definition.")
    if audit["profit_identity_mismatches"] or audit["revenue_formula_mismatches"]:
        st.warning("Some source amounts fail arithmetic consistency checks. Recorded values are retained; see the Data quality tab.")
    overview, sales, customers, operations, transactions, quality = st.tabs([
        "Executive Summary", "Sales Performance", "Customer Behaviour", "Operations & Risk",
        "Detailed Transactions", "Data Quality"])
    domains = {col: sorted(data[col].unique()) for col in ("sales_channel", "category_clean", "customer_segment", "payment_method")}
    for tab, render, args in [(overview, render_insights, (filtered,)),
                               (sales, render_sales, (filtered, start, end, theme_name, domains)),
                               (customers, render_customers, (filtered, theme_name, domains)),
                               (operations, render_operations, (filtered, theme_name))]:
        with tab:
            if filtered.empty:
                st.info("No transactions match these filters. Select at least one channel and category, broaden the date range, or reset all filters.")
            else:
                render(*args)
    with transactions:
        render_transactions(filtered, theme)
    with quality:
        render_quality(filtered, audit, theme)
    st.markdown('<div class="footer">LankaMart · Author: S.M.F.Asra · CIT308 Data Visualization · Source: supplied retail transaction CSV · All monetary values in LKR</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
