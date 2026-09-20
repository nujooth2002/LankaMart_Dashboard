"""Data and Streamlit integration checks, using only the supplied CSV."""

import csv
from datetime import timedelta
from decimal import Decimal
import json
import re
from pathlib import Path
import sys
import unittest

import pandas as pd
from pandas.testing import assert_frame_equal
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utils.charts import rating_distribution
from utils.data_processing import (
    DATA_PATH, calculate_kpis, filter_data, load_dataset, management_insights,
    monthly_summary, prepare_data,
    compare_previous_period,
)
from utils.themes import get_theme


def transaction_payload(app):
    return json.loads(re.search(r'<script id="table-data" type="application/json">(.*?)</script>',
                                app.get("iframe")[0].proto.srcdoc, re.S).group(1))


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = load_dataset()
        cls.data, cls.audit = prepare_data(cls.raw)

    def test_totals_match_independent_csv_calculation(self):
        # An independent csv/Decimal path catches duplicate and denominator errors.
        with DATA_PATH.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list({tuple(row.items()): row for row in reader}.values())
        revenue = sum(Decimal(row["revenue_lkr"]) for row in rows)
        profit = sum(Decimal(row["profit_lkr"]) for row in rows)
        returned = sum(row["returned"] == "Yes" for row in rows)
        kpis = calculate_kpis(self.data)
        self.assertEqual(kpis["revenue"], float(revenue))
        self.assertEqual(kpis["profit"], float(profit))
        self.assertAlmostEqual(kpis["profit_margin"], float(profit / revenue * 100))
        self.assertAlmostEqual(kpis["return_rate"], returned / len(rows) * 100)
        self.assertEqual(kpis["transactions"], len(rows))

    def test_raw_preservation_and_documented_corrections(self):
        before = self.raw.copy(deep=True)
        data, audit = prepare_data(self.raw)
        assert_frame_equal(self.raw, before)
        unique = self.raw.drop_duplicates().reset_index(drop=True)
        self.assertEqual(data["product_category"].tolist(), unique["product_category"].tolist())
        self.assertEqual(data["order_date_raw"].tolist(), unique["order_date"].tolist())
        self.assertTrue(data.loc[data.product_category.eq("electronic"), "category_clean"].eq("Electronics").all())
        self.assertEqual(audit["exact_duplicates"], len(self.raw) - len(unique))
        self.assertEqual(data["promotion"].tolist(), unique["promotion"].tolist())
        self.assertIn("None", data["promotion"].unique())

    def test_missing_ratings_keep_financial_transactions(self):
        unrated_raw = self.raw.loc[self.raw.customer_rating.isna()]
        unrated, _ = prepare_data(unrated_raw)
        self.assertGreater(len(unrated), 0)
        self.assertTrue(unrated.customer_rating.isna().all())
        self.assertGreater(calculate_kpis(unrated)["revenue"], 0)
        figure = rating_distribution(unrated)
        self.assertEqual(len(figure.data[0].x), 0)
        self.assertIn("No customer ratings", figure.layout.annotations[0].text)

    def test_delivery_boundaries_and_source_validity(self):
        for day, band in [(0, "Fast"), (3, "Fast"), (4, "Normal"), (7, "Normal"), (8, "Slow")]:
            subset = self.data.loc[self.data.delivery_days.eq(day)]
            self.assertGreater(len(subset), 0)
            self.assertTrue(subset.delivery_performance_band.eq(band).all())
        self.assertEqual(self.audit["ranges"]["Invalid values"].sum(), 0)
        self.assertEqual(self.audit["types"]["Parse failures"].sum(), 0)
        self.assertEqual(self.audit["profit_identity_mismatches"], 0)
        self.assertEqual(self.audit["revenue_formula_mismatches"], 0)

    def test_zero_order_months_and_empty_denominators(self):
        empty = self.data.iloc[0:0]
        kpis = calculate_kpis(empty)
        self.assertEqual(kpis["revenue"], 0)
        self.assertTrue(pd.isna(kpis["profit_margin"]))
        self.assertTrue(pd.isna(kpis["return_rate"]))
        monthly = monthly_summary(empty, self.data.order_date.min(), self.data.order_date.max())
        self.assertTrue(monthly.revenue_lkr.eq(0).all())
        self.assertEqual(management_insights(empty), [])


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data, _ = prepare_data(load_dataset())

    def setUp(self):
        self.app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()

    def assert_dashboard_matches(self, expected):
        app = self.app
        self.assertEqual(len(app.exception), 0, [x.message for x in app.exception])
        kpis = calculate_kpis(expected)
        values = [f"{kpis['revenue']:,.0f}", f"{kpis['profit']:,.0f}",
                  f"{kpis['profit_margin']:.2f}%", f"{kpis['return_rate']:.2f}%"]
        self.assertEqual([metric.value for metric in app.metric], values)
        table = transaction_payload(app)
        self.assertEqual({row[0] for row in table["rows"]}, set(expected.order_id))
        charts = {fig["layout"]["title"]["text"]: fig for fig in
                  [json.loads(element.proto.spec) for element in app.get("plotly_chart")]}
        self.assertEqual(len(charts), 10)
        # Every chart must reconcile to the same selected transactions.
        self.assertAlmostEqual(sum(charts["Monthly revenue and profit"]["data"][0]["y"]), kpis["revenue"])
        self.assertAlmostEqual(sum(charts["Monthly revenue and profit"]["data"][1]["y"]), kpis["profit"])
        self.assertAlmostEqual(sum(charts["Profit by product category"]["data"][0]["x"]), kpis["profit"])
        self.assertAlmostEqual(sum(charts["Revenue by province"]["data"][0]["x"]), kpis["revenue"])
        self.assertEqual(len(charts["Customer rating distribution"]["data"][0]["x"]), int(expected.customer_rating.notna().sum()))
        self.assertEqual(sum(len(trace["x"]) for trace in charts["Delivery days vs. transaction profit"]["data"]), len(expected))
        for title, column, revenue, hole in [
            ("Sales channel distribution", "sales_channel", True, .64),
            ("Product category share", "category_clean", True, 0),
            ("Customer segment distribution", "customer_segment", False, .64),
            ("Payment method distribution", "payment_method", False, 0),
            ("Return analysis", "returned", False, .64),
        ]:
            trace = charts[title]["data"][0]
            totals = expected.groupby(column).revenue_lkr.sum() if revenue else expected.groupby(column).size()
            if column == "returned":
                totals.index = totals.index.map({"Yes": "Returned Orders", "No": "Successful Orders"})
            self.assertEqual(dict(zip(trace["labels"], trace["values"])), totals.to_dict())
            self.assertEqual(trace["hole"], hole)
            self.assertIn("label", trace["textinfo"])
            self.assertIn("percent", trace["textinfo"])
            self.assertAlmostEqual(sum(trace["values"]), kpis["revenue"] if revenue else len(expected))
        self.assertEqual(len(management_insights(expected)), 4)

    def test_initial_dashboard(self):
        self.assert_dashboard_matches(self.data)

    def test_each_filter_and_combined_selection(self):
        channels = sorted(self.data.sales_channel.unique())
        categories = sorted(self.data.category_clean.unique())
        start, end = self.data.order_date.min().date(), self.data.order_date.max().date()
        self.app.multiselect(key="channels").set_value(["Online"]).run()
        self.assert_dashboard_matches(self.data.loc[self.data.sales_channel.eq("Online")])
        self.app.button(key="reset").click().run()
        self.app.multiselect(key="categories").set_value(["Electronics"]).run()
        self.assert_dashboard_matches(self.data.loc[self.data.category_clean.eq("Electronics")])
        self.app.button(key="reset").click().run()
        cutoff = start + (end - start) // 2
        self.app.date_input(key="date_range").set_value((start, cutoff)).run()
        self.assert_dashboard_matches(filter_data(self.data, start, cutoff, channels, categories))
        self.app.multiselect(key="channels").set_value(["Online"]).run()
        self.app.multiselect(key="categories").set_value(["Electronics"]).run()
        self.assert_dashboard_matches(filter_data(self.data, start, cutoff, ["Online"], ["Electronics"]))
        self.app.button(key="reset").click().run()
        self.assert_dashboard_matches(self.data)

    def test_empty_channel_and_category_selections(self):
        for key in ["channels", "categories"]:
            self.app.multiselect(key=key).set_value([]).run()
            self.assertEqual(len(self.app.exception), 0)
            self.assertEqual([metric.value for metric in self.app.metric], ["0", "0", "N/A", "N/A"])
            self.assertEqual(len(self.app.get("plotly_chart")), 0)
            self.assertEqual(len(transaction_payload(self.app)["rows"]), 0)
            self.app.button(key="reset").click().run()

    def test_incomplete_single_day_and_no_match_dates(self):
        first = self.data.order_date.min().date()
        self.app.date_input(key="date_range").set_value((first,)).run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(any("both a start" in item.value for item in self.app.info))
        self.app.date_input(key="date_range").set_value((first, first)).run()
        self.assert_dashboard_matches(self.data.loc[self.data.order_date.eq(pd.Timestamp(first))])
        days = pd.date_range(self.data.order_date.min(), self.data.order_date.max())
        missing_days = days.difference(self.data.order_date.unique())
        self.assertGreater(len(missing_days), 0)
        missing_day = missing_days[0].date()
        self.app.date_input(key="date_range").set_value((missing_day, missing_day)).run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(self.app.metric[0].value, "0")
        self.app.button(key="reset").click().run()
        self.assert_dashboard_matches(self.data)

    def test_theme_switch_preserves_filtered_data_and_reset_preserves_theme(self):
        self.app.multiselect(key="channels").set_value(["Online"]).run()
        expected = self.data.loc[self.data.sales_channel.eq("Online")]
        for name in ["Dark Mode", "Light Mode", "Dark Mode"]:
            self.app.radio(key="dashboard_theme").set_value(name).run()
            self.assert_dashboard_matches(expected)
            palette = get_theme(name)
            for element in self.app.get("plotly_chart"):
                figure = json.loads(element.proto.spec)
                self.assertEqual(figure["layout"]["paper_bgcolor"], palette["surface"])
                self.assertEqual(figure["layout"]["font"]["color"], palette["text"])
            self.assertIn(f'data-theme="{palette["name"]}"', self.app.get("iframe")[0].proto.srcdoc)
        self.app.button(key="reset").click().run()
        self.assertEqual(self.app.radio(key="dashboard_theme").value, "Dark Mode")
        self.assert_dashboard_matches(self.data)

    def test_previous_period_deltas_use_equal_windows_and_correct_units(self):
        channels = sorted(self.data.sales_channel.unique())
        categories = sorted(self.data.category_clean.unique())
        start = self.data.order_date.max().to_period("M").start_time
        end = self.data.order_date.max()
        current = self.data.loc[self.data.order_date.between(start, end)]
        previous_end = start - pd.Timedelta(days=1)
        previous_start = start - (end - start + pd.Timedelta(days=1))
        previous = self.data.loc[self.data.order_date.between(previous_start, previous_end)]
        result = compare_previous_period(self.data, current, start, end, channels, categories)
        self.assertTrue(result["available"])
        self.assertAlmostEqual(result["deltas"]["revenue"],
                               (current.revenue_lkr.sum() / previous.revenue_lkr.sum() - 1) * 100)
        self.assertAlmostEqual(result["deltas"]["profit_margin"],
                               current.profit_lkr.sum()/current.revenue_lkr.sum()*100
                               - previous.profit_lkr.sum()/previous.revenue_lkr.sum()*100)
        self.assertAlmostEqual(result["deltas"]["return_rate"],
                               (current.is_returned.mean() - previous.is_returned.mean())*100)
        self.app.date_input(key="date_range").set_value((start.date(),end.date())).run()
        self.assert_dashboard_matches(current)
        self.assertIn("% vs prior", self.app.metric[0].delta)
        self.assertIn("pp vs prior", self.app.metric[2].delta)
        full = compare_previous_period(self.data,self.data,self.data.order_date.min(),end,channels,categories)
        self.assertFalse(full["available"])
        self.assertTrue(all(value is None for value in full["deltas"].values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
