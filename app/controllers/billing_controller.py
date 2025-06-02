from fastapi import APIRouter, Request, HTTPException, Depends, Query
from typing import Annotated, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.connection import get_db
from app.utils.helpers import format_currency, calculate_projection_moving_average
from app.db.queries.billing_queries import (
    GET_CLIENT_PROJECTS,
    GET_PROJECT_BREAKDOWN,
    GET_PROJECT_TOTAL_COST,
    GET_OVERALL_SERVICE_BREAKDOWN,
    GET_BILLING_TOTAL_CURRENT,
    GET_BILLING_TOTAL_LAST,
    GET_BILLING_BUDGET,
    GET_PROJECT_TOTALS_BY_MONTH,
    GET_LAST_N_MONTHS_TOTALS,
    GET_CLIENT_NAME_BY_ID,
    UPDATE_BILLING_BUDGET,
    get_monthly_usage_query,
)

router = APIRouter()

def _get_target_client_id(request: Request, provided_client_id: Optional[str]) -> str:
    user_details = request.state.user
    user_role = user_details.get("role")
    user_client_id = user_details.get("clientId")

    if user_role == "admin":
        if provided_client_id:
            return provided_client_id
        else:
            raise HTTPException(status_code=400, detail="Admin must specify a clientId for this operation.")
    else: # Role 'client'
        if not user_client_id:
            raise HTTPException(status_code=401, detail="Unauthorized: Client ID not found in token.")
        if provided_client_id and provided_client_id != str(user_client_id):
            raise HTTPException(status_code=403, detail="Forbidden: Clients can only access their own data.")
        return str(user_client_id)

