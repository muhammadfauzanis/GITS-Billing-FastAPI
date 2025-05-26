from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi import status
from jose import jwt, JWTError
import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET")
ALGORITHM = "HS256"

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        public_paths = ["/api/auth/login", "/api/auth/register", "/docs", "/openapi.json"]

        if request.method == "OPTIONS":
            return Response(status_code=200)

        if request.url.path in public_paths:
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        token = auth_header.split(" ")[1] if auth_header and " " in auth_header else None

        if not token:
            return Response(
                content='{"message": "Authentication token required"}',
                status_code=status.HTTP_401_UNAUTHORIZED,
                media_type="application/json"
            )

        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            request.state.user = {
                "id": payload.get("userId"),
                "username": payload.get("username"),
                "clientId": payload.get("clientId")
            }
        except JWTError:
            return Response(
                content='{"message": "Invalid or expired token"}',
                status_code=status.HTTP_403_FORBIDDEN,
                media_type="application/json"
            )

        return await call_next(request)
