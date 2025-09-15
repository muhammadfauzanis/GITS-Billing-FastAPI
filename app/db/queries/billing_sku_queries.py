GET_SKU_USAGE_TREND_FOR_DATE_RANGE = """
    SELECT
        s.usage_date,
        s.sku_description,
        SUM(s.usage) as total_usage
    FROM sku_usage_data s
    JOIN projects p ON s.project_id = p.project_id
    WHERE p.client_id = %s
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
    JOIN projects p ON s.project_id = p.project_id
    WHERE p.client_id = %s
      AND s.usage_date >= %s
      AND s.usage_date <= %s
    GROUP BY s.sku_description, s.gcp_services, s.sku_id, s.usage_unit
    ORDER BY total_cost DESC;
"""

GET_SKU_COST_TREND_TOP_N = """
    WITH ranked_skus AS (
      SELECT
        s.sku_description
      FROM sku_usage_data s
      JOIN projects p ON s.project_id = p.project_id
      WHERE p.client_id = %s
        AND s.usage_date >= %s AND s.usage_date <= %s
      GROUP BY s.sku_description
      ORDER BY SUM(s.agg_value) DESC -- DIUBAH: Mengurutkan berdasarkan biaya akhir
      LIMIT %s
    )
    SELECT
      s.usage_date,
      s.sku_description,
      SUM(s.agg_value) as daily_cost -- DIUBAH: Gunakan agg_value
    FROM sku_usage_data s
    JOIN projects p ON s.project_id = p.project_id
    INNER JOIN ranked_skus rs ON s.sku_description = rs.sku_description
    WHERE p.client_id = %s
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
    SUM(s.cost_before_discount) as total_cost,
    SUM(s.discount_total) as total_discount, -- DIUBAH: Gunakan discount_total
    SUM(s.promotion) as total_promotion,
    SUM(s.agg_value) as subtotal -- DIUBAH: Subtotal adalah agg_value
  FROM sku_usage_data s
  JOIN projects p ON s.project_id = p.project_id
  WHERE p.client_id = %s
    AND s.usage_date >= %s AND s.usage_date <= %s
  GROUP BY s.sku_description, s.gcp_services, s.sku_id, s.usage_unit
  ORDER BY subtotal DESC; -- DIUBAH: Mengurutkan berdasarkan subtotal
"""

GET_SKU_COST_TREND_TOP_N_PER_PROJECT = """
    WITH TopSkusInProject AS (
        SELECT
            sud.sku_description
        FROM sku_usage_data sud
        JOIN projects p ON sud.project_id = p.project_id
        WHERE
            p.client_id = %s AND sud.project_id = %s AND sud.usage_date BETWEEN %s AND %s
        GROUP BY
            sud.sku_description
        ORDER BY
            SUM(sud.agg_value) DESC -- DIUBAH: Mengurutkan berdasarkan biaya akhir
        LIMIT %s
    )
    SELECT
        DATE(sud.usage_date) as usage_day,
        sud.sku_description,
        SUM(sud.agg_value) as total_cost -- DIUBAH: Gunakan agg_value
    FROM sku_usage_data sud
    JOIN projects p ON sud.project_id = p.project_id
    JOIN TopSkusInProject ts ON sud.sku_description = ts.sku_description
    WHERE
        p.client_id = %s AND sud.project_id = %s AND sud.usage_date BETWEEN %s AND %s
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
        SUM(COALESCE(discount_total, 0)) as total_discount, -- DIUBAH: Gunakan discount_total
        SUM(COALESCE(promotion, 0)) as total_promo,
        SUM(COALESCE(agg_value, 0)) as subtotal -- DIUBAH: Subtotal adalah agg_value
    FROM sku_usage_data s
    JOIN projects p ON s.project_id = p.project_id
    WHERE
        p.client_id = %s AND s.project_id = %s AND s.usage_date BETWEEN %s AND %s
    GROUP BY
        sku_description,
        gcp_services,
        sku_id,
        usage_unit
    ORDER BY
        subtotal DESC; -- DIUBAH: Mengurutkan berdasarkan subtotal
"""