@router.get("/projects")
def get_client_projects_route(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    user_details = request.state.user
    target_client_id_for_query: Optional[str] = None

    if user_details.get("role") == "admin":
        if clientId:
            target_client_id_for_query = clientId
        else:
            return {"projects": []}
    elif user_details.get("role") == "client":
        target_client_id_for_query = user_details.get("clientId")
        if not target_client_id_for_query:
            raise HTTPException(status_code=401, detail="Unauthorized: Client ID not found for client user.")
        if clientId and clientId != str(target_client_id_for_query):
             raise HTTPException(status_code=403, detail="Forbidden: You can only access your own projects.")

    if not target_client_id_for_query:
        return {"projects": []}

    cursor = db.cursor()
    cursor.execute(GET_CLIENT_PROJECTS, (target_client_id_for_query,))
    projects = cursor.fetchall()
    db.close()
    return {"projects": [{"id": row[0], "projectId": row[1]} for row in projects]}

@router.get("/breakdown/services")
def get_overall_service_breakdown_route(
    request: Request,
    month: str = Query(...),
    year: str = Query(default_factory=lambda: str(datetime.now().year)),
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    query_month = f"{year}-{str(month).zfill(2)}-01"

    cursor = db.cursor()
    cursor.execute(GET_OVERALL_SERVICE_BREAKDOWN, (target_client_id, query_month))
    rows = cursor.fetchall()
    db.close()

    breakdown = [{
        "service": row[0],
        "value": format_currency(float(row[1] or 0)),
        "rawValue": float(row[1] or 0)
    } for row in rows]
    return breakdown

@router.get("/breakdown/{project_id}")
def get_project_breakdown_route(
    project_id: str,
    request: Request,
    db: Annotated = Depends(get_db),
    month: str = Query(...),
    year: str = Query(default_factory=lambda: str(datetime.now().year)),
    clientId: Optional[str] = Query(None)
):
    _ = _get_target_client_id(request, clientId) 

    if not project_id or not month:
        raise HTTPException(status_code=400, detail="projectId and month are required")

    query_month = f"{year}-{str(month).zfill(2)}-01"

    cursor = db.cursor()
    cursor.execute(GET_PROJECT_BREAKDOWN, (project_id, query_month))
    breakdown_rows = cursor.fetchall()

    cursor.execute(GET_PROJECT_TOTAL_COST, (project_id, query_month))
    total_row = cursor.fetchone()
    db.close()

    breakdown = [{
        "service": row[0],
        "value": format_currency(float(row[1] or 0)),
        "rawValue": float(row[1] or 0)
    } for row in breakdown_rows]
    total = float(total_row[0] or 0)

    return {
        "breakdown": breakdown,
        "total": {"value": format_currency(total), "rawValue": total}
    }

@router.get("/summary")
def get_billing_summary_route(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)

    now = datetime.now()
    current_month_date = now.replace(day=1).date()
    last_month_date = (current_month_date - timedelta(days=1)).replace(day=1)

    cursor = db.cursor()
    cursor.execute(GET_BILLING_TOTAL_CURRENT, (target_client_id, current_month_date))
    current_value = float(cursor.fetchone()[0] or 0)

    cursor.execute(GET_BILLING_TOTAL_LAST, (target_client_id, last_month_date))
    last_value = float(cursor.fetchone()[0] or 0)

    num_months_for_projection = 3
    cursor.execute(GET_LAST_N_MONTHS_TOTALS, (target_client_id, current_month_date, num_months_for_projection))
    historical_rows = cursor.fetchall()
    historical_data = [float(row[0]) for row in historical_rows if row[0] is not None]

    percentage_change = 0 if last_value == 0 else ((current_value - last_value) / last_value) * 100
    days_in_month = (current_month_date.replace(month=current_month_date.month % 12 + 1, day=1) - timedelta(days=1)).day
    current_day = min(now.day, days_in_month)

    projection = calculate_projection_moving_average(
        current_value, current_day, days_in_month, historical_data, num_months_for_average=num_months_for_projection
    )

    cursor.execute(GET_BILLING_BUDGET, (target_client_id,))
    result = cursor.fetchone()
    db.close()
    
    budget_value = float(result[0]) if result and result[0] is not None else 0
    budget_threshold = int(result[1]) if result and result[1] is not None else 80
    budget_percentage = round((current_value / budget_value) * 100) if budget_value > 0 else 0

    return {
        "currentMonth": {"value": format_currency(current_value), "rawValue": current_value, "percentageChange": f"{percentage_change:.1f}"},
        "lastMonth": {"value": format_currency(last_value), "rawValue": last_value, "label": "Periode sebelumnya"},
        "projection": {"value": format_currency(projection), "rawValue": projection, "label": "Estimasi akhir bulan"},
        "budget": {"value": format_currency(budget_value), "rawValue": budget_value, "percentage": budget_percentage, "label": f"{budget_percentage}% dari budget"}
    }

@router.get("/project-total")
def get_project_totals_by_month_route(
    request: Request,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(default_factory=lambda: datetime.now().year),
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    query_month = f"{year}-{str(month).zfill(2)}-01"

    cursor = db.cursor()
    cursor.execute(GET_PROJECT_TOTALS_BY_MONTH, (target_client_id, query_month))
    rows = cursor.fetchall()
    db.close()

    breakdown = [{"service": row[0], "value": format_currency(float(row[1] or 0)), "rawValue": float(row[1] or 0)} for row in rows]
    total = sum(item["rawValue"] for item in breakdown)
    return {"breakdown": breakdown, "total": {"value": format_currency(total), "rawValue": total}}

class BillingSettings(BaseModel):
    budget_value: Optional[float] = None
    budget_threshold: Optional[int] = None

@router.patch("/budget")
def update_billing_settings_route(
    payload: BillingSettings,
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)

    if payload.budget_value is None and payload.budget_threshold is None:
        raise HTTPException(status_code=400, detail="At least one field (budget_value or budget_threshold) must be provided")

    updates = []
    values = []

    if payload.budget_value is not None:
        updates.append("budget_value = %s")
        values.append(payload.budget_value)
    if payload.budget_threshold is not None:
        updates.append("budget_threshold = %s")
        values.append(payload.budget_threshold)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    values.append(target_client_id)
    query = f"UPDATE clients SET {', '.join(updates)} WHERE id = %s"

    cursor = db.cursor()
    cursor.execute(query, tuple(values))
    db.commit()
    db.close()
    return {"message": "Billing settings updated successfully"}

@router.get("/budget")
def get_billing_settings_route(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    cursor = db.cursor()
    cursor.execute(GET_BILLING_BUDGET, (target_client_id,))
    result = cursor.fetchone()
    db.close()

    if not result:
        return {"budgetValue": 0.0, "budgetThreshold": 80}

    return {"budgetValue": float(result[0] or 0), "budgetThreshold": int(result[1] or 0)}

@router.get("/monthly")
def get_monthly_usage_route(
    request: Request,
    groupBy: str = Query(default="service", pattern="^(service|project)$"),
    months: int = Query(default=6, ge=1, le=24),
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    now = datetime.now()
    date_params = [(now.replace(day=1) - timedelta(days=30 * i)).strftime("%Y-%m-01") for i in range(months)]

    query = get_monthly_usage_query("project_id" if groupBy == "project" else "gcp_services", len(date_params))

    cursor = db.cursor()
    cursor.execute(query, (target_client_id, *date_params))
    rows = cursor.fetchall()
    db.close()

    month_labels = [datetime.strptime(m, "%Y-%m-01").strftime("%B %Y") for m in reversed(date_params)]

    grouped = {}
    for row in rows:
        key_id = str(row[0])
        key_name = str(row[1])
        month_label_from_db = row[2].strftime("%B %Y")
        cost = float(row[3] or 0)

        if key_id not in grouped:
            grouped[key_id] = {"id": key_id, "name": key_name, "months": {label: 0 for label in month_labels}}
        
        if month_label_from_db in grouped[key_id]["months"]:
             grouped[key_id]["months"][month_label_from_db] = cost

    return {"data": list(grouped.values()), "months": month_labels}

def get_client_name_from_billing_controller_route( 
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    user_details = request.state.user
    target_client_id_for_query: Optional[str] = None
    default_name = "Nama Client Tidak Ditemukan"

    if user_details.get("role") == "admin":
        if clientId:
            target_client_id_for_query = clientId
        else:
            return {"name": "Admin View"} 
    elif user_details.get("role") == "client":
        target_client_id_for_query = user_details.get("clientId")
        if not target_client_id_for_query:
            raise HTTPException(status_code=401, detail="Unauthorized: Client ID not found for client user.")
        if clientId and clientId != str(target_client_id_for_query):
            raise HTTPException(status_code=403, detail="Forbidden: Clients can only access their own data.")
    
    if not target_client_id_for_query:
        return {"name": default_name}

    try:
        cursor = db.cursor()
        cursor.execute(GET_CLIENT_NAME_BY_ID, (target_client_id_for_query,))
        result = cursor.fetchone()
        db.close()
        if result and result[0]:
            return {"name": result[0]}
        else:
            return {"name": f"Client (ID: {target_client_id_for_query})"}
    except Exception as e:
        return {"name": default_name}