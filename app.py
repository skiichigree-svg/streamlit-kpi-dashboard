import pandas as pd
import streamlit as st
from io import BytesIO

from modules.charts import (
    make_monthly_progress_chart,
    make_treemap,
    make_donut,
    make_stacked_bar,
    make_pacing_bar,
    make_actual_budget_chart,
    make_clickable_advertiser_bar,
    make_comparison_color_map,
)

from modules.data_loader import load_dashboard_data, load_metadata, load_budget

from modules.data_processing import (
    apply_period_filter,
    get_default_period,
    get_comparison_period,
    get_advertiser_lifecycle_table,
    portfolio_snapshot,
    portfolio_timeline,
    monthly_sales_progress,
    calc_pacing_summary,
    calc_previous_period_progress,
    monthly_actual_budget,
    get_cost_col,
)

from modules.ui_components import (
    inject_design_agency_style,
    render_header,
    render_filter_panel,
    render_kpi_cards,
    render_section_title,
    render_card,
)


st.set_page_config(
    page_title="Performance Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_design_agency_style()

df = load_dashboard_data()
df_budget = load_budget()
metadata = load_metadata()

if df.empty:
    st.warning("データがありません。data/ 配下の parquet または csv を確認してください。")
    st.stop()

# PacingはDigital Pod固定
df_pacing = df[
    df["Pod"].astype(str).str.strip().str.lower() == "digital"
].copy()

if "Pod" in df_budget.columns:
    df_budget_pacing = df_budget[
        df_budget["Pod"].astype(str).str.strip().str.lower() == "digital"
    ].copy()
else:
    st.warning("budget.csv に Pod 列がないため、Digital Pod のBudgetだけに絞れません。")
    df_budget_pacing = df_budget.copy()

render_header(
    title="Performance Dashboard",
    subtitle="Team / Office portfolio, advertiser activity, and Partner Cost trend",
    latest_data_date=metadata.get("latest_jst_date"),
    last_updated=metadata.get("last_updated"),
)


filters = render_filter_panel(df)

selected_pod = filters["selected_pod"]

if selected_pod != "All" and "Pod" in df.columns:
    df_scope = df[df["Pod"].astype(str).str.strip() == selected_pod].copy()
else:
    df_scope = df.copy()

# Budgetも同じscopeがあれば絞る。なければ全体Budgetとして扱う。
if not df_budget.empty and selected_pod != "All" and "Pod" in df_budget.columns:
    df_budget_scope = df_budget[
        df_budget["Pod"].astype(str).str.strip() == selected_pod
    ].copy()
else:
    df_budget_scope = df_budget.copy()

default_start, default_end = get_default_period(df_scope)
start_month = filters["start_month"] or default_start
end_month = filters["end_month"] or default_end

df_current = apply_period_filter(df_scope, start_month, end_month)

def format_month_period(start_month, end_month):
    start = start_month.strftime("%Y/%m")
    end = end_month.strftime("%Y/%m")
    return start if start == end else f"{start} - {end}"

def get_quarter_start(ts):
    ts = pd.Timestamp(ts)
    q_start_month = ((ts.month - 1) // 3) * 3 + 1
    return pd.Timestamp(year=ts.year, month=q_start_month, day=1)

def get_quarter_end(ts):
    q_start = get_quarter_start(ts)
    return q_start + pd.offsets.QuarterEnd(0)

EXPORT_DIMENSIONS = [
    "Year",
    "Quarter",
    "Month",
    "PartnerId",
    "PartnerName",
    "AdvertiserId",
    "AdvertiserName",
    "Pod",
    "MarketFlag",
    "MarketType",
    "Channel",
    "PrivateContractId",
    "Media",
]

EXPORT_METRICS = [
    "AdvertiserCostInAdvertiserCurrency",
    "AdvertiserCostInUSD",
    "PartnerCostInAdvertiserCurrency",
    "PartnerCostInUSD",
    "MediaCostInAdvertiserCurrency",
    "MediaCostInUSD",
    "DataCostInAdvertiserCurrency",
    "DataCostInUSD",
    "ImpressionCount",
    "ClickCount",
    "CustomCPAConversions",
]


def build_export_df(input_df):
    if input_df is None or input_df.empty:
        return pd.DataFrame(columns=EXPORT_DIMENSIONS + EXPORT_METRICS)

    export_df = input_df.copy()

    available_dimensions = [
        c for c in EXPORT_DIMENSIONS
        if c in export_df.columns
    ]

    available_metrics = [
        c for c in EXPORT_METRICS
        if c in export_df.columns
    ]

    for col in available_metrics:
        export_df[col] = pd.to_numeric(export_df[col], errors="coerce").fillna(0)

    export_df = (
        export_df
        .groupby(available_dimensions, dropna=False, as_index=False)[available_metrics]
        .sum()
    )

    return export_df


def to_excel_bytes(export_df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        export_df.to_excel(
            writer,
            index=False,
            sheet_name="export",
        )

        worksheet = writer.sheets["export"]

        # Header filter
        worksheet.auto_filter.ref = worksheet.dimensions

        # Freeze header row
        worksheet.freeze_panes = "A2"

        # Column width
        for column_cells in worksheet.columns:
            max_length = 0
            column_letter = column_cells[0].column_letter

            for cell in column_cells:
                try:
                    value = str(cell.value) if cell.value is not None else ""
                    max_length = max(max_length, len(value))
                except Exception:
                    pass

            worksheet.column_dimensions[column_letter].width = min(max_length + 2, 40)

    output.seek(0)
    return output.getvalue()

def calc_prev_quarter_progress(df, latest_date, value_col):
    latest_date = pd.Timestamp(latest_date)

    current_q_start = get_quarter_start(latest_date)
    current_q_end = get_quarter_end(latest_date)

    prev_q_start = current_q_start - pd.DateOffset(months=3)
    prev_q_end = current_q_start - pd.DateOffset(days=1)

    elapsed_days = (latest_date - current_q_start).days + 1
    total_days = (current_q_end - current_q_start).days + 1
    elapsed_rate = elapsed_days / total_days if total_days > 0 else 0

    current_q_df = df[
        (pd.to_datetime(df["YearMonth"]) >= current_q_start)
        & (pd.to_datetime(df["YearMonth"]) <= latest_date)
    ].copy()

    prev_q_df = df[
        (pd.to_datetime(df["YearMonth"]) >= prev_q_start)
        & (pd.to_datetime(df["YearMonth"]) <= prev_q_end)
    ].copy()

    qtd_actual = float(current_q_df[value_col].sum()) if value_col in current_q_df.columns else 0
    prev_q_total = float(prev_q_df[value_col].sum()) if value_col in prev_q_df.columns else 0

    prev_q_pace_target = prev_q_total * elapsed_rate
    prev_q_pace_progress = (
        qtd_actual / prev_q_pace_target
        if prev_q_pace_target > 0
        else None
    )

    projected_q_end = (
        qtd_actual / elapsed_rate
        if elapsed_rate > 0
        else None
    )

    projected_vs_prev_q = (
        projected_q_end / prev_q_total - 1
        if projected_q_end is not None and prev_q_total > 0
        else None
    )

    return {
        "current_q_start": current_q_start,
        "current_q_end": current_q_end,
        "prev_q_start": prev_q_start,
        "prev_q_end": prev_q_end,
        "elapsed_rate": elapsed_rate,
        "qtd_actual": qtd_actual,
        "prev_q_total": prev_q_total,
        "prev_q_pace_target": prev_q_pace_target,
        "prev_q_pace_progress": prev_q_pace_progress,
        "projected_q_end": projected_q_end,
        "projected_vs_prev_q": projected_vs_prev_q,
    }


current_period_label = format_month_period(start_month, end_month)


def get_pacing_period_label(period_label, latest_date):
    if period_label == "MTD":
        start = latest_date.replace(day=1)

    elif period_label == "QTD":
        q = (latest_date.month - 1) // 3
        start_month = q * 3 + 1
        start = latest_date.replace(month=start_month, day=1)

    elif period_label == "YTD":
        start = latest_date.replace(month=1, day=1)

    else:
        start = latest_date

    return f"{start.strftime('%Y/%m/%d')} - {latest_date.strftime('%Y/%m/%d')}"

def portfolio_snapshot_multi(
    df: pd.DataFrame,
    dimensions: list[str],
    value_col: str,
    top_n: int = 30,
) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=dimensions + [value_col])

    available_dimensions = [c for c in dimensions if c in df.columns]

    if not available_dimensions or value_col not in df.columns:
        return pd.DataFrame(columns=dimensions + [value_col])

    tmp = df.copy()
    tmp[value_col] = pd.to_numeric(tmp[value_col], errors="coerce").fillna(0)

    out = (
        tmp
        .groupby(available_dimensions, dropna=False, as_index=False)[value_col]
        .sum()
        .sort_values(value_col, ascending=False)
    )

    # AdvertiserNameがある場合、Advertiser単位でTop N + Others化
    if "AdvertiserName" in available_dimensions and len(out) > top_n:
        adv_total = (
            out
            .groupby("AdvertiserName", dropna=False)[value_col]
            .sum()
            .sort_values(ascending=False)
        )

        top_advs = set(adv_total.head(top_n).index.astype(str))

        out["AdvertiserName"] = out["AdvertiserName"].astype(str)
        out["AdvertiserName"] = out["AdvertiserName"].where(
            out["AdvertiserName"].isin(top_advs),
            "Others",
        )

        out = (
            out
            .groupby(available_dimensions, dropna=False, as_index=False)[value_col]
            .sum()
            .sort_values(value_col, ascending=False)
        )

    return out

# =========================
# 1. Sales progress / pacing
# =========================
render_section_title("1. 売上進捗（Digital Podのみ）")

currency = st.radio("Currency", ["USD", "JPY"], horizontal=True, key="pacing_currency")
value_col = get_cost_col(currency)
money_format = "$%,.0f" if currency == "USD" else "¥%,.0f"

st.caption(
    f"Pacing scope: Digital Pod | Actual rows: {len(df_pacing):,} | Budget rows: {len(df_budget_pacing):,}"
)

pacing = calc_pacing_summary(
    df=df_pacing,
    df_budget=df_budget_pacing,
    metadata=metadata,
    currency=currency,
)

latest_date = pacing.get("latest_date")

if pacing["has_budget"]:

    for label in ["MTD", "QTD", "YTD"]:
        item = pacing["periods"][label]

        with render_card(f"{label} Pacing"):
            st.plotly_chart(
                make_pacing_bar(item["achievement_to_pace"]),
                use_container_width=True,
                key=f"{label}_pacing_{currency}",
            )

            k1, k2, k3, k4, k5 = st.columns(5)

            k1.metric("Actual", item["actual_fmt"])
            k2.metric("Pace Target", item["pace_fmt"])
            k3.metric("Budget", item["budget_fmt"])
            k4.metric("YoY", item["yoy_fmt"])
            k5.metric("Budget Achv.", item["budget_achievement_fmt"])

            st.divider()

            st.caption(
                f"{item['prev_period_label']} comparison: "
                f"elapsed rate {item['elapsed_rate']:.1%}"
            )

            p1, p2, p3, p4, p5 = st.columns(5)

            p1.metric(f"{item['prev_period_label']} Total", item["prev_period_total_fmt"])
            p2.metric(f"{item['prev_period_label']} Pace Target", item["prev_period_pace_target_fmt"])
            p3.metric("Progress vs Prev Pace", item["progress_vs_prev_period_pace_fmt"])
            p4.metric("Projected End", item["projected_end_fmt"])
            p5.metric("Projected vs Prev", item["projected_vs_prev_period_fmt"])

    with render_card("Overall Monthly Actual vs Budget｜Digital Pod"):
        trend = monthly_actual_budget(df_pacing, df_budget_pacing, currency=currency)
        st.plotly_chart(
            make_actual_budget_chart(trend, currency=currency),
            use_container_width=True,
            key=f"actual_budget_{currency}",
        )
        st.caption("Bar color indicates budget achievement: yellow <80%, green 80–99%, dark green ≥100%.")
else:
    # Budgetがない場合のfallback。数字だけではなく、月次推移は残す。
    st.warning("budget.csv が見つからない、またはBudget列が不足しています。Actual trendのみ表示します。")
    progress_df = monthly_sales_progress(df_current, currency=currency)

    total_cost = float(df_current[value_col].sum()) if value_col in df_current.columns else 0
    active_adv = int(
        df_current.loc[df_current[value_col] > 0, "AdvertiserName"].nunique()
    ) if value_col in df_current.columns else 0

    avg_monthly = float(progress_df[value_col].mean()) if not progress_df.empty and value_col in progress_df.columns else 0

    render_kpi_cards(
        [
            ("Partner Cost", total_cost, "期間内合計"),
            ("Active Advertisers", active_adv, "期間内に売上あり"),
            ("Avg Monthly Cost", avg_monthly, "月平均"),
        ],
        currency=currency,
    )

    with render_card("Monthly Partner Cost Trend"):
        st.plotly_chart(
            make_monthly_progress_chart(progress_df, value_col=value_col),
            use_container_width=True,
        )

# =========================
# 2. Active / Churn Advertiser
# =========================
render_section_title("2. Advertiser ステータス")

lifecycle_df = get_advertiser_lifecycle_table(
    df_scope,
    metadata,
    cost_col=value_col,
)

# -------------------------
# Status label mapping
# -------------------------
status_label_map = {
    "Existing": "継続",
    "New": "新規",
    "Reactivated": "復帰",
    "At Risk": "離脱リスク",
    "Churned": "離脱・休眠",
    "Dormant": "離脱・休眠",
}

status_order = [
    "All",
    "継続",
    "新規",
    "復帰",
    "離脱リスク",
    "離脱・休眠",
]

lifecycle_df = lifecycle_df.copy()

# 元の英語ステータスは残して、日本語表示用の列を追加
lifecycle_df["AdvertiserStatusRaw"] = lifecycle_df["AdvertiserStatus"]
lifecycle_df["AdvertiserStatusJP"] = (
    lifecycle_df["AdvertiserStatusRaw"]
    .map(status_label_map)
    .fillna(lifecycle_df["AdvertiserStatusRaw"])
)

def fmt_money_display(value):
    if pd.isna(value):
        return "-"

    try:
        value = float(value)
    except Exception:
        return "-"

    if currency == "USD":
        return f"${value:,.0f}"
    else:
        return f"¥{value:,.0f}"


def fmt_int_display(value):
    if pd.isna(value):
        return "-"

    try:
        value = float(value)
    except Exception:
        return "-"

    return f"{value:,.0f}"

with render_card("Advertiser ステータス"):

    st.info(
        "このカードでは、Advertiserごとの稼働状況を、現在四半期・過去4四半期・それ以前の売上実績から分類します。"
    )

    # -------------------------
    # Revenue health summary
    # -------------------------
    latest_data_date = pacing.get("latest_date")

    revenue_health_rows = []

    for period_label in ["QTD", "YTD"]:
        prev_comp = calc_previous_period_progress(
            df=df_scope,
            latest_date=latest_data_date,
            period=period_label,
            cost_col=value_col,
            currency=currency,
        )

        revenue_health_rows.append(
            {
                "Period": period_label,
                "Actual": fmt_money_display(prev_comp["actual"]),
                "Prev Period": prev_comp["prev_period_label"],
                "Prev Total": prev_comp["prev_period_total_fmt"],
                "Prev Pace Target": prev_comp["prev_period_pace_target_fmt"],
                "Progress vs Prev Pace": prev_comp["progress_vs_prev_period_pace_fmt"],
                "Projected End": prev_comp["projected_end_fmt"],
                "Projected vs Prev": prev_comp["projected_vs_prev_period_fmt"],
            }
        )

    revenue_health_df = pd.DataFrame(revenue_health_rows)

    st.markdown("**選択Pod / 期間の売上ヘルス**")
    st.caption(
        "Sidebarで選択されたPodを対象に、現在のQTD/YTDが前四半期・前年のペースに対して進んでいるかを確認します。"
    )

    st.dataframe(
        revenue_health_df,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # -------------------------
    # Status filter
    # -------------------------
    status_filter = st.segmented_control(
        "ステータス",
        options=status_order,
        default="All",
        key="advertiser_lifecycle_status_filter",
    )

    show_df = lifecycle_df.copy()

    if status_filter != "All":
        show_df = show_df[show_df["AdvertiserStatusJP"] == status_filter]

    # -------------------------
    # Summary table
    # -------------------------
    summary = (
        lifecycle_df
        .groupby("AdvertiserStatusJP", as_index=False)
        .agg(
            Advertisers=("AdvertiserName", "nunique"),
            CurrentQuarterCost=("CurrentQuarterCost", "sum"),
            Trailing4QCost=("Trailing4QCost", "sum"),
        )
    )

    # 表示順を固定
    summary["StatusOrder"] = summary["AdvertiserStatusJP"].apply(
        lambda x: status_order.index(x) if x in status_order else 999
    )
    summary = summary.sort_values("StatusOrder").drop(columns="StatusOrder")

    summary = summary.rename(
        columns={
            "AdvertiserStatusJP": "ステータス",
            "Advertisers": "Advertiser数",
            "CurrentQuarterCost": "現在四半期売上",
            "Trailing4QCost": "直近4四半期売上",
        }
    )

    summary_display = summary.copy()

    summary_display["Advertiser数"] = summary_display["Advertiser数"].apply(fmt_int_display)
    summary_display["現在四半期売上"] = summary_display["現在四半期売上"].apply(fmt_money_display)
    summary_display["直近4四半期売上"] = summary_display["直近4四半期売上"].apply(fmt_money_display)

    summary_numeric_cols = [
        "Advertiser数",
        "現在四半期売上",
        "直近4四半期売上",
    ]

    summary_style = (
        summary_display
        .style
        .set_properties(
            subset=summary_numeric_cols,
            **{"text-align": "right"}
        )
        .set_properties(
            subset=["ステータス"],
            **{"text-align": "left"}
        )
    )

    st.dataframe(
        summary_style,
        use_container_width=True,
        hide_index=True,
    )

    st.divider()

    # -------------------------
    # Detail table
    # -------------------------
    detail_cols = [
        "AdvertiserName",
        "Pod",
        "AdvertiserStatusJP",
        "CurrentQuarterCost",
        "Trailing4QCost",
        "CurrentQuarter",
        "Trailing4QPeriod",
    ]

    # Pod列がない場合でも落ちないようにする
    detail_cols = [c for c in detail_cols if c in show_df.columns]

    detail_df = show_df[detail_cols].rename(
        columns={
            "AdvertiserName": "Advertiser",
            "Pod": "Pod",
            "AdvertiserStatusJP": "ステータス",
            "CurrentQuarterCost": "現在四半期売上",
            "Trailing4QCost": "直近4四半期売上",
            "CurrentQuarter": "現在四半期",
            "Trailing4QPeriod": "直近4四半期",
        }
    )

    detail_display = detail_df.copy()

    money_cols = [
        "現在四半期売上",
        "直近4四半期売上",
        "過去累計売上",
    ]

    for col in money_cols:
        if col in detail_display.columns:
            detail_display[col] = detail_display[col].apply(fmt_money_display)

    detail_right_cols = [c for c in money_cols if c in detail_display.columns]

    detail_left_cols = [
        c for c in detail_display.columns
        if c not in detail_right_cols
    ]

    detail_style = (
        detail_display
        .style
        .set_properties(
            subset=detail_right_cols,
            **{"text-align": "right"}
        )
        .set_properties(
            subset=detail_left_cols,
            **{"text-align": "left"}
        )
    )

    st.dataframe(
        detail_style,
        use_container_width=True,
        hide_index=True,
    )

    # -------------------------
    # 定義：カード下部
    # -------------------------
    st.markdown(
        """
        <div style="
            margin-top: 18px;
            padding: 14px 16px;
            border: 1px solid #e5e7eb;
            border-radius: 12px;
            background: #fafafa;
        ">
            <div style="
                font-weight: 700;
                margin-bottom: 8px;
                font-size: 14px;
            ">
                ステータス定義・判定ルール
            </div>
            <ul style="
                margin-top: 0;
                margin-bottom: 0;
                padding-left: 20px;
                line-height: 1.8;
                font-size: 13px;
            ">
                <li><b>継続</b>：現在四半期と過去4四半期の両方で売上があるAdvertiser</li>
                <li><b>新規</b>：現在四半期に初めて売上が発生したAdvertiser</li>
                <li><b>復帰</b>：過去に売上があり、過去4四半期では売上がなかったが、現在四半期で再稼働したAdvertiser</li>
                <li><b>離脱リスク</b>：過去4四半期に売上があるが、現在四半期では売上が確認できないAdvertiser</li>
                <li><b>離脱・休眠</b>：過去に売上実績はあるが、現在四半期および過去4四半期で売上が確認できないAdvertiser</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================
# 3. Portfolio
# =========================
render_section_title("3. ポートフォリオ")

# -------------------------
# Portfolio comparison settings
# -------------------------
with render_card("Portfolio 比較設定"):

    portfolio_compare_type = st.segmented_control(
        "比較タイプ",
        ["なし", "Pod比較", "期間比較"],
        default="なし",
        key="portfolio_compare_type",
    )

    # Pod options
    if "Pod" in df.columns:
        pod_options = (
            df["Pod"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
            .tolist()
        )

        pod_options = [x for x in pod_options if x != ""]
        pod_options = ["All"] + sorted(pod_options)
    else:
        pod_options = ["All"]

    # Month options
    ym_options_portfolio = sorted(df["YearMonth"].dropna().unique())
    ym_labels_portfolio = [
        pd.Timestamp(x).strftime("%Y-%m") for x in ym_options_portfolio
    ]

    # デフォルトは全体フィルタと同じ期間
    default_a_start_label = start_month.strftime("%Y-%m")
    default_a_end_label = end_month.strftime("%Y-%m")

    if default_a_start_label not in ym_labels_portfolio:
        default_a_start_label = ym_labels_portfolio[0]

    if default_a_end_label not in ym_labels_portfolio:
        default_a_end_label = ym_labels_portfolio[-1]

    if portfolio_compare_type == "なし":
        df_portfolio_a = df_current.copy()
        df_portfolio_b = None

        portfolio_a_label = f"表示対象｜{current_period_label}"
        portfolio_b_label = None

    elif portfolio_compare_type == "Pod比較":
        c1, c2 = st.columns(2)

        with c1:
            pod_a = st.selectbox(
                "A群 Pod",
                pod_options,
                index=0,
                key="portfolio_pod_a",
            )

        with c2:
            default_b_index = 1 if len(pod_options) > 1 else 0
            pod_b = st.selectbox(
                "B群 Pod",
                pod_options,
                index=default_b_index,
                key="portfolio_pod_b",
            )

        def filter_by_pod(input_df, pod):
            if pod == "All" or "Pod" not in input_df.columns:
                return input_df.copy()
            return input_df[input_df["Pod"].astype(str).str.strip() == pod].copy()

        # Pod比較では、SidebarのPodフィルタ済みデータ df_scope ではなく、
        # 全体データ df からA群/B群を作る
        df_portfolio_a = filter_by_pod(df, pod_a)
        df_portfolio_a = apply_period_filter(df_portfolio_a, start_month, end_month)

        df_portfolio_b = filter_by_pod(df, pod_b)
        df_portfolio_b = apply_period_filter(df_portfolio_b, start_month, end_month)

        portfolio_a_label = f"A群｜{pod_a}｜{current_period_label}"
        portfolio_b_label = f"B群｜{pod_b}｜{current_period_label}"

    elif portfolio_compare_type == "期間比較":
        # 全体フィルタで選ばれているPodを使う
        selected_pod_for_period_compare = filters.get("selected_pod", "All")

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("**A群**")
            a_start_label = st.selectbox(
                "A群 Start Month",
                ym_labels_portfolio,
                index=ym_labels_portfolio.index(default_a_start_label),
                key="portfolio_a_start",
            )
            a_end_label = st.selectbox(
                "A群 End Month",
                ym_labels_portfolio,
                index=ym_labels_portfolio.index(default_a_end_label),
                key="portfolio_a_end",
            )

        with c2:
            st.markdown("**B群**")
            b_start_label = st.selectbox(
                "B群 Start Month",
                ym_labels_portfolio,
                index=0,
                key="portfolio_b_start",
            )
            b_end_label = st.selectbox(
                "B群 End Month",
                ym_labels_portfolio,
                index=min(len(ym_labels_portfolio) - 1, 2),
                key="portfolio_b_end",
            )

        a_start_month = pd.Timestamp(a_start_label + "-01")
        a_end_month = pd.Timestamp(a_end_label + "-01")
        b_start_month = pd.Timestamp(b_start_label + "-01")
        b_end_month = pd.Timestamp(b_end_label + "-01")

        if selected_pod_for_period_compare != "All" and "Pod" in df_scope.columns:
            df_base_period = df_scope[
                df_scope["Pod"].astype(str).str.strip() == selected_pod_for_period_compare
            ].copy()
        else:
            df_base_period = df_scope.copy()

        df_portfolio_a = apply_period_filter(
            df_base_period,
            a_start_month,
            a_end_month,
        )

        df_portfolio_b = apply_period_filter(
            df_base_period,
            b_start_month,
            b_end_month,
        )

        portfolio_a_label = f"A群｜{selected_pod_for_period_compare}｜{a_start_label} - {a_end_label}"
        portfolio_b_label = f"B群｜{selected_pod_for_period_compare}｜{b_start_label} - {b_end_label}"

    # 比較条件を明示
    if portfolio_compare_type != "なし":
        st.success(f"{portfolio_a_label}　vs　{portfolio_b_label}")
    else:
        st.caption("比較なし：全体フィルタで選択されたPod・期間のPortfolioを表示します。")

with render_card("Market Portfolio"):

    if portfolio_compare_type == "なし":
        if "MarketFlag" in df_portfolio_a.columns:
            snap_market = portfolio_snapshot(
                df_portfolio_a,
                "MarketFlag",
                top_n=10,
                value_col=value_col,
            )

            st.plotly_chart(
                make_donut(snap_market, "MarketFlag", value_col),
                use_container_width=True,
                key="market_portfolio",
                config={"displayModeBar": False},
            )
        else:
            st.caption("MarketFlag column is not available.")

    else:
        c1, c2 = st.columns(2)

        snap_market_a = portfolio_snapshot(
            df_portfolio_a,
            "MarketFlag",
            top_n=10,
            value_col=value_col,
        )

        snap_market_b = portfolio_snapshot(
            df_portfolio_b,
            "MarketFlag",
            top_n=10,
            value_col=value_col,
        )

        market_color_map = make_comparison_color_map(
            snap_market_a,
            snap_market_b,
            "MarketFlag",
            value_col,
        )

        with c1:
            st.markdown(f"**{portfolio_a_label}**")
            st.plotly_chart(
                make_donut(
                    snap_market_a,
                    "MarketFlag",
                    value_col,
                    color_map=market_color_map,
                ),
                use_container_width=True,
                key="market_portfolio_a",
                config={"displayModeBar": False},
            )

        with c2:
            st.markdown(f"**{portfolio_b_label}**")
            st.plotly_chart(
                make_donut(
                    snap_market_b,
                    "MarketFlag",
                    value_col,
                    color_map=market_color_map,
                ),
                use_container_width=True,
                key="market_portfolio_b",
                config={"displayModeBar": False},
            )


# ① Advertiser Portfolio Treemap
with render_card("Advertiser Portfolio - Composition"):

    if portfolio_compare_type == "なし":
        if "MarketFlag" in df_portfolio_a.columns:
            snap_adv = portfolio_snapshot_multi(
                df_portfolio_a,
                ["MarketFlag", "AdvertiserName"],
                value_col=value_col,
                top_n=30,
            )
            treemap_path = ["MarketFlag", "AdvertiserName"]
        else:
            snap_adv = portfolio_snapshot(
                df_portfolio_a,
                "AdvertiserName",
                top_n=30,
                value_col=value_col,
            )
            treemap_path = "AdvertiserName"

        st.plotly_chart(
            make_treemap(snap_adv, treemap_path, value_col),
            use_container_width=True,
            key="advertiser_treemap_composition",
        )

    else:
        c1, c2 = st.columns(2)

        with c1:
            st.markdown(f"**{portfolio_a_label}**")

            if "MarketFlag" in df_portfolio_a.columns:
                snap_adv_a = portfolio_snapshot_multi(
                    df_portfolio_a,
                    ["MarketFlag", "AdvertiserName"],
                    value_col=value_col,
                    top_n=30,
                )
                treemap_path_a = ["MarketFlag", "AdvertiserName"]
            else:
                snap_adv_a = portfolio_snapshot(
                    df_portfolio_a,
                    "AdvertiserName",
                    top_n=30,
                    value_col=value_col,
                )
                treemap_path_a = "AdvertiserName"

            st.plotly_chart(
                make_treemap(snap_adv_a, treemap_path_a, value_col),
                use_container_width=True,
                key="advertiser_treemap_composition_a",
            )

        with c2:
            st.markdown(f"**{portfolio_b_label}**")

            if "MarketFlag" in df_portfolio_b.columns:
                snap_adv_b = portfolio_snapshot_multi(
                    df_portfolio_b,
                    ["MarketFlag", "AdvertiserName"],
                    value_col=value_col,
                    top_n=30,
                )
                treemap_path_b = ["MarketFlag", "AdvertiserName"]
            else:
                snap_adv_b = portfolio_snapshot(
                    df_portfolio_b,
                    "AdvertiserName",
                    top_n=30,
                    value_col=value_col,
                )
                treemap_path_b = "AdvertiserName"

            st.plotly_chart(
                make_treemap(snap_adv_b, treemap_path_b, value_col),
                use_container_width=True,
                key="advertiser_treemap_composition_b",
            )

# ② Top Advertiser Bar
with render_card("Top Advertiser"):

    if portfolio_compare_type == "なし":
        st.caption("Advertiser名をクリックすると、下部に詳細が表示されます。")

        top_adv = portfolio_snapshot(
            df_portfolio_a,
            "AdvertiserName",
            top_n=20,
            value_col=value_col,
        )

        fig_adv_bar = make_clickable_advertiser_bar(
            top_adv,
            "AdvertiserName",
            value_col,
        )

        selected = st.plotly_chart(
            fig_adv_bar,
            use_container_width=True,
            key="advertiser_bar_select",
            on_select="rerun",
            selection_mode="points",
        )

        selected_advertiser = None

        try:
            points = selected.get("selection", {}).get("points", [])
            if points:
                selected_advertiser = (
                    points[0].get("customdata", [None])[0]
                    or points[0].get("y")
                    or points[0].get("label")
                )
        except Exception:
            selected_advertiser = None

    else:
        selected_advertiser = None

        c1, c2 = st.columns(2)

        with c1:
            st.markdown(f"**{portfolio_a_label}**")
            top_adv_a = portfolio_snapshot(
                df_portfolio_a,
                "AdvertiserName",
                top_n=20,
                value_col=value_col,
            )

            st.plotly_chart(
                make_clickable_advertiser_bar(
                    top_adv_a,
                    "AdvertiserName",
                    value_col,
                ),
                use_container_width=True,
                key="advertiser_bar_select_a",
                config={"displayModeBar": False},
            )

        with c2:
            st.markdown(f"**{portfolio_b_label}**")
            top_adv_b = portfolio_snapshot(
                df_portfolio_b,
                "AdvertiserName",
                top_n=20,
                value_col=value_col,
            )

            st.plotly_chart(
                make_clickable_advertiser_bar(
                    top_adv_b,
                    "AdvertiserName",
                    value_col,
                ),
                use_container_width=True,
                key="advertiser_bar_select_b",
            )


# ③ Advertiser detail appears only when bar is selected
if selected_advertiser:
    df_adv_detail = df_portfolio_a[
        df_portfolio_a["AdvertiserName"] == selected_advertiser
    ].copy()

    if not df_adv_detail.empty:
        with render_card(f"Advertiser Detail｜{selected_advertiser}"):

            st.caption(
                "Top Advertiserで選択したAdvertiserの月次推移、Channel構成、Media構成を表示します。"
            )

            st.info(f"Selected Scope：{portfolio_a_label}")

            # -------------------------
            # KPI Summary
            # -------------------------
            total_cost = float(df_adv_detail[value_col].sum()) if value_col in df_adv_detail.columns else 0
            impressions = float(df_adv_detail["ImpressionCount"].sum()) if "ImpressionCount" in df_adv_detail.columns else 0
            clicks = float(df_adv_detail["ClickCount"].sum()) if "ClickCount" in df_adv_detail.columns else 0
            conversions = float(df_adv_detail["CustomCPAConversions"].sum()) if "CustomCPAConversions" in df_adv_detail.columns else 0

            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Partner Cost", fmt_money_display(total_cost))
            k2.metric("Impressions", fmt_int_display(impressions))
            k3.metric("Clicks", fmt_int_display(clicks))
            k4.metric("Conversions", fmt_int_display(conversions))

            st.divider()

            # -------------------------
            # Monthly Trend
            # -------------------------
            st.subheader("Monthly Trend")

            trend_adv = (
                df_adv_detail
                .groupby("YearMonth", as_index=False)[value_col]
                .sum()
                .sort_values("YearMonth")
            )

            st.plotly_chart(
                make_monthly_progress_chart(trend_adv, value_col=value_col),
                use_container_width=True,
                key=f"adv_monthly_{selected_advertiser}",
            )

            st.divider()

            # -------------------------
            # Channel / Media Portfolio
            # -------------------------
            c1, c2 = st.columns(2)

            with c1:
                st.subheader("Channel Portfolio")
                channel_mix = portfolio_snapshot(
                    df_adv_detail,
                    "Channel",
                    top_n=10,
                    value_col=value_col,
                )

                st.plotly_chart(
                    make_donut(channel_mix, "Channel", value_col),
                    use_container_width=True,
                    key=f"adv_channel_{selected_advertiser}",
                    config={"displayModeBar": False},
                )

            with c2:
                st.subheader("Media Portfolio")
                media_mix = portfolio_snapshot(
                    df_adv_detail,
                    "Media",
                    top_n=10,
                    value_col=value_col,
                )

                st.plotly_chart(
                    make_donut(media_mix, "Media", value_col),
                    use_container_width=True,
                    key=f"adv_media_{selected_advertiser}",
                    config={"displayModeBar": False},
                )

# ④ Channel Portfolio
with render_card("Channel Portfolio"):

    if portfolio_compare_type == "なし":
        snap_channel = portfolio_snapshot(
            df_portfolio_a,
            "Channel",
            top_n=20,
            value_col=value_col,
        )

        st.plotly_chart(
            make_donut(snap_channel, "Channel", value_col),
            use_container_width=True,
            key="channel_portfolio",
        )

    else:
        c1, c2 = st.columns(2)

        snap_channel_a = portfolio_snapshot(
            df_portfolio_a,
            "Channel",
            top_n=20,
            value_col=value_col,
        )

        snap_channel_b = portfolio_snapshot(
            df_portfolio_b,
            "Channel",
            top_n=20,
            value_col=value_col,
        )

        channel_color_map = make_comparison_color_map(
            snap_channel_a,
            snap_channel_b,
            "Channel",
            value_col,
        )

        with c1:
            st.markdown(f"**{portfolio_a_label}**")

            st.plotly_chart(
                make_donut(
                    snap_channel_a,
                    "Channel",
                    value_col,
                    color_map=channel_color_map,
                ),
                use_container_width=True,
                key="channel_portfolio_a",
            )

        with c2:
            st.markdown(f"**{portfolio_b_label}**")

            st.plotly_chart(
                make_donut(
                    snap_channel_b,
                    "Channel",
                    value_col,
                    color_map=channel_color_map,
                ),
                use_container_width=True,
                key="channel_portfolio_b",
            )

# ⑤ Media Portfolio
with render_card("Media Portfolio"):

    if portfolio_compare_type == "なし":
        snap_media = portfolio_snapshot(
            df_portfolio_a,
            "Media",
            top_n=20,
            value_col=value_col,
        )

        st.plotly_chart(
            make_donut(snap_media, "Media", value_col),
            use_container_width=True,
            key="media_portfolio",
        )

    else:
        c1, c2 = st.columns(2)

        snap_media_a = portfolio_snapshot(
            df_portfolio_a,
            "Media",
            top_n=20,
            value_col=value_col,
        )

        snap_media_b = portfolio_snapshot(
            df_portfolio_b,
            "Media",
            top_n=20,
            value_col=value_col,
        )

        media_color_map = make_comparison_color_map(
            snap_media_a,
            snap_media_b,
            "Media",
            value_col,
        )

        with c1:
            st.markdown(f"**{portfolio_a_label}**")

            st.plotly_chart(
                make_donut(
                    snap_media_a,
                    "Media",
                    value_col,
                    color_map=media_color_map,
                ),
                use_container_width=True,
                key="media_portfolio_a",
            )

        with c2:
            st.markdown(f"**{portfolio_b_label}**")

            st.plotly_chart(
                make_donut(
                    snap_media_b,
                    "Media",
                    value_col,
                    color_map=media_color_map,
                ),
                use_container_width=True,
                key="media_portfolio_b",
            )

# ⑥ Timeline
with render_card("Portfolio Timeline"):

    timeline_dim = st.selectbox(
        "Breakdown",
        ["AdvertiserName", "Channel", "Media"],
        index=1,
        key="portfolio_timeline_dim",
    )

    period_grain = st.radio(
        "Grain",
        ["Month", "Quarter"],
        horizontal=True,
        key="portfolio_timeline_grain",
    )

    if portfolio_compare_type == "なし":
        timeline_df = portfolio_timeline(
            df_portfolio_a,
            timeline_dim,
            period_grain,
            value_col=value_col,
        )

        st.plotly_chart(
            make_stacked_bar(
                timeline_df,
                period_col="Period",
                category_col=timeline_dim,
                value_col=value_col,
            ),
            use_container_width=True,
            key="portfolio_timeline",
        )

    else:
        c1, c2 = st.columns(2)

        timeline_df_a = portfolio_timeline(
            df_portfolio_a,
            timeline_dim,
            period_grain,
            value_col=value_col,
        )

        timeline_df_b = portfolio_timeline(
            df_portfolio_b,
            timeline_dim,
            period_grain,
            value_col=value_col,
        )

        timeline_color_map = make_comparison_color_map(
            timeline_df_a,
            timeline_df_b,
            timeline_dim,
            value_col,
        )

        with c1:
            st.markdown(f"**{portfolio_a_label}**")

            st.plotly_chart(
                make_stacked_bar(
                    timeline_df_a,
                    period_col="Period",
                    category_col=timeline_dim,
                    value_col=value_col,
                    color_map=timeline_color_map,
                ),
                use_container_width=True,
                key="portfolio_timeline_a",
            )

        with c2:
            st.markdown(f"**{portfolio_b_label}**")

            st.plotly_chart(
                make_stacked_bar(
                    timeline_df_b,
                    period_col="Period",
                    category_col=timeline_dim,
                    value_col=value_col,
                    color_map=timeline_color_map,
                ),
                use_container_width=True,
                key="portfolio_timeline_b",
            )


# =========================
# 4. Cross view
# =========================
render_section_title("4. Channel × Media")

cross_df = (
    df_current
    .groupby(["Channel", "Media"], dropna=False)[value_col]
    .sum()
    .reset_index()
)

with render_card(f"Channel × Media Composition｜{current_period_label}"):
    st.plotly_chart(
        make_treemap(cross_df, ["Channel", "Media"], value_col),
        use_container_width=True,
    )

# =========================
# 5. Export
# =========================
render_section_title("5. データエクスポート")

with render_card("Excel Export"):
    st.caption(
        "Sidebarで指定したPod・期間フィルタに基づき、集計済みデータをExcelで出力します。"
    )

    export_df = build_export_df(df_current)

    st.write(f"Export rows: {len(export_df):,}")

    file_pod = selected_pod.replace(" ", "_") if selected_pod else "All"
    file_start = start_month.strftime("%Y%m")
    file_end = end_month.strftime("%Y%m")

    excel_bytes = to_excel_bytes(export_df)

    st.download_button(
        label="Excelをダウンロード",
        data=excel_bytes,
        file_name=f"dashboard_export_{file_pod}_{file_start}_{file_end}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

    st.caption("Preview: first 100 rows")
    st.dataframe(export_df.head(100), use_container_width=True, hide_index=True)