"""Reproducible preparation: raw values are retained, never edited in the CSV."""

from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "CIT308_LankaMart_Retail_Transactions.csv"
NUMERIC_COLUMNS = (
    "units", "unit_price_lkr", "discount_pct", "revenue_lkr", "cost_lkr",
    "profit_lkr", "delivery_days", "customer_rating",
)
REQUIRED_COLUMNS = (
    "order_id", "order_date", "province", "city", "sales_channel",
    "customer_segment", "product_category", "product_name", *NUMERIC_COLUMNS,
    "payment_method", "returned", "promotion",
)
DELIVERY_BANDS = ["Fast", "Normal", "Slow"]
# A documented spelling correction, not a replacement of source observations.
CATEGORY_ALIASES = {"electronic": "Electronics"}


def load_dataset(path: str | Path = DATA_PATH) -> pd.DataFrame:
    """Read the actual CSV; preserve the legitimate promotion label 'None'."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset not found: {path}")
    raw = pd.read_csv(path, keep_default_na=False, na_values=[""], encoding="utf-8-sig")
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(raw.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    if raw.empty:
        raise ValueError("The dataset contains no transaction records.")
    return raw


def check_data_types(raw: pd.DataFrame) -> pd.DataFrame:
    """Report inferred types and values that cannot be parsed as required."""
    rows = []
    for column in raw.columns:
        failures = 0
        expected = "Text / category"
        if column in NUMERIC_COLUMNS:
            expected = "Numeric"
            parsed = pd.to_numeric(raw[column], errors="coerce")
            failures = int((raw[column].notna() & parsed.isna()).sum())
        elif column == "order_date":
            expected = "Date (YYYY-MM-DD)"
            parsed = pd.to_datetime(raw[column], format="%Y-%m-%d", errors="coerce")
            failures = int((raw[column].notna() & parsed.isna()).sum())
        rows.append({"Column": column, "Source type": str(raw[column].dtype),
                     "Expected": expected, "Parse failures": failures})
    return pd.DataFrame(rows)


def check_missing_values(raw: pd.DataFrame) -> pd.DataFrame:
    """Missingness is measured before deduplication for an honest source audit."""
    return pd.DataFrame({
        "Column": raw.columns,
        "Missing values": raw.isna().sum().to_numpy(),
        "Missing (%)": raw.isna().mean().to_numpy() * 100,
    })


def check_duplicates(raw: pd.DataFrame) -> dict[str, int]:
    """Distinguish exact repeats from ambiguous, nonidentical order IDs."""
    unique_rows = raw.drop_duplicates()
    return {
        "exact_duplicates": int(raw.duplicated().sum()),
        "repeated_order_ids": int(raw["order_id"].duplicated().sum()),
        "conflicting_order_ids": int(unique_rows["order_id"].duplicated(keep=False).sum()),
    }


def validate_numerical_ranges(raw: pd.DataFrame) -> pd.DataFrame:
    """Check business-valid ranges; losses and zero-day store orders are valid."""
    rules = {
        "units": ("Positive integer", lambda s: (s > 0) & (s % 1 == 0)),
        "unit_price_lkr": (">= 0", lambda s: s >= 0),
        "discount_pct": ("0 to 1 inclusive", lambda s: s.between(0, 1)),
        "revenue_lkr": (">= 0", lambda s: s >= 0),
        "cost_lkr": (">= 0", lambda s: s >= 0),
        "profit_lkr": ("Any finite value; losses allowed", lambda s: pd.Series(True, index=s.index)),
        "delivery_days": ("Nonnegative integer", lambda s: (s >= 0) & (s % 1 == 0)),
        "customer_rating": ("1 to 5 when present", lambda s: s.between(1, 5)),
    }
    rows = []
    for column, (description, rule) in rules.items():
        values = pd.to_numeric(raw[column], errors="coerce")
        finite = pd.Series(np.isfinite(values), index=values.index)
        invalid = raw[column].notna() & ~(finite & rule(values))
        rows.append({"Column": column, "Valid range": description,
                     "Minimum": values.min(), "Maximum": values.max(),
                     "Invalid values": int(invalid.sum())})
    return pd.DataFrame(rows)


def prepare_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Audit, remove exact repeats and add analysis fields without mutating raw."""
    types = check_data_types(raw)
    missing = check_missing_values(raw)
    duplicates = check_duplicates(raw)
    ranges = validate_numerical_ranges(raw)
    required_missing = raw[list(set(REQUIRED_COLUMNS) - {"customer_rating", "promotion"})].isna().sum().sum()
    if required_missing or types["Parse failures"].sum() or ranges["Invalid values"].sum():
        raise ValueError(
            "Source validation failed: missing required values, unparseable dates/numbers, "
            "or invalid numeric ranges. Inspect the source; no records were silently discarded."
        )
    if duplicates["conflicting_order_ids"]:
        raise ValueError("Conflicting records share an order ID; resolve their meaning before aggregating.")
    if not raw["returned"].isin(["Yes", "No"]).all():
        raise ValueError("Returned status must be Yes or No.")
    if not raw["sales_channel"].isin(["Online", "Mobile App", "Store"]).all():
        raise ValueError("Unexpected sales channel in the supplied data.")

    data = raw.drop_duplicates().copy().reset_index(drop=True)
    # Retain the date text as well as the required datetime representation.
    data["order_date_raw"] = data["order_date"]
    data["order_date"] = pd.to_datetime(data["order_date"], format="%Y-%m-%d")
    for column in NUMERIC_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="raise")
    data["category_clean"] = data["product_category"].replace(CATEGORY_ALIASES)
    data["profit_margin"] = data["profit_lkr"].div(data["revenue_lkr"].replace(0, np.nan)).mul(100)
    # A month-start datetime includes the year and sorts correctly across years.
    data["month"] = data["order_date"].dt.to_period("M").dt.to_timestamp()
    data["delivery_performance_band"] = pd.cut(
        data["delivery_days"], bins=[-np.inf, 3, 7, np.inf],
        labels=DELIVERY_BANDS, right=True, ordered=True,
    )
    data["is_returned"] = data["returned"].eq("Yes")
    data["rating_available"] = data["customer_rating"].notna()
    profit_difference = data["profit_lkr"] - (data["revenue_lkr"] - data["cost_lkr"])
    expected_revenue = data["units"] * data["unit_price_lkr"] * (1 - data["discount_pct"])
    # Integer LKR amounts can differ by up to one rupee due to source rounding.
    accounting = {
        "profit_identity_mismatches": int((profit_difference.abs() > 1.0).sum()),
        "revenue_formula_mismatches": int(((data["revenue_lkr"] - expected_revenue).abs() > 1.0).sum()),
        "store_nonzero_delivery": int((data["sales_channel"].eq("Store") & data["delivery_days"].ne(0)).sum()),
    }
    audit = {
        "source_rows": len(raw), "prepared_rows": len(data), **duplicates, **accounting,
        "category_corrections": int(data["category_clean"].ne(data["product_category"]).sum()),
        "source_missing_ratings": int(raw["customer_rating"].isna().sum()),
        "prepared_missing_ratings": int(data["customer_rating"].isna().sum()),
        "zero_revenue_rows": int(data["revenue_lkr"].eq(0).sum()),
        "types": types, "missing": missing, "ranges": ranges,
    }
    return data, audit


