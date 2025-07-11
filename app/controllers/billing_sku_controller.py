from fastapi import APIRouter, Request, Depends, Query
from typing import Annotated, Optional
from datetime import datetime, timedelta

from app.db.connection import get_db
from app.utils.helpers import format_currency, format_usage
from app.controllers.billing_controller import _get_target_client_id
from app.db.queries.billing_queries import (
    GET_SKU_USAGE_TREND_FOR_DATE_RANGE,
    GET_SKU_USAGE_TABLE_FOR_DATE_RANGE,
)

router = APIRouter()

@router.get("/daily/sku-trend")
def get_daily_sku_trend(
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

    cursor = db.cursor()
    cursor.execute(GET_SKU_USAGE_TREND_FOR_DATE_RANGE, (target_client_id, start_date, end_date))
    rows = cursor.fetchall()
    db.close()

    sku_map = {}
    all_days = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((end_date - start_date).days + 1)]
    all_skus = sorted(list(set(row[1] for row in rows)))

    for row in rows:
        usage_date_str, sku_desc, total_usage = row[0].strftime("%Y-%m-%d"), row[1], float(row[2] or 0)
        if sku_desc not in sku_map:
            sku_map[sku_desc] = {day: 0.0 for day in all_days}
        sku_map[sku_desc][usage_date_str] += total_usage
    
    formatted_result = [{"sku": sku, "daily_usage": usage_data} for sku, usage_data in sku_map.items()]

    return {"skuTrend": formatted_result, "days": all_days, "skus": all_skus}


@router.get("/daily/sku-breakdown")
def get_daily_sku_table(
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

    cursor = db.cursor()
    cursor.execute(GET_SKU_USAGE_TABLE_FOR_DATE_RANGE, (target_client_id, start_date, end_date))
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

    return {"breakdown": breakdown}
