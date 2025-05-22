from fastapi import APIRouter
from app.controllers import user_controller

router = APIRouter(
    prefix="/api/user",
    tags=["User"]
)

router.include_router(user_controller.router)
