import calendar
from datetime import date
import pandas as pd
from pandas.tseries.offsets import DateOffset


def get_default_period(df: pd.DataFrame):
    if df.empty:
        today = pd.Timestamp.today().replace(day=1)
        return today, today

    current_year = 2026
    start = pd.Timestamp(current_year, 1, 1)
    end = df["YearMonth"].max()
    return start, end


def apply_period_filter(df: pd.DataFrame, start_month, end_month) -> pd.DataFrame:
    start_month = pd.Timestamp(start_month).replace(day=1)
    end_month = pd.Timestamp(end_month).replace(day=1)
    return df[(df["YearMonth"] >= start_month) & (df["YearMonth"] <= end_month)].copy()


def get_comparison_period(start_month, end_month, mode, custom_start=None, custom_end=None):
    start = pd.Timestamp(start_month).replace(day=1)
    end = pd.Timestamp(end_month).replace(day=1)
    months = (end.year - start.year) * 12 + (end.month - start.month) + 1

    if mode == "前の同じ期間":
        comp_end = start - DateOffset(months=1)
        comp_start = comp_end - DateOffset(months=months - 1)
        label = "Previous Same Length"
    elif mode == "前年同時期":
        comp_start = start - DateOffset(years=1)
        comp_end = end - DateOffset(years=1)
        label = "YoY Same Period"
    elif mode == "前四半期同時期":
        comp_start = start - DateOffset(months=3)
        comp_end = end - DateOffset(months=3)
        label = "Previous Quarter Same Period"
    elif mode == "任意指定" and custom_start is not None and custom_end is not None:
        comp_start = pd.Timestamp(custom_start).replace(day=1)
        comp_end = pd.Timestamp(custom_end).replace(day=1)
        label = "Custom Comparison"
    else:
        comp_start = None
        comp_end = None
        label = None

    return comp_start, comp_end, label


def monthly_sales_progress(df: pd.DataFrame, currency="JPY") -> pd.DataFrame:
    cost_col = get_cost_col(currency)

    if df.empty or cost_col not in df.columns:
        return pd.DataFrame(columns=["YearMonth", cost_col])

    return (
        df.groupby("YearMonth", as_index=False)[cost_col]
        .sum()
        .sort_values("YearMonth")
    )


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
    return sum(calendar.monthrange(d.year, m)[1] for m in range(start_month, start_month + 3))


def format_money(value, currency):
    value = 0 if pd.isna(value) else float(value)
    if currency == "JPY":
        return f"¥{value:,.0f}"
    return f"${value:,.0f}"


def format_pct(value):
    if value is None or pd.isna(value):
        return "—"
    return f"{value * 100:.1f}%"

def format_signed_pct(value):
    if value is None or pd.isna(value):
        return "—"
    return f"{value * 100:+.1f}%"


def days_in_year(d: date):
    return 366 if calendar.isleap(d.year) else 365


def days_elapsed_in_year(d: date):
    return d.timetuple().tm_yday


def elapsed_rate_for_period(latest_date: date, period: str):
    if period == "MTD":
        return latest_date.day / days_in_month(latest_date)

    if period == "QTD":
        return days_elapsed_in_quarter(latest_date) / days_in_quarter(latest_date)

    if period == "YTD":
        return days_elapsed_in_year(latest_date) / days_in_year(latest_date)

    return 1.0


def previous_period_mask(df: pd.DataFrame, latest_date: date, period: str):
    """
    MTD -> previous month full total
    QTD -> previous quarter full total
    YTD -> previous year full total
    """
    latest_ts = pd.Timestamp(latest_date)

    if period == "MTD":
        prev_month = latest_ts - pd.DateOffset(months=1)
        return (
            (df["Year"] == prev_month.year) &
            (df["Month"] == prev_month.month)
        )

    if period == "QTD":
        current_q = latest_ts.to_period("Q")
        prev_q = current_q - 1
        prev_q_start = prev_q.start_time
        prev_q_end = prev_q.end_time

        return (
            (df["YearMonth"] >= prev_q_start) &
            (df["YearMonth"] <= prev_q_end)
        )

    if period == "YTD":
        return df["Year"] == latest_date.year - 1

    return pd.Series(False, index=df.index)


def previous_period_label(period: str):
    if period == "MTD":
        return "Prev Month"
    if period == "QTD":
        return "Prev Q"
    if period == "YTD":
        return "Prev Year"
    return "Prev Period"


