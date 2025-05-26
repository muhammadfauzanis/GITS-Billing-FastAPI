from fastapi import Response
from jose import jwt
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

def generate_token_and_set_cookie(
    user_id: int, 
    name: str, 
    client_id: int, 
    role: str, 
    response: Response
):
    if not JWT_SECRET:
        raise Exception("JWT_SECRET is not defined in environment variables")
    
    token_data = {
        "userId": user_id,
        "name": name,
        "clientId": client_id,
        "role": role,
    }

    token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)

    max_age_seconds = 15 * 24 * 60 * 60

    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        max_age=max_age_seconds,
        expires=max_age_seconds,
        path="/",
        samesite="none",  
        secure=False     
    ) 

    return token