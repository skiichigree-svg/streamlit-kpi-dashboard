# =====================================
# app.py  (Overall KPI Integrated)
# =====================================

import os
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

# -----------------------------
# Basic Config
# -----------------------------
st.set_page_config(layout="wide")
st.title("📊 Performance Dashboard")

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
HIST_DIR = DATA_DIR / "historical"
RECENT_FILE = DATA_DIR / "recent" / "fact_recent.parquet"
BUDGET_FILE = DATA_DIR / "data" / "budget.csv"
META_FILE = DATA_DIR / "metadata.json"

TODAY = pd.Timestamp.today().normalize()

# -----------------------------
# Data Load
# -----------------------------
@st.cache_data
def load_actual_data():
    dfs = []
    if HIST_DIR.exists():
        for f in HIST_DIR.glob("fact_*.parquet"):
            dfs.append(pd.read_parquet(f))

    if RECENT_FILE.exists():
        dfs.append(pd.read_parquet(RECENT_FILE))

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)
    df["jst_date"] = pd.to_datetime(df["jst_date"])
    return df


@st.cache_data
def load_budget():
    if not os.path.exists(BUDGET_FILE):
        st.warning("Budget file not found. Budget-related KPIs are disabled.")
        return pd.DataFrame()
    return pd.read_csv(BUDGET_FILE)


@st.cache_data
def load_metadata():
    if META_FILE.exists():
        return pd.read_json(META_FILE, typ="series")
    return None


df_all = load_actual_data()
df_budget = load_budget()
meta = load_metadata()

if df_all.empty:
    st.error("No data found. Please check parquet files.")
    st.stop()

# -----------------------------
# Date Helpers
# -----------------------------
def period_start(date, mode):
    if mode == "MTD":
        return date.replace(day=1)
    if mode == "QTD":
        q = (date.month - 1) // 3 * 3 + 1
        return date.replace(month=q, day=1)
    if mode == "YTD":
        return date.replace(month=1, day=1)



# -----------------------------
# KPI Builder
# -----------------------------
def build_overall_kpi(df, df_budget, start, end):
    cur = df[(df["jst_date"] >= start) & (df["jst_date"] <= end)]
    prev = df[(df["jst_date"] >= start - pd.DateOffset(years=1)) &
              (df["jst_date"] <= end - pd.DateOffset(years=1))]

    cur_local = cur["PartnerCostInAdvertiserCurrency"].sum()
    cur_usd = cur["PartnerCostInUSD"].sum()
    prev_local = prev["PartnerCostInAdvertiserCurrency"].sum()
    prev_usd = prev["PartnerCostInUSD"].sum()

    yoy_local = (cur_local / prev_local - 1) if prev_local > 0 else None
    yoy_usd = (cur_usd / prev_usd - 1) if prev_usd > 0 else None

    budget = df_budget[
        (df_budget["year"] == start.year) &
        (df_budget["month"] >= start.month) &
        (df_budget["month"] <= end.month)
    ]["PartnerCostInUSD"].sum()

    achievement = cur_usd / budget if budget > 0 else None

    return {
        "current": {"local": cur_local, "usd": cur_usd},
        "previous": {"local": prev_local, "usd": prev_usd},
        "yoy_local": yoy_local,
        "yoy_usd": yoy_usd,
        "budget": budget,
        "achievement": achievement,
    }

# -----------------------------
# Charts
# -----------------------------
def yoy_bar(prev, cur, title, currency="USD", bar_width=0.35):
    max_val = max(prev, cur) if max(prev, cur) > 0 else 1

    if currency == "JPY":
        prefix = "¥"
        value_fmt = ",.0f"
    else:  # USD
        prefix = "$"
        value_fmt = ",.0f"

    fig = go.Figure()

    fig.add_bar(
        x=["Last Year"],
        y=[prev],
        width=bar_width,
        marker_color="#C0C0C0",
        name="Last Year",
        text=[f"{prefix}{prev:{value_fmt}}"],
        textposition="outside",
    )

    fig.add_bar(
        x=["This Year"],
        y=[cur],
        width=bar_width,
        marker_color="#1f77b4",
        name="This Year",
        text=[f"{prefix}{cur:{value_fmt}}"],
        textposition="outside",
    )

    fig.update_layout(
        paper_bgcolor="#FFF9E6",
        plot_bgcolor="#FFF9E6",
        title=title,
        height=220,
        barmode="group",
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=10),
        yaxis=dict(
            range=[0, max_val * 1.25],
            tickprefix=prefix,   # ★Y軸にも通貨
            tickformat=value_fmt
        ),
        xaxis=dict(title=None),
    )

    return fig



