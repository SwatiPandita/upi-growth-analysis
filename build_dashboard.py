"""Build docs/index.html: a self-contained interactive dashboard (no external files, no packages).

    python build_dashboard.py

Reads data_clean/upi_monthly_clean.csv, outputs/forecast.csv and outputs/growth_decomposition.csv.
Publish it with GitHub Pages: Settings > Pages > Deploy from a branch > main > /docs.
"""
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))


def fy_label(ts):
    start = ts.year if ts.month >= 4 else ts.year - 1
    return f"FY{start}-{str(start + 1)[2:]}"


def build_payload():
    m = pd.read_csv(os.path.join(HERE, "data_clean", "upi_monthly_clean.csv"), parse_dates=["month"])
    m = m[m.volume_mn > 0].copy()
    m["fy"] = m.month.map(fy_label)
    monthly = [{"m": r.month.strftime("%Y-%m"), "v": round(r.volume_mn, 1)}
               for r in m[m.month >= "2018-04-01"].itertuples()]
    fc = pd.read_csv(os.path.join(HERE, "outputs", "forecast.csv"))
    forecast = [{"m": r.month, "v": r.forecast_volume_mn, "lo": r.low_80, "hi": r.high_80} for r in fc.itertuples()]
    y = m.groupby("fy").agg(vol=("volume_mn", "sum"), val=("value_cr", "sum"), n=("month", "count"))
    y = y[y.n == 12].copy()
    y["ticket"] = y.val * 10 / y.vol
    y["vol_growth"] = 100 * y.vol.pct_change()
    y["val_growth"] = 100 * y.val.pct_change()
    y["ticket_change"] = 100 * y.ticket.pct_change()
    y["added_bn"] = y.vol.diff() / 1000
    yearly = [{"fy": fy, "vol_bn": round(r.vol / 1000, 2), "ticket": round(r.ticket),
               "vol_growth": None if pd.isna(r.vol_growth) else round(r.vol_growth, 1),
               "val_growth": None if pd.isna(r.val_growth) else round(r.val_growth, 1),
               "ticket_change": None if pd.isna(r.ticket_change) else round(r.ticket_change, 1),
               "added_bn": None if pd.isna(r.added_bn) else round(r.added_bn, 1)}
              for fy, r in y.iterrows()]
    return {"monthly": monthly, "forecast": forecast, "yearly": yearly}


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UPI Growth Analysis</title>
<style>
:root{color-scheme:light;--bg:#ffffff;--card:#f6f6f6;--text:#191919;--muted:#666666;--grid:#e3e3e3;
--s1:#257de0;--s2:#f47230;--band:rgba(244,114,48,.16)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#191919;--card:#232323;--text:#efefef;--muted:#9c9c9c;--grid:#363636;--s1:#338ced;--s2:#e76624;--band:rgba(231,102,36,.2)}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
main{max-width:1040px;margin:0 auto;padding:24px 16px 48px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:17px;margin:0 0 2px}
.sub{color:var(--muted);margin:0 0 20px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px;margin-bottom:20px}
.kpi{background:var(--card);border-radius:10px;padding:12px 14px}.kpi b{display:block;font-size:24px}.kpi span{color:var(--muted);font-size:13px}
.card{background:var(--card);border-radius:10px;padding:16px;margin-bottom:16px;position:relative}
.card p{margin:0 0 10px;color:var(--muted);font-size:13.5px}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:13px;margin-bottom:6px}
.legend i{display:inline-block;width:12px;height:12px;border-radius:3px;margin-right:6px;vertical-align:-1px}
svg{width:100%;height:auto;display:block;overflow:visible}
.tip{position:absolute;pointer-events:none;background:var(--bg);border:1px solid var(--grid);border-radius:8px;padding:6px 9px;font-size:12.5px;display:none;white-space:nowrap;box-shadow:0 2px 8px rgba(0,0,0,.15);z-index:2}
details{margin-top:8px;font-size:13px}table{border-collapse:collapse;width:100%;margin-top:6px}
th,td{text-align:right;padding:3px 8px;border-bottom:1px solid var(--grid)}th:first-child,td:first-child{text-align:left}
footer{color:var(--muted);font-size:12.5px;margin-top:20px}a{color:var(--s1)}
</style>
</head>
<body>
<main>
<h1>UPI growth, April 2018 to September 2026</h1>
<p class="sub">Percentage growth is slowing, absolute additions are not, and the average payment keeps shrinking. Source: NPCI UPI product statistics (monthly).</p>
<div class="kpis" id="kpis"></div>

