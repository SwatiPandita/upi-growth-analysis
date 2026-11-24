-- Financial-year totals (April to March) with year-on-year growth.
-- Growth is calculated from UNROUNDED yearly sums (the previous version
-- calculated it from already-rounded values, which distorted small years).
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
        COUNT(*)                          AS months,
        SUM(volume_mn)                    AS vol_mn_raw,
        SUM(value_cr)                     AS value_cr_raw,
        MAX(banks_live)                   AS banks_live_end
    FROM fy
    GROUP BY start_yr
)
SELECT
    fin_year,
    months,
    ROUND(vol_mn_raw / 1000.0, 2)          AS volume_bn,
    ROUND(value_cr_raw / 100000.0, 2)      AS value_lakh_cr,
    ROUND(value_cr_raw * 10 / vol_mn_raw, 0) AS avg_ticket_rs,
    banks_live_end,
    ROUND((vol_mn_raw - LAG(vol_mn_raw) OVER (ORDER BY fin_year)) * 100.0
          / LAG(vol_mn_raw) OVER (ORDER BY fin_year), 1)     AS volume_growth_pct,
    ROUND((value_cr_raw - LAG(value_cr_raw) OVER (ORDER BY fin_year)) * 100.0
          / LAG(value_cr_raw) OVER (ORDER BY fin_year), 1)   AS value_growth_pct,
    ROUND((vol_mn_raw - LAG(vol_mn_raw) OVER (ORDER BY fin_year)) / 1000.0, 1) AS volume_added_bn
FROM yearly
ORDER BY fin_year;
