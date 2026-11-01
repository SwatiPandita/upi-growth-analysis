-- Seasonality: how each calendar month compares with the months around it,
-- using average DAILY volume so 28, 30 and 31 day months are comparable.
-- Index above 100 = stronger than its neighbours. Years 2021-2025 only.
WITH daily AS (
    SELECT
        substr(month, 1, 7) AS ym,
        CAST(substr(month, 6, 2) AS INTEGER) AS cal_month,
        CAST(substr(month, 1, 4) AS INTEGER) AS yr,
        volume_mn * 1.0 / CAST(strftime('%d', date(month, '+1 month', '-1 day')) AS INTEGER) AS daily_vol
    FROM upi_monthly
),
idx AS (
    SELECT *,
        daily_vol * 100.0 / ((LAG(daily_vol) OVER (ORDER BY ym)
                            + LEAD(daily_vol) OVER (ORDER BY ym)) / 2.0) AS season_index
    FROM daily
)
SELECT
    cal_month,
    COUNT(*) AS years_used,
    ROUND(AVG(season_index), 1) AS avg_index,
    ROUND(MIN(season_index), 1) AS min_index,
    ROUND(MAX(season_index), 1) AS max_index
FROM idx
WHERE yr BETWEEN 2021 AND 2025 AND season_index IS NOT NULL
GROUP BY cal_month
ORDER BY cal_month;