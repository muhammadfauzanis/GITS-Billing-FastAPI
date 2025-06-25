from fastapi import APIRouter
from app.controllers import admin_controller

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin"]
)

router.include_router(admin_controller.router)
