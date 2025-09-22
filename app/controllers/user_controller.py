from fastapi import APIRouter, Request, Depends, HTTPException, Query, status
from typing import Annotated, Optional
from app.db.connection import get_db
from pydantic import BaseModel, Field

from app.db.queries.user_queries import (
    GET_CLIENT_NAME_BY_ID,
    GET_USER_PROFILE_BY_ID,
    UPDATE_USER_WHATSAPP,
)

router = APIRouter()


class UserProfileSchema(BaseModel):
    email: str
    client_name: str
    whatsapp_number: Optional[str] = None


class UpdateProfileSchema(BaseModel):
    whatsapp_number: Optional[str] = Field(None, max_length=20)


@router.get("/client-name")
def get_client_name(
    request: Request,
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None),
):
    user_details = request.state.user
    user_role = user_details.get("role")

    target_client_id = None

    if user_role == "admin":
        if not clientId:
            raise HTTPException(
                status_code=400, detail="Admin must provide a clientId."
            )
        target_client_id = clientId
    else:
        target_client_id = user_details.get("clientId")

    if not target_client_id:
        raise HTTPException(
            status_code=401, detail="Unauthorized or Client ID not specified."
        )

    cursor = db.cursor()
    cursor.execute(GET_CLIENT_NAME_BY_ID, (target_client_id,))
    result = cursor.fetchone()
    db.close()

    if not result:
        raise HTTPException(status_code=404, detail="Client not found")

    return {"clientId": target_client_id, "name": result[0]}


@router.get("/profile", response_model=UserProfileSchema)
def get_user_profile(request: Request, db: Annotated = Depends(get_db)):
    user_id = request.state.user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated"
        )

    cursor = db.cursor()
    cursor.execute(GET_USER_PROFILE_BY_ID, (user_id,))
    profile_data = cursor.fetchone()
    db.close()

    if not profile_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User profile not found"
        )

    email, client_name, whatsapp_number_from_db = profile_data

    whatsapp_number_to_send = None
    if whatsapp_number_from_db and whatsapp_number_from_db.endswith("@c.us"):
        whatsapp_number_to_send = whatsapp_number_from_db.removesuffix("@c.us")
    else:
        whatsapp_number_to_send = whatsapp_number_from_db

    return UserProfileSchema(
        email=email,
        client_name=client_name,
        whatsapp_number=whatsapp_number_to_send,
    )


@router.patch("/profile")
def update_user_profile(
    payload: UpdateProfileSchema, request: Request, db: Annotated = Depends(get_db)
):
    user_id = request.state.user.get("id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not authenticated"
        )

    whatsapp_number_to_save = None
    if payload.whatsapp_number:
        cleaned_number = "".join(filter(str.isdigit, payload.whatsapp_number))
        if cleaned_number:
            whatsapp_number_to_save = f"{cleaned_number}@c.us"

    cursor = db.cursor()
    cursor.execute(UPDATE_USER_WHATSAPP, (whatsapp_number_to_save, user_id))
    db.commit()

    if cursor.rowcount == 0:
        db.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found to update"
        )

    db.close()
    return {"message": "WhatsApp number updated successfully"}
