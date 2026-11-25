"""Rolling-origin backtest, start-date sensitivity and 80%-range coverage check for the UPI forecast.

    python rolling_backtest.py                      # your exact model from forecast_upi.py (needs statsmodels)
    python rolling_backtest.py --model reference    # independent scipy re-implementation (no statsmodels)

--model statsmodels uses the same ExponentialSmoothing settings and the same simulated 80% range
(10th to 90th percentile of 1,000 simulations) as forecast_upi.py, so it tests the model you ship.
--model reference is a separate least-squares implementation of the same model family. It is a
cross-check, not a replica, so quote numbers from --model statsmodels when describing the shipped model.

What it reports (the report is also saved to outputs/rolling_backtest_<model>.txt):
  A  the README's single backtest (train from 2021-04 to 2025-09, hide the next 12 months)
  B  start-date sensitivity on that same holdout
  C  rolling origins every 3 months, error by horizon and by origin, against two baselines
  D  how often the 80% range contains the actual value, by horizon
  E  the one-month-ahead forecast for the latest month in the data
"""
import argparse
import os

import numpy as np
import pandas as pd

M = 12
Z80 = 1.2816
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_CSV = os.path.join(HERE, "data_clean", "upi_monthly_clean.csv")


def load(path):
    df = pd.read_csv(path, parse_dates=["month"])
    df = df[df.volume_mn > 0]
    return pd.Series(np.log(df.volume_mn.to_numpy()), index=pd.PeriodIndex(df.month, freq="M"))


# ---------- models: f(train_log: Series, h) -> {"fc": log forecasts, "lo"/"hi": log range or None, "sigma": float or None}

def statsmodels_model(train, h):
    from statsmodels.tsa.holtwinters import ExponentialSmoothing  # same settings as forecast_upi.py
    s = pd.Series(train.to_numpy(), index=train.index.to_timestamp(how="start")).asfreq("MS")
    res = ExponentialSmoothing(
        s, trend="add", damped_trend=True, seasonal="add", seasonal_periods=12,
        initialization_method="estimated",
    ).fit()
    fc = np.asarray(res.forecast(h), dtype=float)
    sims = np.asarray(res.simulate(h, repetitions=1000, error="add", anchor="end", random_state=1))
    return {"fc": fc, "lo": np.percentile(sims, 10, axis=1), "hi": np.percentile(sims, 90, axis=1), "sigma": None}


def _filter(y, p):
    alpha, beta, gamma, phi = p
    n = len(y)
    b = (y[M:2 * M].mean() - y[:M].mean()) / M if n >= 2 * M else 0.0
    mean0 = y[:M].mean()
    level = mean0 + b * (M - 1) / 2
    seas = [y[i] - mean0 - b * (i - (M - 1) / 2) for i in range(M)]
    resid = []
    for t in range(M, n):
        e = y[t] - (level + phi * b + seas[t - M])
        level = level + phi * b + alpha * e
        b = phi * b + beta * e
        seas.append(seas[t - M] + gamma * e)
        resid.append(e)
    return level, b, seas, np.array(resid)


def reference_model(train, h):
    from scipy.optimize import minimize
    starts = [(0.3, 0.05, 0.1, 0.9), (0.6, 0.1, 0.05, 0.95), (0.15, 0.02, 0.2, 0.85)]
    bounds = [(0.01, 0.99), (0.0, 0.5), (0.0, 0.5), (0.80, 0.98)]  # alpha, beta, gamma, phi
    y = train.to_numpy()
    best = None
    for x0 in starts:
        r = minimize(lambda p: float(np.sum(_filter(y, p)[3] ** 2)), x0, bounds=bounds, method="L-BFGS-B")
        if best is None or r.fun < best.fun:
            best = r
    level, b, seas, res = _filter(y, best.x)
    n, phi = len(y), best.x[3]
    fc = [level + sum(phi ** j for j in range(1, k + 1)) * b + seas[n - 1 + k - M * int(np.ceil(k / M))]
          for k in range(1, h + 1)]
    return {"fc": np.array(fc), "lo": None, "hi": None, "sigma": float(np.std(res, ddof=4))}


def naive(train, h):
    return {"fc": np.repeat(train.iloc[-1], h), "lo": None, "hi": None, "sigma": None}


def seasonal_growth(train, h):
    lv = np.exp(train.to_numpy())
    g = lv[-12:].sum() / lv[-24:-12].sum()
    fc = np.log(np.array([lv[len(lv) - 12 + (k - 1) % 12] * g for k in range(1, h + 1)]))
    return {"fc": fc, "lo": None, "hi": None, "sigma": None}


