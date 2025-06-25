from fastapi import APIRouter
from app.controllers import billing_controller

router = APIRouter(
    prefix="/api/billing",
    tags=["Billing"]
)

router.include_router(billing_controller.router)
