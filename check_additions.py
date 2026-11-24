"""Print yearly UPI volume, % growth and ABSOLUTE additions per financial year.

Run from your repo root:  python check_additions.py
If it says a column is missing, open data_clean/upi_monthly_clean.csv, look at the
header row, and change the three names in the CONFIG block below.
"""
import pandas as pd

# ---- CONFIG: change these to match your CSV header ----
CSV = "data_clean/upi_monthly_clean.csv"
DATE_COL = "month"            # a column that holds a date like 2024-05-01 or 'May-2024'
VOLUME_COL = "volume_mn"      # transactions in millions
# --------------------------------------------------------

df = pd.read_csv(CSV)
missing = [c for c in (DATE_COL, VOLUME_COL) if c not in df.columns]
if missing:
    raise SystemExit(f"Column(s) {missing} not found. Your columns are: {list(df.columns)}")

df[DATE_COL] = pd.to_datetime(df[DATE_COL])
# Indian financial year: April to March. FY2025-26 = Apr 2025 to Mar 2026.
fy_start = df[DATE_COL].dt.year.where(df[DATE_COL].dt.month >= 4, df[DATE_COL].dt.year - 1)
df["fy"] = fy_start.astype(str) + "-" + ((fy_start + 1) % 100).astype(str).str.zfill(2)

months = df.groupby("fy")[DATE_COL].count()
yearly = df.groupby("fy")[VOLUME_COL].sum().to_frame("volume_mn")
yearly["months_in_data"] = months
yearly["volume_bn"] = (yearly["volume_mn"] / 1000).round(2)
yearly["growth_pct"] = (yearly["volume_mn"].pct_change() * 100).round(1)
yearly["added_bn"] = (yearly["volume_mn"].diff() / 1000).round(1)
print(yearly[["months_in_data", "volume_bn", "growth_pct", "added_bn"]].to_string())
print("\nIgnore any year with months_in_data < 12 (partial year).")
print("Use the 'added_bn' column for the absolute-growth finding in the README.")
