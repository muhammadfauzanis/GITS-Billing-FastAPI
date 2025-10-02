import os
from urllib.parse import urlparse
import httpx
import locale
from math import ceil
from datetime import date
from collections import defaultdict
from typing import Annotated, Optional, List, Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    BackgroundTasks,
    status,
)
from pydantic import BaseModel
from weasyprint import HTML

from app.db.connection import get_db
from app.db.queries import invoice_queries
from app.middleware.auth_middleware import supabase
from app.utils.helpers import format_currency, _get_target_client_id

try:
    locale.setlocale(locale.LC_TIME, "id_ID.UTF-8")
except locale.Error:
    locale.setlocale(locale.LC_TIME, "")

N8N_SEND_INVOICE_WEBHOOK_URL = os.getenv("N8N_SEND_INVOICE_WEBHOOK_URL")
router = APIRouter()


class RejectInvoicePayload(BaseModel):
    reason: str


class ApproveAllPayload(BaseModel):
    invoice_ids: List[int]


class AdminUpdatePaymentSchema(BaseModel):
    status: Literal["pending", "paid", "overdue", "failed", "canceled"]
    payment_date: Optional[date] = None
    payment_notes: Optional[str] = None
    proof_of_payment_url: Optional[str] = None


class AdminInvoiceItem(BaseModel):
    id: int
    invoice_number: str
    client_name: str
    invoice_period: date
    due_date: Optional[date]
    total_amount: float
    status: str
    approval_status: str
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


async def trigger_send_invoice_workflow(invoice_id: int):
    INTERNAL_API_KEY = os.getenv("INTERNAL_API_KEY")

    if not N8N_SEND_INVOICE_WEBHOOK_URL or not INTERNAL_API_KEY:
        print(
            f"CRITICAL: N8N_SEND_INVOICE_WEBHOOK_URL or INTERNAL_API_KEY is not set. Cannot send invoice {invoice_id}."
        )
        return

    try:
        headers = {"X-API-KEY": INTERNAL_API_KEY}

        async with httpx.AsyncClient() as client:
            response = await client.post(
                N8N_SEND_INVOICE_WEBHOOK_URL,
                json={"invoice_id": invoice_id},
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
            print(f"Successfully triggered n8n send workflow for invoice {invoice_id}")

    except httpx.RequestError as e:
        print(f"Failed to trigger n8n workflow for invoice {invoice_id}: {e}")
    except httpx.HTTPStatusError as e:
        print(
            f"n8n send workflow returned an error for invoice {invoice_id}: {e.response.status_code}"
        )


def get_current_admin_user_id(request: Request) -> int:
    user_details = request.state.user
    if user_details.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )
    return user_details.get("id")


@router.post("/admin/{invoice_id}/approve")
async def approve_invoice(
    invoice_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Annotated[any, Depends(get_db)],
):
    admin_user_id = get_current_admin_user_id(request)
    cursor = db.cursor()
    try:
        cursor.execute(
            invoice_queries.GET_INVOICE_APPROVAL_STATUS_AND_CLIENT_ID, (invoice_id,)
        )
        invoice = cursor.fetchone()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found."
            )
        if invoice[0] != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invoice is not in 'draft' status. Current status: {invoice[0]}",
            )

        cursor.execute(invoice_queries.APPROVE_INVOICE, (admin_user_id, invoice_id))
        if cursor.rowcount == 0:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Failed to approve invoice. It may have been processed already.",
            )
        db.commit()

        background_tasks.add_task(trigger_send_invoice_workflow, invoice_id)
        return {"message": f"Invoice {invoice_id} approved and is being sent."}
    finally:
        cursor.close()
        db.close()


@router.post("/admin/{invoice_id}/reject")
def reject_invoice(
    invoice_id: int,
    payload: RejectInvoicePayload,
    request: Request,
    db: Annotated[any, Depends(get_db)],
):
    admin_user_id = get_current_admin_user_id(request)
    cursor = db.cursor()
    try:
        cursor.execute(
            invoice_queries.GET_INVOICE_APPROVAL_STATUS_AND_CLIENT_ID, (invoice_id,)
        )
        invoice = cursor.fetchone()

        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found."
            )
        if invoice[0] != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only draft invoices can be rejected.",
            )

        cursor.execute(
            invoice_queries.REJECT_INVOICE, (admin_user_id, payload.reason, invoice_id)
        )
        if cursor.rowcount == 0:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Failed to reject invoice."
            )
        db.commit()
        return {"message": f"Invoice {invoice_id} has been rejected."}
    finally:
        cursor.close()
        db.close()


@router.post("/admin/approve-all")
async def approve_all_invoices(
    payload: ApproveAllPayload,
    request: Request,
    background_tasks: BackgroundTasks,
):
    admin_user_id = get_current_admin_user_id(request)
    approved_ids, errors = [], []

    for invoice_id in payload.invoice_ids:
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(
                invoice_queries.GET_INVOICE_APPROVAL_STATUS_AND_CLIENT_ID, (invoice_id,)
            )
            invoice = cursor.fetchone()
            if not invoice or invoice[0] != "draft":
                errors.append({"id": invoice_id, "error": "Not a draft or not found."})
                continue

            cursor.execute(invoice_queries.APPROVE_INVOICE, (admin_user_id, invoice_id))
            if cursor.rowcount > 0:
                conn.commit()
                background_tasks.add_task(trigger_send_invoice_workflow, invoice_id)
                approved_ids.append(invoice_id)
            else:
                conn.rollback()
                errors.append(
                    {
                        "id": invoice_id,
                        "error": "Update failed, possibly already processed.",
                    }
                )
        except Exception as e:
            conn.rollback()
            errors.append({"id": invoice_id, "error": str(e)})
        finally:
            cursor.close()
            conn.close()

    return {
        "message": "Bulk approval process finished.",
        "approved_count": len(approved_ids),
        "error_count": len(errors),
        "errors": errors,
    }


