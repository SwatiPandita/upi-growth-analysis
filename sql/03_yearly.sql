-- Financial-year totals (April to March) with year-on-year growth
WITH base AS (
    SELECT
        CAST(substr(month, 1, 4) AS INTEGER) AS yr,
        CAST(substr(month, 6, 2) AS INTEGER) AS mo,
        volume_mn, value_cr, banks_live
    FROM upi_monthly
),
fy AS (
    SELECT CASE WHEN mo >= 4 THEN yr ELSE yr - 1 END AS start_yr,
           volume_mn, value_cr, banks_live
    FROM base
),
yearly AS (
    SELECT
        start_yr || '-' || substr(start_yr + 1, 3, 2) AS fin_year,
        COUNT(*) AS months,
        ROUND(SUM(volume_mn) / 1000.0, 2) AS volume_bn,
        ROUND(SUM(value_cr) / 100000.0, 2) AS value_lakh_cr,
        ROUND(SUM(value_cr) * 10 / SUM(volume_mn), 0) AS avg_ticket_rs,
        MAX(banks_live) AS banks_live_end
    FROM fy
    GROUP BY start_yr
)
SELECT *,
    ROUND((volume_bn - LAG(volume_bn) OVER (ORDER BY fin_year)) * 100.0
          / LAG(volume_bn) OVER (ORDER BY fin_year), 1) AS volume_growth_pct,
    ROUND((value_lakh_cr - LAG(value_lakh_cr) OVER (ORDER BY fin_year)) * 100.0
          / LAG(value_lakh_cr) OVER (ORDER BY fin_year), 1) AS value_growth_pct
FROM yearly
ORDER BY fin_year;