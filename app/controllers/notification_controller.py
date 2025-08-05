from fastapi import APIRouter, Request, Depends, HTTPException
from typing import Annotated
from app.db.connection import get_db
from app.db.queries.notification_queries import (
    GET_UNREAD_NOTIFICATIONS_BY_CLIENT_ID,
    MARK_NOTIFICATION_AS_READ,
    DELETE_NOTIFICATION_BY_ID
)

router = APIRouter()

@router.get("/")
def get_notifications(request: Request, db: Annotated = Depends(get_db)):
    user = request.state.user
    role = user.get("role")
    client_id = user.get("clientId")

    if role == 'admin':
        return {"notifications": []}

    if not client_id:
        raise HTTPException(status_code=403, detail="User is not associated with a client.")

    cursor = db.cursor()
    cursor.execute(GET_UNREAD_NOTIFICATIONS_BY_CLIENT_ID, (client_id,))
    notifications = [{"id": row[0], "message": row[1], "createdAt": row[2].strftime("%Y-%m-%d %H:%M:%S")} for row in cursor.fetchall()]
    db.close()
    return {"notifications": notifications}

@router.post("/{notification_id}/read")
def mark_as_read(notification_id: int, request: Request, db: Annotated = Depends(get_db)):
    user = request.state.user
    role = user.get("role")
    client_id = user.get("clientId")

    if role == 'admin':
        return {"message": "No action required for admin."}

    if not client_id:
        raise HTTPException(status_code=403, detail="User is not associated with a client.")
    
    cursor = db.cursor()
    cursor.execute(MARK_NOTIFICATION_AS_READ, (notification_id, client_id))
    db.commit()

    if cursor.rowcount == 0:
        db.close()
        raise HTTPException(status_code=404, detail="Notification not found or you do not have permission to read it.")
    
    db.close()
    return {"message": f"Notification {notification_id} marked as read."}

@router.delete("/{notification_id}")
def delete_notification(notification_id: int, request: Request, db: Annotated = Depends(get_db)):
    user = request.state.user
    role = user.get("role")
    client_id = user.get("clientId")

    if role == 'admin':
        return {"message": "No action required for admin."}

    if not client_id:
        raise HTTPException(status_code=403, detail="User is not associated with a client.")

    cursor = db.cursor()
    cursor.execute(DELETE_NOTIFICATION_BY_ID, (notification_id, client_id))
    db.commit()

    if cursor.rowcount == 0:
        db.close()
        raise HTTPException(status_code=404, detail="Notification not found or you do not have permission to delete it.")

    db.close()
    return {"message": f"Notification {notification_id} has been deleted."}