def progress_bar(rate):
    # 安全ガード
    rate = rate or 0
    rate_capped = min(rate, 1.2)  # 120% まで表示

    # ---- 色ルール ----
    # 100%以上：濃緑
    # 80%〜99%：通常グリーン
    # 80%未満：黄色
    if rate >= 1.0:
        color = "#1a9850"   # 濃緑
    elif rate >= 0.8:
        color = "#2ca02c"   # 緑
    else:
        color = "#f1c40f"   # 黄色

    fig = go.Figure()

    # 実績バー
    fig.add_bar(
        x=[rate_capped * 100],
        y=["Progress"],
        orientation="h",
        width=0.6,  # ★ Monthlyの約半分
        marker_color=color,
        text=[f"{rate*100:.1f}%"],
        textposition="auto",
        hovertemplate="Achievement: %{x:.1f}%<extra></extra>",
    )

    # ---- 100% ライン ----
    fig.add_vline(
        x=100,
        line_dash="dash",
        line_color="gray",
        annotation_text="100%",
        annotation_position="top",
        annotation_font_color="gray",
    )

    fig.update_layout(
        height=160,
        xaxis=dict(
            range=[0, 120],
            title="%",
            ticksuffix="%",
        ),
        yaxis=dict(showticklabels=False),
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=False,
    )

    return fig

def monthly_actual_budget(df, df_budget):
    df = df.copy()

    df["year"] = df["jst_date"].dt.year
    df["month"] = df["jst_date"].dt.month

    # Actual（USD / JPY 両方）
    act = df.groupby(["year", "month"], as_index=False).agg(
        PartnerCostInUSD=("PartnerCostInUSD", "sum"),
        PartnerCostInAdvertiserCurrency=("PartnerCostInAdvertiserCurrency", "sum"),
    )

    # Budget（USD / JPY 両方）
    bud = df_budget.groupby(["year", "month"], as_index=False).agg(
        PartnerCostInUSD=("PartnerCostInUSD", "sum"),
        PartnerCostInAdvertiserCurrency=("PartnerCostInAdvertiserCurrency", "sum"),
    )

    m = act.merge(bud, on=["year", "month"], how="left", suffixes=("_actual", "_budget"))

    m["ym"] = pd.to_datetime(m["year"].astype(str) + "-" + m["month"].astype(str) + "-01")

    return m.sort_values("ym").tail(13)