# ---------- harness

def interval(out, h):
    if out.get("lo") is not None:
        return np.asarray(out["lo"]), np.asarray(out["hi"])
    if out.get("sigma") is not None:
        half = Z80 * out["sigma"] * np.sqrt(np.arange(1, h + 1))
        return out["fc"] - half, out["fc"] + half
    return None


def backtest(logy, fn, start, origin, h=12):
    out = fn(logy.loc[start:origin], h)
    actual = logy.reindex(pd.period_range(origin + 1, periods=h, freq="M"))
    if actual.isna().any():
        raise ValueError(f"actual values missing after {origin}")
    act_log = actual.to_numpy()
    pred, act = np.exp(out["fc"]), np.exp(act_log)
    ape = np.abs(pred - act) / act
    rng = interval(out, h)
    cover = None if rng is None else ((act_log >= rng[0]) & (act_log <= rng[1])).astype(float)
    return ape, cover


def pct(x):
    return f"{100 * x:.1f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=DEFAULT_CSV)
    ap.add_argument("--model", choices=["statsmodels", "reference"], default="statsmodels")
    args = ap.parse_args()
    model = statsmodels_model if args.model == "statsmodels" else reference_model

    lines = []

    def say(text=""):
        print(text)
        lines.append(text)

    logy = load(args.csv)
    last = logy.index[-1]
    holdout_origin = last - 12
    say(f"model: {args.model} | data: {logy.index[0]} to {last}, {len(logy)} months | holdout origin: {holdout_origin}")

    say("\nA. Single backtest (train from 2021-04, hide the last 12 months)")
    for name, fn in [(args.model, model), ("naive", naive), ("seasonal growth", seasonal_growth)]:
        say(f"   {name:16s} MAPE {pct(backtest(logy, fn, '2021-04', holdout_origin)[0].mean())}")

    say(f"\nB. Start-date sensitivity (same holdout, origin {holdout_origin})")
    for s in ["2019-04", "2020-04", "2021-04", "2022-04"]:
        say(f"   train from {s}: MAPE {pct(backtest(logy, model, s, holdout_origin)[0].mean())}")

    origins = [holdout_origin - 3 * i for i in range(8, -1, -1)]  # 9 origins, every 3 months, ending at the holdout origin
    apes, covs, nv, sg = [], [], [], []
    for og in origins:
        a, c = backtest(logy, model, "2021-04", og)
        apes.append(a); covs.append(c)
        nv.append(backtest(logy, naive, "2021-04", og)[0].mean())
        sg.append(backtest(logy, seasonal_growth, "2021-04", og)[0].mean())
    apes = np.array(apes)
    say(f"\nC. Rolling origins ({len(origins)} origins, {origins[0]} to {origins[-1]}, 12-month horizon each)")
    say(f"   {args.model} MAPE {pct(apes.mean())} | naive {pct(np.mean(nv))} | seasonal growth {pct(np.mean(sg))}")
    say("   MAPE by horizon (months ahead):")
    say("   " + " ".join(f"h{h:<2d}" for h in range(1, 13)))
    say("   " + " ".join(f"{100 * x:3.1f}" for x in apes.mean(axis=0)))
    say("   MAPE by origin:")
    for og, a in zip(origins, apes):
        say(f"   origin {og}: {len(logy.loc['2021-04':og])} training months, MAPE {pct(a.mean())}")

    if all(c is not None for c in covs):
        covs = np.array(covs)
        say("\nD. Share of actual values inside the 80% range, pooled over origins (target: 80%)")
        for lo, hi in [(1, 3), (4, 6), (7, 12)]:
            say(f"   horizons {lo}-{hi}: {pct(covs[:, lo - 1:hi].mean())}")
        say("   (9 overlapping origins: indicative, not a precise coverage estimate)")

    out = model(logy.loc["2021-04":last], 1)
    pt = float(np.exp(out["fc"][0]))
    rng = interval(out, 1)
    month = last + 1
    msg = f"\nE. One month ahead ({month}): point {pt:,.0f} mn"
    if rng is not None:
        msg += f", 80% range {float(np.exp(rng[0][0])):,.0f} to {float(np.exp(rng[1][0])):,.0f}"
    say(msg)

    os.makedirs(os.path.join(HERE, "outputs"), exist_ok=True)
    path = os.path.join(HERE, "outputs", f"rolling_backtest_{args.model}.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\nsaved {os.path.relpath(path, HERE)}")


if __name__ == "__main__":
    main()
