import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from modules.style_config import build_extended_palette

PLOT_FONT_FAMILY = (
    "Inter, "
    "'Noto Sans JP', "
    "-apple-system, "
    "BlinkMacSystemFont, "
    "'Segoe UI', "
    "sans-serif"
)


def apply_chart_theme(fig):
    fig.update_layout(
        font=dict(
            family=PLOT_FONT_FAMILY,
            size=13,
            color="#1f2937",
        )
    )
    return fig


def _money_fmt():
    return ",.0f"


def make_monthly_progress_chart(df: pd.DataFrame, value_col="PartnerCostInAdvertiserCurrency"):
    if df is None or df.empty:
        fig = px.bar()
        fig.update_layout(
            height=360,
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        return apply_chart_theme(fig)

    plot_df = df.copy()

    # YearMonthを月次カテゴリとして表示する
    plot_df["YearMonth"] = pd.to_datetime(plot_df["YearMonth"], errors="coerce")
    plot_df = plot_df.dropna(subset=["YearMonth"])
    plot_df = plot_df.sort_values("YearMonth")

    plot_df["Period"] = plot_df["YearMonth"].dt.strftime("%Y-%m")
    plot_df[value_col] = pd.to_numeric(plot_df[value_col], errors="coerce").fillna(0)
    plot_df["_value_fmt"] = plot_df[value_col].apply(lambda x: f"{x:,.0f}")

    fig = px.bar(
        plot_df,
        x="Period",
        y=value_col,
        text="_value_fmt",
        category_orders={"Period": plot_df["Period"].tolist()},
    )

    fig.update_traces(
        marker_color="#0372E2",
        textposition="inside",
        hovertemplate=(
            "Month: %{x}<br>"
            "Partner Cost: %{y:,.0f}"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=20, b=20),
        yaxis_title=value_col,
        xaxis_title="",
        plot_bgcolor="white",
        paper_bgcolor="white",
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )

    fig.update_yaxes(tickformat=",.0f")
    fig.update_xaxes(type="category")

    return apply_chart_theme(fig)


def make_pacing_bar(rate):
    rate = 0 if rate is None or pd.isna(rate) else float(rate)
    rate_capped = min(rate, 1.2)

    if rate >= 1.0:
        color = "#1a9850"
    elif rate >= 0.8:
        color = "#2ca02c"
    else:
        color = "#f1c40f"

    fig = go.Figure()

    fig.add_bar(
        x=[rate_capped * 100],
        y=["Progress"],
        orientation="h",
        width=0.6,
        marker_color=color,
        text=[f"{rate * 100:.1f}%"],
        textposition="auto",
        hovertemplate="Pace achievement: %{x:.1f}%<extra></extra>",
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
        height=150,
        xaxis=dict(range=[0, 120], title="", ticksuffix="%"),
        yaxis=dict(showticklabels=False),
        margin=dict(l=8, r=8, t=18, b=8),
        showlegend=False,
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    return apply_chart_theme(fig)


def make_actual_budget_chart(df: pd.DataFrame, currency="USD"):
    prefix = "¥" if currency == "JPY" else "$"

    if df.empty:
        return go.Figure()

    def color_rule(rate):
        if pd.isna(rate):
            return "#bdc3c7"
        if rate >= 1.0:
            return "#1a9850"
        if rate >= 0.8:
            return "#2ca02c"
        return "#f1c40f"

    fig = go.Figure()

    fig.add_bar(
        x=df["YearMonth"],
        y=df["Actual"],
        name="Actual",
        marker_color=df["Achievement"].apply(color_rule),
        customdata=df["Achievement"],
        hovertemplate=(
            "Month: %{x|%Y-%m}<br>"
            f"Actual: {prefix}%{{y:,.0f}}<br>"
            "Achievement: %{customdata:.1%}"
            "<extra></extra>"
        ),
    )

    fig.add_scatter(
        x=df["YearMonth"],
        y=df["Budget"],
        name="Budget",
        mode="lines+markers",
        line=dict(color="#667085", dash="dash"),
        marker=dict(size=6),
        hovertemplate=(
            "Month: %{x|%Y-%m}<br>"
            f"Budget: {prefix}%{{y:,.0f}}"
            "<extra></extra>"
        ),
    )

    fig.update_layout(
        height=420,
        xaxis=dict(title=None),
        yaxis=dict(title=currency, tickprefix=prefix),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(l=20, r=20, t=30, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    return apply_chart_theme(fig)


def make_treemap(df, path, value_col):

    if df is None or df.empty:
        fig = px.treemap()
        fig.update_layout(
            height=420,
            margin=dict(l=8, r=8, t=8, b=8),
        )
        return fig

    plot_df = df.copy()

    # 表示用の丸め済み金額
    plot_df["_value_fmt"] = plot_df[value_col].apply(
        lambda x: f"{float(x):,.0f}" if pd.notna(x) else "0"
    )

    fig = px.treemap(
        plot_df,
        path=path if isinstance(path, list) else [path],
        values=value_col,
        color=value_col,
        color_continuous_scale="Blues",
    )

    fig.update_traces(
        texttemplate="<b>%{label}</b><br>%{value:,.0f}<br>%{percentEntry:.0%}",
        hovertemplate="<b>%{label}</b><br>Cost: %{value:,.0f}<br>Share: %{percentEntry:.1%}<extra></extra>",
        textfont_size=13,
        textposition="middle right",
    )

    fig.update_layout(
        height=420,
        margin=dict(l=8, r=8, t=8, b=8),
        coloraxis_colorbar=dict(
            title=value_col,
            tickformat=",.0f",
        ),
    )

    return fig



def make_comparison_color_map(df_a, df_b, category_col, value_col):
    def get_ordered_categories(input_df):
        if input_df is None or input_df.empty or category_col not in input_df.columns:
            return []

        return (
            input_df
            .groupby(category_col, dropna=False)[value_col]
            .sum()
            .sort_values(ascending=False)
            .index
            .astype(str)
            .tolist()
        )

    categories_a = get_ordered_categories(df_a)
    categories_b = get_ordered_categories(df_b)

    ordered_categories = categories_a + [
        c for c in categories_b if c not in categories_a
    ]

    palette = build_extended_palette(len(ordered_categories))

    return {
        category: palette[i]
        for i, category in enumerate(ordered_categories)
    }


def make_donut(df, label_col, value_col, color_map=None):
    if df is None or df.empty:
        fig = go.Figure()
        fig.update_layout(
            height=420,
            margin=dict(l=20, r=20, t=20, b=20),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        return apply_chart_theme(fig)

    plot_df = df.copy()
    plot_df[label_col] = plot_df[label_col].astype(str)
    plot_df[value_col] = pd.to_numeric(plot_df[value_col], errors="coerce").fillna(0)

    # 0以下は除外
    plot_df = plot_df[plot_df[value_col] > 0].copy()

    if plot_df.empty:
        fig = go.Figure()
        fig.update_layout(height=420)
        return apply_chart_theme(fig)

    # Otherは最後
    if "IsOthers" not in plot_df.columns:
        plot_df["IsOthers"] = plot_df[label_col].astype(str).eq("Others")

    plot_df = (
        plot_df
        .sort_values(["IsOthers", value_col], ascending=[True, False])
        .reset_index(drop=True)
    )

    labels = plot_df[label_col].tolist()
    values = plot_df[value_col].tolist()

    if color_map is None:
        palette = build_extended_palette(len(labels))
        colors = palette[:len(labels)]
    else:
        fallback_palette = build_extended_palette(len(labels))
        colors = [
            color_map.get(label, fallback_palette[i])
            for i, label in enumerate(labels)
        ]

    total_value = sum(values)

    text_values = []
    for label, value in zip(labels, values):
        share = value / total_value if total_value > 0 else 0
        if share >= 0.03:
            text_values.append(f"{label}<br>{share:.1%}")
        else:
            text_values.append("")

    fig = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.55,
                sort=False,
                direction="clockwise",
                rotation=0,  # 12時スタート
                marker=dict(colors=colors),
                text=text_values,
                textinfo="text",
                textposition="inside",
                insidetextorientation="auto",
                hovertemplate=(
                    "<b>%{label}</b><br>"
                    "Cost: %{value:,.0f}<br>"
                    "Share: %{percent:.1%}"
                    "<extra></extra>"
                ),
            )
        ]
    )

    fig.update_layout(
        height=420,
        margin=dict(l=20, r=20, t=20, b=20),
        plot_bgcolor="white",
        paper_bgcolor="white",
        legend=dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=11),
            traceorder="normal",
        ),
        legend_title_text=None,
        uniformtext_minsize=10,
        uniformtext_mode="hide",
    )

    return apply_chart_theme(fig)


