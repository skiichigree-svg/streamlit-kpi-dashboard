# =====================================
# app.py  (Performance Dashboard)
# =====================================

import os
import json
import calendar
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime, date
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

# -----------------------------
# Helpers
# -----------------------------
def load_json_dict(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        st.warning(f"metadata.json はあるが読み込みに失敗: {e}")
        return None

def css_inject():
    st.markdown(
        """
        <style>
        /* Pacing Card Typography */
        .pacing-title {
            font-size: 2.25rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .pacing-spend {
            font-size: 1.75rem;
            font-weight: 600;
            line-height: 1.2;
        }
        .pacing-yoy {
            font-size: 1.5rem;
            font-weight: 600;
        }

        /* YoY color rules */
        .yoy-up   { color: #1a9850; }   /* green */
        .yoy-down { color: #d73027; }   /* red */
        .yoy-flat { color: #7f8c8d; }   /* gray */
        </style>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------
# Date helpers
# -------------------------------------
def days_in_month(d: date):
    return calendar.monthrange(d.year, d.month)[1]

def days_elapsed_in_quarter(d: date):
    q = (d.month - 1) // 3
    start_month = q * 3 + 1
    elapsed = 0
    for m in range(start_month, d.month):
        elapsed += calendar.monthrange(d.year, m)[1]
    return elapsed + d.day

def days_in_quarter(d: date):
    q = (d.month - 1) // 3
    start_month = q * 3 + 1
    total = 0
    for m in range(start_month, start_month + 3):
        total += calendar.monthrange(d.year, m)[1]
    return total



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

st.markdown(
    f"""
    <div style="
        display: flex;
        align-items: baseline;
        gap: 12px;
        margin-bottom: 8px;
    ">
        <div style="font-size: 2.2rem; font-weight: 700;">
            📊 Performance Dashboard
        </div>
        <div style="
            font-size: 9px;
            color: #7f8c8d;
            line-height: 1.2;
        ">
            データリフレッシュ実行日時： {meta['last_updated']}<br>
            最新データ日付： {meta['latest_jst_date']}
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

css_inject()

# -----------------------------
# Guards: data existence
# -----------------------------
has_hist = HIST_DIR.exists() and any(HIST_DIR.glob("fact_*.parquet"))
has_recent = RECENT_FILE.exists()

if not has_hist and not has_recent:
    st.error(
        "データがまだ生成されていません。\n\n"
        "✅ まず refresh を実行してください（scheduler / 手動 refresh_data.py）。"
    )
    st.stop()

# -------------------------------------
# MTD / QTD / YTD
# -------------------------------------
currency = st.radio("Currency", ["USD", "JPY"], horizontal=True)

cost_col = "PartnerCostInUSD" if currency == "USD" else "PartnerCostInAdvertiserCurrency"
budget_col = "PartnerCostInUSD" if currency == "USD" else "PartnerCostInAdvertiserCurrency"

# MTD
mtd_actual = df_all[
    (df_all["year"] == latest_date.year) &
    (df_all["month"] == latest_date.month)
][cost_col].sum()

mtd_budget = df_budget[
    (df_budget["year"] == latest_date.year) &
    (df_budget["month"] == latest_date.month)
][budget_col].sum()

mtd_pace = mtd_budget * latest_date.day / days_in_month(latest_date)

# QTD
q = (latest_date.month - 1) // 3
q_months = [q * 3 + 1, q * 3 + 2, q * 3 + 3]

qtd_actual = df_all[
    (df_all["year"] == latest_date.year) &
    (df_all["month"].isin(q_months))
][cost_col].sum()

qtd_budget = df_budget[
    (df_budget["year"] == latest_date.year) &
    (df_budget["month"].isin(q_months))
][budget_col].sum()

qtd_pace = qtd_budget * days_elapsed_in_quarter(latest_date) / days_in_quarter(latest_date)

# YTD
ytd_actual = df_all[df_all["year"] == latest_date.year][cost_col].sum()
ytd_budget = df_budget[df_budget["year"] == latest_date.year][budget_col].sum()

days_year = 366 if calendar.isleap(latest_date.year) else 365
ytd_pace = ytd_budget * latest_date.timetuple().tm_yday / days_year

c1, c2, c3 = st.columns(3)
c1.metric("MTD", f"{currency} {mtd_actual:,.0f}", f"Pace {mtd_pace:,.0f}")
c2.metric("QTD", f"{currency} {qtd_actual:,.0f}", f"Pace {qtd_pace:,.0f}")
c3.metric("YTD", f"{currency} {ytd_actual:,.0f}", f"Pace {ytd_pace:,.0f}")

st.divider()

# -------------------------------------
# Monthly Trend (Last 13 Months)
# -------------------------------------
st.subheader("📈 Overall Monthly Trend (Last 13 Months)")

trend = monthly_actual_budget(df_all, df_budget).tail(13)

latest_ym = f"{latest_date.year}-{latest_date.month}"

fig = go.Figure()

fig.add_bar(
    x=trend["ym"],
    y=trend[f"actual_{currency.lower()}"],
    name="Actual",
    marker=dict(
        color="#2ecc71",
        pattern_shape=["/" if ym == latest_ym else "" for ym in trend["ym"]],
    ),
)

fig.add_scatter(
    x=trend["ym"],
    y=trend[f"budget_{currency.lower()}"],
    name="Budget",
    mode="lines+markers",
    line=dict(color="#7f8c8d", dash="dash"),
)

fig.update_layout(
    height=420,
    yaxis_title=currency,
    xaxis_title="Month",
    legend=dict(orientation="h"),
)

st.plotly_chart(fig, use_container_width=True)

st.caption("※ Striped bar indicates partial (in-progress) month.")
