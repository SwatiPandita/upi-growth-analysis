-- Fair comparison: April-September 2026 vs April-September 2025
WITH h AS (
    SELECT
        SUM(CASE WHEN substr(month, 1, 7) BETWEEN '2025-04' AND '2025-09' THEN volume_mn END) AS v_prev,
        SUM(CASE WHEN substr(month, 1, 7) BETWEEN '2026-04' AND '2026-09' THEN volume_mn END) AS v_curr,
        SUM(CASE WHEN substr(month, 1, 7) BETWEEN '2025-04' AND '2025-09' THEN value_cr END) AS val_prev,
        SUM(CASE WHEN substr(month, 1, 7) BETWEEN '2026-04' AND '2026-09' THEN value_cr END) AS val_curr
    FROM upi_monthly
)
SELECT
    ROUND(v_prev / 1000.0, 2) AS apr_sep_2025_volume_bn,
    ROUND(v_curr / 1000.0, 2) AS apr_sep_2026_volume_bn,
    ROUND((v_curr - v_prev) * 100.0 / v_prev, 1) AS volume_growth_pct,
    ROUND((val_curr - val_prev) * 100.0 / val_prev, 1) AS value_growth_pct
FROM h;