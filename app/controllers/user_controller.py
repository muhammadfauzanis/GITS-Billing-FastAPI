from fastapi import APIRouter, Request, Depends, HTTPException, Query
from typing import Annotated, Optional
from app.db.connection import get_db
from app.db.queries.user_queries import GET_CLIENT_NAME_BY_ID

router = APIRouter()

@router.get("/client-name")
def get_client_name(
    request: Request, 
    db: Annotated = Depends(get_db),
    clientId: Optional[str] = Query(None) 
):
    user_details = request.state.user
    user_role = user_details.get("role")
    
    target_client_id = None
    
    if user_role == "admin":
        if not clientId:
            raise HTTPException(status_code=400, detail="Admin must provide a clientId.")
        target_client_id = clientId
    else: 
        target_client_id = user_details.get("clientId")

    if not target_client_id:
        raise HTTPException(status_code=401, detail="Unauthorized or Client ID not specified.")

    cursor = db.cursor()
    cursor.execute(GET_CLIENT_NAME_BY_ID, (target_client_id,))
    result = cursor.fetchone()
    db.close()

    if not result:
        raise HTTPException(status_code=404, detail="Client not found")

    return {"clientId": target_client_id, "name": result[0]}