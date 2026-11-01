import glob
import os
import pandas as pd

folder = os.path.dirname(os.path.abspath(__file__))
files = sorted(glob.glob(os.path.join(folder, "data_raw", "Product-Statistics-UPI*Monthly*.xlsx")))
print("Files found:", len(files))


def to_number(s):
    s = s.astype(str).str.replace(",", "", regex=False).str.strip()
    return pd.to_numeric(s, errors="coerce")


def to_month(s):
    s = s.astype(str).str.strip()
    out = pd.Series(pd.NaT, index=s.index)
    for fmt in ["%B-%Y", "%b-%Y", "%B-%y", "%b-%y"]:
        out = out.fillna(pd.to_datetime(s, format=fmt, errors="coerce"))
    return out


frames = []
for f in files:
    df = pd.read_excel(f).iloc[:, :4]
    df.columns = ["month_text", "banks_live", "volume_mn", "value_cr"]
    df["source_file"] = os.path.basename(f)
    frames.append(df)

data = pd.concat(frames, ignore_index=True).dropna(subset=["month_text"])
data["month"] = to_month(data["month_text"])
for c in ["banks_live", "volume_mn", "value_cr"]:
    data[c] = to_number(data[c])

num_cols = ["banks_live", "volume_mn", "value_cr"]
bad = data[data["month"].isna() | data[num_cols].isna().any(axis=1)]
print("Rows with problems:", len(bad))
if len(bad):
    print(bad[["source_file", "month_text", "banks_live", "volume_mn", "value_cr"]])

data = data.drop_duplicates(subset="month").sort_values("month").reset_index(drop=True)
data["avg_ticket_rs"] = (data["value_cr"] * 10 / data["volume_mn"]).where(data["volume_mn"] > 0).round(0)

full = pd.date_range(data["month"].min(), data["month"].max(), freq="MS")
missing = sorted(set(full) - set(data["month"]))

out = data[["month", "banks_live", "volume_mn", "value_cr", "avg_ticket_rs"]]
out.to_csv(os.path.join(folder, "data_clean", "upi_monthly_clean.csv"), index=False)

print("Rows saved:", len(out))
print("First month:", out["month"].min().date(), "| Last month:", out["month"].max().date())
print("Missing months:", [m.strftime("%Y-%m") for m in missing])
print("Months with zero volume:", int((out["volume_mn"] == 0).sum()))
print(out.tail(3).to_string(index=False))