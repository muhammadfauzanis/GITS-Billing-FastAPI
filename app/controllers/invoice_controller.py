from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from typing import Annotated, Optional, List
from app.db.connection import get_db
from app.db.queries.invoice_queries import (
    GET_INVOICES_BY_CLIENT_ID,
    GET_INVOICE_DETAILS_BY_ID,
    UPDATE_INVOICE_STATUS,
    COUNT_INVOICES_FOR_ADMIN,
    GET_PAGINATED_INVOICES_FOR_ADMIN,
    ADMIN_UPDATE_INVOICE_DETAILS,
)
from app.middleware.auth_middleware import supabase
from app.utils.helpers import format_currency, _get_target_client_id
from weasyprint import HTML
from pydantic import BaseModel
from typing import Literal
from datetime import date
from collections import defaultdict
import locale
from math import ceil

try:
    locale.setlocale(locale.LC_TIME, "id_ID.UTF-8")
except locale.Error:
    locale.setlocale(locale.LC_TIME, "")

router = APIRouter()


class UpdateStatusPayload(BaseModel):
    status: Literal["pending", "paid", "overdue", "failed"]


class AdminUpdateInvoiceSchema(BaseModel):
    status: Literal["pending", "paid", "overdue", "failed", "canceled"]
    payment_date: Optional[date] = None
    payment_notes: Optional[str] = None


class AdminInvoiceItem(BaseModel):
    id: int
    invoice_number: str
    client_name: str
    invoice_period: date
    due_date: Optional[date]
    total_amount: float
    status: str
    proof_of_payment_url: Optional[str]


class GroupedInvoices(BaseModel):
    month: str
    invoices: List[AdminInvoiceItem]


class PaginationResponse(BaseModel):
    total_items: int
    total_pages: int
    current_page: int
    limit: int


class PaginatedGroupedInvoicesResponse(BaseModel):
    pagination: PaginationResponse
    data: List[GroupedInvoices]


@router.post("/generate-pdf")
async def generate_pdf_from_html(request: Request):
    try:
        html_content = await request.body()
        if not html_content:
            raise HTTPException(status_code=400, detail="HTML content is missing.")
        pdf_bytes = HTML(string=html_content.decode("utf-8")).write_pdf()
        return Response(content=pdf_bytes, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


@router.get("/admin/all", response_model=PaginatedGroupedInvoicesResponse)
def get_all_invoices_for_admin(
    request: Request,
    db: Annotated = Depends(get_db),
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    clientId: Optional[int] = Query(None),
):
    if request.state.user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()
    filter_params = (status, status, clientId, clientId, month, month, year, year)

    cursor.execute(COUNT_INVOICES_FOR_ADMIN, filter_params)
    total_items = cursor.fetchone()[0]
    total_pages = ceil(total_items / limit)

    offset = (page - 1) * limit
    paginated_params = (*filter_params, limit, offset)
    cursor.execute(GET_PAGINATED_INVOICES_FOR_ADMIN, paginated_params)
    invoices_raw = cursor.fetchall()
    db.close()

    grouped_invoices = defaultdict(list)
    for row in invoices_raw:
        invoice_item = AdminInvoiceItem(
            id=row[0],
            invoice_number=row[1],
            client_name=row[2],
            invoice_period=row[3],
            due_date=row[4],
            total_amount=float(row[5] or 0),
            status=row[6],
            proof_of_payment_url=row[7],
        )
        month_key = row[3].strftime("%B %Y")
        grouped_invoices[month_key].append(invoice_item)

    grouped_data = [
        GroupedInvoices(month=month, invoices=invoices)
        for month, invoices in grouped_invoices.items()
    ]

    # Langkah 4: Susun respons akhir
    return PaginatedGroupedInvoicesResponse(
        pagination=PaginationResponse(
            total_items=total_items,
            total_pages=total_pages,
            current_page=page,
            limit=limit,
        ),
        data=grouped_data,
    )


@router.patch("/admin/{invoice_id}/details")
def admin_update_invoice_details(
    invoice_id: int,
    payload: AdminUpdateInvoiceSchema,
    request: Request,
    db: Annotated = Depends(get_db),
):
    if request.state.user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    try:
        cursor = db.cursor()
        cursor.execute(
            ADMIN_UPDATE_INVOICE_DETAILS,
            (payload.status, payload.payment_date, payload.payment_notes, invoice_id),
        )
        if cursor.rowcount == 0:
            db.rollback()
            raise HTTPException(status_code=404, detail="Invoice not found.")
        db.commit()
        return {"message": "Invoice details updated successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@router.get("/")
def get_client_invoices(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None),
):
    target_client_id = _get_target_client_id(request, clientId)
    cursor = db.cursor()
    cursor.execute(GET_INVOICES_BY_CLIENT_ID, (target_client_id,))
    invoices_raw = cursor.fetchall()
    db.close()
    invoices = [
        {
            "id": row[0],
            "invoiceNumber": row[1],
            "period": row[2].strftime("%B %Y"),
            "total": format_currency(float(row[3] or 0)),
            "dueDate": row[4].strftime("%Y-%m-%d") if row[4] else None,
            "status": row[5],
            "createdAt": row[6].strftime("%Y-%m-%d"),
        }
        for row in invoices_raw
    ]
    return {"invoices": invoices}


@router.get("/{invoice_id}/view")
def get_invoice_view_url(
    invoice_id: int,
    request: Request,
    db: Annotated = Depends(get_db),
):
    user_details = request.state.user
    cursor = db.cursor()
    cursor.execute(GET_INVOICE_DETAILS_BY_ID, (invoice_id,))
    invoice_data = cursor.fetchone()
    db.close()
    if not invoice_data:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    invoice_storage_path = invoice_data[1]
    invoice_client_id = invoice_data[2]
    is_admin = user_details.get("role") == "admin"
    user_client_id = user_details.get("clientId")
    if not is_admin and str(user_client_id) != str(invoice_client_id):
        raise HTTPException(
            status_code=403, detail="Forbidden: You do not have access to this invoice."
        )
    try:
        signed_url_response = supabase.storage.from_("invoices").create_signed_url(
            invoice_storage_path, 60
        )
        return {"url": signed_url_response.get("signedURL")}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Could not generate invoice URL: {str(e)}"
        )


@router.patch("/{invoice_id}/status")
def update_invoice_status(
    invoice_id: int,
    payload: UpdateStatusPayload,
    request: Request,
    db: Annotated = Depends(get_db),
):
    if request.state.user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")
    cursor = db.cursor()
    cursor.execute(UPDATE_INVOICE_STATUS, (payload.status, invoice_id))
    db.commit()
    if cursor.rowcount == 0:
        db.close()
        raise HTTPException(status_code=404, detail="Invoice not found.")
    db.close()
    return {
        "message": "Invoice status updated successfully.",
        "newStatus": payload.status,
    }
