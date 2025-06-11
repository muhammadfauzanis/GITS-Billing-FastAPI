# controller backend saya

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
# Remove bcrypt, it's not needed
# import bcrypt
from typing import Annotated, Optional

from app.db.connection import get_db
from app.db.queries.auth_queries import (
    check_user_exists_query,
    # Modify your insert query
    insert_user_query,
    get_user_by_email_query,
    # This is no longer needed if Supabase handles passwords
    # UPDATE_USER_PASSWORD
)
from app.middleware.auth_middleware import supabase

router = APIRouter()

# You can remove the hash_password function completely.

class RegisterSchema(BaseModel):
    email: str
    password: Optional[str] = None
    role: str
    clientId: Optional[str] = None

class UpdateStatusPayload(BaseModel):
    userId: str 

@router.post("/register")
def register_user(
    payload: RegisterSchema,
    db: Annotated = Depends(get_db)
):
    email = payload.email
    password = payload.password
    role = payload.role.lower()
    client_id = payload.clientId

    # ... (validasi role dan pengecekan user tetap sama)

    try:
        new_user = None
        
        # Untuk alur ini, kita asumsikan admin harus membuat password sementara
        if not password or len(password) < 6:
            raise HTTPException(status_code=400, detail="Admin harus mengatur password sementara minimal 6 karakter.")
            
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
        
        # --- INI ADALAH PERUBAHAN UTAMA ---
        # Kita atur 'is_password_set' menjadi FALSE secara manual.
        # Ini akan memaksa pengguna untuk mengunjungi halaman /set-password
        # saat mereka login pertama kali dengan password sementara dari admin.
        is_password_set_for_db = False

        # Query INSERT Anda (pastikan tidak ada kolom 'password' lagi)
        # INSERT INTO users (email, client_id, role, is_password_set, supabase_auth_id) VALUES (%s, %s, %s, %s, %s)
        cursor = db.cursor()
        cursor.execute(
            insert_user_query, 
            (email, client_id, role, is_password_set_for_db, supabase_id)
        )
        db.commit()

        return {"message": "User created with a temporary password. They will be required to set a new password on first login."}

    except Exception as e:
        # ... (error handling tetap sama)
        db.rollback()
        error_message = str(e)
        if "User already registered" in error_message:
            raise HTTPException(status_code=409, detail="User with this email already exists in Supabase.")
        
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {error_message}")

@router.patch("/update-password-status")
def update_password_status(
    payload: UpdateStatusPayload, # <-- Menerima payload dari frontend
    db: Annotated = Depends(get_db)
):
    """
    Endpoint ini dipanggil setelah pengguna berhasil mengatur password baru.
    Tugasnya adalah mengubah flag is_password_set menjadi TRUE.
    """
    user_id = payload.userId # <-- Mengambil user_id dari body payload

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required.")

    try:
        cursor = db.cursor()
        # Query untuk mengupdate flag berdasarkan supabase_auth_id
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