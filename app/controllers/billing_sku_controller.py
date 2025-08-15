# Ganti seluruh file controller Anda dengan kode ini

from fastapi import APIRouter, Request, Depends, Query
from typing import Annotated, Optional
from datetime import date, timedelta

from app.db.connection import get_db
from app.utils.helpers import (
    _get_target_client_id,
    get_validated_date_range,
    format_currency,
    format_usage,
)
from app.db.queries.billing_sku_queries import (
    GET_SKU_COST_TREND_TOP_N,
    GET_SKU_BREAKDOWN_ALL,
    GET_SKU_COST_TREND_TOP_N_PER_PROJECT,
    GET_SKU_BREAKDOWN_PER_PROJECT,
)

router = APIRouter()


@router.get("/trend")
def get_daily_sku_cost_trend(
    # ... (Tidak ada perubahan di endpoint ini, sudah benar)
    request: Request,
    top_n: int = Query(10, ge=3, le=20),
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    target_client_id = _get_target_client_id(request, clientId)
    final_start_date, final_end_date = get_validated_date_range(
        start_date, end_date, month, year
    )

    cursor = db.cursor()
    params = (
        int(target_client_id),
        final_start_date,
        final_end_date,
        top_n,
        int(target_client_id),
        final_start_date,
        final_end_date,
    )
    cursor.execute(GET_SKU_COST_TREND_TOP_N, params)
    rows = cursor.fetchall()
    db.close()

    sku_map = {}
    num_days_in_range = (final_end_date - final_start_date).days + 1
    all_days = [
        (final_start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(num_days_in_range)
    ]
    all_skus = sorted(list(set(row[1] for row in rows)))

    for sku_desc in all_skus:
        sku_map[sku_desc] = {day: 0.0 for day in all_days}

    for row in rows:
        usage_date_str, sku_desc, total_cost = (
            row[0].strftime("%Y-%m-%d"),
            row[1],
            float(row[2] or 0),
        )
        if usage_date_str in sku_map[sku_desc]:
            sku_map[sku_desc][usage_date_str] = total_cost

    formatted_result = [
        {"sku": sku, "daily_costs": cost_data} for sku, cost_data in sku_map.items()
    ]

    return {"skuCostTrend": formatted_result, "days": all_days, "skus": all_skus}


@router.get("/breakdown")
def get_sku_breakdown_table(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    target_client_id = _get_target_client_id(request, clientId)
    final_start_date, final_end_date = get_validated_date_range(
        start_date, end_date, month, year
    )

    cursor = db.cursor()
    params = (int(target_client_id), final_start_date, final_end_date)
    cursor.execute(GET_SKU_BREAKDOWN_ALL, params)
    rows = cursor.fetchall()
    db.close()

    breakdown = []
    for row in rows:
        sku_desc, service, sku_id, unit, usage, cost, discount, promo, subtotal = row

        breakdown.append(
            {
                "sku": sku_desc,
                "service": service,
                "skuId": sku_id,
                "usage": format_usage(float(usage or 0), unit),
                # DIUBAH: Kolom "cost" sekarang diisi dengan nilai subtotal (biaya akhir)
                "cost": format_currency(float(subtotal or 0)),
                "discounts": format_currency(float(discount or 0)),
                "promotions": format_currency(float(promo or 0)),
                "subtotal": format_currency(float(subtotal or 0)),
                "rawSubtotal": float(subtotal or 0),
            }
        )

    return {"data": breakdown}


@router.get("/trend/project/{project_id}")
def get_daily_sku_cost_trend_for_project(
    # ... (Tidak ada perubahan di endpoint ini, sudah benar)
    project_id: str,
    request: Request,
    top_n: int = Query(10, ge=3, le=20),
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    target_client_id = _get_target_client_id(request, clientId)
    final_start_date, final_end_date = get_validated_date_range(
        start_date, end_date, month, year
    )

    cursor = db.cursor()
    params = (
        int(target_client_id),
        project_id,
        final_start_date,
        final_end_date,
        top_n,
        int(target_client_id),
        project_id,
        final_start_date,
        final_end_date,
    )
    cursor.execute(GET_SKU_COST_TREND_TOP_N_PER_PROJECT, params)
    rows = cursor.fetchall()
    db.close()

    sku_map = {}
    num_days_in_range = (final_end_date - final_start_date).days + 1
    all_days = [
        (final_start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(num_days_in_range)
    ]
    all_skus = sorted(list(set(row[1] for row in rows)))

    for sku_desc in all_skus:
        sku_map[sku_desc] = {day: 0.0 for day in all_days}

    for row in rows:
        usage_date_str, sku_desc, total_cost = (
            row[0].strftime("%Y-%m-%d"),
            row[1],
            float(row[2] or 0),
        )
        if usage_date_str in sku_map[sku_desc]:
            sku_map[sku_desc][usage_date_str] = total_cost

    formatted_result = [
        {"sku": sku, "daily_costs": cost_data} for sku, cost_data in sku_map.items()
    ]

    return {"skuCostTrend": formatted_result, "days": all_days, "skus": all_skus}


@router.get("/breakdown/project/{project_id}")
def get_sku_breakdown_table_for_project(
    project_id: str,
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    target_client_id = _get_target_client_id(request, clientId)
    final_start_date, final_end_date = get_validated_date_range(
        start_date, end_date, month, year
    )

    cursor = db.cursor()
    params = (int(target_client_id), project_id, final_start_date, final_end_date)
    cursor.execute(GET_SKU_BREAKDOWN_PER_PROJECT, params)
    rows = cursor.fetchall()
    db.close()

    breakdown = []
    for row in rows:
        sku_desc, service, sku_id, unit, usage, cost, discount, promo, subtotal = row

        breakdown.append(
            {
                "sku": sku_desc,
                "service": service,
                "skuId": sku_id,
                "usage": format_usage(float(usage or 0), unit),
                # DIUBAH: Kolom "cost" sekarang diisi dengan nilai subtotal (biaya akhir)
                "cost": format_currency(float(subtotal or 0)),
                "discounts": format_currency(float(discount or 0)),
                "promotions": format_currency(float(promo or 0)),
                "subtotal": format_currency(float(subtotal or 0)),
                "rawSubtotal": float(subtotal or 0),
            }
        )

    return {"data": breakdown}
