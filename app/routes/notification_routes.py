from fastapi import APIRouter
from app.controllers import notification_controller

router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"]
)

router.include_router(notification_controller.router)