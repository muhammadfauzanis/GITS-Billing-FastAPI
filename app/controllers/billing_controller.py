from fastapi import APIRouter, Request, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from app.db.connection import get_db
from app.utils.helpers import format_currency, calculate_projection
from app.db.queries.billing_queries import (
    GET_CLIENT_PROJECTS,
    GET_PROJECT_BREAKDOWN,
    GET_PROJECT_TOTAL_COST,
    GET_OVERALL_SERVICE_BREAKDOWN,
    GET_BILLING_TOTAL_CURRENT,
    GET_BILLING_TOTAL_LAST,
    GET_BILLING_BUDGET,
    GET_PROJECT_TOTALS_BY_MONTH,
    UPDATE_BILLING_BUDGET,
    get_monthly_usage_query
)
from typing import Annotated
from datetime import datetime, timedelta
from pydantic import BaseModel

router = APIRouter()

@router.get("/projects")
def get_client_projects(request: Request, db: Annotated = Depends(get_db)):
    client_id = request.state.user.get("clientId")
    if not client_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    cursor = db.cursor()
    cursor.execute(GET_CLIENT_PROJECTS, (client_id,))
    projects = cursor.fetchall()

    return {"projects": [{"id": row[0], "projectId": row[1]} for row in projects]}

@router.get("/breakdown/services")
def get_overall_service_breakdown(
    request: Request,
    month: str = Query(...),
    year: str = Query(default=str(datetime.now().year)),
    db: Annotated = Depends(get_db)
):
    client_id = request.state.user.get("clientId")
    if not month:
        raise HTTPException(status_code=400, detail="month is required")

    query_month = f"{year}-{str(month).zfill(2)}-01"

    cursor = db.cursor()
    cursor.execute(GET_OVERALL_SERVICE_BREAKDOWN, (client_id, query_month))
    rows = cursor.fetchall()

    breakdown = [{
        "service": row[0],
        "value": format_currency(float(row[1])),
        "rawValue": float(row[1])
    } for row in rows]

    return breakdown

@router.get("/breakdown/{project_id}")
def get_project_breakdown(
    project_id: str,
    month: str = Query(...),
    year: str = Query(default=str(datetime.now().year)),
    db: Annotated = Depends(get_db)
):
    if not project_id or not month:
        raise HTTPException(status_code=400, detail="projectId and month are required")

    query_month = f"{year}-{str(month).zfill(2)}-01"

    cursor = db.cursor()
    cursor.execute(GET_PROJECT_BREAKDOWN, (project_id, query_month))
    breakdown_rows = cursor.fetchall()

    cursor.execute(GET_PROJECT_TOTAL_COST, (project_id, query_month))
    total_row = cursor.fetchone()

    breakdown = [{
        "service": row[0],
        "value": format_currency(float(row[1])),
        "rawValue": float(row[1])
    } for row in breakdown_rows]

    total = float(total_row[0] or 0)

    return {
        "breakdown": breakdown,
        "total": {
            "value": format_currency(total),
            "rawValue": total
        }
    }

@router.get("/summary")
def get_billing_summary(request: Request, db: Annotated = Depends(get_db)):
    client_id = request.state.user.get("clientId")
    now = datetime.now()
    current_month_date = now.replace(day=1).date()
    last_month_date = (current_month_date - timedelta(days=1)).replace(day=1)

    cursor = db.cursor()
    cursor.execute(GET_BILLING_TOTAL_CURRENT, (client_id, current_month_date))
    current_value = float(cursor.fetchone()[0] or 0)

    cursor.execute(GET_BILLING_TOTAL_LAST, (client_id, last_month_date))
    last_value = float(cursor.fetchone()[0] or 0)

    percentage_change = 0 if last_value == 0 else ((current_value - last_value) / last_value) * 100
    days_in_month = (current_month_date.replace(month=current_month_date.month % 12 + 1, day=1) - timedelta(days=1)).day
    current_day = min(now.day, days_in_month)
    projection = calculate_projection(current_value, current_day, days_in_month)

    cursor.execute(GET_BILLING_BUDGET, (client_id,))
    result = cursor.fetchone()
    budget_value = float(result[0]) if result and result[0] is not None else 1500000
    budget_threshold = int(result[1]) if result and result[1] is not None else 80
    budget_percentage = round((current_value / budget_value) * 100) if budget_value else 0


    return {
        "currentMonth": {
            "value": format_currency(current_value),
            "rawValue": current_value,
            "percentageChange": f"{percentage_change:.1f}"
        },
        "lastMonth": {
            "value": format_currency(last_value),
            "rawValue": last_value,
            "label": "Periode sebelumnya"
        },
        "projection": {
            "value": format_currency(projection),
            "rawValue": projection,
            "label": "Estimasi akhir bulan"
        },
        "budget": {
            "value": format_currency(budget_value),
            "rawValue": budget_value,
            "percentage": budget_percentage,
            "label": f"{budget_percentage}% dari budget"
        }
    }

