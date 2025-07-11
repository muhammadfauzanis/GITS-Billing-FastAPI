from fastapi import APIRouter, Request, HTTPException, Depends, Query
from typing import Annotated, Optional
from datetime import datetime, timedelta

from app.db.connection import get_db
from app.utils.helpers import format_currency
from app.controllers.billing_controller import _get_target_client_id
from app.db.queries.billing_queries import (
    GET_MONTHLY_TOTAL_AGG_VALUE,
    GET_DAILY_COSTS_BREAKDOWN_FOR_DATE_RANGE,
    GET_MONTHLY_TOTAL_RAW_COST,
    GET_DAILY_COSTS_PROJECT_BREAKDOWN_FOR_DATE_RANGE
)

router = APIRouter()

@router.get("/daily/service-breakdown")
def get_daily_service_breakdown(
    request: Request,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(default_factory=lambda: datetime.now().year),
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    
    start_date = datetime(year, month, 1).date()
    next_month = start_date.replace(day=28) + timedelta(days=4)
    end_date = next_month - timedelta(days=next_month.day)
    month_start_for_agg_query = start_date.strftime("%Y-%m-01")

    cursor = db.cursor()

    cursor.execute(GET_DAILY_COSTS_BREAKDOWN_FOR_DATE_RANGE, (target_client_id, start_date, end_date))
    daily_raw_breakdown = cursor.fetchall()
    
    total_raw_from_daily = sum(float(row[2] or 0) for row in daily_raw_breakdown)

    cursor.execute(GET_MONTHLY_TOTAL_AGG_VALUE, (target_client_id, month_start_for_agg_query))
    monthly_agg_total_row = cursor.fetchone()
    monthly_agg_total = float(monthly_agg_total_row[0] or 0)
    db.close()

    discount_factor = 1.0
    if total_raw_from_daily > 0 and monthly_agg_total > 0:
        discount_factor = monthly_agg_total / total_raw_from_daily

    all_days_in_month = [start_date + timedelta(days=i) for i in range((end_date - start_date).days + 1)]
    
    breakdown_map = {day.strftime("%Y-%m-%d"): {"services": [], "total": 0.0} for day in all_days_in_month}
    
    all_services = sorted(list(set(row[1] for row in daily_raw_breakdown)))

    for row in daily_raw_breakdown:
        usage_date_str, service_name, raw_cost = row[0].strftime("%Y-%m-%d"), row[1], float(row[2] or 0)
        approximated_cost = raw_cost * discount_factor
        
        if usage_date_str in breakdown_map:
            breakdown_map[usage_date_str]["services"].append({"service": service_name, "cost": approximated_cost})
            breakdown_map[usage_date_str]["total"] += approximated_cost

    formatted_result = [{"date": date, **data} for date, data in breakdown_map.items()]

    return {"dailyBreakdown": formatted_result, "services": all_services}

@router.get("/daily/project-breakdown")
def get_daily_project_breakdown(
    request: Request,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(default_factory=lambda: datetime.now().year),
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    
    start_date = datetime(year, month, 1).date()
    next_month = start_date.replace(day=28) + timedelta(days=4)
    end_date = next_month - timedelta(days=next_month.day)
    month_start_for_agg_query = start_date.strftime("%Y-%m-01")

    cursor = db.cursor()

    cursor.execute(GET_DAILY_COSTS_PROJECT_BREAKDOWN_FOR_DATE_RANGE, (target_client_id, start_date, end_date))
    daily_raw_breakdown = cursor.fetchall()
    
    total_raw_from_daily = sum(float(row[2] or 0) for row in daily_raw_breakdown)
    cursor.execute(GET_MONTHLY_TOTAL_AGG_VALUE, (target_client_id, month_start_for_agg_query))
    monthly_agg_total_row = cursor.fetchone()
    monthly_agg_total = float(monthly_agg_total_row[0] or 0)
    db.close()

    discount_factor = 1.0
    if total_raw_from_daily > 0 and monthly_agg_total > 0:
        discount_factor = monthly_agg_total / total_raw_from_daily

    projects_map = {}
    all_days = [ (start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end_date - start_date).days + 1) ]

    for row in daily_raw_breakdown:
        usage_date_str, project_id, raw_cost = row[0].strftime("%Y-%m-%d"), row[1], float(row[2] or 0)
        
        if project_id not in projects_map:
            projects_map[project_id] = {day: 0.0 for day in all_days}
        
        approximated_cost = raw_cost * discount_factor
        projects_map[project_id][usage_date_str] += approximated_cost

    formatted_result = [
        {"project": project_id, "daily_costs": costs}
        for project_id, costs in projects_map.items()
    ]

    return {"projectTrend": formatted_result, "days": all_days}