<section class="card"><h2>Monthly transactions and 12-month forecast</h2>
<p>Millions of transactions per month. Dashed line and band: forecast and 80% range from the model in <code>forecast_upi.py</code>.</p>
<div class="legend"><span><i style="background:var(--s1)"></i>Actual</span><span><i style="background:var(--s2)"></i>Forecast (80% range shaded)</span></div>
<div id="c1"></div><div class="tip" id="t1"></div></section>

<section class="card"><h2>Yearly growth: volume against value</h2>
<p>Value grows more slowly than volume because the average ticket has fallen about 7 to 9% a year since FY2022-23.</p>
<div class="legend"><span><i style="background:var(--s1)"></i>Volume growth %</span><span><i style="background:var(--s2)"></i>Value growth %</span></div>
<div id="c2"></div><div class="tip" id="t2"></div></section>

<section class="card"><h2>Transactions added each year (billions)</h2>
<p>The yearly addition is still rising even as the percentage falls.</p>
<div id="c3"></div><div class="tip" id="t3"></div></section>

<section class="card"><h2>Average ticket (Rs per transaction)</h2>
<p>Value divided by volume, nominal rupees.</p>
<div id="c4"></div><div class="tip" id="t4"></div>
<details><summary>Show data table</summary><div id="tbl"></div></details></section>

<footer>Forecast is a statistical baseline, not a prediction of policy changes. Code and method:
<a href="https://github.com/SwatiPandita/upi-growth-analysis">github.com/SwatiPandita/upi-growth-analysis</a>.</footer>
</main>
<script>
const D = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const NS = "http://www.w3.org/2000/svg";
const el = (n, a = {}, t) => { const e = document.createElementNS(NS, n); for (const k in a) e.setAttribute(k, a[k]); if (t != null) e.textContent = t; return e; };
const fmt = (x, d = 0) => x.toLocaleString("en-IN", {maximumFractionDigits: d, minimumFractionDigits: d});
const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const lab = m => MON[+m.slice(5) - 1] + " " + m.slice(0, 4);
const W = 960, H = 320, P = {l: 56, r: 16, t: 12, b: 34};

function frame(id, h = H) {
  const host = document.getElementById(id); host.innerHTML = "";
  const svg = el("svg", {viewBox: `0 0 ${W} ${h}`, role: "img"}); host.appendChild(svg); return {svg, host, h};
}
function axes(svg, h, ymax, yfmt, xticks, xs) {
  const iy = v => P.t + (h - P.t - P.b) * (1 - v / ymax);
  const step = ymax <= 10 ? 2 : ymax <= 60 ? 10 : ymax <= 150 ? 50 : ymax <= 400 ? 50 : ymax <= 1500 ? 200 : ymax <= 2500 ? 500 : 5000;
  for (let v = 0; v <= ymax; v += step) {
    svg.appendChild(el("line", {x1: P.l, x2: W - P.r, y1: iy(v), y2: iy(v), stroke: css("--grid"), "stroke-width": 1}));
    svg.appendChild(el("text", {x: P.l - 8, y: iy(v) + 4, "text-anchor": "end", fill: css("--muted"), "font-size": 12}, yfmt(v)));
  }
  xticks.forEach(i => svg.appendChild(el("text", {x: xs(i), y: h - 10, "text-anchor": "middle", fill: css("--muted"), "font-size": 12}, xticks.labels[xticks.indexOf(i)])));
  return iy;
}
function tipper(host, tip) {
  return (html, x, y) => {
    tip.innerHTML = html; tip.style.display = "block";
    const r = host.getBoundingClientRect(), cr = host.parentElement.getBoundingClientRect();
    const px = (x / W) * r.width + (r.left - cr.left), py = (y / H) * r.height + (r.top - cr.top);
    tip.style.left = Math.min(px + 12, cr.width - tip.offsetWidth - 8) + "px"; tip.style.top = Math.max(py - 40, 0) + "px";
  };
}

