from pathlib import Path
import json
import pandas as pd
import streamlit as st

DATA_DIR = Path("data")
METADATA_PATH = DATA_DIR / "metadata.json"
BUDGET_PATH = DATA_DIR / "budget.csv"


@st.cache_data(show_spinner=False)
def load_dashboard_data() -> pd.DataFrame:
    paths = []

    historical_dir = DATA_DIR / "historical"
    if historical_dir.exists():
        paths.extend(sorted(historical_dir.glob("*.parquet")))

    recent = DATA_DIR / "recent" / "fact_recent.parquet"
    if recent.exists():
        paths.append(recent)

    single_parquet = DATA_DIR / "fact_dashboard.parquet"
    single_csv = DATA_DIR / "fact_dashboard.csv"

    dfs = []

    for p in paths:
        if p.exists():
            dfs.append(pd.read_parquet(p))

    if not dfs and single_parquet.exists():
        dfs.append(pd.read_parquet(single_parquet))

    if not dfs and single_csv.exists():
        dfs.append(pd.read_csv(single_csv))

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)
    df = normalize_columns(df)
    df = ensure_required_columns(df)
    df = finalize_types(df)

    return df


@st.cache_data(show_spinner=False)
def load_budget() -> pd.DataFrame:
    if not BUDGET_PATH.exists():
        return pd.DataFrame()

    df = pd.read_csv(BUDGET_PATH)
    df.columns = df.columns.str.replace("\ufeff", "", regex=False).str.strip()
    df = normalize_columns(df)

    if "PartnerCostInAdvertiserCurrency" not in df.columns:
        df["PartnerCostInAdvertiserCurrency"] = 0

    if "PartnerCostInUSD" not in df.columns:
        df["PartnerCostInUSD"] = 0

    for col in ["Year", "Month"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    for col in ["PartnerCostInUSD", "PartnerCostInAdvertiserCurrency"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    if "Year" in df.columns and "Month" in df.columns:
        df = df.dropna(subset=["Year", "Month"]).copy()
        df["Year"] = df["Year"].astype(int)
        df["Month"] = df["Month"].astype(int)
        df["YearMonth"] = pd.to_datetime(
            df["Year"].astype(str) + "-" + df["Month"].astype(str).str.zfill(2) + "-01",
            errors="coerce",
        )

    return df


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "year": "Year",
        "month": "Month",
        "quarter": "Quarter",
        "Advertiser Nam": "AdvertiserName",
        "Advertiser Name": "AdvertiserName",
        "CustomCPAConversion": "CustomCPAConversions",
        "UnifiedChannel_Normalized": "Channel",
    }
    return df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})


def ensure_required_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    required_defaults = {
        "Year": pd.NA,
        "Quarter": pd.NA,
        "Month": pd.NA,

        "PartnerId": "Not Specified",
        "PartnerName": "Not Specified",
        "AdvertiserId": "Not Specified",
        "AdvertiserName": "Not Specified",
        "Pod": "Not Specified",
        "MarketFlag": "Not Specified",
        "MarketType": "Not Specified",
        "Channel": "Not specified",
        "PrivateContractId": "Not Specified",
        "Media": "Not specified",

        "AdvertiserCostInAdvertiserCurrency": 0,
        "AdvertiserCostInUSD": 0,
        "PartnerCostInAdvertiserCurrency": 0,
        "PartnerCostInUSD": 0,
        "MediaCostInAdvertiserCurrency": 0,
        "MediaCostInUSD": 0,
        "DataCostInAdvertiserCurrency": 0,
        "DataCostInUSD": 0,
        "ImpressionCount": 0,
        "ClickCount": 0,
        "CustomCPAConversions": 0,
    }

    for col, default_value in required_defaults.items():
        if col not in out.columns:
            out[col] = default_value

    return out


def finalize_types(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    out["Year"] = pd.to_numeric(out["Year"], errors="coerce").astype("Int64")
    out["Month"] = pd.to_numeric(out["Month"], errors="coerce").astype("Int64")

    out = out.dropna(subset=["Year", "Month"]).copy()
    out["Year"] = out["Year"].astype(int)
    out["Month"] = out["Month"].astype(int)

    out["YearMonth"] = pd.to_datetime(
        out["Year"].astype(str) + "-" + out["Month"].astype(str).str.zfill(2) + "-01",
        errors="coerce",
    )

    text_cols = [
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

    for col in text_cols:
        if col in out.columns:
            out[col] = out[col].fillna("Not Specified").astype(str)

    numeric_cols = [
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

    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0)

    return out


@st.cache_data(show_spinner=False)
def load_metadata() -> dict:
    if METADATA_PATH.exists():
        with open(METADATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}
