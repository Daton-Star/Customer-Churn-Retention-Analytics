"""Central paths for the pipeline. Every script imports its locations from here."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]           # repo root
DATA = ROOT / "stage1_kaggle" / "data"               # Stage 1 summary tables (Kaggle notebook output)
SQL = ROOT / "sql"                                   # named DuckDB queries (Phase 2)
OUTPUTS = ROOT / "outputs"                           # result tables, one folder per phase
IMAGES = ROOT / "images"                             # charts, one folder per phase
DASHBOARD = ROOT / "dashboard"                       # HTML dashboard, Power BI kit, Excel workbook
KEY_NUMBERS = ROOT / "key_numbers" / "key_numbers.csv"
