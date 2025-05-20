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

GET_BILLING_TOTAL_CURRENT = """
  SELECT SUM(bd.agg_value) AS total
  FROM billing_data bd
  JOIN projects p ON bd.project_id = p.project_id
  WHERE p.client_id = %s
    AND bd.month_grouped_by_year_month = %s
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