def monthly_chart(df, show_usd=True):
    df = df.copy()

    # 通貨カラム切替（← ★ここが重要）
    if show_usd:
        actual_col = "PartnerCostInUSD_actual"
        budget_col = "PartnerCostInUSD_budget"
        currency = "USD"
        prefix = "$"
        yaxis_title = "USD"
    else:
        actual_col = "PartnerCostInAdvertiserCurrency_actual"
        budget_col = "PartnerCostInAdvertiserCurrency_budget"
        currency = "JPY"
        prefix = "¥"
        yaxis_title = "JPY"

    # 達成率
    df["achievement"] = df[actual_col] / df[budget_col]

    # 色ルール（Budget Achievement と完全一致）
    def color_rule(rate):
        if pd.isna(rate):
            return "#bdc3c7"  # Budgetなし
        if rate >= 1.0:
            return "#1a9850"  # 濃緑
        elif rate >= 0.8:
            return "#2ca02c"  # 緑
        else:
            return "#f1c40f"  # 黄色

    bar_colors = df["achievement"].apply(color_rule)

    fig = go.Figure()

    # Actual（月次）
    fig.add_bar(
        x=df["ym"],
        y=df[actual_col],
        name="Actual",
        marker_color=bar_colors,
        customdata=df["achievement"],
        hovertemplate=(
            "Month: %{x|%Y-%m}<br>"
            f"Actual: {prefix}%{{y:,.0f}}<br>"
            "Achievement: %{customdata:.1%}"
            "<extra></extra>"
        ),
    )

    # Budget（線）
    fig.add_trace(
        go.Scatter(
            x=df["ym"],
            y=df[budget_col],
            name="Budget",
            mode="lines+markers",
            line=dict(color="#7f8c8d", dash="dash"),
            marker=dict(size=6),
            hovertemplate=(
                "Month: %{x|%Y-%m}<br>"
                f"Budget: {prefix}%{{y:,.0f}}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_layout(
        height=420,
        title=f"Overall Monthly Actual vs Budget ({currency})",
        xaxis=dict(title=None),
        yaxis=dict(title=yaxis_title, tickprefix=prefix),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=20, r=20, t=70, b=20),
    )

    return fig



# -----------------------------
# UI : Overall KPI
# -----------------------------
st.header("📌 Overall KPI")

left, right = st.columns([3, 2])

with left:
    show_usd_global = st.toggle("Show USD in YoY charts", value=False)

with right:
    if meta is not None:
        latest_date = df_all["jst_date"].max().strftime("%Y-%m-%d")
        updated_at = meta.get("last_updated", "—")

        st.caption(
            f"📅 Latest data: **{latest_date}**  ｜ 🔄 Updated at: **{updated_at}**"
        )


for label in ["MTD", "QTD", "YTD"]:
    with st.expander(label, expanded=(label == "MTD")):
        start = period_start(TODAY, label)
        kpi = build_overall_kpi(df_all, df_budget, start, TODAY)


    st.subheader(label)

    # =========================
    # 2カラム：Budget / YoY
    # =========================
    c_budget, c_yoy = st.columns([1, 2])

    # =====================
    # Budget Achievement
    # =====================
    with c_budget:
        with st.container(border=True):

            # KPI
            st.metric(
                "Budget Achievement",
                f"{kpi['achievement']*100:.1f}%" if kpi["achievement"] else "—",
                f"Actual ${kpi['current']['usd']:,.0f} / Budget ${kpi['budget']:,.0f}"
            )

            # グラフ背景
            with st.container():
                st.markdown(
                    "<div style='background:#FFF9E6; padding:8px; border-radius:6px'>",
                    unsafe_allow_html=True,
                )

                st.plotly_chart(
                    progress_bar(kpi["achievement"]),
                    use_container_width=True,
                    key=f"{label}_budget"
                )

                st.markdown("</div>", unsafe_allow_html=True)

    # =====================
    # YoY
    # =====================
    with c_yoy:
        with st.container(border=True):

            # KPI
            m1, m2 = st.columns(2)
            m1.metric(
                "PartnerCost (JPY)",
                f"¥{kpi['current']['local']:,.0f}",
                f"{kpi['yoy_local']*100:.1f}% YoY" if kpi["yoy_local"] else "—"
            )
            m2.metric(
                "PartnerCost (USD)",
                f"${kpi['current']['usd']:,.0f}",
                f"{kpi['yoy_usd']*100:.1f}% YoY" if kpi["yoy_usd"] else "—"
            )

            # グラフ背景
            with st.container():
                st.markdown(
                    "<div style='background:#FFF9E6; padding:8px; border-radius:6px'>",
                    unsafe_allow_html=True,
                )

                st.plotly_chart(
                    yoy_bar(
                        kpi["previous"]["local"],
                        kpi["current"]["local"],
                        "JPY",
                        currency="JPY",
                        bar_width=0.35,   # ★ ここで幅統一
                    ),
                    use_container_width=True,
                    key=f"{label}_yoy_jpy"
                )

                if show_usd_global:
                    st.plotly_chart(
                        yoy_bar(
                            kpi["previous"]["usd"],
                            kpi["current"]["usd"],
                            "USD",
                            currency="USD",
                            bar_width=0.35,
                        ),
                        use_container_width=True,
                        key=f"{label}_yoy_usd"
                    )

                st.markdown("</div>", unsafe_allow_html=True)


    st.divider()




# -----------------------------
# Monthly Trend
# -----------------------------
st.subheader("📈 Overall Monthly Trend (Last 13 Months)")

df_m = monthly_actual_budget(df_all, df_budget)

st.plotly_chart(
    monthly_chart(df_m, show_usd=show_usd_global),
    use_container_width=True,
    key="overall_monthly"
)

