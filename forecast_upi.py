import os

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from statsmodels.tsa.holtwinters import ExponentialSmoothing

folder = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(folder, "data_clean", "upi_monthly_clean.csv"), parse_dates=["month"])
s = df.set_index("month")["volume_mn"]
s = s[s.index >= "2021-04-01"].asfreq("MS")
ls = np.log(s)


def fit(series):
    model = ExponentialSmoothing(
        series, trend="add", damped_trend=True,
        seasonal="add", seasonal_periods=12,
        initialization_method="estimated",
    )
    return model.fit()


# 1) Backtest: hide the last 12 months, forecast them, measure the error
train, test = ls[:-12], ls[-12:]
pred = np.exp(fit(train).forecast(12))
actual = np.exp(test)
mape_model = float(np.mean(np.abs(pred.values - actual.values) / actual.values) * 100)
naive = np.repeat(np.exp(train.iloc[-1]), 12)
mape_naive = float(np.mean(np.abs(naive - actual.values) / actual.values) * 100)
print("Backtest (last 12 months hidden):")
print("  Model average error  : %.1f%%" % mape_model)
print("  Naive guess error    : %.1f%%" % mape_naive)

# 2) Final forecast: refit on all data, forecast 12 months with an 80% range
res = fit(ls)
point = np.exp(res.forecast(12))
sims = res.simulate(12, repetitions=1000, error="add", anchor="end", random_state=1)
low = np.exp(np.percentile(sims.values, 10, axis=1))
high = np.exp(np.percentile(sims.values, 90, axis=1))
future = pd.date_range(s.index[-1] + pd.offsets.MonthBegin(1), periods=12, freq="MS")
out = pd.DataFrame({
    "month": future.strftime("%Y-%m"),
    "forecast_volume_mn": point.values.round(0),
    "low_80": low.round(0),
    "high_80": high.round(0),
})
os.makedirs(os.path.join(folder, "outputs"), exist_ok=True)
out.to_csv(os.path.join(folder, "outputs", "forecast.csv"), index=False)

next12 = point.sum()
last12 = s.iloc[-12:].sum()
print("\nForecast Oct 2026 to Sep 2027:")
print(out.to_string(index=False))
print("\nNext 12 months total: %.1f bn vs last 12 months %.1f bn (%+.1f%%)"
      % (next12 / 1000, last12 / 1000, (next12 / last12 - 1) * 100))

# 3) Chart
plt.figure(figsize=(10, 5))
plt.plot(s.index, s.values, label="Actual", color="#1f4e79")
plt.plot(future, point.values, label="Forecast", color="#e67e22")
plt.fill_between(future, low, high, color="#e67e22", alpha=0.2, label="80% range")
plt.title("UPI monthly volume (millions) and 12-month forecast")
plt.ylabel("Volume (millions)")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(folder, "outputs", "forecast_chart.png"), dpi=150)
print("Saved outputs\\forecast.csv and outputs\\forecast_chart.png")