function kpis() {
  const y = D.yearly, last = y[y.length - 1];
  const items = [[fmt(last.vol_bn, 1) + " bn", "transactions in " + last.fy],
    ["+" + fmt(last.vol_growth, 1) + "%", "volume growth, down from " + fmt(y.find(r => r.fy == "FY2021-22").vol_growth, 0) + "% in FY2021-22"],
    ["+" + fmt(last.added_bn, 1) + " bn", "added in " + last.fy + ", the most in any year"],
    ["Rs " + fmt(last.ticket), "average ticket, from Rs " + fmt(Math.max(...y.filter(r => r.fy != "FY2016-17").map(r => r.ticket))) + " at the FY2020-21 peak"]];
  document.getElementById("kpis").innerHTML = items.map(i => `<div class="kpi"><b>${i[0]}</b><span>${i[1]}</span></div>`).join("");
}

function chart1() {
  const {svg, host} = frame("c1"), tip = document.getElementById("t1"), show = tipper(host, tip);
  const all = D.monthly.map(r => ({m: r.m, v: r.v})), fc = D.forecast;
  const n = all.length + fc.length, ymax = 30000, xs = i => P.l + (W - P.l - P.r) * i / (n - 1);
  const ticks = [], labels = [];
  all.concat(fc).forEach((r, i) => { if (r.m.endsWith("-04") && +r.m.slice(0, 4) % 2 == 0) { ticks.push(i); labels.push("Apr " + r.m.slice(0, 4)); } });
  ticks.labels = labels;
  const iy = axes(svg, H, ymax, v => fmt(v / 1000) + "k", ticks, xs);
  const band = fc.map((r, i) => `${xs(all.length + i)},${iy(r.hi)}`).concat(fc.slice().reverse().map((r, i) => `${xs(all.length + fc.length - 1 - i)},${iy(r.lo)}`));
  svg.appendChild(el("polygon", {points: band.join(" "), fill: css("--band")}));
  svg.appendChild(el("polyline", {points: all.map((r, i) => `${xs(i)},${iy(r.v)}`).join(" "), fill: "none", stroke: css("--s1"), "stroke-width": 2}));
  const join = [all[all.length - 1]].concat(fc);
  svg.appendChild(el("polyline", {points: join.map((r, i) => `${xs(all.length - 1 + i)},${iy(r.v)}`).join(" "), fill: "none", stroke: css("--s2"), "stroke-width": 2, "stroke-dasharray": "6 4"}));
  const cross = el("line", {y1: P.t, y2: H - P.b, stroke: css("--muted"), "stroke-width": 1, visibility: "hidden"}); svg.appendChild(cross);
  const hit = el("rect", {x: P.l, y: P.t, width: W - P.l - P.r, height: H - P.t - P.b, fill: "transparent"}); svg.appendChild(hit);
  hit.addEventListener("mousemove", e => {
    const r = svg.getBoundingClientRect(), x = (e.clientX - r.left) / r.width * W;
    const i = Math.max(0, Math.min(n - 1, Math.round((x - P.l) / (W - P.l - P.r) * (n - 1))));
    const isF = i >= all.length, row = isF ? fc[i - all.length] : all[i];
    cross.setAttribute("x1", xs(i)); cross.setAttribute("x2", xs(i)); cross.setAttribute("visibility", "visible");
    show(`<b>${lab(row.m)}</b><br>${isF ? "Forecast" : "Actual"}: ${fmt(row.v)} mn` + (isF ? `<br>80% range: ${fmt(row.lo)} to ${fmt(row.hi)}` : ""), xs(i), iy(row.v));
  });
  hit.addEventListener("mouseleave", () => { tip.style.display = "none"; cross.setAttribute("visibility", "hidden"); });
}

function groupedBars(id, tid, rows, series, ymaxIn, yfmt, tipFn) {
  const {svg, host} = frame(id), tip = document.getElementById(tid), show = tipper(host, tip);
  const n = rows.length, bw = (W - P.l - P.r) / n, k = series.length, w = Math.min(34, (bw * 0.7) / k);
  const xs = i => P.l + bw * (i + 0.5);
  const ticks = rows.map((_, i) => i); ticks.labels = rows.map(r => r.fy.replace("FY", "").replace("20", "'").replace(/-/, "-"));
  const iy = axes(svg, H, ymaxIn, yfmt, ticks, xs);
  rows.forEach((r, i) => series.forEach((s, j) => {
    const v = r[s.key]; if (v == null) return;
    const x = xs(i) - (k * w) / 2 + j * w, y = iy(Math.max(v, 0)), h = Math.max(iy(0) - y, 1);
    const b = el("rect", {x: x + 1, y, width: w - 2, height: h, rx: 3, fill: css(s.color)}); svg.appendChild(b);
    b.addEventListener("mousemove", () => show(tipFn(r), xs(i), y)); b.addEventListener("mouseleave", () => tip.style.display = "none");
  }));
}

