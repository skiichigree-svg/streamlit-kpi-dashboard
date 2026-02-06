# scripts/bootstrap_historical.py

import os
import argparse
from datetime import datetime
import pandas as pd
import sys

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from scripts.utils import fetch_data_from_vertica


from scripts.utils import fetch_data_from_vertica

# =========================
# パス設定
# =========================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SQL_PATH = os.path.join(BASE_DIR, "sql", "performance.sql")
HIST_DIR = os.path.join(BASE_DIR, "data", "historical")


# =========================
# SQLロード
# =========================
def load_sql():
    with open(SQL_PATH, encoding="utf-8") as f:
        return f.read()


# =========================
# メイン処理
# =========================
def bootstrap(start_date: str, end_date: str):
    print(f"[INFO] Bootstrapping historical data")
    print(f"       Period: {start_date} ~ {end_date}")

    sql_template = load_sql()
    sql = (
        sql_template
        .replace("${StartDate}", start_date)
        .replace("${EndDate}", end_date)
    )

    df = fetch_data_from_vertica(sql)

    if df.empty:
        raise RuntimeError("historical データが空です")

    os.makedirs(HIST_DIR, exist_ok=True)

    # 年ごとに分割保存
    for year, df_y in df.groupby("year"):
        path = os.path.join(HIST_DIR, f"fact_{int(year)}.parquet")
        df_y.to_parquet(path, index=False)
        print(f"[SUCCESS] Saved: {path} ({len(df_y):,} rows)")


# =========================
# エントリーポイント
# =========================
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")

    args = parser.parse_args()
    bootstrap(args.start, args.end)
