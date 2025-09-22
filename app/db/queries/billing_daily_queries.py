GET_DAILY_COSTS_FOR_DATE_RANGE = """
    SELECT
        bd.usage_date,
        SUM(bd.cost_before_discount) AS daily_total
    FROM billing_data_daily bd
    JOIN projects p ON bd.project_id = p.project_id
    WHERE p.client_id = %s
      AND bd.usage_date >= %s
      AND bd.usage_date <= %s
    GROUP BY bd.usage_date
    ORDER BY bd.usage_date ASC;
"""

GET_PROJECT_BREAKDOWN_FOR_DATE_RANGE = """
    SELECT
        bd.project_id,
        SUM(bd.cost_before_discount) as total_raw_cost
    FROM billing_data_daily bd
    JOIN projects p ON bd.project_id = p.project_id
    WHERE p.client_id = %s
      AND bd.usage_date >= %s
      AND bd.usage_date <= %s
    GROUP BY bd.project_id
    ORDER BY total_raw_cost DESC;
"""

GET_MONTHLY_TOTAL_RAW_COST = """
    SELECT SUM(bd.cost_before_discount) AS total
    FROM billing_data_daily bd
    JOIN projects p ON bd.project_id = p.project_id
    WHERE p.client_id = %s
      AND DATE_TRUNC('month', bd.usage_date) = %s;
"""

GET_DAILY_COSTS_BREAKDOWN_FOR_DATE_RANGE = """
    SELECT
        s.usage_date,
        s.gcp_services,
        SUM(s.agg_value) AS daily_service_total -- DIUBAH: Gunakan agg_value
    FROM billing_data_daily s
    JOIN projects p ON s.project_id = p.project_id
    WHERE p.client_id = %s
      AND s.usage_date >= %s
      AND s.usage_date <= %s
    GROUP BY s.usage_date, s.gcp_services
    ORDER BY s.usage_date, daily_service_total DESC;
"""

GET_DAILY_COSTS_PROJECT_BREAKDOWN_FOR_DATE_RANGE = """
    SELECT
        bd.usage_date,
        bd.project_id,
        SUM(bd.agg_value) AS daily_project_total -- DIUBAH: Gunakan agg_value
    FROM billing_data_daily bd
    JOIN projects p ON bd.project_id = p.project_id
    WHERE p.client_id = %s
      AND bd.usage_date >= %s
      AND bd.usage_date <= %s
    GROUP BY bd.usage_date, bd.project_id
    ORDER BY bd.usage_date, daily_project_total DESC;
"""

GET_SERVICE_BREAKDOWN_FOR_DATE_RANGE = """
    SELECT
        s.gcp_services,
        SUM(s.cost_before_discount) as total_cost,
        SUM(s.discount_total) as total_discounts, -- DIUBAH: Kolom dan nama yang benar
        SUM(s.reseller_margin) as total_reseller_margin, -- DIUBAH: Kolom dan nama yang benar
        SUM(s.agg_value) as subtotal -- DIUBAH: Subtotal adalah agg_value
    FROM billing_data_daily s
    JOIN projects p ON s.project_id = p.project_id
    WHERE p.client_id = %s
      AND s.usage_date >= %s
      AND s.usage_date <= %s
    GROUP BY s.gcp_services
    ORDER BY total_cost DESC;
"""

GET_DAILY_SERVICE_BREAKDOWN_PER_PROJECT = """
  SELECT
    DATE(bd.usage_date) as day,
    bd.gcp_services,
    SUM(bd.agg_value) as total
  FROM billing_data_daily bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE bd.project_id = %s
    AND p.client_id  = %s
    AND bd.usage_date BETWEEN %s AND %s
  GROUP BY day, bd.gcp_services
  ORDER BY day, total DESC;
"""
