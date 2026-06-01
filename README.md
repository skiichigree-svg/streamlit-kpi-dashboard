# Streamlit Dashboard v2

## File structure

```text
.
├─ app.py
├─ modules/
│  ├─ data_loader.py
│  ├─ data_processing.py
│  ├─ charts.py
│  └─ ui_components.py
├─ sql/
│  └─ monthly_dashboard_extract.sql
└─ data/
   ├─ metadata.json
   ├─ fact_dashboard.parquet
   ├─ historical/*.parquet
   └─ recent/fact_recent.parquet
```

## Expected data grain

Minimum recommended grain:

- Year
- Month
- Pod
- Office, optional
- AdvertiserId
- AdvertiserName
- Channel
- Media
- PartnerCost

## Metadata

Use `data/metadata.json` for latest data date and refresh timestamp.

Example:

```json
{
  "latest_jst_date": "2026-03-31",
  "last_updated": "2026-05-12 15:30:00"
}
```

## Why split files?

- `app.py`: screen layout and flow only
- `data_loader.py`: read parquet/csv and normalize columns
- `data_processing.py`: period filtering, churn, aggregation
- `charts.py`: Plotly chart definitions
- `ui_components.py`: CSS and reusable UI components
