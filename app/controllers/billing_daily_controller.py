from fastapi import APIRouter, Request, HTTPException, Depends, Query, status
from typing import Annotated, Optional
from datetime import datetime, timedelta, date
import calendar

from app.db.connection import get_db
from app.utils.helpers import _get_target_client_id, format_currency, get_validated_date_range 
from app.db.queries.billing_daily_queries import (
    GET_DAILY_COSTS_BREAKDOWN_FOR_DATE_RANGE,
    GET_DAILY_COSTS_PROJECT_BREAKDOWN_FOR_DATE_RANGE,
    GET_SERVICE_BREAKDOWN_FOR_DATE_RANGE,
    GET_DAILY_SERVICE_BREAKDOWN_PER_PROJECT
)
from app.db.queries.billing_queries import GET_MONTHLY_TOTAL_AGG_VALUE

router = APIRouter()

@router.get("/daily/service-breakdown")
def get_daily_service_breakdown(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    final_start_date, final_end_date = get_validated_date_range(start_date, end_date, month, year)
    
    cursor = db.cursor()
    cursor.execute(GET_DAILY_COSTS_BREAKDOWN_FOR_DATE_RANGE, (int(target_client_id), final_start_date, final_end_date))
    daily_raw_breakdown = cursor.fetchall()
    
    total_raw_from_daily = sum(float(row[2] or 0) for row in daily_raw_breakdown)

    discount_factor = 1.0
    if month and year:
        month_start_for_agg_query = final_start_date.strftime("%Y-%m-01")
        cursor.execute(GET_MONTHLY_TOTAL_AGG_VALUE, (int(target_client_id), month_start_for_agg_query))
        monthly_agg_total_row = cursor.fetchone()
        monthly_agg_total = float(monthly_agg_total_row[0] or 0)
        if total_raw_from_daily > 0 and monthly_agg_total > 0:
            discount_factor = monthly_agg_total / total_raw_from_daily
    
    db.close()

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
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    final_start_date, final_end_date = get_validated_date_range(start_date, end_date, month, year)

    cursor = db.cursor()
    cursor.execute(GET_DAILY_COSTS_PROJECT_BREAKDOWN_FOR_DATE_RANGE, (target_client_id, final_start_date, final_end_date))
    daily_raw_breakdown = cursor.fetchall()
    
    total_raw_from_daily = sum(float(row[2] or 0) for row in daily_raw_breakdown)

    discount_factor = 1.0
    if month and year:
        month_start_for_agg_query = final_start_date.strftime("%Y-%m-01")
        cursor.execute(GET_MONTHLY_TOTAL_AGG_VALUE, (target_client_id, month_start_for_agg_query))
        monthly_agg_total_row = cursor.fetchone()
        monthly_agg_total = float(monthly_agg_total_row[0] or 0)
        if total_raw_from_daily > 0 and monthly_agg_total > 0:
            discount_factor = monthly_agg_total / total_raw_from_daily
    
    db.close()

    projects_map = {}
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
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    final_start_date, final_end_date = get_validated_date_range(start_date, end_date, month, year)

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

@router.get("/daily/services-breakdown/project/{project_id}")
def get_daily_service_breakdown_for_project(
    project_id: str,
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    final_start_date, final_end_date = get_validated_date_range(start_date, end_date, month, year)

    cursor = db.cursor()
    params = (project_id, target_client_id, final_start_date, final_end_date)
    cursor.execute(GET_DAILY_SERVICE_BREAKDOWN_PER_PROJECT, params)
    rows = cursor.fetchall()
    db.close()
    
    daily_breakdown = {}
    num_days_in_range = (final_end_date - final_start_date).days + 1
    all_days = [(final_start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days_in_range)]

    for day_str in all_days:
        daily_breakdown[day_str] = {
            "date": day_str,
            "services": [],
            "total_daily_raw": 0.0
        }

    total_cost = 0.0
    for day_raw, service_name, cost_raw in rows:
        day_str = day_raw.strftime("%Y-%m-%d")
        cost = float(cost_raw or 0)
        
        if day_str in daily_breakdown:
            daily_breakdown[day_str]["services"].append({
                "service": service_name,
                "value": format_currency(cost),
                "rawValue": cost
            })
            daily_breakdown[day_str]["total_daily_raw"] += cost
            total_cost += cost


    for day_data in daily_breakdown.values():
        day_data["total_daily_formatted"] = format_currency(day_data["total_daily_raw"])

    return {
        "project_id": project_id,
        "start_date": final_start_date.strftime("%Y-%m-%d"),
        "end_date": final_end_date.strftime("%Y-%m-%d"),
        "daily_breakdown": sorted(list(daily_breakdown.values()), key=lambda x: x['date']),
        "grand_total": {
            "value": format_currency(total_cost),
            "rawValue": total_cost
        }
    }