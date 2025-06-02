from jose import jwt
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

def generate_token(user_id: int, name: str, client_id: int, role: str) -> str:
    if not JWT_SECRET:
        raise Exception("JWT_SECRET is not defined in environment variables")

    token_data = {
        "userId": user_id,
        "name": name,
        "clientId": client_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=15)
    }

    token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return token