def calc_previous_period_progress(
    df: pd.DataFrame,
    latest_date: date,
    period: str,
    cost_col: str,
    currency: str = "USD",
    actual: float | None = None,
):
    """
    前期間売上に対する現在期間の進捗を計算する。

    MTD:
      Actual = current month to date
      Previous = previous month total
      Pace Target = previous month total * current month elapsed rate

    QTD:
      Actual = current quarter to date
      Previous = previous quarter total
      Pace Target = previous quarter total * current quarter elapsed rate

    YTD:
      Actual = current year to date
      Previous = previous year total
      Pace Target = previous year total * current year elapsed rate
    """
    if df.empty or cost_col not in df.columns:
        return {
            "prev_period_label": previous_period_label(period),
            "elapsed_rate": 0,
            "actual": 0,
            "prev_period_total": 0,
            "prev_period_pace_target": 0,
            "progress_vs_prev_period_pace": None,
            "projected_end": None,
            "projected_vs_prev_period": None,
            "prev_period_total_fmt": format_money(0, currency),
            "prev_period_pace_target_fmt": format_money(0, currency),
            "progress_vs_prev_period_pace_fmt": "—",
            "projected_end_fmt": "—",
            "projected_vs_prev_period_fmt": "—",
        }

    elapsed_rate = elapsed_rate_for_period(latest_date, period)

    if actual is None:
        months = actual_months_for_period(latest_date, period)
        actual = df[
            (df["Year"] == latest_date.year) &
            (df["Month"].isin(months))
        ][cost_col].sum()

    prev_mask = previous_period_mask(df, latest_date, period)
    prev_period_total = df.loc[prev_mask, cost_col].sum()

    prev_period_pace_target = prev_period_total * elapsed_rate

    progress_vs_prev_period_pace = (
        actual / prev_period_pace_target
        if prev_period_pace_target > 0
        else None
    )

    projected_end = (
        actual / elapsed_rate
        if elapsed_rate > 0
        else None
    )

    projected_vs_prev_period = (
        projected_end / prev_period_total - 1
        if projected_end is not None and prev_period_total > 0
        else None
    )

    return {
        "prev_period_label": previous_period_label(period),
        "elapsed_rate": elapsed_rate,
        "actual": actual,
        "prev_period_total": prev_period_total,
        "prev_period_pace_target": prev_period_pace_target,
        "progress_vs_prev_period_pace": progress_vs_prev_period_pace,
        "projected_end": projected_end,
        "projected_vs_prev_period": projected_vs_prev_period,
        "prev_period_total_fmt": format_money(prev_period_total, currency),
        "prev_period_pace_target_fmt": format_money(prev_period_pace_target, currency),
        "progress_vs_prev_period_pace_fmt": format_pct(progress_vs_prev_period_pace),
        "projected_end_fmt": format_money(projected_end, currency) if projected_end is not None else "—",
        "projected_vs_prev_period_fmt": format_signed_pct(projected_vs_prev_period),
    }

def get_latest_date(df: pd.DataFrame, metadata: dict) -> date:
    if metadata.get("latest_jst_date"):
        return pd.to_datetime(metadata["latest_jst_date"]).date()

    if "YearMonth" in df.columns and not df.empty:
        ym = df["YearMonth"].max()
        # 月次粒度だけの場合は、その月の末日を仮置き
        return date(ym.year, ym.month, calendar.monthrange(ym.year, ym.month)[1])

    return date.today()


def get_cost_col(currency):
    return "PartnerCostInAdvertiserCurrency" if currency == "JPY" else "PartnerCostInUSD"


def prepare_budget(df_budget: pd.DataFrame, currency: str) -> tuple[pd.DataFrame, str]:
    if df_budget.empty:
        return df_budget, ""

    budget_col = get_cost_col(currency)

    if budget_col not in df_budget.columns:
        return df_budget, ""

    return df_budget, budget_col


def period_months(latest_date: date, period: str):
    if period == "MTD":
        return [latest_date.month]
    if period == "QTD":
        q = (latest_date.month - 1) // 3
        return [q * 3 + 1, q * 3 + 2, q * 3 + 3]
    return list(range(1, latest_date.month + 1))


def calc_yoy(df: pd.DataFrame, latest_date: date, period: str, cost_col: str):
    months = period_months(latest_date, period)

    cur = df[(df["Year"] == latest_date.year) & (df["Month"].isin(months))]
    prev = df[(df["Year"] == latest_date.year - 1) & (df["Month"].isin(months))]

    cur_val = cur[cost_col].sum() if cost_col in cur.columns else 0
    prev_val = prev[cost_col].sum() if cost_col in prev.columns else 0

    if prev_val <= 0:
        return None

    return cur_val / prev_val - 1


