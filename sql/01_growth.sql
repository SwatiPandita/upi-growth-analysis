-- Month-on-month and year-on-year growth in UPI volume and value
SELECT
    substr(month, 1, 7) AS month,
    volume_mn,
    value_cr,
    avg_ticket_rs,
    ROUND((volume_mn - LAG(volume_mn, 1) OVER (ORDER BY month)) * 100.0
          / NULLIF(LAG(volume_mn, 1) OVER (ORDER BY month), 0), 2) AS volume_mom_pct,
    ROUND((volume_mn - LAG(volume_mn, 12) OVER (ORDER BY month)) * 100.0
          / NULLIF(LAG(volume_mn, 12) OVER (ORDER BY month), 0), 2) AS volume_yoy_pct,
    ROUND((value_cr - LAG(value_cr, 12) OVER (ORDER BY month)) * 100.0
          / NULLIF(LAG(value_cr, 12) OVER (ORDER BY month), 0), 2) AS value_yoy_pct
FROM upi_monthly
ORDER BY month;