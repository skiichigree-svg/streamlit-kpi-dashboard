# =====================================
# app.py  (Overall KPI Integrated) - cleaned & hardened
# =====================================

import json
import os
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# -----------------------------
# Basic Config
# -----------------------------
st.set_page_config(layout="wide")

# -----------------------------
# Paths (single source of truth)
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
HIST_DIR = DATA_DIR / "historical"
RECENT_FILE = DATA_DIR / "recent" / "fact_recent.parquet"
BUDGET_FILE = DATA_DIR / "budget.csv"
META_PATH = DATA_DIR / "metadata.json"

TODAY = pd.Timestamp.today().normalize()

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

# -----------------------------
# Meta (dict only)
# -----------------------------
meta = load_json_dict(META_PATH)

refresh_time = meta.get("last_updated", "—") if meta else "—"
latest_data_date = meta.get("latest_jst_date", "—") if meta else "—"

# -----------------------------
# Header
# -----------------------------
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
            データリフレッシュ実行日時：{refresh_time}<br>
            最新データ日付：{latest_data_date}
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

# -----------------------------
# Data Load
# -----------------------------
@st.cache_data(show_spinner=False)
def load_actual_data(hist_dir: Path, recent_file: Path) -> pd.DataFrame:
    dfs = []

    if hist_dir.exists():
        for f in sorted(hist_dir.glob("fact_*.parquet")):
            try:
                dfs.append(pd.read_parquet(f))
            except Exception as e:
                # 1ファイル壊れても全停止しない
                st.warning(f"historical の読み込み失敗: {f.name} ({e})")

    if recent_file.exists():
        try:
            dfs.append(pd.read_parquet(recent_file))
        except Exception as e:
            st.warning(f"recent の読み込み失敗: {recent_file.name} ({e})")

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)
    if "jst_date" in df.columns:
        df["jst_date"] = pd.to_datetime(df["jst_date"], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def load_budget(budget_file: Path) -> pd.DataFrame:
    if not budget_file.exists():
        st.warning("Budget file not found.")
        return pd.DataFrame()

    df = pd.read_csv(budget_file)
    df.columns = df.columns.str.strip()
    return df


df_all = load_actual_data(HIST_DIR, RECENT_FILE)
df_budget = load_budget(BUDGET_FILE)

if df_all.empty:
    st.error("No data found. Please check parquet files.")
    st.stop()

# -----------------------------
# Date Helpers
# -----------------------------
def period_start(date: pd.Timestamp, mode: str) -> pd.Timestamp:
    if mode == "MTD":
        return date.replace(day=1)
    if mode == "QTD":
        q = (date.month - 1) // 3 * 3 + 1
        return date.replace(month=q, day=1)
    if mode == "YTD":
        return date.replace(month=1, day=1)
    raise ValueError(f"Unknown mode: {mode}")

# -----------------------------
# KPI Builder
# -----------------------------
def build_overall_kpi(df: pd.DataFrame, df_budget: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp):
    cur = df[(df["jst_date"] >= start) & (df["jst_date"] <= end)]
    prev = df[(df["jst_date"] >= start - pd.DateOffset(years=1)) &
              (df["jst_date"] <= end - pd.DateOffset(years=1))]

    cur_local = cur.get("PartnerCostInAdvertiserCurrency", pd.Series(dtype=float)).sum()
    cur_usd = cur.get("PartnerCostInUSD", pd.Series(dtype=float)).sum()
    prev_local = prev.get("PartnerCostInAdvertiserCurrency", pd.Series(dtype=float)).sum()
    prev_usd = prev.get("PartnerCostInUSD", pd.Series(dtype=float)).sum()

    yoy_local = (cur_local / prev_local - 1) if prev_local > 0 else None
    yoy_usd = (cur_usd / prev_usd - 1) if prev_usd > 0 else None

    # Budget: require columns year/month/PartnerCostInUSD
    budget = 0.0
    if not df_budget.empty and {"year", "month", "PartnerCostInUSD"}.issubset(df_budget.columns):
        budget = df_budget[
            (df_budget["year"] == start.year) &
            (df_budget["month"] >= start.month) &
            (df_budget["month"] <= end.month)
        ]["PartnerCostInUSD"].sum()

    achievement = (cur_usd / budget) if budget and budget > 0 else None

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
    else:
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
            tickprefix=prefix,
            tickformat=value_fmt
        ),
        xaxis=dict(title=None),
    )

    return fig


def progress_bar(rate):
    rate = rate or 0
    rate_capped = min(rate, 1.2)  # 120% まで表示

    if rate >= 1.0:
        color = "#1a9850"   # 濃緑
    elif rate >= 0.8:
        color = "#2ca02c"   # 緑
    else:
        color = "#f1c40f"   # 黄色

    fig = go.Figure()

    fig.add_bar(
        x=[rate_capped * 100],
        y=["Progress"],
        orientation="h",
        width=0.6,
        marker_color=color,
        text=[f"{rate*100:.1f}%"],
        textposition="auto",
        hovertemplate="Achievement: %{x:.1f}%<extra></extra>",
    )

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
        xaxis=dict(range=[0, 120], title="%", ticksuffix="%"),
        yaxis=dict(showticklabels=False),
        margin=dict(l=10, r=10, t=20, b=10),
        showlegend=False,
    )

    return fig


