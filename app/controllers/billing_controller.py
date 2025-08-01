from fastapi import APIRouter, Request, HTTPException, Depends, Query
from typing import Annotated, Optional,List
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.connection import get_db
from app.utils.helpers import format_currency, _get_target_client_id
from app.db.queries.billing_queries import (
    GET_CLIENT_PROJECTS,
    GET_PROJECT_BREAKDOWN,
    GET_PROJECT_TOTAL_COST,
    GET_OVERALL_SERVICE_BREAKDOWN,
    GET_BILLING_TOTAL_CURRENT,
    GET_BILLING_TOTAL_LAST,
    GET_BILLING_BUDGET,
    GET_PROJECT_TOTALS_BY_MONTH,
    GET_CLIENT_NAME_BY_ID,
    GET_YEARLY_MONTHLY_TOTALS,
    GET_YEARLY_SERVICE_TOTALS,
    GET_YEAR_TO_DATE_TOTAL,
    get_monthly_usage_query,
    GET_BILLING_BUDGET_VALUE,
    UPDATE_BUDGET_SETTINGS
)

router = APIRouter()

class BudgetSettingsSchema(BaseModel):
    budget_value: float
    alert_thresholds: List[int]  
    alert_emails: List[str]  

@router.get("/projects")
def get_client_projects(
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
def get_overall_service_breakdown(
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

    total = sum(item["rawValue"] for item in breakdown)

    return {
        "breakdown": breakdown,
        "total": {
            "value": format_currency(total),
            "rawValue": total
        }
    }


@router.get("/breakdown/{project_id}")
def get_project_breakdown(
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
def get_billing_summary(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    
    now = datetime.now()
    current_year = now.year
    current_month_date = now.replace(day=1).date()
    last_month_date = (current_month_date - timedelta(days=1)).replace(day=1)

    cursor = db.cursor()
    
    # Ambil data pengeluaran (tidak berubah)
    cursor.execute(GET_BILLING_TOTAL_CURRENT, (target_client_id, current_month_date))
    current_value = float(cursor.fetchone()[0] or 0)
    
    cursor.execute(GET_BILLING_TOTAL_LAST, (target_client_id, last_month_date))
    last_value = float(cursor.fetchone()[0] or 0)
    
    cursor.execute(GET_YEAR_TO_DATE_TOTAL, (target_client_id, current_year))
    year_to_date_total_raw = float(cursor.fetchone()[0] or 0)

    cursor.execute(GET_BILLING_BUDGET_VALUE, (target_client_id,))
    result = cursor.fetchone()
    db.close()

    percentage_change = 0 if last_value == 0 else ((current_value - last_value) / last_value) * 100
    budget_value = float(result[0]) if result and result[0] is not None else 0
    
    budget_percentage = round((current_value / budget_value) * 100) if budget_value > 0 else 0
    label = f"{budget_percentage}% dari budget"

    return {
        "currentMonth": {"value": format_currency(current_value), "rawValue": current_value, "percentageChange": f"{percentage_change:.1f}"},
        "lastMonth": {"value": format_currency(last_value), "rawValue": last_value, "label": "Periode sebelumnya"},
        "yearToDateTotal": {"value": format_currency(year_to_date_total_raw), "rawValue": year_to_date_total_raw, "label": f"Total Biaya Tahun {current_year}"},
        "budget": {"value": format_currency(budget_value), "rawValue": budget_value, "percentage": budget_percentage, "label": label}
    }
@router.get("/project-total")
def get_project_totals_by_month(
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

@router.post("/budget-settings") 
def update_budget_settings(
    payload: BudgetSettingsSchema,
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    print("Received payload:", payload)  # DEBUG
    target_client_id = _get_target_client_id(request, clientId)
    cursor = db.cursor()
    cursor.execute(
        UPDATE_BUDGET_SETTINGS,
        (payload.budget_value, payload.alert_thresholds, payload.alert_emails, target_client_id)
    )
    db.commit()
    db.close()
    return {"message": "Budget settings updated successfully."}


@router.get("/budget-settings")
def get_budget_settings(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    
    from app.db.queries.billing_queries import GET_BUDGET_SETTINGS

    cursor = db.cursor()
    cursor.execute(GET_BUDGET_SETTINGS, (target_client_id,))
    result = cursor.fetchone()
    db.close()

    if not result:
        return {"budgetValue": 0, "alertThresholds": [], "alertEmails": []}

    return {
        "budgetValue": float(result[0] or 0),
        "alertThresholds": result[1] or [],
        "alertEmails": result[2] or []
    }

@router.get("/monthly")
def get_monthly_usage(
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

def get_client_name_from_billing_controller( 
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
    
@router.get("/yearly-summary")
def get_yearly_summary(
    request: Request,
    year: int = Query(default_factory=lambda: datetime.now().year),
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)
    
    cursor = db.cursor()

    cursor.execute(GET_YEARLY_MONTHLY_TOTALS, (target_client_id, year))
    monthly_rows = cursor.fetchall()
    
    monthly_costs_map = {i: 0 for i in range(1, 13)}
    for row in monthly_rows:
        month_number = row[0].month
        monthly_costs_map[month_number] = float(row[1] or 0)

    monthly_costs = [
        {"month": datetime(year, month_num, 1).strftime("%B"), "total": total_cost}
        for month_num, total_cost in monthly_costs_map.items()
    ]

    cursor.execute(GET_YEARLY_SERVICE_TOTALS, (target_client_id, year))
    service_rows = cursor.fetchall()
    
    service_costs = [{
        "service": row[0],
        "total": {
            "value": format_currency(float(row[1] or 0)),
            "rawValue": float(row[1] or 0)
        }
    } for row in service_rows]

    db.close()

    grand_total_raw = sum(item["total"]["rawValue"] for item in service_costs)

    return {
        "year": year,
        "monthlyCosts": monthly_costs,
        "serviceCosts": service_costs,
        "grandTotal": {
            "value": format_currency(grand_total_raw),
            "rawValue": grand_total_raw
        }
    }