function chart4() {
  const rows = D.yearly.filter(r => r.fy != "FY2016-17" && r.ticket > 0);
  const {svg, host} = frame("c4"), tip = document.getElementById("t4"), show = tipper(host, tip);
  const n = rows.length, xs = i => P.l + (W - P.l - P.r) * (i + 0.5) / n, ymax = 2000;
  const ticks = rows.map((_, i) => i); ticks.labels = rows.map(r => r.fy.replace("FY", "").replace("20", "'"));
  const iy = axes(svg, H, ymax, v => fmt(v), ticks, xs);
  svg.appendChild(el("polyline", {points: rows.map((r, i) => `${xs(i)},${iy(r.ticket)}`).join(" "), fill: "none", stroke: css("--s1"), "stroke-width": 2}));
  rows.forEach((r, i) => {
    const c = el("circle", {cx: xs(i), cy: iy(r.ticket), r: 5, fill: css("--s1"), stroke: css("--card"), "stroke-width": 2}); svg.appendChild(c);
    const hit = el("circle", {cx: xs(i), cy: iy(r.ticket), r: 16, fill: "transparent"}); svg.appendChild(hit);
    hit.addEventListener("mousemove", () => show(`<b>${r.fy}</b><br>Rs ${fmt(r.ticket)} per transaction` + (r.ticket_change == null ? "" : `<br>${r.ticket_change > 0 ? "+" : ""}${fmt(r.ticket_change, 1)}% vs previous year`), xs(i), iy(r.ticket)));
    hit.addEventListener("mouseleave", () => tip.style.display = "none");
  });
}

function table() {
  const head = "<tr><th>Year</th><th>Volume (bn)</th><th>Volume growth %</th><th>Value growth %</th><th>Ticket (Rs)</th><th>Added (bn)</th></tr>";
  const body = D.yearly.map(r => `<tr><td>${r.fy}</td><td>${fmt(r.vol_bn, 2)}</td><td>${r.vol_growth == null ? "" : fmt(r.vol_growth, 1)}</td><td>${r.val_growth == null ? "" : fmt(r.val_growth, 1)}</td><td>${fmt(r.ticket)}</td><td>${r.added_bn == null ? "" : fmt(r.added_bn, 1)}</td></tr>`).join("");
  document.getElementById("tbl").innerHTML = "<table>" + head + body + "</table>";
}

function draw() {
  kpis(); chart1();
  const rows = D.yearly.filter(r => r.fy >= "FY2021-22");
  groupedBars("c2", "t2", rows, [{key: "vol_growth", color: "--s1"}, {key: "val_growth", color: "--s2"}], 120, v => v + "%",
    r => `<b>${r.fy}</b><br>Volume growth: ${fmt(r.vol_growth, 1)}%<br>Value growth: ${fmt(r.val_growth, 1)}%<br>Average ticket: ${r.ticket_change > 0 ? "+" : ""}${fmt(r.ticket_change, 1)}%`);
  groupedBars("c3", "t3", D.yearly.filter(r => r.added_bn != null && r.fy >= "FY2019-20"), [{key: "added_bn", color: "--s1"}], 60, v => v,
    r => `<b>${r.fy}</b><br>Added ${fmt(r.added_bn, 1)} bn transactions<br>Total ${fmt(r.vol_bn, 1)} bn`);
  chart4(); table();
}
draw();
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
</script>
</body>
</html>
"""


def main():
    html = TEMPLATE.replace("__DATA__", json.dumps(build_payload(), separators=(",", ":")))
    os.makedirs(os.path.join(HERE, "docs"), exist_ok=True)
    path = os.path.join(HERE, "docs", "index.html")
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    print("wrote", os.path.relpath(path, HERE), f"({len(html) // 1024} KB)")


if __name__ == "__main__":
    main()
