from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from typing import Annotated, Optional
from app.db.connection import get_db
from app.db.queries.invoice_queries import GET_INVOICES_BY_CLIENT_ID, GET_INVOICE_DETAILS_BY_ID, UPDATE_INVOICE_STATUS
from app.middleware.auth_middleware import supabase
from app.utils.helpers import format_currency
from app.controllers.billing_controller import _get_target_client_id
from weasyprint import HTML
from pydantic import BaseModel
from typing import Literal

router = APIRouter()

class UpdateStatusPayload(BaseModel):
    status: Literal['pending', 'paid', 'overdue', 'failed']

# generate invoice to pdf on n8n
@router.post("/generate-pdf")
async def generate_pdf_from_html(request: Request):
    try:
        html_content = await request.body()
        
        if not html_content:
            raise HTTPException(status_code=400, detail="HTML content is missing.")

        pdf_bytes = HTML(string=html_content.decode('utf-8')).write_pdf()

        return Response(
            content=pdf_bytes,
            media_type="application/pdf"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")
    
@router.get("/")
def get_client_invoices(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None)
):
    target_client_id = _get_target_client_id(request, clientId)

    cursor = db.cursor()
    cursor.execute(GET_INVOICES_BY_CLIENT_ID, (target_client_id,))
    invoices_raw = cursor.fetchall()
    db.close()

    invoices = [{
        "id": row[0],
        "invoiceNumber": row[1],
        "period": row[2].strftime("%B %Y"),
        "total": format_currency(float(row[3] or 0)),
        "dueDate": row[4].strftime("%Y-%m-%d") if row[5] else None,
        "status": row[5],
        "createdAt": row[6].strftime("%Y-%m-%d")
    } for row in invoices_raw]

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

    if user_details.get("role") != "admin" and str(user_details.get("clientId")) != str(invoice_client_id):
        raise HTTPException(status_code=403, detail="Forbidden: You do not have access to this invoice.")

    try:
        # Ganti "invoices" dengan nama bucket Anda
        signed_url_response = supabase.storage.from_("invoices").create_signed_url(invoice_storage_path, 60)

        if 'error' in signed_url_response and signed_url_response['error']:
             raise Exception(signed_url_response['error'])

        return {"url": signed_url_response['signedURL']}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not generate invoice URL: {str(e)}")
    
@router.patch("/{invoice_id}/status")
def update_invoice_status(
    invoice_id: int,
    payload: UpdateStatusPayload,
    request: Request,
    db: Annotated = Depends(get_db)
):
    # Hanya admin yang boleh mengubah status
    if request.state.user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()
    cursor.execute(UPDATE_INVOICE_STATUS, (payload.status, invoice_id))
    db.commit()

    if cursor.rowcount == 0:
        db.close()
        raise HTTPException(status_code=404, detail="Invoice not found.")

    db.close()
    return {"message": "Invoice status updated successfully.", "newStatus": payload.status}