def monthly_actual_budget(df: pd.DataFrame, df_budget: pd.DataFrame):
    df = df.copy()
    df["year"] = df["jst_date"].dt.year
    df["month"] = df["jst_date"].dt.month

    act = df.groupby(["year", "month"], as_index=False).agg(
        PartnerCostInUSD=("PartnerCostInUSD", "sum"),
        PartnerCostInAdvertiserCurrency=("PartnerCostInAdvertiserCurrency", "sum"),
    )

    bud = pd.DataFrame(columns=["year", "month", "PartnerCostInUSD", "PartnerCostInAdvertiserCurrency"])
    if not df_budget.empty and {"year", "month"}.issubset(df_budget.columns):
        # 予算CSVにJPY列が無い場合に備えて get で安全に
        bud = df_budget.groupby(["year", "month"], as_index=False).agg(
            PartnerCostInUSD=("PartnerCostInUSD", "sum") if "PartnerCostInUSD" in df_budget.columns else ("month", "size"),
            PartnerCostInAdvertiserCurrency=("PartnerCostInAdvertiserCurrency", "sum") if "PartnerCostInAdvertiserCurrency" in df_budget.columns else ("month", "size"),
        )

    m = act.merge(bud, on=["year", "month"], how="left", suffixes=("_actual", "_budget"))
    m["ym"] = pd.to_datetime(m["year"].astype(str) + "-" + m["month"].astype(str) + "-01")
    return m.sort_values("ym").tail(13)


def monthly_chart(df: pd.DataFrame, show_usd: bool = True):
    df = df.copy()

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

    if actual_col not in df.columns:
        st.warning("Monthly chart: actual column not found.")
        return go.Figure()

    # 達成率
    df["achievement"] = df[actual_col] / df[budget_col] if budget_col in df.columns else None

    def color_rule(rate):
        if pd.isna(rate):
            return "#bdc3c7"
        if rate >= 1.0:
            return "#1a9850"
        elif rate >= 0.8:
            return "#2ca02c"
        else:
            return "#f1c40f"

    bar_colors = df["achievement"].apply(color_rule) if "achievement" in df.columns else "#bdc3c7"

    fig = go.Figure()

    fig.add_bar(
        x=df["ym"],
        y=df[actual_col],
        name="Actual",
        marker_color=bar_colors,
        customdata=df["achievement"] if "achievement" in df.columns else None,
        hovertemplate=(
            "Month: %{x|%Y-%m}<br>"
            f"Actual: {prefix}%{{y:,.0f}}<br>"
            "Achievement: %{customdata:.1%}"
            "<extra></extra>"
        ) if "achievement" in df.columns else (
            "Month: %{x|%Y-%m}<br>"
            f"Actual: {prefix}%{{y:,.0f}}"
            "<extra></extra>"
        ),
    )

    if budget_col in df.columns:
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


def format_yoy(yoy):
    if yoy is None:
        return "—", "yoy-flat", ""
    if yoy > 0:
        return f"{yoy*100:.1f}%", "yoy-up", "▲"
    if yoy < 0:
        return f"{abs(yoy)*100:.1f}%", "yoy-down", "▼"
    return "0.0%", "yoy-flat", ""


def render_pacing_block(label: str, df_all_: pd.DataFrame, df_budget_: pd.DataFrame):
    start = period_start(TODAY, label)
    kpi = build_overall_kpi(df_all_, df_budget_, start, TODAY)

    st.markdown(f"<div class='pacing-title'>{label}</div>", unsafe_allow_html=True)

    spend_jpy = kpi["current"]["local"]
    spend_usd = kpi["current"]["usd"]
    budget_usd = kpi["budget"]

    st.markdown(
        f"""
        <div class="pacing-spend">
            ¥{spend_jpy:,.0f}
            <span style="color:#7f8c8d;"> / Budget —</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="pacing-spend">
            ${spend_usd:,.0f}
            <span style="color:#7f8c8d;"> / Budget ${budget_usd:,.0f}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.plotly_chart(
        progress_bar(kpi["achievement"]),
        use_container_width=True,
        key=f"{label}_pacing_bar"
    )

    yoy_jpy_val, yoy_jpy_class, yoy_jpy_icon = format_yoy(kpi["yoy_local"])
    yoy_usd_val, yoy_usd_class, yoy_usd_icon = format_yoy(kpi["yoy_usd"])

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            f"""
            <div class="pacing-yoy {yoy_jpy_class}">
                YoY JPY<br>
                {yoy_jpy_icon} {yoy_jpy_val}
            </div>
            """,
            unsafe_allow_html=True
        )
    with c2:
        st.markdown(
            f"""
            <div class="pacing-yoy {yoy_usd_class}">
                YoY USD<br>
                {yoy_usd_icon} {yoy_usd_val}
            </div>
            """,
            unsafe_allow_html=True
        )

# =============================
# Pacing Card
# =============================
st.header("🚦 Pacing")

with st.container():
    cols = st.columns(3)
    for col, label in zip(cols, ["MTD", "QTD", "YTD"]):
        with col:
            render_pacing_block(label, df_all, df_budget)

st.divider()

# -----------------------------
# Monthly Trend
# -----------------------------
show_usd_global = st.toggle("Show USD (toggle to JPY)", value=True)
st.subheader("📈 Overall Monthly Trend (Last 13 Months)")

df_m = monthly_actual_budget(df_all, df_budget)

st.plotly_chart(
    monthly_chart(df_m, show_usd=show_usd_global),
    use_container_width=True,
    key="overall_monthly"
)