def filter_data(data: pd.DataFrame, start_date: Any, end_date: Any,
                channels: Sequence[str], categories: Sequence[str]) -> pd.DataFrame:
    """Apply inclusive dates and both category filters to one shared dataframe."""
    mask = (
        data["order_date"].between(pd.Timestamp(start_date), pd.Timestamp(end_date))
        & data["sales_channel"].isin(channels)
        & data["category_clean"].isin(categories)
    )
    return data.loc[mask].copy()


def calculate_kpis(data: pd.DataFrame) -> dict[str, float | int]:
    revenue = float(data["revenue_lkr"].sum())
    profit = float(data["profit_lkr"].sum())
    count = len(data)
    return {
        "revenue": revenue, "profit": profit, "transactions": count,
        "profit_margin": profit / revenue * 100 if revenue else float("nan"),
        "returned_count": int(data["is_returned"].sum()),
        "return_rate": float(data["is_returned"].mean() * 100) if count else float("nan"),
    }


def summarize_by(data: pd.DataFrame, column: str) -> pd.DataFrame:
    summary = data.groupby(column, observed=True).agg(
        revenue_lkr=("revenue_lkr", "sum"), profit_lkr=("profit_lkr", "sum"),
        transactions=("order_id", "size"), returned_count=("is_returned", "sum"),
    ).reset_index()
    summary["profit_margin"] = summary["profit_lkr"].div(summary["revenue_lkr"].replace(0, np.nan)).mul(100)
    summary["return_rate"] = summary["returned_count"].div(summary["transactions"]).mul(100)
    return summary


