from fastapi import APIRouter, Request, Depends, HTTPException
from typing import Annotated, Optional
from app.db.connection import get_db
from pydantic import BaseModel
from app.db.queries.admin_queries import (
    GET_ALL_CLIENT_NAMES,
    GET_ALL_USERS_INFO,
    DELETE_USER_BY_ID,
    CHECK_USER_EXISTS_BY_ID,
    UPDATE_USER_CLIENT_ID,
)
from app.db.queries.gw_contracts_queries import GET_ALL_GW_CLIENTS

router = APIRouter()


class UpdateUserClientSchema(BaseModel):
    clientId: Optional[int]


@router.get("/clients")
def get_all_clients(request: Request, db: Annotated = Depends(get_db)):
    if request.state.user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()
    cursor.execute(GET_ALL_CLIENT_NAMES)
    results = cursor.fetchall()

    clients = [{"id": row[0], "name": row[1]} for row in results]
    return {"clients": clients}


@router.get("/gw-clients")
def get_all_gw_clients(request: Request, db: Annotated = Depends(get_db)):
    if request.state.user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()
    cursor.execute(GET_ALL_GW_CLIENTS)
    results = cursor.fetchall()
    db.close()

    clients = [{"id": row[0], "name": row[1]} for row in results]
    return {"clients": clients}


@router.get("/users")
def get_all_users(request: Request, db: Annotated = Depends(get_db)):
    role = request.state.user.get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()
    cursor.execute(GET_ALL_USERS_INFO)
    results = cursor.fetchall()

    users = []
    for row in results:
        id, email, role, client_name, is_password_set, created_at = row
        users.append(
            {
                "id": id,
                "email": email,
                "role": role,
                "client": client_name or "-",
                "status": "Aktif" if is_password_set else "Nonaktif",
                "createdAt": created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return {"users": users}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, request: Request, db: Annotated = Depends(get_db)):
    role = request.state.user.get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()
    cursor.execute(CHECK_USER_EXISTS_BY_ID, (user_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    cursor.execute(DELETE_USER_BY_ID, (user_id,))
    db.commit()

    return {"message": f"User with ID {user_id} has been deleted successfully."}


@router.patch("/users/{user_id}")
def update_user_client_id(
    user_id: int,
    payload: UpdateUserClientSchema,
    request: Request,
    db: Annotated = Depends(get_db),
):
    role = request.state.user.get("role")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Access denied")

    cursor = db.cursor()

    cursor.execute(CHECK_USER_EXISTS_BY_ID, (user_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="User not found")

    cursor.execute(UPDATE_USER_CLIENT_ID, (payload.clientId, user_id))
    db.commit()

    return {"message": "ClientId updated successfully", "clientId": payload.clientId}