@router.get("/admin/all", response_model=PaginatedGroupedInvoicesResponse)
def get_all_invoices_for_admin(
    request: Request,
    db: Annotated[any, Depends(get_db)],
    page: int = Query(1, ge=1),
    limit: int = Query(15, ge=1),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    approval_status: Optional[str] = Query(None),
    clientId: Optional[int] = Query(None),
):
    get_current_admin_user_id(request)
    cursor = db.cursor()
    try:
        filter_params = (
            status,
            status,
            approval_status,
            approval_status,
            clientId,
            clientId,
            month,
            month,
            year,
            year,
        )
        cursor.execute(invoice_queries.COUNT_INVOICES_FOR_ADMIN, filter_params)
        total_items = cursor.fetchone()[0]
        total_pages = ceil(total_items / limit)

        offset = (page - 1) * limit
        paginated_params = (*filter_params, limit, offset)
        cursor.execute(
            invoice_queries.GET_PAGINATED_INVOICES_FOR_ADMIN, paginated_params
        )
        invoices_raw = cursor.fetchall()
    finally:
        cursor.close()
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
            approval_status=row[7],
            proof_of_payment_url=row[8],
        )
        month_key = row[3].strftime("%B %Y")
        grouped_invoices[month_key].append(invoice_item)

    grouped_data = [
        GroupedInvoices(month=month, invoices=invoices)
        for month, invoices in grouped_invoices.items()
    ]

    return PaginatedGroupedInvoicesResponse(
        pagination=PaginationResponse(
            total_items=total_items,
            total_pages=total_pages,
            current_page=page,
            limit=limit,
        ),
        data=grouped_data,
    )


@router.patch("/admin/{invoice_id}/payment-details")
def admin_update_payment_details(
    invoice_id: int,
    payload: AdminUpdatePaymentSchema,
    request: Request,
    db: Annotated[any, Depends(get_db)],
):
    get_current_admin_user_id(request)
    cursor = db.cursor()
    try:
        params = (
            payload.status,
            payload.payment_date,
            payload.payment_notes,
            payload.proof_of_payment_url,
            invoice_id,
        )
        cursor.execute(invoice_queries.ADMIN_UPDATE_PAYMENT_DETAILS, params)
        if cursor.rowcount == 0:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found."
            )
        db.commit()
        return {"message": "Invoice payment details updated successfully."}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )
    finally:
        cursor.close()
        db.close()


@router.get("/")
def get_client_invoices(
    request: Request,
    db: Annotated[any, Depends(get_db)],
    clientId: Optional[str] = Query(None),
):
    target_client_id = _get_target_client_id(request, clientId)
    cursor = db.cursor()
    try:
        cursor.execute(invoice_queries.GET_INVOICES_BY_CLIENT_ID, (target_client_id,))
        invoices_raw = cursor.fetchall()
    finally:
        cursor.close()
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
    invoice_id: int, request: Request, db: Annotated[any, Depends(get_db)]
):
    user_details = request.state.user
    cursor = db.cursor()
    try:
        cursor.execute(invoice_queries.GET_INVOICE_DETAILS_BY_ID, (invoice_id,))
        invoice_data = cursor.fetchone()
    finally:
        cursor.close()
        db.close()

    if not invoice_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found."
        )

    storage_path_url, invoice_client_id = invoice_data[1], invoice_data[2]
    is_admin = user_details.get("role") == "admin"
    user_client_id = user_details.get("clientId")

    if not is_admin and str(user_client_id) != str(invoice_client_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: You do not have access to this invoice.",
        )

    return {"url": storage_path_url}


@router.post("/generate-pdf")
async def generate_pdf_from_html(request: Request):
    try:
        html_content = await request.body()
        if not html_content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="HTML content is missing.",
            )

        pdf_bytes = HTML(string=html_content.decode("utf-8")).write_pdf()
        return Response(content=pdf_bytes, media_type="application/pdf")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {str(e)}",
        )


@router.post("/admin/generate-all-invoices")
async def trigger_all_invoices_generation(request: Request):
    if request.state.user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
        )

    webhook_url = os.getenv("N8N_GENERATE_INVOICES_WEBHOOK_URL")
    api_key = os.getenv("INTERNAL_API_KEY")

    if not webhook_url or not api_key:
        print("CRITICAL: N8N_GENERATE_INVOICES_WEBHOOK_URL or N8N_API_KEY is not set.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook configuration is missing on the server.",
        )

    try:
        headers = {"X-API-KEY": api_key}
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, headers=headers, timeout=15.0)
            response.raise_for_status()

    except httpx.RequestError as e:
        print(f"Error calling n8n generate-invoices webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not connect to the invoice generation service.",
        )
    except httpx.HTTPStatusError as e:
        print(
            f"n8n generate-invoices webhook returned an error: {e.response.status_code}"
        )
        if e.response.status_code == 403:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Authentication failed with the invoice service. Check API Key.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The invoice generation service returned an error: {e.response.status_code}",
        )

    return {"message": "Process to generate all invoices has been started."}