def compare_previous_period(data, selected, start, end, channels, categories):
    """Compare equal inclusive windows only when the earlier window is covered."""
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    duration = end - start + pd.Timedelta(days=1)
    previous_end = start - pd.Timedelta(days=1)
    previous_start = start - duration
    result = {"start": previous_start, "end": previous_end, "available": False,
              "deltas": {key: None for key in ("revenue", "profit", "profit_margin", "return_rate")}}
    if previous_start < data.order_date.min() or previous_end > data.order_date.max() or selected.empty:
        return result
    previous = filter_data(data, previous_start, previous_end, channels, categories)
    if previous.empty:
        return result
    current_kpis, previous_kpis = calculate_kpis(selected), calculate_kpis(previous)
    for key in ("revenue", "profit"):
        baseline = previous_kpis[key]
        if baseline:
            result["deltas"][key] = (current_kpis[key] - baseline) / abs(baseline) * 100
    for key in ("profit_margin", "return_rate"):
        if pd.notna(current_kpis[key]) and pd.notna(previous_kpis[key]):
            result["deltas"][key] = current_kpis[key] - previous_kpis[key]
    result["available"] = True
    return result


def monthly_summary(data: pd.DataFrame, start_date: Any, end_date: Any) -> pd.DataFrame:
    """Keep no-order months as zeros within the selected period."""
    months = pd.date_range(pd.Timestamp(start_date).to_period("M").start_time,
                           pd.Timestamp(end_date).to_period("M").start_time, freq="MS")
    return (data.groupby("month")[["revenue_lkr", "profit_lkr"]].sum()
            .reindex(months, fill_value=0).rename_axis("month").reset_index())


def management_insights(data: pd.DataFrame) -> list[dict[str, str]]:
    """Create scoped findings and proportionate actions from actual records."""
    if data.empty:
        return []
    kpis = calculate_kpis(data)
    province = summarize_by(data, "province").sort_values(
        ["revenue_lkr", "province"], ascending=[False, True]).iloc[0]
    share = province["revenue_lkr"] / kpis["revenue"] * 100 if kpis["revenue"] else 0
    insights = [{
        "title": "01 / Regional opportunity",
        "finding": f"{province['province']} is the highest-revenue province: LKR {province['revenue_lkr']:,.0f} "
                   f"({share:.1f}% of selected revenue; {province['transactions']:,} transactions).",
        "action": "Review stock availability in this province before increasing campaign spend; demand and capacity need to align.",
    }]
    categories = summarize_by(data, "category_clean").dropna(subset=["profit_margin"])
    if not categories.empty:
        low = categories.sort_values(["profit_margin", "category_clean"]).iloc[0]
        insights.append({
            "title": "02 / Margin priority",
            "finding": f"{low['category_clean']} has the lowest category profit margin at {low['profit_margin']:.2f}% "
                       f"(LKR {low['profit_lkr']:,.0f} profit / LKR {low['revenue_lkr']:,.0f} revenue).",
            "action": "Inspect discounts, product mix and fulfilment costs in this category before expanding sales.",
        })
    insights.append({
        "title": "03 / Returns to investigate",
        "finding": f"Returned orders represent {kpis['return_rate']:.2f}% of selected transactions "
                   f"({kpis['returned_count']:,} of {kpis['transactions']:,}).",
        "action": "Review returned products and collect reason codes. Recorded revenue and profit do not establish the cost of refunds.",
    })
    slow = data.loc[data["delivery_performance_band"].eq("Slow")]
    delivered = data.loc[data["sales_channel"].ne("Store")]
    slow_delivered = delivered.loc[delivered["delivery_performance_band"].eq("Slow")]
    if not delivered.empty:
        rate = len(slow_delivered) / len(delivered) * 100
        insight = f"{len(slow_delivered):,} of {len(delivered):,} Online / Mobile App transactions " \
                  f"({rate:.1f}%) took more than 7 days."
        action = "Review routes and courier capacity for slow orders. Compare similar products and channels before attributing profit differences to delivery speed."
    else:
        insight = f"The selection contains {len(data):,} Store transactions; {len(slow):,} took more than 7 days."
        action = "Use Online or Mobile App filters to investigate courier fulfilment; zero-day Store records reflect a different operating model."
    insights.append({"title": "04 / Fulfilment watch", "finding": insight, "action": action})
    return insights
