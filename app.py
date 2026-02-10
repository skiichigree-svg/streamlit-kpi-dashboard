# =====================================
# app.py  (Performance Dashboard)
# =====================================

import os
import json
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path

# -------------------------------------
# Config
# -------------------------------------
st.set_page_config(layout="wide")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

RECENT_PATH = DATA_DIR / "recent" / "fact_recent.parquet"
BUDGET_PATH = DATA_DIR / "budget.csv"
META_PATH = DATA_DIR / "metadata.json"

# -------------------------------------
# Loaders
# -------------------------------------
@st.cache_data
def load_recent():
    return pd.read_parquet(RECENT_PATH)

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

# -------------------------------------
# Aggregation
# -------------------------------------
def monthly_actual_budget(df, df_budget):
    act = df.groupby(["year", "month"], as_index=False).agg(
        PartnerCostInUSD=("PartnerCostInUSD", "sum"),
        PartnerCostInAdvertiserCurrency=("PartnerCostInAdvertiserCurrency", "sum"),
    )

    bud = df_budget.groupby(["year", "month"], as_index=False).agg(
        PartnerCostInUSD=("PartnerCostInUSD", "sum"),
        PartnerCostInAdvertiserCurrency=("PartnerCostInAdvertiserCurrency", "sum"),
    ) if not df_budget.empty else pd.DataFrame()

    m = act.merge(
        bud,
        on=["year", "month"],
        how="left",
        suffixes=("_actual", "_budget"),
    )

    m["ym"] = pd.to_datetime(
        m["year"].astype(str) + "-" + m["month"].astype(str) + "-01"
    )

    return m.sort_values("ym").tail(13)

# -------------------------------------
# Main
# -------------------------------------
df_all = load_recent()
df_budget = load_budget()
meta = load_metadata()

st.title("📊 Performance Dashboard")

# 最新データ日付（metadata 由来）
if "latest_jst_date" in meta:
    st.caption(f"最新データ日付: {meta['latest_jst_date']}")

# -------------------------------------
# MTD / QTD / YTD
# -------------------------------------
today = pd.to_datetime(meta["latest_jst_date"])
current_year = today.year
current_month = today.month

mtd = df_all.query("year == @current_year and month == @current_month")
ytd = df_all.query("year == @current_year")

qtd_months = [(current_month - 1) // 3 * 3 + i for i in range(1, 4)]
qtd = df_all.query(
    "year == @current_year and month in @qtd_months"
)

def sum_block(df):
    return (
        df["PartnerCostInUSD"].sum(),
        df["PartnerCostInAdvertiserCurrency"].sum(),
    )

mtd_usd, mtd_jpy = sum_block(mtd)
qtd_usd, qtd_jpy = sum_block(qtd)
ytd_usd, ytd_jpy = sum_block(ytd)

c1, c2, c3 = st.columns(3)
c1.metric("MTD (USD)", f"${mtd_usd:,.0f}")
c1.metric("MTD (JPY)", f"¥{mtd_jpy:,.0f}")

c2.metric("QTD (USD)", f"${qtd_usd:,.0f}")
c2.metric("QTD (JPY)", f"¥{qtd_jpy:,.0f}")

c3.metric("YTD (USD)", f"${ytd_usd:,.0f}")
c3.metric("YTD (JPY)", f"¥{ytd_jpy:,.0f}")

st.divider()

# -------------------------------------
# Monthly Trend (Last 13 Months)
# -------------------------------------
st.subheader("📈 Overall Monthly Trend (Last 13 Months)")

currency = st.radio("Currency", ["USD", "JPY"], horizontal=True)

m = monthly_actual_budget(df_all, df_budget)

value_col = (
    "PartnerCostInUSD_actual"
    if currency == "USD"
    else "PartnerCostInAdvertiserCurrency_actual"
)
budget_col = (
    "PartnerCostInUSD_budget"
    if currency == "USD"
    else "PartnerCostInAdvertiserCurrency_budget"
)

latest_ym = m["ym"].max()

colors = []
patterns = []

for ym in m["ym"]:
    if ym == latest_ym:
        colors.append("#2ECC71")
        patterns.append("/")
    else:
        colors.append("#2ECC71")
        patterns.append("")

fig = go.Figure()

fig.add_bar(
    x=m["ym"],
    y=m[value_col],
    name="Actual",
    marker=dict(color=colors, pattern_shape=patterns),
)

if budget_col in m.columns:
    fig.add_scatter(
        x=m["ym"],
        y=m[budget_col],
        name="Budget",
        mode="lines+markers",
        line=dict(dash="dash"),
    )

fig.update_layout(
    height=450,
    xaxis_title="Month",
    yaxis_title=currency,
    legend_orientation="h",
)

st.plotly_chart(fig, use_container_width=True)

st.caption("※ ストライプ表示は進行中の月を示します")
