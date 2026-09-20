"""Live browser verification and screenshots for the enhanced dashboard."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys

from playwright.sync_api import expect, sync_playwright
import numpy as np
import pandas as pd
import plotly
import streamlit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from utils.data_processing import DATA_PATH, calculate_kpis, load_dataset, prepare_data
from utils.themes import get_theme

OUTPUT = ROOT / "screenshots" / "enhanced"
TABS = ["Executive Summary", "Sales Performance", "Customer Behaviour", "Operations & Risk", "Detailed Transactions", "Data Quality"]


def rgb(color):
    return "rgb(" + ", ".join(str(int(color[i:i+2],16)) for i in (1,3,5)) + ")"


def idle(page):
    page.locator(".footer").wait_for(timeout=30000)
    expect(page.get_by_test_id("stStatusWidget")).not_to_be_visible(timeout=30000)
    expect(page.get_by_test_id("stException")).to_have_count(0)


def metrics(page, data):
    k = calculate_kpis(data)
    values = [f"{k['revenue']:,.0f}",f"{k['profit']:,.0f}",
              f"{k['profit_margin']:.2f}%" if len(data) else "N/A",
              f"{k['return_rate']:.2f}%" if len(data) else "N/A"]
    expect(page.get_by_test_id("stMetricValue")).to_have_text(values,timeout=30000)
    idle(page)
    return k


def visit(page, tab):
    page.get_by_role("tab",name=tab,exact=True).click()
    idle(page)


def screenshot(page, name):
    idle(page)
    page.set_viewport_size({"width":1440,"height":1050})
    page.get_by_test_id("stMain").evaluate("e=>e.scrollTop=0")
    height=page.get_by_test_id("stMain").evaluate("e=>e.scrollHeight")
    page.set_viewport_size({"width":1440,"height":max(1050,height+30)})
    page.mouse.move(2,2)
    page.wait_for_timeout(650)
    page.screenshot(path=str(OUTPUT/name),full_page=True,animations="disabled")


def chart(page, key):
    page.wait_for_function("""key=>[...document.querySelectorAll('.js-plotly-plot')]
        .some(e=>e.layout?.meta?.dashboard_key===key && e.data?.length)""",arg=key,timeout=30000)
    return page.evaluate("""key=>{const e=[...document.querySelectorAll('.js-plotly-plot')]
        .find(e=>e.layout?.meta?.dashboard_key===key);return {data:e.data,background:e.layout.paper_bgcolor}}""",key)


def check_charts(page, data, theme_name):
    palette=get_theme(theme_name)
    k=calculate_kpis(data)
    checked=[]
    for tab, checks in [
        ("Sales Performance", [("monthly_trend","y",k["revenue"]), ("category_profit","x",k["profit"]),
                                ("channel_distribution","values",k["revenue"]),("category_share","values",k["revenue"])]),
        ("Customer Behaviour", [("segment_distribution","values",len(data)),("payment_distribution","values",len(data)),
                                 ("rating_distribution","rating_count",int(data.customer_rating.notna().sum()))]),
        ("Operations & Risk", [("return_analysis","values",len(data)),("province_revenue","x",k["revenue"]),
                                 ("delivery_profit","points",len(data))]),
    ]:
        visit(page,tab)
        for key,measure,total in checks:
            result=chart(page,key)
            assert result["background"]==palette["surface"], (key,result["background"])
            if measure=="points": value=sum(len(t["x"]) for t in result["data"])
            elif measure=="rating_count": value=len(result["data"][0]["x"])
            else: value=sum(result["data"][0][measure])
            assert abs(value-total)<.01,(key,value,total)
            if measure=="values":
                trace=result["data"][0]
                assert "label" in trace["textinfo"] and "percent" in trace["textinfo"]
                assert trace["hovertemplate"]
            checked.append(key)
    return checked


def select_only(page,label,options,selected):
    widget=page.get_by_test_id("stMultiSelect").filter(has=page.get_by_role("combobox",name=label,exact=True))
    for option in options:
        if option!=selected:
            widget.get_by_role("button",name=f"Remove {option}",exact=True).click()


def main():
    OUTPUT.mkdir(exist_ok=True,parents=True)
    data,audit=prepare_data(load_dataset())
    errors=[]
    report={"captured_at_utc":datetime.now(timezone.utc).isoformat(),"python":platform.python_version(),
            "libraries":{"streamlit":streamlit.__version__,"pandas":pd.__version__,"plotly":plotly.__version__,"numpy":np.__version__},
            "source_sha256":hashlib.sha256(DATA_PATH.read_bytes()).hexdigest(),
            "source_audit":{key:value for key,value in audit.items() if not isinstance(value,pd.DataFrame)},
            "states":[],"theme_checks":[]}
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        page=browser.new_page(viewport={"width":1440,"height":1050},device_scale_factor=1)
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.goto("http://127.0.0.1:8501",wait_until="domcontentloaded")
        metrics(page,data)
        # Animation preferences change presentation only, never the analytics.
        hero=page.locator(".st-key-dashboard_hero")
        page.emulate_media(reduced_motion="no-preference")
        expect(hero).to_be_visible()
        assert hero.evaluate("e=>getComputedStyle(e,'::after').animationName")=="lm-glow"
        page.get_by_text("Animations",exact=True).click()
        metrics(page,data)
        assert hero.evaluate("e=>getComputedStyle(e,'::after').animationName")=="none"
        page.get_by_text("Animations",exact=True).click()
        metrics(page,data)
        page.emulate_media(reduced_motion="reduce")
        assert hero.evaluate("e=>getComputedStyle(e,'::after').animationName")=="none"
        assert page.get_by_test_id("stMetric").first.evaluate("e=>getComputedStyle(e).animationName")=="none"
        page.emulate_media(reduced_motion="no-preference")
        accents=page.get_by_test_id("stMetric").evaluate_all("elements=>elements.map(e=>getComputedStyle(e).borderTopColor)")
        assert len(set(accents))==4,accents
        report["animation_toggle_and_reduced_motion"]="passed"
        report["distinct_kpi_accents"]=len(set(accents))
        for theme_name in ("Light Mode","Dark Mode"):
            page.get_by_text(theme_name,exact=True).click()
            metrics(page,data)
            palette=get_theme(theme_name)
            assert page.get_by_test_id("stMain").evaluate("e=>getComputedStyle(e).backgroundColor")==rgb(palette["bg"])
            assert page.get_by_test_id("stDateInputField").evaluate("e=>getComputedStyle(e).backgroundColor")==rgb(palette["surface_alt"])
            assert page.get_by_test_id("stDateInput").locator('[data-type="literal"]').first.evaluate("e=>getComputedStyle(e).color")==rgb(palette["text"])
            checked=check_charts(page,data,theme_name)
            before=page.get_by_test_id("stMetricValue").all_text_contents()
            page.get_by_test_id("stMetric").first.hover()
            page.wait_for_timeout(300)
            assert page.get_by_test_id("stMetric").first.evaluate("e=>getComputedStyle(e).transform")!="none"
            assert page.get_by_test_id("stMetricValue").all_text_contents()==before
            for tab in TABS:
                visit(page,tab)
                screenshot(page,f"{palette['name']}_{tab.lower().replace(' ','_').replace('&','and')}.png")
            visit(page,"Detailed Transactions")
            frame=page.frame_locator("iframe").first
            expect(frame.locator(".table-shell")).to_have_attribute("data-theme",palette["name"])
            assert frame.locator("th").first.evaluate("e=>getComputedStyle(e).backgroundColor")==rgb(palette["surface_alt"])
            assert frame.locator("tbody td").first.evaluate("e=>getComputedStyle(e).color")==rgb(palette["text"])
            payload=json.loads(frame.locator("#table-data").text_content())
            assert len(payload["rows"])==len(data)
            # Exercise the actual searchable, sortable, paginated table.
            order=data.order_id.iloc[0]
            frame.get_by_label("Search records").fill(order)
            expect(frame.locator("tbody tr")).to_have_count(1)
            expect(frame.locator("tbody td").first).to_have_text(order)
            frame.get_by_label("Search records").fill("")
            frame.get_by_role("button",name="Sort by Revenue (LKR)",exact=True).click()
            assert float(frame.locator("tbody tr").first.locator("td").nth(5).inner_text().replace(",",""))==data.revenue_lkr.min()
            frame.get_by_role("button",name="Next",exact=True).click()
            expect(frame.locator("#page")).to_contain_text("Page 2")
            report["theme_checks"].append({"theme":theme_name,"charts_checked":checked,"table_search_sort_pagination":"passed"})
            print(f"Verified all 10 charts, filters and table styling in {theme_name}.",flush=True)

        for channel,category in [("Online","Electronics"),("Mobile App","Beauty")]:
            page.get_by_role("button",name="Reset all filters",exact=True).click()
            metrics(page,data)
            select_only(page,"Sales Channel",sorted(data.sales_channel.unique()),channel)
            select_only(page,"Product Category",sorted(data.category_clean.unique()),category)
            filtered=data.loc[data.sales_channel.eq(channel)&data.category_clean.eq(category)]
            k=metrics(page,filtered)
            checked=check_charts(page,filtered,"Dark Mode")
            visit(page,"Sales Performance")
            screenshot(page,f"filtered_{channel.lower().replace(' ','_')}.png")
            report["states"].append({"selection":f"{channel} / {category}","kpis":k,"charts_checked":checked})
            print(f"Verified filtered state: {channel} / {category}.",flush=True)

        page.get_by_role("button",name="Reset all filters",exact=True).click()
        metrics(page,data)
        cutoff=(data.order_date.min().to_period("M")+2).end_time.date()
        field=page.get_by_role("spinbutton",name="month, Date range end date",exact=True)
        field.click();field.press_sequentially(str(cutoff.month))
        field=page.get_by_role("spinbutton",name="day, Date range end date",exact=True)
        field.click();field.press_sequentially(str(cutoff.day));field.press("Tab")
        filtered=data.loc[data.order_date.le(pd.Timestamp(cutoff))]
        k=metrics(page,filtered)
        checked=check_charts(page,filtered,"Dark Mode")
        report["states"].append({"selection":f"Through {cutoff}","kpis":k,"charts_checked":checked})
        visit(page,"Sales Performance");screenshot(page,"filtered_date_range.png")
        visit(page,"Detailed Transactions")
        with page.expect_download() as download_info:
            page.get_by_role("button",name="Download filtered transactions (CSV)",exact=True).click()
        downloaded=pd.read_csv(download_info.value.path(),keep_default_na=False)
        assert set(downloaded.order_id)==set(filtered.order_id)
        report["download_rows_verified"]=len(downloaded)

        page.get_by_role("button",name="Reset all filters",exact=True).click()
        metrics(page,data)
        last_month=data.order_date.max().to_period("M").start_time
        field=page.get_by_role("spinbutton",name="month, Date range start date",exact=True)
        field.click();field.press_sequentially(str(last_month.month));field.press("Tab")
        recent=data.loc[data.order_date.ge(last_month)]
        metrics(page,recent)
        expect(page.get_by_test_id("stMetricDelta")).to_have_count(4)
        visit(page,"Executive Summary");screenshot(page,"kpi_prior_period_comparison.png")
        report["prior_period_indicators_verified"]=True

        phone=browser.new_page(viewport={"width":390,"height":844},is_mobile=True)
        phone.on("pageerror",lambda error:errors.append(str(error)))
        phone.goto("http://127.0.0.1:8501")
        metrics(phone,data)
        phone.get_by_text("Dark Mode",exact=True).click()
        metrics(phone,data)
        phone.get_by_test_id("stSidebarCollapseButton").click()
        expect(phone.get_by_test_id("stSidebar")).to_have_attribute("aria-expanded","false")
        phone.wait_for_function("""()=>[...document.querySelectorAll('[data-testid="stMetric"]')]
            .every(e=>e.getBoundingClientRect().right<=innerWidth-8)""")
        phone.wait_for_timeout(1000)
        assert phone.evaluate("document.documentElement.scrollWidth<=innerWidth")
        phone.screenshot(path=str(OUTPUT/"mobile_dark.png"))
        report["mobile_layout_and_sidebar"]="passed"
        report["browser_errors"]=errors
        assert not errors,errors
        browser.close()
    (OUTPUT/"validation_results.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print("Browser validation passed. Enhanced screenshots and validation report saved.",flush=True)


if __name__=="__main__":
    main()
