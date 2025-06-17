from fastapi import APIRouter, HTTPException, Depends, Request, Query
from pydantic import BaseModel
from typing import Annotated, Optional
from datetime import datetime
import os
import requests

from app.db.connection import get_db
from app.db.queries.auth_queries import (
    CHECK_USER_EXIST,
    INSERT_USER_QUERY
)
from app.middleware.auth_middleware import supabase

router = APIRouter()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

class RegisterSchema(BaseModel):
    email: str
    password: Optional[str] = None
    role: str
    clientId: Optional[str] = None

def get_supabase_user_by_email(email: str):
    url = f"{SUPABASE_URL}/auth/v1/admin/users?email={email}"
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
    }

    print("[DEBUG] Mengirim request ke Supabase Admin API...")
    print("[DEBUG] URL:", url)
    print("[DEBUG] Headers:", headers)

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print("[DEBUG] Status Code:", response.status_code)
        print("[DEBUG] Response Text:", response.text)

        if response.status_code == 200:
            data = response.json()
            users = data.get("users", [])
            print("[DEBUG] Ditemukan users:", users)
            return users[0] if users else None
        else:
            raise Exception(f"Failed to fetch Supabase user: {response.status_code} {response.text}")
    except requests.exceptions.RequestException as e:
        print("[ERROR] Network error saat request ke Supabase:", str(e))
        raise Exception("Gagal menghubungi Supabase Admin API (network error)")


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
    cursor.execute(CHECK_USER_EXIST, (email,))
    if cursor.fetchone():
        raise HTTPException(status_code=409, detail="Email already exists in the application database")

    try:
        if password:
            if len(password) < 6:
                raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

            from supabase import create_client, Client
            supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
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

        else:
            existing_user = get_supabase_user_by_email(email)

            if not existing_user:
                raise HTTPException(status_code=404, detail="Email belum pernah login dengan Google")

            supabase_id = existing_user["id"]
            is_password_set_for_db = True

        cursor.execute(
            INSERT_USER_QUERY,
            (email, client_id, role, is_password_set_for_db, supabase_id)
        )
        db.commit()

        return {"message": "User successfully registered."}

    except Exception as e:
        db.rollback()
        error_message = str(e)

        if "User already registered" in error_message:
            raise HTTPException(status_code=409, detail="User already exists in Supabase.")

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