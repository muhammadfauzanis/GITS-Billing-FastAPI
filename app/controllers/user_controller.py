from fastapi import APIRouter, Request, Depends, HTTPException
from typing import Annotated
from app.db.connection import get_db
from app.db.queries.user_queries import GET_CLIENT_NAME_BY_ID

router = APIRouter()

@router.get("/client-name")
def get_client_name(request: Request, db: Annotated = Depends(get_db)):
    client_id = request.state.user.get("clientId")
    
    if not client_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    cursor = db.cursor()
    cursor.execute(GET_CLIENT_NAME_BY_ID, (client_id,))
    result = cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Client not found")

    return {"clientId": client_id, "name": result[0]}
