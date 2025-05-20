from fastapi import Response
from jose import jwt
import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")

def generate_token_and_set_cookie(user_id: int, name: str, client_id: int, response: Response):
    if not JWT_SECRET:
        raise Exception("JWT_SECRET is not defined in environment variables")

    token_data = {
        "userId": user_id,
        "name": name,
        "clientId": client_id,
    }

    token = jwt.encode(token_data, JWT_SECRET, algorithm="HS256")

    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        max_age=15 * 24 * 60 * 60,  # 15 days in seconds
    )

    return token
