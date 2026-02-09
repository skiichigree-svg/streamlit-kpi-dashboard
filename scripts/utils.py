import vertica_python
import pandas as pd
import os
import configparser

# このスクリプト(utils.py)があるディレクトリを取得
# これにより、どこから呼び出されてもパスの基準が狂わない
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__)) 
# プロジェクトのルートディレクトリ (scriptsの一つ上)
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

def get_config():
    """設定ファイルを読み込んでconfigオブジェクトを返す関数"""
    config = configparser.ConfigParser()
    config_path = os.path.join(PROJECT_ROOT, "config", "config.ini")
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"設定ファイルが見つかりません: {config_path}")
    config.read(config_path, encoding="utf-8")
    return config

def fetch_data_from_vertica(query):
    """
    設定ファイルを読み込み、Verticaに接続してクエリを実行し、DataFrameを返す
    """
    config = get_config()
    db_config = config["Vertica"] # セクション名はconfig.iniに合わせてください
    
    connection = None
    try:
        # connect to vertica
        conn_info = {
            'host': db_config.get('host'),
            'port': db_config.getint('port', 5433), # .getintで整数として取得
            'user': db_config.get('user'),
            'password': db_config.get('password'),
            'database': db_config.get('database')
        }
        connection = vertica_python.connect(**conn_info)

        # execute query and convert to dataframe
        # pd.read_sql_queryの方が型推論などで安定することが多い
        df = pd.read_sql_query(query, connection)

        return df
    
    finally:
        # connection closed
        if connection:
            connection.close()