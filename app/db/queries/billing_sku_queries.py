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
