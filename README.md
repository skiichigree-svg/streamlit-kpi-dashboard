\# Streamlit KPI Dashboard



This project visualizes overall performance KPIs using a cached Parquet layer.



\## Architecture

Vertica → Parquet (Local ETL) → Streamlit Dashboard (Cloud)



\## Data Update

Data is refreshed daily on a local machine via Task Scheduler.

The dashboard reads Parquet files committed to this repository.



\## Run Locally

```bash

pip install -r requirements.txt

streamlit run app.py



