from fastapi import APIRouter
from app.controllers import invoice_controller

router = APIRouter(
    prefix="/api/invoices",
    tags=["Invoices"]
)

router.include_router(invoice_controller.router)