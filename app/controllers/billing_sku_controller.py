from fastapi import APIRouter, Request, Depends, Query
from typing import Annotated, Optional
from datetime import datetime, timedelta
import calendar
import math

from app.db.connection import get_db
from app.utils.helpers import format_currency, format_usage, _get_target_client_id
from app.db.queries.billing_sku_queries import (
    GET_SKU_COST_TREND_TOP_N,
    GET_SKU_BREAKDOWN_ALL
)

router = APIRouter()

@router.get("/trend")
def get_daily_sku_cost_trend(
    request: Request,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(default_factory=lambda: datetime.now().year),
    top_n: int = Query(10, ge=3, le=20),
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    start_date = datetime(year, month, 1).date()
    _, num_days_in_month = calendar.monthrange(year, month)
    end_date = datetime(year, month, num_days_in_month).date()

    cursor = db.cursor()
    params = (int(target_client_id), start_date, end_date, top_n, int(target_client_id), start_date, end_date)
    cursor.execute(GET_SKU_COST_TREND_TOP_N, params)
    rows = cursor.fetchall()
    db.close()

    sku_map = {}
    all_days = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(num_days_in_month)]
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
    month: int = Query(..., ge=1, le=12),
    year: int = Query(default_factory=lambda: datetime.now().year),
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    """
    Menyediakan data untuk tabel rincian SKU tanpa paginasi.
    """
    target_client_id = _get_target_client_id(request, clientId)
    start_date = datetime(year, month, 1).date()
    _, num_days_in_month = calendar.monthrange(year, month)
    end_date = datetime(year, month, num_days_in_month).date()
    
    cursor = db.cursor()
    params = (int(target_client_id), start_date, end_date)
    cursor.execute(GET_SKU_BREAKDOWN_ALL, params) # Menggunakan kueri baru
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