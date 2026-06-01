from contextlib import contextmanager
from pathlib import Path
import base64

import pandas as pd
import streamlit as st


FONT_DIR = Path(__file__).resolve().parents[1] / "assets" / "fonts"


def font_to_base64(path: Path) -> str:
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def inject_design_agency_style():
    noto_regular = font_to_base64(FONT_DIR / "NotoSansJP-Regular.ttf")
    noto_bold = font_to_base64(FONT_DIR / "NotoSansJP-Bold.ttf")

    st.markdown(
        f"""
        <style>
        @font-face {{
            font-family: "Noto Sans JP";
            src: url(data:font/truetype;charset=utf-8;base64,{noto_regular}) format("truetype");
            font-weight: 400;
            font-style: normal;
        }}

        @font-face {{
            font-family: "Noto Sans JP";
            src: url(data:font/truetype;charset=utf-8;base64,{noto_bold}) format("truetype");
            font-weight: 700;
            font-style: normal;
        }}

        :root {{
            --bg: #f6f7f9;
            --card-bg: #ffffff;
            --text: #1f2937;
            --muted: #667085;
            --line: #e5e7eb;
            --accent: #0068b7;
            --font-main: "Ventura", Calibri, "Noto Sans JP", sans-serif;
        }}

        html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
        [data-testid="stMarkdownContainer"], [data-testid="stMetric"], div, p, span, label, button {{
            font-family: var(--font-main) !important;
        }}

        .stApp {{
            background: var(--bg);
            color: var(--text);
        }}

        .block-container {{
            padding-top: 1.4rem;
            padding-bottom: 3rem;
            max-width: 1440px;
        }}

        [data-testid="stSidebar"] {{
            background: #ffffff;
            border-right: 1px solid var(--line);
        }}

        .da-header {{
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 24px 28px;
            margin-bottom: 18px;
        }}

        .da-title {{
            font-size: 30px;
            font-weight: 700;
            letter-spacing: -0.02em;
            margin-bottom: 4px;
        }}

        .da-subtitle {{
            font-size: 14px;
            color: var(--muted);
            margin-bottom: 12px;
        }}

        .da-meta {{
            font-size: 12px;
            color: var(--muted);
        }}

        .da-section {{
            margin-top: 26px;
            margin-bottom: 10px;
            font-size: 20px;
            font-weight: 700;
            border-left: 6px solid var(--accent);
            padding-left: 12px;
        }}

        div[data-testid="stMetric"] {{
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 14px;
            padding: 12px 14px;
        }}

        div[data-testid="stMetricLabel"] {{
            color: var(--muted);
        }}

        .da-card {{
            background: #ffffff;
            border: 1px solid var(--line);
            border-radius: 16px;
            padding: 18px;
            margin-bottom: 16px;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        }}

        .da-card-title {{
            font-size: 16px;
            font-weight: 700;
            margin-bottom: 12px;
        }}

        [data-testid="stExpander"] details summary {{
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 14px;
        }}

        [data-testid="stExpander"] details summary p {{
            margin: 0;
            line-height: 1.4;
            font-weight: 600;
        }}

        [data-testid="stExpander"] summary svg {{
            flex-shrink: 0;
            margin-right: 4px;
        }}

        [data-testid="stExpander"] details {{
            border: none;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(title, subtitle, latest_data_date=None, last_updated=None):
    latest = latest_data_date or "N/A"
    updated = last_updated or "N/A"

    st.markdown(
        f"""
        <div class="da-header">
            <div class="da-title">{title}</div>
            <div class="da-subtitle">{subtitle}</div>
            <div class="da-meta">
                最新データ日付：{latest}　|　データリフレッシュ実行日時：{updated}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_filter_panel(df):
    with st.sidebar:
        st.header("フィルタ")

        with st.form("filter_form"):
            # =========================
            # Pod filter
            # =========================
            if "Pod" in df.columns:
                pod_options = (
                    df["Pod"]
                    .dropna()
                    .astype(str)
                    .str.strip()
                    .replace("", pd.NA)
                    .dropna()
                    .unique()
                    .tolist()
                )
                pod_options = ["All"] + sorted(pod_options)
            else:
                pod_options = ["All"]

            selected_pod = st.selectbox(
                "Pod",
                pod_options,
                index=0,
            )

            # =========================
            # Period filter
            # =========================
            ym_options = sorted(df["YearMonth"].dropna().unique())
            ym_labels = [pd.Timestamp(x).strftime("%Y-%m") for x in ym_options]

            default_start_idx = 0
            for i, x in enumerate(ym_options):
                if pd.Timestamp(x).year == 2026 and pd.Timestamp(x).month == 1:
                    default_start_idx = i
                    break

            start_label = st.selectbox(
                "Start Month",
                ym_labels,
                index=default_start_idx,
            )

            end_label = st.selectbox(
                "End Month",
                ym_labels,
                index=len(ym_labels) - 1,
            )

            submitted = st.form_submit_button(
                "適用する",
                use_container_width=True,
            )

    return {
        "selected_pod": selected_pod,
        "start_month": pd.Timestamp(start_label + "-01"),
        "end_month": pd.Timestamp(end_label + "-01"),
        "submitted": submitted,
    }


def render_kpi_cards(items, currency="USD"):
    prefix = "¥" if currency == "JPY" else "$"

    cols = st.columns(len(items))
    for col, (label, value, help_text) in zip(cols, items):
        with col:
            if "Cost" in label or "売上" in label or "費用" in label:
                display_value = f"{prefix}{value:,.0f}"
            else:
                display_value = f"{value:,.0f}"

            st.metric(label, display_value, help=help_text)


def render_section_title(text):
    st.markdown(f'<div class="da-section">{text}</div>', unsafe_allow_html=True)


@contextmanager
def render_card(title):
    with st.container(border=True):
        st.markdown(
            f"""
            <div style="font-size:16px; font-weight:700; margin-bottom:12px;">
                {title}
            </div>
            """,
            unsafe_allow_html=True,
        )
        yield
