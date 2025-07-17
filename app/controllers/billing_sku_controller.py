from fastapi import APIRouter, Request, Depends, Query, HTTPException, status
from typing import Annotated, Optional
from datetime import datetime, timedelta, date
import calendar
import math

from app.db.connection import get_db
from app.utils.helpers import format_currency, format_usage, _get_target_client_id
from app.db.queries.billing_sku_queries import (
    GET_SKU_COST_TREND_TOP_N,
    GET_SKU_BREAKDOWN_ALL
)

router = APIRouter()

# RE-USED HELPER (bisa juga diletakkan di file terpisah misal: app/utils/dependencies.py)
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


@router.get("/trend")
def get_daily_sku_cost_trend(
    request: Request,
    top_n: int = Query(10, ge=3, le=20),
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
    # MODIFIED: The query parameters are now dynamic based on the determined date range
    params = (int(target_client_id), final_start_date, final_end_date, top_n, int(target_client_id), final_start_date, final_end_date)
    cursor.execute(GET_SKU_COST_TREND_TOP_N, params)
    rows = cursor.fetchall()
    db.close()

    sku_map = {}
    # MODIFIED: Generate all days based on the final determined range
    num_days_in_range = (final_end_date - final_start_date).days + 1
    all_days = [(final_start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days_in_range)]
    all_skus = sorted(list(set(row[1] for row in rows)))

    for row in rows:
        usage_date_str, sku_desc, total_cost = row[0].strftime("%Y-%m-%d"), row[1], float(row[2] or 0)
        if sku_desc not in sku_map:
            sku_map[sku_desc] = {day: 0.0 for day in all_days}
        if usage_date_str in sku_map[sku_desc]:
            sku_map[sku_desc][usage_date_str] += total_cost
    
    formatted_result = [{"sku": sku, "daily_costs": cost_data} for sku, cost_data in sku_map.items()]

    return {"skuCostTrend": formatted_result, "days": all_days, "skus": all_skus}

@router.get("/breakdown")
def get_sku_breakdown_table(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    
    # NEW: Use helper to get validated date range
    final_start_date, final_end_date = _get_validated_date_range(start_date, end_date, month, year)
    
    cursor = db.cursor()
    params = (int(target_client_id), final_start_date, final_end_date)
    cursor.execute(GET_SKU_BREAKDOWN_ALL, params)
    rows = cursor.fetchall()
    db.close()

    breakdown = []
    for row in rows:
        sku_desc, service, sku_id, unit, usage, cost, discount, promo = row
        subtotal = float(cost or 0) - float(discount or 0) - float(promo or 0)
        
        breakdown.append({
            "sku": sku_desc,
            "service": service,
            "skuId": sku_id,
            "usage": format_usage(float(usage or 0), unit),
            "cost": format_currency(float(cost or 0)),
            "discounts": format_currency(float(discount or 0)),
            "promotions": format_currency(float(promo or 0)),
            "subtotal": format_currency(subtotal),
            "rawSubtotal": subtotal
        })

    return {"data": breakdown}
