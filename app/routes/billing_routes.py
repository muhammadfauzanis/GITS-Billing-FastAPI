from fastapi import APIRouter
from app.controllers import billing_controller, billing_daily_controller,billing_sku_controller

router = APIRouter(
    prefix="/api/billing",
    tags=["Billing"]
)

router.include_router(billing_controller.router)
router.include_router(billing_daily_controller.router)
router.include_router(billing_sku_controller.router, prefix="/sku", tags=["SKU Usage"])