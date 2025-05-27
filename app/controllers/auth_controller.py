from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel
from app.db.connection import get_db
from app.utils.token import generate_token
from app.db.queries.auth_queries import (
    check_user_exists_query,
    insert_user_query,
    get_user_by_email_query
)
import bcrypt
from typing import Annotated

router = APIRouter()

# --- Password Hashing Helpers ---
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

# --- Pydantic Schemas ---
class RegisterSchema(BaseModel):
    email: str
    password: str
    clientId: str

class LoginSchema(BaseModel):
    email: str
    password: str

class PasswordSchema(BaseModel):
    email: str
    password: str
    repassword: str

# --- Endpoints ---
@router.post("/register")
def register_user(
    payload: RegisterSchema,
    response: Response,
    db: Annotated = Depends(get_db)
):
    email = payload.email
    password = payload.password
    client_id = payload.clientId

    cursor = db.cursor()
    cursor.execute(check_user_exists_query, (email,))
    if cursor.fetchone():
        raise HTTPException(status_code=409, detail="Email already exists")

    hashed = hash_password(password)
    cursor.execute(insert_user_query, (email, hashed, client_id))
    db.commit()

    return {"message": "User registered successfully"}

@router.post("/login")
def user_login(
    payload: LoginSchema,
    response: Response,
    db: Annotated = Depends(get_db)
):
    email = payload.email
    password = payload.password

    cursor = db.cursor()
    cursor.execute(get_user_by_email_query, (email,))
    user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_id, user_email, user_password, role, client_id, is_password_set = user

    if not verify_password(password, user_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = generate_token(
        user_id=user_id,
        name=user_email,
        role=role,
        client_id=client_id,
    )

    return {
        "message": "Login successful",
        "token": token,
        "user": {
            "id": user_id,
            "email": user_email,
            "clientId": client_id,
            "role": role,
            "isPasswordSet": is_password_set,
        },
    }

@router.post("/logout")
def user_logout(response: Response):
    response.delete_cookie("token")
    return {"message": "Logout successfully"}

@router.post("/set-password")
def set_new_password(
    payload: PasswordSchema,
    db: Annotated = Depends(get_db)
):
    email = payload.email
    password = payload.password
    repassword = payload.repassword

    if password != repassword:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    cursor = db.cursor()
    cursor.execute(get_user_by_email_query, (email,))
    user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user[5]:  # is_password_set
        raise HTTPException(status_code=400, detail="Password already set")

    hashed = hash_password(password)
    cursor.execute(
        "UPDATE users SET password = %s, is_password_set = true WHERE email = %s",
        (hashed, email),
    )
    db.commit()

    return {"message": "Password has been set successfully"}
