GET_SKU_USAGE_TREND_FOR_DATE_RANGE = """
    SELECT
        s.usage_date,
        s.sku_description,
        SUM(s.usage) as total_usage
    FROM sku_usage_data s
    WHERE s.client_id = %s
      AND s.usage_date >= %s
      AND s.usage_date <= %s
    GROUP BY s.usage_date, s.sku_description
    ORDER BY s.usage_date, total_usage DESC;
"""

GET_SKU_USAGE_TABLE_FOR_DATE_RANGE = """
    SELECT
        s.sku_description,
        s.gcp_services,
        s.sku_id,
        s.usage_unit,
        SUM(s.usage) as total_usage,
        SUM(s.cost_before_discount) as total_cost,
        SUM(s.reseller_margin) as total_discount, -- MENGGUNAKAN reseller_margin SEBAGAI DISKON
        SUM(s.promotion) as total_promotion
    FROM sku_usage_data s
    WHERE s.client_id = %s
      AND s.usage_date >= %s
      AND s.usage_date <= %s
    GROUP BY s.sku_description, s.gcp_services, s.sku_id, s.usage_unit
    ORDER BY total_cost DESC;
"""

# Kueri untuk mengambil tren biaya harian dari N SKU teratas
GET_SKU_COST_TREND_TOP_N = """
WITH ranked_skus AS (
  SELECT
    sku_description
  FROM sku_usage_data
  WHERE client_id = %s
    AND usage_date >= %s AND usage_date <= %s
  GROUP BY sku_description
  ORDER BY SUM(cost_before_discount) DESC
  LIMIT %s -- Ambil hanya N teratas
)
SELECT
  s.usage_date,
  s.sku_description,
  SUM(s.cost_before_discount) as daily_cost
FROM sku_usage_data s
INNER JOIN ranked_skus rs ON s.sku_description = rs.sku_description
WHERE s.client_id = %s
  AND s.usage_date >= %s AND s.usage_date <= %s
GROUP BY s.usage_date, s.sku_description
ORDER BY s.usage_date, daily_cost DESC;
"""

GET_SKU_BREAKDOWN_ALL = """
  SELECT
    s.sku_description,
    s.gcp_services,
    s.sku_id,
    s.usage_unit,
    SUM(s.usage) as total_usage,
    SUM(COALESCE(s.cost_before_discount, 0)) as total_cost,
    SUM(COALESCE(s.reseller_margin, 0)) as total_discount,
    SUM(COALESCE(s.promotion, 0)) as total_promotion
  FROM sku_usage_data s
  WHERE s.client_id = %s
    AND s.usage_date >= %s AND s.usage_date <= %s
  GROUP BY s.sku_description, s.gcp_services, s.sku_id, s.usage_unit
  ORDER BY total_cost DESC;
"""

GET_SKU_COST_TREND_TOP_N_PER_PROJECT = """
    WITH TopSkusInProject AS (
        SELECT
            sku_description
        FROM sku_usage_data
        WHERE
            client_id = %s AND project_id = %s AND usage_date BETWEEN %s AND %s
        GROUP BY
            sku_description
        ORDER BY
            SUM(cost_before_discount) DESC
        LIMIT %s
    )
    SELECT
        DATE(sud.usage_date) as usage_day,
        sud.sku_description,
        SUM(sud.cost_before_discount) as total_cost
    FROM sku_usage_data sud
    JOIN TopSkusInProject ts ON sud.sku_description = ts.sku_description
    WHERE
        sud.client_id = %s AND sud.project_id = %s AND sud.usage_date BETWEEN %s AND %s
    GROUP BY
        usage_day,
        sud.sku_description
    ORDER BY
        usage_day,
        total_cost DESC;
"""

GET_SKU_BREAKDOWN_PER_PROJECT = """
    SELECT
        sku_description,
        gcp_services,
        sku_id,
        usage_unit,
        SUM(COALESCE(usage, 0)) as total_usage,
        SUM(COALESCE(cost_before_discount, 0)) as total_cost,
        SUM(COALESCE(reseller_margin, 0)) as total_discount,
        SUM(COALESCE(promotion, 0)) as total_promo
    FROM sku_usage_data
    WHERE
        client_id = %s AND project_id = %s AND usage_date BETWEEN %s AND %s
    GROUP BY
        sku_description,
        gcp_services,
        sku_id,
        usage_unit
    ORDER BY
        total_cost DESC;
"""