from fastapi import APIRouter, Request, HTTPException, Depends, Query, status
from typing import Annotated, Optional
from datetime import datetime, timedelta, date
import calendar

from app.db.connection import get_db
from app.utils.helpers import format_currency, _get_target_client_id
from app.db.queries.billing_daily_queries import (
    GET_DAILY_COSTS_BREAKDOWN_FOR_DATE_RANGE,
    GET_DAILY_COSTS_PROJECT_BREAKDOWN_FOR_DATE_RANGE,
    GET_SERVICE_BREAKDOWN_FOR_DATE_RANGE
)
from app.db.queries.billing_queries import GET_MONTHLY_TOTAL_AGG_VALUE

router = APIRouter()

def _get_validated_date_range(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    max_days: int = 31
) -> tuple[date, date]:
    """Helper function to validate and determine the date range."""
    if start_date and end_date:
        if (end_date - start_date).days >= max_days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Custom date range cannot exceed {max_days} days."
            )
        return start_date, end_date
    
    if month and year:
        final_start_date = date(year, month, 1)
        _, num_days_in_month = calendar.monthrange(year, month)
        final_end_date = date(year, month, num_days_in_month)
        return final_start_date, final_end_date

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="You must provide either 'month' and 'year', or 'start_date' and 'end_date'."
    )


@router.get("/daily/service-breakdown")
def get_daily_service_breakdown(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None),
    # MODIFIED: Parameters are now optional to allow for custom date ranges
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    
    # NEW: Use helper to get validated date range
    final_start_date, final_end_date = _get_validated_date_range(start_date, end_date, month, year)
    
    cursor = db.cursor()
    cursor.execute(GET_DAILY_COSTS_BREAKDOWN_FOR_DATE_RANGE, (int(target_client_id), final_start_date, final_end_date))
    daily_raw_breakdown = cursor.fetchall()
    
    total_raw_from_daily = sum(float(row[2] or 0) for row in daily_raw_breakdown)

    # MODIFIED: Discount factor is only calculated for full month view
    discount_factor = 1.0
    if month and year: # Only calculate if it's a monthly view
        month_start_for_agg_query = final_start_date.strftime("%Y-%m-01")
        cursor.execute(GET_MONTHLY_TOTAL_AGG_VALUE, (int(target_client_id), month_start_for_agg_query))
        monthly_agg_total_row = cursor.fetchone()
        monthly_agg_total = float(monthly_agg_total_row[0] or 0)
        if total_raw_from_daily > 0 and monthly_agg_total > 0:
            discount_factor = monthly_agg_total / total_raw_from_daily
    
    db.close()

    # MODIFIED: Generate all days based on the final determined range
    num_days_in_range = (final_end_date - final_start_date).days + 1
    all_days_in_range = [final_start_date + timedelta(days=i) for i in range(num_days_in_range)]
    breakdown_map = {day.strftime("%Y-%m-%d"): {"services": [], "total": 0.0} for day in all_days_in_range}
    
    for row in daily_raw_breakdown:
        usage_date_str, service_name, raw_cost = row[0].strftime("%Y-%m-%d"), row[1], float(row[2] or 0)
        approximated_cost = raw_cost * discount_factor
        
        if usage_date_str in breakdown_map:
            breakdown_map[usage_date_str]["services"].append({
                "service": service_name, 
                "cost": approximated_cost
            })
            breakdown_map[usage_date_str]["total"] += approximated_cost

    formatted_result = [{"date": date, **data} for date, data in breakdown_map.items()]
    all_services = sorted(list(set(row[1] for row in daily_raw_breakdown)))

    return {"dailyBreakdown": formatted_result, "services": all_services}


@router.get("/daily/project-breakdown")
def get_daily_project_breakdown(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None),
    # MODIFIED: Parameters are now optional
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    
    # NEW: Use helper to get validated date range
    final_start_date, final_end_date = _get_validated_date_range(start_date, end_date, month, year)

    cursor = db.cursor()
    cursor.execute(GET_DAILY_COSTS_PROJECT_BREAKDOWN_FOR_DATE_RANGE, (target_client_id, final_start_date, final_end_date))
    daily_raw_breakdown = cursor.fetchall()
    
    total_raw_from_daily = sum(float(row[2] or 0) for row in daily_raw_breakdown)

    # MODIFIED: Discount factor is only calculated for full month view
    discount_factor = 1.0
    if month and year: # Only calculate if it's a monthly view
        month_start_for_agg_query = final_start_date.strftime("%Y-%m-01")
        cursor.execute(GET_MONTHLY_TOTAL_AGG_VALUE, (target_client_id, month_start_for_agg_query))
        monthly_agg_total_row = cursor.fetchone()
        monthly_agg_total = float(monthly_agg_total_row[0] or 0)
        if total_raw_from_daily > 0 and monthly_agg_total > 0:
            discount_factor = monthly_agg_total / total_raw_from_daily
    
    db.close()

    projects_map = {}
    # MODIFIED: Generate all days based on the final determined range
    num_days_in_range = (final_end_date - final_start_date).days + 1
    all_days = [ (final_start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days_in_range) ]

    for row in daily_raw_breakdown:
        usage_date_str, project_id, raw_cost = row[0].strftime("%Y-%m-%d"), row[1], float(row[2] or 0)
        
        if project_id not in projects_map:
            projects_map[project_id] = {day: 0.0 for day in all_days}
        
        approximated_cost = raw_cost * discount_factor
        if usage_date_str in projects_map[project_id]:
            projects_map[project_id][usage_date_str] += approximated_cost

    formatted_result = [
        {"project": project_id, "daily_costs": costs}
        for project_id, costs in projects_map.items()
    ]

    return {"projectTrend": formatted_result, "days": all_days}


@router.get("/daily/total/service-breakdown")
def get_month_to_date_service_breakdown(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None),
    # MODIFIED: Added optional date parameters for flexibility
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    
    # NEW: Flexible date logic
    if start_date and end_date:
        final_start_date, final_end_date = start_date, end_date
    elif month and year:
        final_start_date = date(year, month, 1)
        _, num_days_in_month = calendar.monthrange(year, month)
        final_end_date = date(year, month, num_days_in_month)
    else:
        # Default behavior: current month-to-date
        today = datetime.now().date()
        final_start_date = today.replace(day=1)
        final_end_date = today

    cursor = db.cursor()
    cursor.execute(GET_SERVICE_BREAKDOWN_FOR_DATE_RANGE, (int(target_client_id), final_start_date, final_end_date))
    rows = cursor.fetchall()
    db.close()

    breakdown = []
    for row in rows:
        service, cost, discount, promo = row
        cost_float = float(cost or 0)
        discount_float = float(discount or 0)
        promo_float = float(promo or 0)
        subtotal = cost_float - discount_float - promo_float
        
        breakdown.append({
            "service": service,
            "cost": format_currency(cost_float),
            "discounts": format_currency(discount_float),
            "promotions": format_currency(promo_float),
            "subtotal": format_currency(subtotal),
            "rawSubtotal": subtotal
        })

    return {"breakdown": breakdown}