def actual_months_for_period(latest_date: date, period: str):
    """
    Actual集計用の月リスト。
    実績は最新月までしか存在しない前提。
    """
    if period == "MTD":
        return [latest_date.month]

    if period == "QTD":
        q = (latest_date.month - 1) // 3
        start_month = q * 3 + 1
        return list(range(start_month, latest_date.month + 1))

    if period == "YTD":
        return list(range(1, latest_date.month + 1))

    return [latest_date.month]


def budget_months_for_period(latest_date: date, period: str):
    """
    Budget集計用の月リスト。
    MTD = 当月Budget
    QTD = 四半期Budget
    YTD = 年間Budget
    """
    if period == "MTD":
        return [latest_date.month]

    if period == "QTD":
        q = (latest_date.month - 1) // 3
        start_month = q * 3 + 1
        return list(range(start_month, start_month + 3))

    if period == "YTD":
        return list(range(1, 13))

    return [latest_date.month]


def completed_months_for_pace(latest_date: date, period: str):
    """
    Pace Target計算で、すでに完了している月。
    当月は日割りするので含めない。
    """
    if period == "MTD":
        return []

    if period == "QTD":
        q = (latest_date.month - 1) // 3
        start_month = q * 3 + 1
        return list(range(start_month, latest_date.month))

    if period == "YTD":
        return list(range(1, latest_date.month))

    return []


def calc_period_budget_pace(
    df_budget: pd.DataFrame,
    latest_date: date,
    period: str,
    budget_col: str,
):
    """
    月別BudgetベースのPace Target。

    MTD:
      current month budget * elapsed days / days in month

    QTD:
      completed months budget
      + current month budget * elapsed days / days in month

    YTD:
      completed months budget
      + current month budget * elapsed days / days in month
    """
    if df_budget.empty or budget_col not in df_budget.columns:
        return 0

    year = latest_date.year
    current_month = latest_date.month

    completed_months = completed_months_for_pace(latest_date, period)

    completed_budget = df_budget[
        (df_budget["Year"] == year) &
        (df_budget["Month"].isin(completed_months))
    ][budget_col].sum()

    current_month_budget = df_budget[
        (df_budget["Year"] == year) &
        (df_budget["Month"] == current_month)
    ][budget_col].sum()

    current_month_pace = (
        current_month_budget
        * latest_date.day
        / days_in_month(latest_date)
    )

    return completed_budget + current_month_pace


def calc_pacing_summary(df: pd.DataFrame, df_budget: pd.DataFrame, metadata: dict, currency="USD"):
    latest_date = get_latest_date(df, metadata)
    cost_col = get_cost_col(currency)

    if cost_col not in df.columns:
        return {
            "has_budget": False,
            "latest_date": latest_date,
            "periods": {},
        }

    df_budget, budget_col = prepare_budget(df_budget, currency)

    if df_budget.empty or not budget_col:
        return {
            "has_budget": False,
            "latest_date": latest_date,
            "periods": {},
        }

    periods = {}

    for label in ["MTD", "QTD", "YTD"]:
        actual_months = actual_months_for_period(latest_date, label)
        budget_months = budget_months_for_period(latest_date, label)

        actual = df[
            (df["Year"] == latest_date.year) &
            (df["Month"].isin(actual_months))
        ][cost_col].sum()

        budget = df_budget[
            (df_budget["Year"] == latest_date.year) &
            (df_budget["Month"].isin(budget_months))
        ][budget_col].sum()

        pace = calc_period_budget_pace(
            df_budget=df_budget,
            latest_date=latest_date,
            period=label,
            budget_col=budget_col,
        )

        yoy = calc_yoy(df, latest_date, label, cost_col)

        achievement_to_pace = actual / pace if pace > 0 else 0
        budget_achievement = actual / budget if budget > 0 else 0

        prev_period = calc_previous_period_progress(
            df=df,
            latest_date=latest_date,
            period=label,
            cost_col=cost_col,
            currency=currency,
            actual=actual,
        )

        periods[label] = {
            "actual": actual,
            "budget": budget,
            "pace": pace,
            "yoy": yoy,
            "achievement_to_pace": achievement_to_pace,
            "budget_achievement": budget_achievement,

            "actual_fmt": format_money(actual, currency),
            "budget_fmt": format_money(budget, currency),
            "pace_fmt": format_money(pace, currency),
            "yoy_fmt": format_pct(yoy),
            "budget_achievement_fmt": format_pct(budget_achievement),

            # Previous period comparison
            "prev_period_label": prev_period["prev_period_label"],
            "elapsed_rate": prev_period["elapsed_rate"],
            "prev_period_total": prev_period["prev_period_total"],
            "prev_period_pace_target": prev_period["prev_period_pace_target"],
            "progress_vs_prev_period_pace": prev_period["progress_vs_prev_period_pace"],
            "projected_end": prev_period["projected_end"],
            "projected_vs_prev_period": prev_period["projected_vs_prev_period"],

            "prev_period_total_fmt": prev_period["prev_period_total_fmt"],
            "prev_period_pace_target_fmt": prev_period["prev_period_pace_target_fmt"],
            "progress_vs_prev_period_pace_fmt": prev_period["progress_vs_prev_period_pace_fmt"],
            "projected_end_fmt": prev_period["projected_end_fmt"],
            "projected_vs_prev_period_fmt": prev_period["projected_vs_prev_period_fmt"],
        }

    return {
        "has_budget": True,
        "latest_date": latest_date,
        "periods": periods,
    }