@router.get("/project-total")
def get_project_totals_by_month(
    request: Request,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(default=datetime.now().year),
    db: Annotated = Depends(get_db)
):
    client_id = request.state.user.get("clientId")
    if not client_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    query_month = f"{year}-{str(month).zfill(2)}-01"

    cursor = db.cursor()
    cursor.execute(GET_PROJECT_TOTALS_BY_MONTH, (client_id, query_month))
    rows = cursor.fetchall()

    breakdown = [
        {
            "service": row[0],  # ini adalah project_id
            "value": format_currency(float(row[1])),
            "rawValue": float(row[1])
        }
        for row in rows
    ]

    total = sum(item["rawValue"] for item in breakdown)

    return {
        "breakdown": breakdown,
        "total": {
            "value": format_currency(total),
            "rawValue": total
        }
    }


class BillingSettings(BaseModel):
    budget_value: float | None = None
    budget_threshold: int | None = None


@router.patch("/budget")
def update_billing_settings(
    payload: BillingSettings,
    request: Request,
    db: Annotated = Depends(get_db)
):
    client_id = request.state.user.get("clientId")

    if payload.budget_value is None and payload.budget_threshold is None:
        raise HTTPException(status_code=400, detail="At least one field must be provided")

    updates = []
    values = []

    if payload.budget_value is not None:
        updates.append("budget_value = %s")
        values.append(payload.budget_value)

    if payload.budget_threshold is not None:
        updates.append("budget_threshold = %s")
        values.append(payload.budget_threshold)

    values.append(client_id)

    query = f"""
        UPDATE clients
        SET {", ".join(updates)}
        WHERE id = %s
    """

    cursor = db.cursor()
    cursor.execute(query, tuple(values))
    db.commit()

    return {"message": "Billing settings updated successfully"}


@router.get("/budget")
def get_billing_settings(
    request: Request,
    db: Annotated = Depends(get_db)
):
    client_id = request.state.user.get("clientId")

    cursor = db.cursor()
    cursor.execute(GET_BILLING_BUDGET, (client_id,))
    result = cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Client budget not found")

    return {
        "budgetValue": float(result[0]),
        "budgetThreshold": int(result[1])
    }


@router.get("/monthly")
def get_monthly_usage(
    request: Request,
    groupBy: str = Query(default="service"),
    months: int = Query(default=12),
    db: Annotated = Depends(get_db)
):
    client_id = request.state.user.get("clientId")
    now = datetime.now()
    date_params = []

    for i in range(months):
        date = now.replace(day=1) - timedelta(days=30 * i)
        date_params.append(date.strftime("%Y-%m-01"))

    query = get_monthly_usage_query(
        "project_id" if groupBy == "project" else "gcp_services",
        len(date_params)
    )

    cursor = db.cursor()
    cursor.execute(query, (client_id, *date_params))
    rows = cursor.fetchall()

    month_labels = [
        datetime.strptime(m, "%Y-%m-01").strftime("%B %Y")
        for m in date_params
    ]

    grouped = {}
    for row in rows:
        key = row[0]
        if key not in grouped:
            grouped[key] = {"id": row[0], "name": row[1], "months": {}}
        label = row[2].strftime("%B %Y")
        grouped[key]["months"][label] = float(row[3])

    for item in grouped.values():
        for label in month_labels:
            item["months"].setdefault(label, 0)

    return {
        "data": list(grouped.values()),
        "months": month_labels
    }
