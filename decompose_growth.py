"""Split UPI value growth into a volume effect and an average-ticket effect, and compare
FY2026-27 outlook scenarios.

    python decompose_growth.py

Value = volume x average ticket, so ln(value growth) = ln(volume growth) + ln(ticket growth).
The share of growth from each part is its log change divided by the log change in value.
Writes outputs/growth_decomposition.csv and outputs/fy27_scenarios.csv.
"""
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(HERE, "data_clean", "upi_monthly_clean.csv")
FORECAST = os.path.join(HERE, "outputs", "forecast.csv")


def fy_label(ts):
    start = ts.year if ts.month >= 4 else ts.year - 1
    return f"FY{start}-{str(start + 1)[2:]}"


def decompose(df):
    d = df[df.volume_mn > 0].copy()
    d["fy"] = d.month.map(fy_label)
    y = d.groupby("fy").agg(vol=("volume_mn", "sum"), val=("value_cr", "sum"), n=("month", "count"))
    y = y[y.n == 12].copy()                      # full financial years only
    y["ticket"] = y.val * 10 / y.vol
    out = y.copy()
    out["value_growth_pct"] = 100 * y.val.pct_change()
    out["volume_growth_pct"] = 100 * y.vol.pct_change()
    out["ticket_change_pct"] = 100 * y.ticket.pct_change()
    lv, ln_, lt = np.log(y.val).diff(), np.log(y.vol).diff(), np.log(y.ticket).diff()
    out["volume_share_of_value_growth_pct"] = 100 * ln_ / lv
    out["ticket_share_of_value_growth_pct"] = 100 * lt / lv
    return out.dropna()


def half_year(df, year):
    m = df[(df.month >= f"{year}-04-01") & (df.month <= f"{year}-09-01")]
    return m.volume_mn.sum(), m.value_cr.sum()


def main():
    df = pd.read_csv(CSV, parse_dates=["month"])
    dec = decompose(df)
    cols = ["vol", "val", "ticket", "value_growth_pct", "volume_growth_pct", "ticket_change_pct",
            "volume_share_of_value_growth_pct", "ticket_share_of_value_growth_pct"]
    dec[cols].round(2).to_csv(os.path.join(HERE, "outputs", "growth_decomposition.csv"))
    print("Value growth split into volume and average-ticket effects (full financial years)")
    print(dec[["value_growth_pct", "volume_growth_pct", "ticket_change_pct",
               "volume_share_of_value_growth_pct"]].round(1).to_string())

    v1, c1 = half_year(df, 2026)
    v0, c0 = half_year(df, 2025)
    t1, t0 = c1 * 10 / v1, c0 * 10 / v0
    print(f"\nApr-Sep 2026 vs Apr-Sep 2025: value {100 * (c1 / c0 - 1):.1f}%, volume {100 * (v1 / v0 - 1):.1f}%, "
          f"ticket {100 * (t1 / t0 - 1):.1f}%, volume share of value growth "
          f"{100 * np.log(v1 / v0) / np.log(c1 / c0):.0f}%")

    # FY2026-27 outlook: three simple scenarios, all anchored on actual Apr-Sep 2026 volume
    fy26 = dec.loc["FY2025-26", "vol"]
    fy25 = dec.loc["FY2024-25", "vol"]
    fc = pd.read_csv(FORECAST)
    h2 = fc[fc.month <= "2027-03"].forecast_volume_mn.sum()   # Oct 2026 to Mar 2027
    rows = [
        ("Same yearly addition as FY2025-26", fy26 + (fy26 - fy25)),
        ("Same growth rate as Apr-Sep 2026 (year on year)", fy26 * (v1 / v0)),
        ("Actual Apr-Sep 2026 + model forecast Oct 2026-Mar 2027", v1 + h2),
    ]
    sc = pd.DataFrame(rows, columns=["scenario", "fy2026_27_volume_mn"])
    sc["fy2026_27_volume_bn"] = (sc.fy2026_27_volume_mn / 1000).round(1)
    sc["growth_vs_fy2025_26_pct"] = (100 * (sc.fy2026_27_volume_mn / fy26 - 1)).round(1)
    sc.round(1).to_csv(os.path.join(HERE, "outputs", "fy27_scenarios.csv"), index=False)
    print(f"\nFY2025-26 actual: {fy26 / 1000:.1f} bn")
    print(sc[["scenario", "fy2026_27_volume_bn", "growth_vs_fy2025_26_pct"]].to_string(index=False))


if __name__ == "__main__":
    main()