def monthly_actual_budget(df: pd.DataFrame, df_budget: pd.DataFrame, currency="USD") -> pd.DataFrame:
    cost_col = get_cost_col(currency)
    if cost_col not in df.columns:
        return pd.DataFrame(columns=["Year", "Month", "Actual", "Budget", "YearMonth", "Achievement"])

    df_budget, budget_col = prepare_budget(df_budget, currency)

    act = (
        df.groupby(["Year", "Month"], as_index=False)
        .agg(Actual=(cost_col, "sum"))
    )

    if df_budget.empty or not budget_col:
        act["Budget"] = 0
    else:
        bud = (
            df_budget.groupby(["Year", "Month"], as_index=False)
            .agg(Budget=(budget_col, "sum"))
        )
        act = act.merge(bud, on=["Year", "Month"], how="left")

    act["Budget"] = act["Budget"].fillna(0)
    act["YearMonth"] = pd.to_datetime(
        act["Year"].astype(str) + "-" + act["Month"].astype(str).str.zfill(2) + "-01"
    )
    act["Achievement"] = act["Actual"] / act["Budget"].replace({0: pd.NA})

    return act.sort_values("YearMonth").tail(13)


def get_advertiser_lifecycle_table(
    df: pd.DataFrame,
    metadata: dict | None = None,
    cost_col: str = "PartnerCostInAdvertiserCurrency",
) -> pd.DataFrame:
    """
    Advertiser lifecycle classification.

    Status definition:
      New:
        current_q_spend > 0 and lifetime_prior_spend == 0

      Existing:
        current_q_spend > 0 and lifetime_prior_spend > 0 and trailing_4q_spend > 0

      Reactivated:
        current_q_spend > 0 and lifetime_prior_spend > 0 and trailing_4q_spend == 0

      Churned:
        current_q_spend == 0 and trailing_4q_spend > 0 and current quarter is completed

      At Risk:
        current_q_spend == 0 and trailing_4q_spend > 0 and current quarter is not completed

      Dormant:
        current_q_spend == 0 and trailing_4q_spend == 0 and lifetime_prior_spend > 0

      Never Active:
        current_q_spend == 0 and trailing_4q_spend == 0 and lifetime_prior_spend == 0
    """
    if df.empty:
        return pd.DataFrame()

    tmp = df.copy()

    # latest date
    if metadata and metadata.get("latest_jst_date"):
        latest_date = pd.to_datetime(metadata["latest_jst_date"]).date()
        latest_month = pd.Timestamp(latest_date.year, latest_date.month, 1)
    else:
        latest_month = tmp["YearMonth"].max()
        latest_date = latest_month.date()

    current_q = latest_month.to_period("Q")
    current_q_start = current_q.start_time
    current_q_end = current_q.end_time

    # current quarter completed?
    # metadataのlatest_jst_dateが四半期末以上ならcompleted扱い
    is_completed_quarter = pd.Timestamp(latest_date) >= current_q_end.normalize()

    # trailing 4 quarters = current quarterより前の4四半期
    trailing_start_q = current_q - 4
    trailing_start = trailing_start_q.start_time
    trailing_end = current_q_start - pd.offsets.Day(1)

    # lifetime prior = current quarter以前すべて
    lifetime_prior_end = current_q_start - pd.offsets.Day(1)

    # monthly pivot用
    monthly = (
        tmp.groupby(["AdvertiserName", "YearMonth"], as_index=False)[cost_col]
        .sum()
    )

    advertisers = pd.DataFrame({
        "AdvertiserName": sorted(tmp["AdvertiserName"].dropna().unique().tolist())
    })

    current_q_spend = (
        monthly[
            (monthly["YearMonth"] >= current_q_start) &
            (monthly["YearMonth"] <= current_q_end)
        ]
        .groupby("AdvertiserName", as_index=False)[cost_col]
        .sum()
        .rename(columns={cost_col: "CurrentQuarterCost"})
    )

    trailing_4q_spend = (
        monthly[
            (monthly["YearMonth"] >= trailing_start) &
            (monthly["YearMonth"] <= trailing_end)
        ]
        .groupby("AdvertiserName", as_index=False)[cost_col]
        .sum()
        .rename(columns={cost_col: "Trailing4QCost"})
    )

    lifetime_prior_spend = (
        monthly[
            monthly["YearMonth"] <= lifetime_prior_end
        ]
        .groupby("AdvertiserName", as_index=False)[cost_col]
        .sum()
        .rename(columns={cost_col: "LifetimePriorCost"})
    )

    out = (
        advertisers
        .merge(current_q_spend, on="AdvertiserName", how="left")
        .merge(trailing_4q_spend, on="AdvertiserName", how="left")
        .merge(lifetime_prior_spend, on="AdvertiserName", how="left")
    )

    for col in ["CurrentQuarterCost", "Trailing4QCost", "LifetimePriorCost"]:
        out[col] = out[col].fillna(0)

    def classify(row):
        current_q_spend = row["CurrentQuarterCost"]
        trailing_4q_spend = row["Trailing4QCost"]
        lifetime_prior_spend = row["LifetimePriorCost"]

        if current_q_spend > 0:
            if lifetime_prior_spend == 0:
                return "New"
            elif trailing_4q_spend > 0:
                return "Existing"
            else:
                return "Reactivated"
        else:
            if trailing_4q_spend > 0:
                if is_completed_quarter:
                    return "Churned"
                else:
                    return "At Risk"
            elif lifetime_prior_spend > 0:
                return "Dormant"
            else:
                return "Never Active"

    out["AdvertiserStatus"] = out.apply(classify, axis=1)

    out["CurrentQuarter"] = str(current_q)
    out["Trailing4QPeriod"] = (
        f"{trailing_start.strftime('%Y-%m')} - {trailing_end.strftime('%Y-%m')}"
    )
    out["IsCompletedQuarter"] = is_completed_quarter

    status_order = {
        "Existing": 1,
        "New": 2,
        "Reactivated": 3,
        "At Risk": 4,
        "Churned": 5,
        "Dormant": 6,
        "Never Active": 7,
    }

    out["StatusSort"] = out["AdvertiserStatus"].map(status_order).fillna(99)

    return (
        out.sort_values(
            ["StatusSort", "CurrentQuarterCost", "Trailing4QCost"],
            ascending=[True, False, False],
        )
        .drop(columns=["StatusSort"])
        .reset_index(drop=True)
    )


