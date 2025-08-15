from fastapi import APIRouter
from app.controllers import admin_controller, contracts_controller, settings_controller

router = APIRouter(prefix="/api/admin", tags=["Admin"])

router.include_router(admin_controller.router)
router.include_router(
    contracts_controller.router, prefix="/contracts", tags=["Contracts"]
)
router.include_router(
    settings_controller.router, prefix="/settings", tags=["Contracts"]
)
