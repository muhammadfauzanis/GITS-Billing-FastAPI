# app/middleware/auth_middleware.py

import os
from dotenv import load_dotenv
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import status, HTTPException
from supabase import create_client, Client

# Impor koneksi database Anda
from app.db.connection import get_db

load_dotenv()

# Inisialisasi Klien Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise Exception("Supabase URL and Service Key must be set in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Path publik tidak memerlukan otentikasi
        public_paths = ["/api/auth/login", "/api/auth/register", "/docs", "/openapi.json", "/redoc"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        if request.method == "OPTIONS":
            return Response(status_code=status.HTTP_200_OK)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return Response(
                content='{"message": "Authentication token required"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )

        token = auth_header.split(" ")[1]
        db_conn = None
        try:
            # 1. Verifikasi token menggunakan Supabase
            user_response = supabase.auth.get_user(token)
            supabase_user = user_response.user
            
            if not supabase_user:
                raise HTTPException(status_code=403, detail="Invalid or expired token")

            # 2. Ambil detail pengguna (role, clientId) dari database Anda
            # Middleware tidak mendukung Depends(), jadi kita buat koneksi manual
            db_conn = get_db()
            cursor = db_conn.cursor()
            
            # Gunakan email dari token Supabase untuk mencari user di tabel 'users' Anda
            cursor.execute(
                "SELECT id, role, client_id FROM users WHERE email = %s", 
                (supabase_user.email,)
            )
            app_user = cursor.fetchone()

            if not app_user:
                raise HTTPException(status_code=404, detail="User not found in application database")

            user_id, user_role, user_client_id = app_user

            # 3. Tetapkan state pengguna seperti sebelumnya
            request.state.user = {
                "id": user_id,
                "username": supabase_user.email,
                "clientId": user_client_id,
                "role": user_role
            }

        except HTTPException as e:
            return Response(
                content=f'{{"message": "{e.detail}"}}',
                status_code=e.status_code,
                media_type="application/json"
            )
        except Exception as e:
            # Tangani error lain, misal koneksi database gagal
            return Response(
                content=f'{{"message": "Authentication failed: {str(e)}"}}',
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                media_type="application/json"
            )
        finally:
            # Pastikan koneksi database selalu ditutup
            if db_conn:
                db_conn.close()

        return await call_next(request)