def portfolio_snapshot(
    df: pd.DataFrame,
    dimension,
    top_n=20,
    value_col="PartnerCostInAdvertiserCurrency",
) -> pd.DataFrame:
    if df.empty or dimension not in df.columns or value_col not in df.columns:
        return pd.DataFrame(columns=[dimension, value_col, "IsOthers"])

    out = (
        df.groupby(dimension, dropna=False, as_index=False)[value_col]
        .sum()
        .sort_values(value_col, ascending=False)
    )

    out[dimension] = out[dimension].astype(str)

    if len(out) > top_n:
        top = out.head(top_n).copy()
        other = pd.DataFrame({
            dimension: ["Others"],
            value_col: [out.iloc[top_n:][value_col].sum()],
        })
        out = pd.concat([top, other], ignore_index=True)

    out["IsOthers"] = out[dimension].astype(str).eq("Others")

    # Othersは常に最後。それ以外はvalue降順。
    out = (
        out
        .sort_values(["IsOthers", value_col], ascending=[True, False])
        .reset_index(drop=True)
    )

    return out


def portfolio_timeline(df: pd.DataFrame, dimension, grain="Month", top_n=12, value_col="PartnerCostInAdvertiserCurrency",) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["Period", dimension, value_col])

    tmp = df.copy()

    if grain == "Quarter":
        tmp["Period"] = tmp["YearMonth"].dt.to_period("Q").astype(str)
    else:
        tmp["Period"] = tmp["YearMonth"].dt.strftime("%Y-%m")

    top_categories = (
        tmp.groupby(dimension)[value_col]
        .sum()
        .sort_values(ascending=False)
        .head(top_n)
        .index
    )

    tmp[dimension] = tmp[dimension].where(tmp[dimension].isin(top_categories), "Others")

    return (
        tmp.groupby(["Period", dimension], as_index=False)[value_col]
        .sum()
        .sort_values("Period")
    )