def make_stacked_bar(df, period_col, category_col, value_col, color_map=None):

    if df is None or df.empty:
        fig = px.bar()
        fig.update_layout(
            height=420,
            margin=dict(l=8, r=8, t=8, b=40),
        )
        return fig

    plot_df = df.copy()
    plot_df[category_col] = plot_df[category_col].astype(str)

    fig = px.bar(
        plot_df,
        x=period_col,
        y=value_col,
        color=category_col,
        color_discrete_map=color_map,
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Cost: %{y:,.0f}"
            "<extra></extra>"
        )
    )

    fig.update_layout(
        height=420,
        margin=dict(l=8, r=8, t=8, b=40),
        barmode="stack",
        xaxis_title=None,
        yaxis_title="Partner Cost",
        legend_title_text=None,
    )

    fig.update_yaxes(tickformat=",.0f")

    return fig

def make_clickable_advertiser_bar(df, dimension_col, value_col):
    if df is None or df.empty:
        fig = px.bar()
        fig.update_layout(
            height=420,
            margin=dict(l=160, r=100, t=8, b=40),
            plot_bgcolor="white",
            paper_bgcolor="white",
        )
        return apply_chart_theme(fig)

    def shorten_label(x, max_len=18):
        x = str(x)
        return x if len(x) <= max_len else x[:max_len] + "…"

    plot_df = df.copy()

    if "IsOthers" not in plot_df.columns:
        plot_df["IsOthers"] = plot_df[dimension_col].astype(str).eq("Others")

    plot_df[value_col] = pd.to_numeric(plot_df[value_col], errors="coerce").fillna(0)

    plot_df = (
        plot_df
        .sort_values(["IsOthers", value_col], ascending=[True, False])
        .reset_index(drop=True)
    )

    plot_df[value_col] = pd.to_numeric(plot_df[value_col], errors="coerce").fillna(0)

    plot_df["_display_name"] = plot_df[dimension_col].apply(
        lambda x: shorten_label(x, max_len=18)
    )

    plot_df["_value_fmt"] = plot_df[value_col].apply(
        lambda x: f"{float(x):,.0f}"
    )

    max_val = float(plot_df[value_col].max()) if not plot_df.empty else 0
    x_max = max_val * 1.35 if max_val > 0 else 1

    fig = px.bar(
        plot_df,
        x=value_col,
        y="_display_name",
        orientation="h",
        custom_data=[dimension_col],
    )

    fig.update_traces(
        marker_color="#0372E2",
        cliponaxis=False,
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>"
            "Partner Cost: %{x:,.0f}"
            "<extra></extra>"
        ),
    )

    # 数字をannotationで強制表示
    for _, row in plot_df.iterrows():
        fig.add_annotation(
            x=float(row[value_col]),
            y=row["_display_name"],
            text=row["_value_fmt"],
            showarrow=False,
            xanchor="left",
            xshift=6,
            font=dict(size=11, color="#667085"),
        )

    fig.update_layout(
        height=max(420, 28 * len(plot_df) + 80),
        margin=dict(l=170, r=140, t=8, b=40),
        xaxis_title="Partner Cost",
        yaxis_title=None,
        plot_bgcolor="white",
        paper_bgcolor="white",
        showlegend=False,
        dragmode=False,
    )

    fig.update_xaxes(
        tickformat=",.0f",
        automargin=True,
        range=[0, x_max],
        showgrid=False,
        zeroline=False,
    )

    fig.update_yaxes(
        autorange="reversed",
        automargin=True,
        tickfont=dict(size=11),
    )

    return apply_chart_theme(fig)