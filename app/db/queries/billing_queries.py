GET_CLIENT_PROJECTS = """
  SELECT 
    id, 
    project_id 
  FROM projects 
  WHERE client_id = %s
  ORDER BY project_id ASC
"""

GET_PROJECT_BREAKDOWN = """
  SELECT 
    gcp_services, 
    SUM(agg_value) as total 
  FROM billing_data 
  WHERE project_id = %s 
    AND month_grouped_by_year_month = %s 
  GROUP BY gcp_services 
  ORDER BY total DESC
"""

GET_PROJECT_TOTAL_COST = """
  SELECT SUM(agg_value) as total 
  FROM billing_data 
  WHERE project_id = %s 
    AND month_grouped_by_year_month = %s
"""

GET_OVERALL_SERVICE_BREAKDOWN = """
  SELECT 
    bd.gcp_services, 
    SUM(bd.agg_value) AS total
  FROM billing_data bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE p.client_id = %s
    AND bd.month_grouped_by_year_month = %s
  GROUP BY bd.gcp_services
  ORDER BY total DESC
"""

GET_SERVICE_TOTAL_COST = """
  SELECT SUM(agg_value) as total 
  FROM billing_data 
  WHERE project_id = %s 
    AND month_grouped_by_year_month = %s
"""

GET_BILLING_TOTAL_CURRENT = """
  SELECT SUM(bd.agg_value) AS total
  FROM billing_data bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE p.client_id = %s
    AND DATE(bd.month_grouped_by_year_month) = %s
"""

GET_BILLING_TOTAL_LAST = """
  SELECT SUM(bd.agg_value) AS total
  FROM billing_data bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE p.client_id = %s
    AND bd.month_grouped_by_year_month = %s
"""

GET_BILLING_BUDGET = """
SELECT budget_value, budget_threshold
FROM clients
WHERE id = %s
"""

UPDATE_BILLING_BUDGET = """
UPDATE clients
SET budget_value = %s, budget_threshold = %s
WHERE id = %s
"""

GET_PROJECT_TOTALS_BY_MONTH = """
  SELECT 
    bd.project_id,
    SUM(bd.agg_value) AS total
  FROM billing_data bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE p.client_id = %s
    AND bd.month_grouped_by_year_month = %s
  GROUP BY bd.project_id
  ORDER BY total DESC
"""

GET_LAST_N_MONTHS_TOTALS = """
  SELECT SUM(bd.agg_value) AS total, bd.month_grouped_by_year_month
  FROM billing_data bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE p.client_id = %s
    AND bd.month_grouped_by_year_month < %s
  GROUP BY bd.month_grouped_by_year_month
  ORDER BY bd.month_grouped_by_year_month DESC
  LIMIT %s
"""

GET_CLIENT_NAME_BY_ID = """
  SELECT name FROM clients WHERE id = %s
"""

GET_YEARLY_MONTHLY_TOTALS = """
  SELECT
    DATE_TRUNC('month', bd.month_grouped_by_year_month) as month,
    SUM(bd.agg_value) AS total
  FROM billing_data bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE p.client_id = %s
    AND EXTRACT(YEAR FROM bd.month_grouped_by_year_month) = %s
  GROUP BY month
  ORDER BY month ASC
"""

GET_YEARLY_SERVICE_TOTALS = """
  SELECT 
    bd.gcp_services, 
    SUM(bd.agg_value) AS total
  FROM billing_data bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE p.client_id = %s
    AND EXTRACT(YEAR FROM bd.month_grouped_by_year_month) = %s
  GROUP BY bd.gcp_services
  ORDER BY total DESC
"""

GET_YEAR_TO_DATE_TOTAL = """
  SELECT SUM(bd.agg_value) AS total
  FROM billing_data bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE p.client_id = %s
    AND EXTRACT(YEAR FROM bd.month_grouped_by_year_month) = %s
"""

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

GET_MONTHLY_TOTAL_AGG_VALUE = """
    SELECT SUM(bd.agg_value) AS total
    FROM billing_data bd
    JOIN projects p ON bd.project_id = p.project_id
    WHERE p.client_id = %s
      AND bd.month_grouped_by_year_month = %s;
"""

GET_DAILY_COSTS_BREAKDOWN_FOR_DATE_RANGE = """
    SELECT
        bd.usage_date,
        bd.gcp_services,
        SUM(bd.cost_before_discount) AS daily_service_total
    FROM billing_data_daily bd
    JOIN projects p ON bd.project_id = p.project_id
    WHERE p.client_id = %s
      AND bd.usage_date >= %s
      AND bd.usage_date <= %s
    GROUP BY bd.usage_date, bd.gcp_services
    ORDER BY bd.usage_date, daily_service_total DESC;
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

GET_DAILY_COSTS_PROJECT_BREAKDOWN_FOR_DATE_RANGE = """
    SELECT
        bd.usage_date,
        bd.project_id,
        SUM(bd.cost_before_discount) AS daily_project_total
    FROM billing_data_daily bd
    JOIN projects p ON bd.project_id = p.project_id
    WHERE p.client_id = %s
      AND bd.usage_date >= %s
      AND bd.usage_date <= %s
    GROUP BY bd.usage_date, bd.project_id
    ORDER BY bd.usage_date, daily_project_total DESC;
"""

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
        SUM(s.discount_total) as total_discount,
        SUM(s.promotion) as total_promotion
    FROM sku_usage_data s
    WHERE s.client_id = %s
      AND s.usage_date >= %s
      AND s.usage_date <= %s
    GROUP BY s.sku_description, s.gcp_services, s.sku_id, s.usage_unit
    ORDER BY total_cost DESC;
"""

def get_monthly_usage_query(group_by: str, month_count: int) -> str:
    placeholders = ', '.join([f"%s" for _ in range(month_count)])
    return f"""
        SELECT 
          COALESCE(b.{group_by}, 'Unspecified') AS id,
          COALESCE(b.{group_by}, 'Unspecified') AS name,
          b.month_grouped_by_year_month AS month,
          SUM(b.agg_value) AS total
        FROM billing_data b
        JOIN projects p ON b.project_id = p.project_id
        WHERE p.client_id = %s
          AND b.month_grouped_by_year_month IN ({placeholders})
        GROUP BY b.{group_by}, b.month_grouped_by_year_month
        ORDER BY name, month;
    """
