# =====================================
# app.py  (Performance Dashboard)
# =====================================

import os
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import date
from pathlib import Path

# -------------------------------------
# Config
# -------------------------------------
st.set_page_config(layout="wide")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

RECENT_PATH = DATA_DIR / "recent" / "fact_recent.parquet"
BUDGET_PATH = DATA_DIR / "budget.csv"

# -------------------------------------
# Utils (Date)
# -------------------------------------
def get_today_jst():
    return pd.Timestamp.now(tz="Asia/Tokyo").normalize()

def get_qtd_start(d: pd.Timestamp):
    q_month = ((d.month - 1) // 3) * 3 + 1
    return d.replace(month=q_month, day=1)

# -------------------------------------
# Load Data
# -------------------------------------
@st.cache_data
def load_recent():
    df = pd.read_parquet(RECENT_PATH)

    required_cols = {
        "year",
        "month",
        "PartnerCostInUSD",
        "PartnerCostInAdvertiserCurrency",
    }
    missing = required_cols - set(df.columns)
    if missing:
        raise ValueError(f"fact_recent.parquet missing columns: {missing}")

    return df

@st.cache_data
def load_budget():
    if BUDGET_PATH.exists():
        return pd.read_csv(BUDGET_PATH)
    return pd.DataFrame()

@st.cache_data
def load_metadata():
    if META_PATH.exists():
        with open(META_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}

meta = load_metadata()

if "latest_jst_date" in meta:
    st.caption(f"最新データ日付: {meta['latest_jst_date']}")

df_all = load_recent()
df_budget = load_budget()

# -------------------------------------
# Header
# -------------------------------------
st.title("📊 Performance Dashboard")

latest_date = df_all["jst_date"].max()
st.caption(f"最新データ日付: {latest_date.date()}")

# -------------------------------------
# MTD / QTD / YTD (fact_recent 直)
# -------------------------------------
def calc_mtd_qtd_ytd(df_all: pd.DataFrame):
    # 最新 month を「現在月」とみなす
    max_ym = (df_all["year"] * 100 + df_all["month"]).max()
    cur_year = max_ym // 100
    cur_month = max_ym % 100

    mtd = df_all[
        (df_all["year"] == cur_year) &
        (df_all["month"] == cur_month)
    ]

    q_start_month = ((cur_month - 1) // 3) * 3 + 1
    qtd = df_all[
        (df_all["year"] == cur_year) &
        (df_all["month"] >= q_start_month) &
        (df_all["month"] <= cur_month)
    ]

    ytd = df_all[df_all["year"] == cur_year]

    return {
        "MTD": {
            "USD": mtd["PartnerCostInUSD"].sum(),
            "JPY": mtd["PartnerCostInAdvertiserCurrency"].sum(),
        },
        "QTD": {
            "USD": qtd["PartnerCostInUSD"].sum(),
            "JPY": qtd["PartnerCostInAdvertiserCurrency"].sum(),
        },
        "YTD": {
            "USD": ytd["PartnerCostInUSD"].sum(),
            "JPY": ytd["PartnerCostInAdvertiserCurrency"].sum(),
        },
    }


progress = calc_mtd_qtd_ytd(df_all)

# -------------------------------------
# Pacing Display
# -------------------------------------
st.header("🚦 Pacing")

cols = st.columns(3)
for col, key in zip(cols, ["MTD", "QTD", "YTD"]):
    with col:
        st.subheader(key)
        st.metric(
            label="USD",
            value=f"${progress[key]['USD']:,.0f}"
        )
        st.metric(
            label="JPY",
            value=f"¥{progress[key]['JPY']:,.0f}"
        )

# -------------------------------------
# Monthly Trend (途中月含む)
# -------------------------------------
def build_monthly_trend(df_all: pd.DataFrame, df_budget: pd.DataFrame):
    max_ym = (df_all["year"] * 100 + df_all["month"]).max()
    cur_year = max_ym // 100
    cur_month = max_ym % 100

    monthly = (
        df_all
        .groupby(["year", "month"], as_index=False)
        .agg(
            actual_usd=("PartnerCostInUSD", "sum"),
            actual_jpy=("PartnerCostInAdvertiserCurrency", "sum"),
        )
    )

    monthly["is_partial_month"] = (
        (monthly["year"] == cur_year) &
        (monthly["month"] == cur_month)
    )

    monthly["ym"] = pd.to_datetime(
        monthly["year"].astype(str)
        + "-"
        + monthly["month"].astype(str).str.zfill(2)
        + "-01"
    )

    if not df_budget.empty:
        monthly = monthly.merge(
            df_budget.rename(
                columns={
                    "PartnerCostInUSD": "budget_usd",
                    "PartnerCostInAdvertiserCurrency": "budget_jpy",
                }
            ),
            on=["year", "month"],
            how="left",
        )

    return monthly.sort_values("ym").tail(13)


monthly = build_monthly_trend(df_all, df_budget)

# -------------------------------------
# Plotly Chart
# -------------------------------------
def plot_monthly_trend(monthly: pd.DataFrame, currency="USD"):
    actual_col = "actual_usd" if currency == "USD" else "actual_jpy"
    budget_col = "budget_usd" if currency == "USD" else "budget_jpy"

    fig = go.Figure()

    done = monthly[~monthly["is_partial_month"]]
    fig.add_bar(
        x=done["ym"],
        y=done[actual_col],
        name="Actual (Closed Month)",
        marker_color="#16a34a",
    )

    partial = monthly[monthly["is_partial_month"]]
    fig.add_bar(
        x=partial["ym"],
        y=partial[actual_col],
        name="Actual (MTD)",
        marker_color="#16a34a",
        marker_pattern_shape="/",
        opacity=0.6,
    )

    if budget_col in monthly.columns:
        fig.add_trace(
            go.Scatter(
                x=monthly["ym"],
                y=monthly[budget_col],
                name="Budget",
                mode="lines+markers",
                line=dict(dash="dash", color="gray"),
            )
        )

    fig.update_layout(
        title="Overall Monthly Actual vs Budget",
        barmode="overlay",
        xaxis_title="Month",
        yaxis_title=currency,
        legend_orientation="h",
    )

    return fig

st.header("📈 Overall Monthly Trend (Last 13 Months)")
currency = st.radio("Currency", ["USD", "JPY"], horizontal=True)
fig = plot_monthly_trend(monthly, currency=currency)
st.plotly_chart(fig, use_container_width=True)

st.caption("※ Striped bar indicates partial (in-progress) month.")
