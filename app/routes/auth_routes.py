from fastapi import APIRouter
from app.controllers import auth_controller

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"]
)

router.include_router(auth_controller.router)
