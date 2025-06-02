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
    AND gcp_services IS NOT NULL 
  GROUP BY gcp_services 
  ORDER BY total DESC
"""

GET_PROJECT_TOTAL_COST = """
  SELECT SUM(agg_value) as total 
  FROM billing_data 
  WHERE project_id = %s 
    AND month_grouped_by_year_month = %s 
    AND gcp_services IS NULL
"""

GET_OVERALL_SERVICE_BREAKDOWN = """
  SELECT 
    bd.gcp_services, 
    SUM(bd.agg_value) AS total
  FROM billing_data bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE p.client_id = %s
    AND bd.month_grouped_by_year_month = %s
    AND bd.gcp_services IS NOT NULL
  GROUP BY bd.gcp_services
  ORDER BY total DESC
"""

GET_SERVICE_TOTAL_COST = """
  SELECT SUM(agg_value) as total 
  FROM billing_data 
  WHERE project_id = %s 
    AND month_grouped_by_year_month = %s 
    AND gcp_services IS NULL
"""

GET_BILLING_TOTAL_CURRENT = """
  SELECT SUM(bd.agg_value) AS total
  FROM billing_data bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE p.client_id = %s
    AND DATE(bd.month_grouped_by_year_month) = %s
    AND bd.gcp_services IS NULL
"""

GET_BILLING_TOTAL_LAST = """
  SELECT SUM(bd.agg_value) AS total
  FROM billing_data bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE p.client_id = %s
    AND bd.month_grouped_by_year_month = %s
    AND bd.gcp_services IS NULL
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
    AND bd.gcp_services IS NULL
  GROUP BY bd.project_id
  ORDER BY total DESC
"""

GET_LAST_N_MONTHS_TOTALS = """
  SELECT SUM(bd.agg_value) AS total, bd.month_grouped_by_year_month
  FROM billing_data bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE p.client_id = %s
    AND bd.month_grouped_by_year_month < %s -- Filter for months before the current month
    AND bd.gcp_services IS NULL
  GROUP BY bd.month_grouped_by_year_month
  ORDER BY bd.month_grouped_by_year_month DESC
  LIMIT %s; -- Get the last N months
"""

GET_CLIENT_NAME_BY_ID = """
  SELECT name FROM clients WHERE id = %s
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
