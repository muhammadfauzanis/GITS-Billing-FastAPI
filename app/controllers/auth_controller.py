from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from typing import Annotated, Optional

from app.db.connection import get_db
from app.db.queries.auth_queries import (
    check_user_exists_query,
    insert_user_query
)
from app.middleware.auth_middleware import supabase

router = APIRouter()

class RegisterSchema(BaseModel):
    email: str
    password: Optional[str] = None
    role: str
    clientId: Optional[str] = None

@router.post("/register")
def register_user(
    payload: RegisterSchema,
    db: Annotated = Depends(get_db)
):
    email = payload.email
    password = payload.password
    role = payload.role.lower()
    client_id = payload.clientId

    if role not in ["admin", "client"]:
        raise HTTPException(status_code=400, detail="Invalid role. Must be 'admin' or 'client'")

    cursor = db.cursor()
    cursor.execute(check_user_exists_query, (email,))
    if cursor.fetchone():
        raise HTTPException(status_code=409, detail="Email already exists in the application database")

    try:
        # Alur 1: Pendaftaran dengan password sementara
        if password:
            if len(password) < 6:
                raise HTTPException(status_code=400, detail="Admin must set an initial password of at least 6 characters.")
            
            user_attributes = {
                "email": email,
                "password": password,
                "email_confirm": True
            }
            response = supabase.auth.admin.create_user(user_attributes)
            new_user = response.user

            if not new_user:
                raise HTTPException(status_code=500, detail="Failed to create user in Supabase.")

            supabase_id = new_user.id
            is_password_set_for_db = False

            cursor.execute(
                insert_user_query, 
                (email, client_id, role, is_password_set_for_db, supabase_id)
            )
            db.commit()
            return {"message": "User created with a temporary password."}

        # Alur 2: Pra-pendaftaran akun Google (tanpa password)
        else:
            supabase_id = None
            is_password_set_for_db = True

            cursor.execute(
                insert_user_query, 
                (email, client_id, role, is_password_set_for_db, supabase_id)
            )
            db.commit()
            return {"message": "Google user pre-registered successfully."}

    except Exception as e:
        db.rollback()
        error_message = str(e)
        if "User already registered" in error_message:
            raise HTTPException(status_code=409, detail="User with this email already exists in Supabase.")
        
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {error_message}")


@router.patch("/update-password-status")
def update_password_status(
    request: Request, 
    db: Annotated = Depends(get_db)
):
    user_id = request.state.user.get("sub") 

    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication token is invalid or missing user ID.")

    try:
        cursor = db.cursor()
        cursor.execute(
            "UPDATE users SET is_password_set = TRUE WHERE supabase_auth_id = %s",
            (user_id,)
        )
        
        if cursor.rowcount == 0:
            db.rollback()
            raise HTTPException(status_code=404, detail="User profile not found in database to update status.")

        db.commit()
        return {"message": "User password status updated successfully."}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")