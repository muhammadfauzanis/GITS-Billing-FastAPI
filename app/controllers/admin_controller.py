from fastapi import APIRouter, Request, Depends, HTTPException
from typing import Annotated, Optional, List
from app.db.connection import get_db
from pydantic import BaseModel
from datetime import date
from app.db.queries.admin_queries import (
    GET_ALL_CLIENT_NAMES,
    GET_ALL_USERS_INFO,
    DELETE_USER_BY_ID,
    CHECK_USER_EXISTS_BY_ID,
    UPDATE_USER_CLIENT_ID,
    GET_CLIENTS_COUNT,
    GET_CONTRACTS_STATS,
    GET_INVOICES_STATS,
    GET_UPCOMING_RENEWALS,
    GET_RECENT_INVOICES,
)
from app.db.queries.gw_contracts_queries import GET_ALL_GW_CLIENTS

router = APIRouter()


class UpdateUserClientSchema(BaseModel):
    clientId: Optional[int]


class DashboardStatsSchema(BaseModel):
    totalClients: int
    totalActiveContracts: int
    expiringSoonContracts: int
    pendingInvoicesCount: int
    overdueInvoicesCount: int


class UpcomingRenewalSchema(BaseModel):
    id: str
    client_name: str
    end_date: date
    type: str


class RecentInvoiceSchema(BaseModel):
    id: int
    invoice_number: str
    client_name: str
    total_amount: float
    status: str
    due_date: Optional[date]


class AdminDashboardResponse(BaseModel):
    stats: DashboardStatsSchema
    upcomingRenewals: List[UpcomingRenewalSchema]
    recentInvoices: List[RecentInvoiceSchema]


@router.get("/clients")
def get_all_clients(request: Request, db: Annotated = Depends(get_db)):
    if request.state.user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()
    cursor.execute(GET_ALL_CLIENT_NAMES)
    results = cursor.fetchall()

    clients = [{"id": row[0], "name": row[1]} for row in results]
    return {"clients": clients}


@router.get("/dashboard-summary", response_model=AdminDashboardResponse)
def get_admin_dashboard_summary(request: Request, db: Annotated = Depends(get_db)):
    if request.state.user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()

    # Get stats
    cursor.execute(GET_CLIENTS_COUNT)
    total_clients = cursor.fetchone()[0]

    cursor.execute(GET_CONTRACTS_STATS)
    contracts_stats = cursor.fetchone()
    total_active_contracts, expiring_soon_contracts = contracts_stats

    cursor.execute(GET_INVOICES_STATS)
    invoices_stats = cursor.fetchone()
    pending_invoices_count, overdue_invoices_count = invoices_stats

    stats = DashboardStatsSchema(
        totalClients=total_clients,
        totalActiveContracts=total_active_contracts,
        expiringSoonContracts=expiring_soon_contracts,
        pendingInvoicesCount=pending_invoices_count,
        overdueInvoicesCount=overdue_invoices_count,
    )

    # Get upcoming renewals
    cursor.execute(GET_UPCOMING_RENEWALS)
    upcoming_renewals_raw = cursor.fetchall()
    upcoming_renewals = [
        UpcomingRenewalSchema(
            id=str(row[0]), client_name=row[1], end_date=row[2], type=row[3]
        )
        for row in upcoming_renewals_raw
    ]

    # Get recent invoices
    cursor.execute(GET_RECENT_INVOICES)
    recent_invoices_raw = cursor.fetchall()
    recent_invoices = [
        RecentInvoiceSchema(
            id=row[0],
            invoice_number=row[1],
            client_name=row[2],
            total_amount=float(row[3] or 0),
            status=row[4],
            due_date=row[5],
        )
        for row in recent_invoices_raw
    ]

    db.close()

    return AdminDashboardResponse(
        stats=stats, upcomingRenewals=upcoming_renewals, recentInvoices=recent_invoices
    )


@router.get("/gw-clients")
def get_all_gw_clients(request: Request, db: Annotated = Depends(get_db)):
    if request.state.user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()
    cursor.execute(GET_ALL_GW_CLIENTS)
    results = cursor.fetchall()
    db.close()

    clients = [{"id": row[0], "name": row[1]} for row in results]
    return {"clients": clients}


@router.get("/users")
def get_all_users(request: Request, db: Annotated = Depends(get_db)):
    role = request.state.user.get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()
    cursor.execute(GET_ALL_USERS_INFO)
    results = cursor.fetchall()

    users = []
    for row in results:
        id, email, role, client_name, is_password_set, created_at = row
        users.append(
            {
                "id": id,
                "email": email,
                "role": role,
                "client": client_name or "-",
                "status": "Aktif" if is_password_set else "Nonaktif",
                "createdAt": created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return {"users": users}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, request: Request, db: Annotated = Depends(get_db)):
    role = request.state.user.get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()
    cursor.execute(CHECK_USER_EXISTS_BY_ID, (user_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    cursor.execute(DELETE_USER_BY_ID, (user_id,))
    db.commit()

    return {"message": f"User with ID {user_id} has been deleted successfully."}


@router.patch("/users/{user_id}")
def update_user_client_id(
    user_id: int,
    payload: UpdateUserClientSchema,
    request: Request,
    db: Annotated = Depends(get_db),
):
    role = request.state.user.get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()

    cursor.execute(CHECK_USER_EXISTS_BY_ID, (user_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    cursor.execute(UPDATE_USER_CLIENT_ID, (payload.clientId, user_id))
    db.commit()

    return {"message": "ClientId updated successfully", "clientId": payload.clientId}
